# Local Research Stack — fresh-clone path

Authorized by `docs/engineering/SAFETY-REVIEW-REQUEST-RESEARCH-INFRASTRUCTURE.md`
(Decision record: GRANTED, 2026-09-10). **Local development only.**

```text
InfrastructureHasNetwork != AgentHasNetwork
```

This stack is research infrastructure. It grants experimental agents nothing:
sandbox L2 remains `REVIEW_REQUIRED` and `network_allowed` stays `False`.

## Destructive commands

```text
docker compose down       stops containers, KEEPS volumes
docker compose down -v    DELETES volumes — canonical research records and
                          artifacts are gone. There is no backup.
```

## Fresh clone to running stack

```bash
git clone <repo> && cd logos-1

# 1. credentials — compose has no defaults on purpose and fails closed without them
cp .env.example infra/.env
$EDITOR infra/.env            # fill in values; infra/.env is git-ignored

# 2. python dependencies
python -m pip install -e ".[test,infra]"

# 3. start the stack
cd infra && docker compose up -d && cd ..

# 4. migrate the canonical database (idempotent)
python -c "from logos_research.infra.backends import backends_from_env as b; \
           r=b()['repository'].connect(); print('applied', r.migrate(), \
           'version', r.schema_version()); r.close()"

# 5. health
python -c "from logos_research.infra.backends import backends_from_env as b; \
           x=b(); x['repository'].connect(); \
           [print(f'{h.name:16} {h.status:12} {h.criticality}') \
            for h in (x[k].health() for k in ['repository','tracker','artifacts','traces','llm_traces'])]"

# 6. infrastructure smoke run (NON_SCIENTIFIC)
python -c "import json;from logos_research.infra import smoke;print(json.dumps(smoke.run(),indent=2))"

# 7. tests
python -m pytest
```

Integration tests skip automatically when the stack is not running.

## Services

| Service | Image | Loopback port | Role | Criticality |
|---|---|---|---|---|
| postgres | `postgres:16.4-alpine` | 55432 | canonical research records | `CANONICAL` |
| minio | `minio/minio:RELEASE.2024-09-13T20-26-02Z` | 59000 / 59001 | artifacts, MLflow store, DVC remote | `CANONICAL` |
| mlflow | `ghcr.io/mlflow/mlflow:v2.16.2` + psycopg2/boto3 | 55000 | run tracking | `OBSERVABILITY` |
| langfuse | `langfuse/langfuse:2.95.0` | 53000 | LLM traces | `OBSERVABILITY` |
| otel-collector | `otel/opentelemetry-collector-contrib:0.109.0` | 54317 / 54318 / 55679 | system traces | `OBSERVABILITY` |

Langfuse **v2** is pinned deliberately: it needs PostgreSQL only. v3 additionally
requires ClickHouse and Redis.

Databases `mlflow` and `langfuse` are created alongside `logos_research` by
`infra/postgres/init/01-databases.sh` at first initialisation.

Buckets `logos-artifacts`, `logos-mlflow` and `logos-dvc` are created by the
`minio-init` one-shot service, so storage namespaces are explicit rather than
created implicitly on first write.

## DVC

```bash
python -m dvc push        # to s3://logos-dvc on MinIO
python -m dvc pull
```

Remote URL and endpoint live in the committed `.dvc/config`. **Credentials live
in `.dvc/config.local`, which is git-ignored** — check that `.dvc/.gitignore`
contains `config.local` before committing anything under `.dvc/`.

DVC's object hash is not the scientific identity of a dataset. See
`docs/architecture/RESEARCH-INFRASTRUCTURE.md`.

## Known environment constraint

`dvc 3.55.2` requires `pathspec<1.0` (`_DIR_MARK`). If `pathspec>=1.0` is
installed by another package, DVC fails with an import error; pin `pathspec==0.12.1`.

## Degradation

```text
canonical service unavailable      run aborts; no durable completion is claimed
observability service unavailable  run continues as DEGRADED, loss recorded
```

A missing trace and an unavailable sink are distinguishable: the latter records a
`DegradedSink`.
