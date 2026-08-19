#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, re, hashlib
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction import DictVectorizer

SEED=260818
REQUIRED_COLUMNS={
    'doc_id','modality','model','model_family','training_type','benchmark','correct',
    'question','model_cot','evaluation','source_file'
}
FORBIDDEN_ONLINE={
    'correct','ground_truth','exact_match','math_verify','evaluator_notes',
    'reaches_correct_conclusion','logical_steps_valid','confidence_calibration',
    'knowledge_alignment','self_awareness','failure_modes'
}
SURFACE_PATTERNS={
    'self_correction':[re.compile(r'\bwait\b',re.I),re.compile(r'\blet me (?:rethink|check|reconsider|try again)\b',re.I),re.compile(r'\bi (?:was|am) wrong\b',re.I),re.compile(r'\bcorrection\b',re.I)],
    'uncertainty':[re.compile(r'\bnot sure\b',re.I),re.compile(r'\buncertain\b',re.I),re.compile(r'\bmaybe\b',re.I),re.compile(r'\bperhaps\b',re.I),re.compile(r'\bi think\b',re.I),re.compile(r'\bprobably\b',re.I),re.compile(r'\bconfidence\b',re.I)],
    'hypothesis_testing':[re.compile(r'\bif\b.{0,80}\bthen\b',re.I|re.S),re.compile(r'\balternative\b',re.I),re.compile(r'\bsuppose\b',re.I),re.compile(r'\bhypothesis\b',re.I),re.compile(r'\bcase \d+\b',re.I)]
}

def file_sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def parse_eval(s):
    if isinstance(s,dict): return s
    try:return json.loads(s)
    except Exception:return {}

def surface_row(text):
    t=str(text or '')
    out={k:sum(len(p.findall(t)) for p in pats) for k,pats in SURFACE_PATTERNS.items()}
    out['trace_words']=len(t.split());out['trace_chars']=len(t)
    return out

def ece(y,p,bins=10):
    y=np.asarray(y,float);p=np.asarray(p,float);edges=np.linspace(0,1,bins+1);out=0.0
    for i in range(bins):
        m=(p>=edges[i])&(p<=edges[i+1] if i==bins-1 else p<edges[i+1])
        if m.any():out+=m.mean()*abs(y[m].mean()-p[m].mean())
    return float(out)

def selective_risk(y,p,coverage):
    y=np.asarray(y,int);p=np.asarray(p,float);conf=np.maximum(p,1-p);n=max(1,int(round(len(y)*coverage)));idx=np.argsort(-conf)[:n]
    return float(np.mean((p[idx]>=.5).astype(int)!=y[idx]))

def abstention_utility(y,p,cost=.1,threshold=.6):
    y=np.asarray(y,int);p=np.asarray(p,float);conf=np.maximum(p,1-p);accept=conf>=threshold;pred=(p>=.5).astype(int)
    return float((((pred==y)&accept).sum()-((pred!=y)&accept).sum()-cost*(~accept).sum())/len(y))

def metrics(y,p):
    y=np.asarray(y,int);p=np.clip(np.asarray(p,float),1e-6,1-1e-6)
    out={'n':int(len(y)),'accuracy_at_0p5':float(np.mean((p>=.5)==y)),'brier':float(brier_score_loss(y,p)),'ece_10':ece(y,p),'log_loss':float(log_loss(y,p,labels=[0,1])),'selective_risk_50':selective_risk(y,p,.5),'selective_risk_70':selective_risk(y,p,.7),'selective_risk_90':selective_risk(y,p,.9),'decision_utility_abstention_0p1':abstention_utility(y,p)}
    if len(set(y))==2:
        out['roc_auc_correct']=float(roc_auc_score(y,p));out['roc_auc_failure']=float(roc_auc_score(1-y,1-p))
    else:out['roc_auc_correct']=out['roc_auc_failure']=None
    return out

def load_data(args):
    supplied=[args.input_parquet,args.input_jsonl,args.input_csv]
    if sum(x is not None for x in supplied)>1:raise ValueError('choose only one local input format')
    if args.input_parquet:
        p=Path(args.input_parquet);return pd.read_parquet(p),{'mode':'local_parquet','path':str(p),'sha256':file_sha256(p)}
    if args.input_jsonl:
        p=Path(args.input_jsonl);return pd.read_json(p,lines=True),{'mode':'local_jsonl','path':str(p),'sha256':file_sha256(p)}
    if args.input_csv:
        p=Path(args.input_csv);return pd.read_csv(p),{'mode':'local_csv','path':str(p),'sha256':file_sha256(p)}
    try:from datasets import load_dataset
    except ImportError as e:raise RuntimeError('Install datasets or pass --input-parquet/--input-jsonl') from e
    ds=load_dataset(args.dataset)
    return ds['llm'].to_pandas(),{'mode':'huggingface','dataset':args.dataset,'split':'llm','sha256':'provider-managed-not-local-file'}

