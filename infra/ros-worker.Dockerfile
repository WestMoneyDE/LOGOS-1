# LOGOS-1 Research OS — deterministic worker (Phase 3).
# Runs `tests` (allowlisted pytest paths) and `snapshot` jobs from the ros_jobs queue. No Claude, no API key, no network beyond the compose bridge.
# The repository is COPIED into the image (no host mount — constraint of the infrastructure safety grant); results carry LOGOS_REPO_SHA.
FROM python:3.12.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* && useradd -m -u 10001 ros
WORKDIR /app
COPY requirements-dashboard.txt /app/
RUN pip install --no-cache-dir -r requirements-dashboard.txt "psycopg[binary]==3.2.3" "pytest>=8" "hypothesis>=6"
COPY --chown=ros:ros . /app
ARG LOGOS_REPO_SHA=unknown
ENV LOGOS_REPO_SHA=${LOGOS_REPO_SHA} PYTHONPATH=/app/src
USER ros
CMD ["python", "-m", "logos_dashboard.control.worker", "--loop", "--interval", "5"]
