# Database deployment integration

Database schema ownership has moved to:

```text
platform-core-and-infra/platform-ai-utilities/db-schema
```

This application repository does not contain or execute database DDL. Its
pipeline waits for tests and image verification, then
`trigger-db-schema-deployment` starts the schema repository's protected `main`
pipeline with `strategy: depend`.

The downstream pipeline validates the canonical NNP Knowledge Management schema
twice against disposable PostgreSQL, applies it transactionally to the target
database, and reports success or failure to this pipeline. Kubernetes deployment
depends on that success.

The application passes only deployment context:

- `UPSTREAM_PROJECT_PATH`
- `UPSTREAM_COMMIT_SHA`
- `TARGET_ENVIRONMENT`

Database endpoints and credentials belong exclusively to the schema project.
Do not add `psql`, database passwords, schema files, or migration commands to
this repository.

GitLab administrators must add this application project to the schema project's
CI job-token allowlist. No personal access token is required or permitted for
the multi-project trigger.

For local development, provision the database through an approved schema-project
pipeline or use a disposable database populated from a checked-out copy of the
schema repository. Starting this application's Docker Compose stack does not
create database objects.
