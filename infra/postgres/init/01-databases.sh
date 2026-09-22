#!/bin/sh
# MLflow and Langfuse each need their own database alongside the canonical
# LOGOS research database. Created once, at first initialisation.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    CREATE DATABASE mlflow;
    CREATE DATABASE langfuse;
SQL