def validate_raw(df,args):
    missing=sorted(REQUIRED_COLUMNS-set(df.columns))
    if missing:raise RuntimeError(f'missing required columns: {missing}')
    if not args.smoke and len(df)!=8282:raise RuntimeError(f'expected 8282 llm rows, got {len(df)}')
    if set(df.modality.astype(str).unique())!={'llm'}:raise RuntimeError('primary executor accepts llm modality only')
    if df.correct.isna().any():raise RuntimeError('correct contains nulls')
    return {'rows':int(len(df)),'columns':list(df.columns),'models':sorted(df.model.astype(str).unique()),'model_families':sorted(df.model_family.astype(str).unique()),'training_types':sorted(df.training_type.astype(str).unique()),'benchmarks':sorted(df.benchmark.astype(str).unique())}

def prepare(df):
    df=df.copy();df['correct']=df.correct.astype(int);df['item_key']=df.benchmark.astype(str)+'::'+df.doc_id.astype(str)
    surf=[surface_row(x) for x in df.model_cot]
    for k in surf[0]:df['surface_'+k]=[r[k] for r in surf]
    ann=[parse_eval(x) for x in df.evaluation]
    keys=['self_correction','hypothesis_testing','uncertainty_acknowledgment','confidence_calibration','self_awareness','knowledge_alignment']
    for key in keys:
        df['ann_'+key]=[int(bool(a.get('advanced_and_metacognitive',{}).get(key,False))) for a in ann]
    # outcome-semantic fields remain descriptive-only and are never used by any fit_* function.
    return df

def group_history_prob(train,test):
    gp=float(train.correct.mean());alpha=20.0
    mb=train.groupby(['model','benchmark']).correct.agg(['mean','count']);m=train.groupby('model').correct.agg(['mean','count']);b=train.groupby('benchmark').correct.agg(['mean','count'])
    out=[]
    for _,r in test.iterrows():
        key=(r.model,r.benchmark)
        st=None
        if key in mb.index:st=mb.loc[key]
        elif r.model in m.index:st=m.loc[r.model]
        elif r.benchmark in b.index:st=b.loc[r.benchmark]
        if st is None:out.append(gp)
        else:out.append((float(st['mean'])*float(st['count'])+gp*alpha)/(float(st['count'])+alpha))
    return np.asarray(out)

def item_history_prob(train,test):
    gp=float(train.correct.mean());alpha=8.0;st=train.groupby('item_key').correct.agg(['mean','count']);out=[]
    for key in test.item_key:
        if key in st.index:
            r=st.loc[key];out.append((float(r['mean'])*float(r['count'])+gp*alpha)/(float(r['count'])+alpha))
        else:out.append(gp)
    return np.asarray(out)

def lr_bal():return LogisticRegression(max_iter=2000,class_weight='balanced',random_state=SEED)

def fit_surface(train,test):
    cols=['surface_self_correction','surface_uncertainty','surface_hypothesis_testing','surface_trace_words','surface_trace_chars'];sc=StandardScaler();Xtr=sc.fit_transform(train[cols].astype(float));Xte=sc.transform(test[cols].astype(float));clf=lr_bal();clf.fit(Xtr,train.correct);return clf.predict_proba(Xte)[:,1]

def fit_annotation_surface(train,test):
    cols=['ann_self_correction','ann_hypothesis_testing','ann_uncertainty_acknowledgment'];clf=lr_bal();clf.fit(train[cols],train.correct);return clf.predict_proba(test[cols])[:,1]

def fit_input_only(train,test):
    v=TfidfVectorizer(min_df=3,max_features=12000,ngram_range=(1,2),sublinear_tf=True);X=v.fit_transform(train.question.astype(str));Xt=v.transform(test.question.astype(str));clf=lr_bal();clf.fit(X,train.correct);return clf.predict_proba(Xt)[:,1]

def _meta_sparse(train,test):
    cols=['benchmark','training_type','model_family'];enc=OneHotEncoder(handle_unknown='ignore');return enc.fit_transform(train[cols]),enc.transform(test[cols])

def fit_trace(train,test):
    v=TfidfVectorizer(min_df=3,max_features=20000,ngram_range=(1,2),sublinear_tf=True);X=v.fit_transform(train.model_cot.astype(str));Xt=v.transform(test.model_cot.astype(str));M,Mt=_meta_sparse(train,test);clf=lr_bal();clf.fit(hstack([X,M]).tocsr(),train.correct);return clf.predict_proba(hstack([Xt,Mt]).tocsr())[:,1]

def fit_input_surface(train,test):
    v=TfidfVectorizer(min_df=3,max_features=12000,ngram_range=(1,2),sublinear_tf=True);Q=v.fit_transform(train.question.astype(str));Qt=v.transform(test.question.astype(str));cols=['surface_self_correction','surface_uncertainty','surface_hypothesis_testing','surface_trace_words','surface_trace_chars'];sc=StandardScaler();N=csr_matrix(sc.fit_transform(train[cols].astype(float)));Nt=csr_matrix(sc.transform(test[cols].astype(float)));M,Mt=_meta_sparse(train,test);clf=lr_bal();clf.fit(hstack([Q,N,M]).tocsr(),train.correct);return clf.predict_proba(hstack([Qt,Nt,Mt]).tocsr())[:,1]

