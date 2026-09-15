# Contributing to Nubo Native Platform (NNP)

This repository, **PICC-AIKM-AIKM-backend**, is part of the **AI Knowledge Management (AIKM)** area of the Nubo Native Platform. Contributions are welcome under the **Apache 2.0 License**.

## Before You Start

Contributions should align with an open issue, an approved enhancement request, or an agreed maintenance task for the AIKM backend service.

Before starting implementation:

1. Confirm the intended change scope with the maintainers.
2. Check whether the change affects API contracts, database schema, downstream service calls, or deployment configuration.
3. Avoid adding real credentials, internal hostnames, private URLs, production database values, or personal access tokens to code, documentation, examples, tests, or logs.
4. Use placeholders such as `<CONFIG_SERVER_URL>`, `<POSTGRES_PASSWORD>`, `<RAG_QUERY_SERVICE_URL>`, and `<MINIO_BUCKET>` in documentation and sample configuration.

For contribution coordination, use the repository issue tracker or the approved project communication channel. If an email address is required by your organization, document it as `<CONTRIBUTION_CONTACT_EMAIL>` until an approved public contact is provided.

## Development and Contribution Steps

1. **Fork and Clone**
   - Fork the repository or create a working branch from the approved base branch.
   - Use a focused branch name, for example `feature/bucket-validation`, `fix/health-readiness`, or `docs/readme-setup`.

2. **Set Up the Local Environment**
   - Copy `.env.sample` to `.env`.
   - Replace placeholders with local development values only.
   - Keep `PROVISION_ENABLED=false` and `INGESTION_ENABLED=false` unless the downstream services are available.
   - Use `MODEL_TYPE=local` for local-only flows that should not require public LLM credentials.

3. **Install Dependencies**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   python -m pip install --upgrade pip
   pip install -r requirements-api.txt
   ```

   On Linux or macOS:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements-api.txt
   ```

4. **Run the Service Locally**

   With Docker Compose:

   ```bash
   docker compose up --build
   ```

   Or with an existing PostgreSQL instance:

   ```bash
   python run_api.py
   ```

5. **Follow Development Guidelines**
   - Review [DEVELOPMENT_GUIDELINES.md](DEVELOPMENT_GUIDELINES.md) before changing API routers, models, repositories, services, configuration loading, database schema, or deployment files.
   - Keep route handlers thin and move reusable logic into services or repositories.
   - Keep schema changes explicit in `db/schema.sql` and document deployment effects.

6. **Automated Verification**

   Run the test suite before opening a pull request:

   ```bash
   pytest
   ```

   For container-impacting changes, verify the API image and local stack:

   ```bash
   docker compose up --build
   curl http://localhost:8000/health
   curl http://localhost:8000/health/deep
   ```

7. **Submit a Pull Request**
   - Include a concise summary of the change.
   - Mention affected API endpoints, configuration keys, database tables, or deployment files.
   - Include test evidence such as `pytest` results or local Docker Compose verification.
   - Call out any required migration, configuration, or operational follow-up.

## Security and Standards

- **Never commit secrets, tokens, private URLs, internal hostnames, production `.env` files, or real credentials.**
- Keep `.env` local. Commit only sanitized examples such as `.env.sample`.
- Do not log request payloads, database passwords, API keys, object-storage credentials, or LLM provider tokens.
- Treat `PG_PASSWORD`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MINIO_ROOT_PASSWORD`, and `PG_CONNECTION_STRING_VANNA` as sensitive.
- Use placeholders in documentation and test data unless the value is a safe local-only default.
- Keep new dependencies minimal and justified. Update `requirements-api.txt` only when the runtime needs the package.
- All participation is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).
