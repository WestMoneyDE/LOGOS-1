# LOGOS-1 — logos-laya, the local juror service (contract `laya-classify/1`).
#
# The model is fetched ONCE, here, at a full 40-character revision. At runtime the hub is
# offline: the container can answer only with the bytes baked into this image, and every
# response names them (pins: package_version, hf_revision, route, device).
# CPU only. Non-root (uid 10001). Read-only root filesystem at runtime (see compose).
FROM python:3.12.7-slim

ARG LAYA_HF_REPO=convaiinnovations/laya
# The revision every in-session measurement used. The newer aa8c91ca... lacks `multilingual/`.
ARG LAYA_HF_REVISION=5e7b2b1b8ca2ecdd3f2322d94069c9b6ce7e844b

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/tmp/hf HF_HUB_DISABLE_TELEMETRY=1

RUN useradd -m -u 10001 laya
WORKDIR /app

RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==2.14.0+cpu"
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Download the pinned snapshot (all three checkpoints: english at the root, multilingual and
# typed-decisions as subfolders) into a BuildKit cache mount, so a network failure part-way
# resumes instead of starting over (plain HTTP with Range resume; xet disabled because its
# failures are not resumable). Retried a bounded number of times. The snapshot is then copied,
# symlinks dereferenced, into the image at /opt/laya/<revision>; laya's own tokenizer-config
# repair is applied at build time (the runtime filesystem is read-only), and the build fails
# if any checkpoint is missing.
RUN --mount=type=cache,target=/hf-dl,sharing=locked     HF_HUB_CACHE=/hf-dl HF_HUB_DISABLE_XET=1 HF_HUB_DOWNLOAD_TIMEOUT=60 python - <<PY
import os, shutil, time
from huggingface_hub import snapshot_download
from laya.agent import _fix_tokenizer_config
files = ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")
subs = ("", "multilingual/", "typed-decisions/")
for attempt in range(1, 9):
    try:
        path = snapshot_download("${LAYA_HF_REPO}", revision="${LAYA_HF_REVISION}",
                                 allow_patterns=[s + f for s in subs for f in files])
        break
    except Exception as exc:
        print("attempt", attempt, "failed:", type(exc).__name__, str(exc)[:200], flush=True)
        if attempt == 8:
            raise
        time.sleep(10 * attempt)
assert os.path.basename(path) == "${LAYA_HF_REVISION}", path
dest = "/opt/laya/${LAYA_HF_REVISION}"
shutil.copytree(path, dest, symlinks=False)
for s in subs:
    d = os.path.join(dest, s)
    for f in ("rl_agent_config.json", "model.safetensors", "tokenizer/tokenizer.json"):
        assert os.path.exists(os.path.join(d, f)), (s, f)
    _fix_tokenizer_config(d)
print("snapshot", dest, flush=True)
PY

# Content pins: sha256 of each checkpoint's weights (= the HF LFS oid at this revision;
# cross-checked against an independently downloaded cache of the same revision). Written into
# the image as SHA256SUMS; the build fails on any mismatch.
RUN cd /opt/laya/${LAYA_HF_REVISION} && printf '%s\n' \
      "891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c  model.safetensors" \
      "9d628fd971b700382ac6f65920a86f149777b2e748e0c955fb3b19695aa8f204  multilingual/model.safetensors" \
      "4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e  typed-decisions/model.safetensors" \
      > SHA256SUMS && sha256sum -c SHA256SUMS

ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    XDG_CACHE_HOME=/tmp/.cache HOME=/tmp \
    LAYA_HF_REVISION=${LAYA_HF_REVISION} \
    LAYA_SNAPSHOT_DIR=/opt/laya/${LAYA_HF_REVISION} \
    LAYA_DEVICE=cpu LAYA_PRELOAD=english LAYA_MAX_LOADED=1

COPY app.py /app/app.py
USER 10001
EXPOSE 8110
HEALTHCHECK --interval=10s --timeout=3s --start-period=180s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8110/readyz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8110", "--workers", "1", "--no-access-log"]