def run_fold(train,test,fold_name):
    y=test.correct.to_numpy();gp=float(train.correct.mean())
    preds={'BASE_RATE':np.full(len(test),gp),'OUTCOME_HISTORY':group_history_prob(train,test),'INPUT_ONLY':fit_input_only(train,test),'SURFACE_RAW':fit_surface(train,test),'GENERIC_TRACE_MONITOR':fit_trace(train,test),'INPUT_PLUS_SURFACE':fit_input_surface(train,test),'ANNOTATION_SURFACE_DIAGNOSTIC_ONLY':fit_annotation_surface(train,test)}
    arms={k:metrics(y,p) for k,p in preds.items()}
    strata={}
    for tt,g in test.groupby('training_type'):
        if len(g)<20:continue
        idx=test.index.get_indexer(g.index)
        strata[str(tt)]={k:metrics(y[idx],p[idx]) for k,p in preds.items()}
    diffp=item_history_prob(train,test)
    return {'fold':fold_name,'n_train':int(len(train)),'n_test':int(len(test)),'test_correct_rate':float(y.mean()),'arms':arms,'training_type_strata':strata,'item_difficulty_control_diagnostic':metrics(y,diffp)}

def run_cv(df,kind):
    key={'leave_one_model_out':'model','leave_one_model_family_out':'model_family','leave_one_benchmark_out':'benchmark'}[kind];folds=[]
    for g in sorted(df[key].astype(str).unique()):
        test=df[df[key].astype(str)==g];train=df[df[key].astype(str)!=g]
        if len(test)>=20 and train.correct.nunique()==2:folds.append(run_fold(train,test,f'{key}={g}'))
    return folds

def summarize(folds):
    if not folds:return {}
    out={}
    for arm in sorted(folds[0]['arms']):
        vals=defaultdict(list)
        for f in folds:
            for k,v in f['arms'][arm].items():
                if isinstance(v,(int,float)) and v is not None:vals[k].append(v)
        out[arm]={k:float(np.mean(v)) for k,v in vals.items()}
    return out

def descriptive(df):
    result={}
    behaviors=['ann_self_correction','ann_hypothesis_testing','ann_uncertainty_acknowledgment','ann_confidence_calibration','ann_self_awareness','ann_knowledge_alignment']
    for b in behaviors:
        z={}
        for val,g in df.groupby(b):z[str(int(val))]={'n':int(len(g)),'correct_rate':float(g.correct.mean())}
        z['delta_correct_rate_present_minus_absent']=float(df[df[b]==1].correct.mean()-df[df[b]==0].correct.mean()) if set(df[b])=={0,1} else None
        result[b]=z
    result['by_training_type']={}
    for tt,g in df.groupby('training_type'):
        result['by_training_type'][str(tt)]={'n':int(len(g)),'correct_rate':float(g.correct.mean()),'raw_surface_self_correction_rate':float((g.surface_self_correction>0).mean()),'raw_surface_uncertainty_rate':float((g.surface_uncertainty>0).mean()),'ann_confidence_calibration_rate':float(g.ann_confidence_calibration.mean())}
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dataset',default='neulab/behavioral-lift');ap.add_argument('--input-parquet');ap.add_argument('--input-jsonl');ap.add_argument('--input-csv');ap.add_argument('--output',required=True);ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
    raw,transport=load_data(args);contract=validate_raw(raw,args);df=prepare(raw)
    result={'schema':'logos-mbe-em2-result-v2','dataset':'neulab/behavioral-lift','transport':transport,'data_contract':contract,'rows':int(len(df)),'online_leakage_exclusions':sorted(FORBIDDEN_ONLINE),'primary_cv':{},'required_secondary_cv':{},'descriptive_annotations_only':descriptive(df),'scientific_scope':{'behavioral_proxy_prediction':'eligible_if_full_8282_run','internal_state_mbe':'UNTESTED','behavioral_lift_causal_mechanism':'UNLICENSED','L3_to_L2':'UNLICENSED'}}
    for kind in ['leave_one_model_out','leave_one_benchmark_out']:
        folds=run_cv(df,kind);result['primary_cv'][kind]={'folds':folds,'mean':summarize(folds)}
    kind='leave_one_model_family_out';folds=run_cv(df,kind);result['required_secondary_cv'][kind]={'folds':folds,'mean':summarize(folds)}
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'rows':len(df),'transport':transport,'primary':{k:v['mean'] for k,v in result['primary_cv'].items()},'secondary':{k:v['mean'] for k,v in result['required_secondary_cv'].items()}},indent=2))
if __name__=='__main__':main()
