#!/usr/bin/env python3
"""ENF-R3A external adapter for safe-control-gym.

This file is intentionally not a replacement simulator. It runs only when the
pinned public safe-control-gym checkout and dependencies are present.

Primary comparison:
  shared disturbed observation -> CBF
  independent env.state -> same CBF

Secondary comparison:
  current constraint spec -> CBF
  stale permissive constraint spec -> same CBF, evaluated against current truth
"""
from __future__ import annotations
import argparse, copy, importlib.util, json, os, sys
from functools import partial
from pathlib import Path

PINNED_COMMIT="6b5391d014f36fdfa0f9d22d92c77387e5274308"
REQUIRED=("safe_control_gym","pybullet","pybullet_data","gymnasium","casadi","numpy","torch")
NOISE_LEVELS=(0.0,0.10,0.50,1.00)

TASK_CONFIG={
    "seed":42,"ctrl_freq":25,"pyb_freq":1000,"cost":"quadratic","task":"stabilization",
    "task_info":{"stabilization_goal":[0,0],"stabilization_goal_tolerance":0.05},
    "init_state":{"init_x":0.4,"init_x_dot":-0.4,"init_theta":-0.18,"init_theta_dot":-0.4},
    "randomized_init":False,
    "constraints":[
        {"constraint_form":"default_constraint","constrained_variable":"state",
         "upper_bounds":[2,2,0.2,2],"lower_bounds":[-2,-2,-0.2,-2]},
        {"constraint_form":"default_constraint","constrained_variable":"input"},
    ],
    "done_on_out_of_bound":True,"done_on_violation":False,
}
PPO_CONFIG={
    "hidden_dim":64,"activation":"tanh","norm_obs":False,"norm_reward":False,"clip_obs":10.0,"clip_reward":10.0,
    "gamma":0.99,"use_gae":True,"gae_lambda":0.95,"use_clipped_value":False,"clip_param":0.2,"target_kl":0.01,
    "entropy_coef":0.01,"opt_epochs":10,"mini_batch_size":64,"actor_lr":0.0003,"critic_lr":0.001,"max_grad_norm":0.5,
    "max_env_steps":100000,"num_workers":1,"rollout_batch_size":4,"rollout_steps":100,"deque_size":10,"eval_batch_size":10,
    "log_interval":1000,"save_interval":1000,"num_checkpoints":0,"eval_interval":1000,"eval_save_best":True,"tensorboard":False,
}
CBF_CONFIG={"slope":0.1,"soft_constrained":True,"slack_weight":10000.0,"slack_tolerance":1e-3,
            "prior_info":{"prior_prop":None,"randomize_prior_prop":False,"prior_prop_rand_info":None}}

def preflight(repo_root:Path):
    missing=[m for m in REQUIRED if importlib.util.find_spec(m) is None]
    model=repo_root/'examples/cbf/models/ppo_model_cartpole.pt'
    return {"pinned_commit":PINNED_COMMIT,"repo_root":str(repo_root),"missing_modules":missing,
            "model_exists":model.exists(),"ready":not missing and model.exists()}

def build_task(noise_std:float, theta_limit:float=0.2):
    cfg=copy.deepcopy(TASK_CONFIG)
    cfg["constraints"][0]["upper_bounds"][2]=float(theta_limit)
    cfg["constraints"][0]["lower_bounds"][2]=-float(theta_limit)
    if noise_std>0:
        cfg["disturbances"]={"observation":[{"disturbance_func":"white_noise","std":float(noise_std)}]}
    return cfg

def current_truth_violation(state, physical_action):
    # Narrow R3A truth predicate uses the same official CartPole state/input bounds
    # frozen in examples/cbf/config_overrides/cartpole_config.yaml.
    import numpy as np
    s=np.asarray(state,float); a=np.atleast_1d(np.asarray(physical_action,float))
    ub=np.array([2.,2.,0.2,2.]); lb=-ub
    return bool((s>ub).any() or (s<lb).any() or (abs(a)>10.0).any())

def run_arm(repo_root:Path, arm:str, noise_std:float, theta_limit:float, seeds:list[int], fail_closed:bool=False):
    import numpy as np
    from safe_control_gym.utils.registration import make
    task_cfg=build_task(noise_std,theta_limit=0.2)  # evaluation plant always current truth spec
    env_func=partial(make,'cartpole',**task_cfg)
    env=env_func()
    ctrl=make('ppo',env_func,**PPO_CONFIG,output_dir=str(repo_root/'examples/cbf/temp-logos-enf-r3'))
    ctrl.load(str(repo_root/'examples/cbf/models/ppo_model_cartpole.pt'))

    # Certification model may use current or stale permissive spec.
    cert_cfg=build_task(noise_std=0.0,theta_limit=theta_limit)
    cert_env_func=partial(make,'cartpole',**cert_cfg)
    sf=make('cbf',cert_env_func,**CBF_CONFIG,output_dir=str(repo_root/'examples/cbf/temp-logos-enf-r3'))
    sf.reset()
    rows=[]
    try:
        for seed in seeds:
            obs,info=env.reset(seed=seed)
            ctrl.reset_before_run(obs,info,env=env); sf.reset_before_run(env=env)
            done=False; step=0
            while not done:
                proposal=ctrl.select_action(obs,info)
                physical=env.denormalize_action(proposal)
                cert_success=True; correction=0.0
                if arm!='NO_FILTER':
                    if arm in {'CBF_SHARED_OBS','CBF_STALE_SHARED_OBS'}:
                        cert_state=np.asarray(obs[:env.symbolic.nx],float)
                    else:
                        cert_state=np.asarray(env.state,float).copy()
                    certified,cert_success=sf.certify_action(cert_state,physical,info)
                    correction=float(np.linalg.norm(np.atleast_1d(certified)-np.atleast_1d(physical)))
                    if cert_success:
                        proposal=env.normalize_action(certified)
                    elif fail_closed:
                        proposal=env.normalize_action(np.zeros_like(np.atleast_1d(physical)))
                before_state=np.asarray(env.state,float).copy()
                obs,reward,done,info=env.step(proposal)
                executed=np.asarray(env.current_clipped_action,float).copy()
                rows.append({"arm":arm,"noise_std":noise_std,"theta_limit":theta_limit,"seed":seed,"step":step,
                             "constraint_violation":int(info.get('constraint_violation',0)),
                             "truth_violation":int(current_truth_violation(env.state,executed)),
                             "cert_success":int(bool(cert_success)),"correction":correction,
                             "reward":float(reward),"state_error_l2":float(np.linalg.norm(np.asarray(env.state)-np.asarray(env.X_GOAL))),
                             "executed_action_l2":float(np.linalg.norm(executed))})
                step+=1
    finally:
        try: ctrl.close()
        except Exception: pass
        try: sf.close()
        except Exception: pass
        try: env.close()
        except Exception: pass
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,required=True)
    ap.add_argument('--preflight',action='store_true')
    ap.add_argument('--episodes',type=int,default=50)
    ap.add_argument('--seed-start',type=int,default=73000)
    ap.add_argument('--output',type=Path,default=Path('enf-r3-results.jsonl'))
    args=ap.parse_args()
    pf=preflight(args.repo_root)
    if args.preflight or not pf['ready']:
        print(json.dumps(pf,indent=2)); return 0 if pf['ready'] else 2
    seeds=list(range(args.seed_start,args.seed_start+args.episodes))
    rows=[]
    for noise in NOISE_LEVELS:
        rows += run_arm(args.repo_root,'NO_FILTER',noise,0.2,seeds)
        rows += run_arm(args.repo_root,'CBF_SHARED_OBS',noise,0.2,seeds)
        rows += run_arm(args.repo_root,'CBF_INDEPENDENT_STATE',noise,0.2,seeds)
    # External specification attack: same independent evidence, permissive CBF specification.
    rows += run_arm(args.repo_root,'CBF_INDEPENDENT_STATE',0.0,0.2,seeds)
    rows += run_arm(args.repo_root,'CBF_INDEPENDENT_STALE_SPEC',0.0,0.4,seeds)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w') as f:
        for r in rows: f.write(json.dumps(r)+'\n')
    print(json.dumps({"status":"EXECUTED","rows":len(rows),"output":str(args.output)},indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
