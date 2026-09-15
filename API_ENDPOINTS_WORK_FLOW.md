<h1 style="color:#1f4e79; border-bottom:3px solid #53a7ba; padding-bottom:8px;">
  KM Backend API Endpoint Details
</h1>

<p>
  This document explains the <strong>Knowledge Base</strong> and <strong>SQL Query</strong> API endpoints end to end from the backend service perspective.
</p>

| # | API Endpoint | Purpose |
|---|--------------|---------|
| 1 | <span style="color:#4a77b4;"><strong>POST /manageKnowledge/search</strong></span> | Search Knowledge Base content through the RAG query service |
| 2 | <span style="color:#4a77b4;"><strong>GET /manageBucket/getDetails/{account_id}</strong></span> | Load Knowledge Base buckets mapped to an account |
| 3 | <span style="color:#4a77b4;"><strong>GET /manageBucket/getAccountIds/{bucket_id}</strong></span> | Load readonly account mappings for a bucket |
| 4 | <span style="color:#4a77b4;"><strong>POST /manageBucket/createBucket</strong></span> | Create a bucket and provision its Milvus collection |
| 5 | <span style="color:#4a77b4;"><strong>PUT /manageBucket/updateBucket/{bucket_id}</strong></span> | Update bucket metadata and account mappings |
| 6 | <span style="color:#4a77b4;"><strong>DELETE /manageBucket/deleteBucket/{bucket_id}</strong></span> | Soft-delete a bucket and drop its Milvus collection |
| 7 | <span style="color:#4a77b4;"><strong>GET /manageBucketDetails/getDetails/{bucket_id}</strong></span> | Load source/document rows for a bucket |
| 8 | <span style="color:#4a77b4;"><strong>POST /manageBucketDetails/createBucketDetails</strong></span> | Add document or web source and ingest it |
| 9 | <span style="color:#4a77b4;"><strong>POST /manageBucketDetails/createGitBucketDetails</strong></span> | Add a Git repository source and ingest code knowledge |
| 10 | <span style="color:#4a77b4;"><strong>POST /manageBucketDetails/createRedmineBucketDetails</strong></span> | Add a Redmine issue source and ingest incidents |
| 11 | <span style="color:#4a77b4;"><strong>PUT /manageBucketDetails/updateBucketDetails/{detail_id}</strong></span> | Update source metadata or mark a source deleted |
| 12 | <span style="color:#4a77b4;"><strong>DELETE /manageBucketDetails/deleteBucketDetail/{detail_id}</strong></span> | Soft-delete a source and remove its vectors |
| 13 | <span style="color:#4a77b4;"><strong>GET /manageQuestions/getDetails</strong></span> | Load curated Q&A rows across buckets |
| 14 | <span style="color:#4a77b4;"><strong>POST /manageQuestions/addQDetails</strong></span> | Create a curated Q&A pair |
| 15 | <span style="color:#4a77b4;"><strong>PUT /manageQuestions/updateQDetails/{qa_id}</strong></span> | Update a curated Q&A pair |
| 16 | <span style="color:#4a77b4;"><strong>DELETE /manageQuestions/deleteQDetail/{qa_id}</strong></span> | Soft-delete a curated Q&A pair |
| 17 | <span style="color:#4a77b4;"><strong>GET /manageDataSql/getDetails</strong></span> | Load SQL databases and training context for buckets |
| 18 | <span style="color:#4a77b4;"><strong>POST /manageDataSql/addDBDetails</strong></span> | Register a SQL database and train Vanna context |
| 19 | <span style="color:#4a77b4;"><strong>PUT /manageDataSql/updateDBDetails/{db_id}</strong></span> | Update a SQL database and retrain Vanna context |
| 20 | <span style="color:#4a77b4;"><strong>DELETE /manageDataSql/deleteDBDetail/{db_id}</strong></span> | Soft-delete a SQL database and clear training vectors |
| 21 | <span style="color:#4a77b4;"><strong>POST /manageDataSql/addSQLDetails</strong></span> | Save a curated SQL query and train it into Vanna |
| 22 | <span style="color:#4a77b4;"><strong>PUT /manageDataSql/updateSQLDetails/{sql_id}</strong></span> | Update a curated SQL query and retrain it |
| 23 | <span style="color:#4a77b4;"><strong>DELETE /manageDataSql/deleteSQLDetail/{sql_id}</strong></span> | Soft-delete a curated SQL query and remove training data |
| 24 | <span style="color:#4a77b4;"><strong>POST /manageDataSql/addDDLDetails</strong></span> | Add DDL training text for a database |
| 25 | <span style="color:#4a77b4;"><strong>PUT /manageDataSql/updateDDLDetails/{ddl_id}</strong></span> | Update DDL training text and retrain |
| 26 | <span style="color:#4a77b4;"><strong>DELETE /manageDataSql/deleteDDLDetail/{ddl_id}</strong></span> | Soft-delete DDL training text and remove vector |
| 27 | <span style="color:#4a77b4;"><strong>POST /manageDataSql/addRuleDetails</strong></span> | Add business-rule training text |
| 28 | <span style="color:#4a77b4;"><strong>PUT /manageDataSql/updateRuleDetails/{rule_id}</strong></span> | Update business-rule training text and retrain |
| 29 | <span style="color:#4a77b4;"><strong>DELETE /manageDataSql/deleteRuleDetail/{rule_id}</strong></span> | Soft-delete business-rule training text and remove vector |
| 30 | <span style="color:#4a77b4;"><strong>POST /manageSqlQuery/query</strong></span> | Generate and optionally execute SQL from a natural-language question |
| 31 | <span style="color:#4a77b4;"><strong>POST /manageSqlQuery/promoteQuery</strong></span> | Promote generated SQL into curated saved queries |
| 32 | <span style="color:#4a77b4;"><strong>POST /manageSqlQuery/saveHistory</strong></span> | Save query history |
| 33 | <span style="color:#4a77b4;"><strong>POST /manageSqlQuery/submitFeedback</strong></span> | Save feedback for generated SQL |
| 34 | <span style="color:#4a77b4;"><strong>GET /manageSqlQuery/getHistory</strong></span> | Load recent query history |

> <strong>Service Context:</strong> These endpoints are exposed by the FastAPI backend service over the CoreComp / <code>nnp-rag</code> data model.

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  1. POST /manageKnowledge/search
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint searches the Knowledge Base for a natural-language question.
  It prepares the RAG request, enriches it with active model details, forwards it to the RAG query service, and returns the search response.
</div>

### Endpoint Summary

| Item | Detail |
|------|--------|
| Method | `POST` |
| Path | `/manageKnowledge/search` |
| Router | `manageKnowledge` |
| Handler | `search_knowledge` |
| Main Responsibility | Proxy and normalize Knowledge Base search requests for the RAG service |
| Downstream Service | `RAG_QUERY_SERVICE_URL/ask` |

<h3 style="color:#4a77b4;">Complete Working Flow</h3>

1. **Request is received**
   - The API receives a natural-language question and optional search controls.
   - FastAPI validates the request body using `SearchRequest`.

2. **Model type is selected**
   - If `MODEL_TYPE=local`, the endpoint uses `local`.
   - For all other values, it uses `public`.

3. **Active model details are loaded**
   - The endpoint queries `model_details`.
   - It looks for the active text model for the selected model type.
   - If lookup fails, the error is logged and the endpoint continues without model credentials.

4. **RAG payload is prepared**
   - `question` is passed as-is.
   - `bucket_names` becomes `collectionNames`.
   - `limit` becomes `sourceCount`.
   - `similarity_threshold` becomes `similarityThreshold`.
   - `extend_public` becomes `extendPublicInfo`.
   - `modelType` is added.
   - `ModelName` and `APIKey` are added when available.

5. **RAG service is called**
   - The endpoint creates an `httpx.AsyncClient`.
   - Timeout is selected from local/public timeout settings.
   - The endpoint posts to `{RAG_QUERY_SERVICE_URL}/ask`.

6. **Response is returned**
   - On success, the RAG service JSON response is returned directly.
   - On HTTP failure, the endpoint currently returns an empty answer list with an `error` field.

### Related Backend Flow

```text
POST /manageKnowledge/search
  -> SearchRequest validation
  -> model type selection from MODEL_TYPE
  -> model_details lookup
  -> RAG payload mapping
  -> POST {RAG_QUERY_SERVICE_URL}/ask
  -> return RAG response JSON
```

<h3 style="color:#4a77b4;">Request Body</h3>

```json
{
  "question": "How do I configure deployment?",
  "limit": 5,
  "similarity_threshold": 0.4,
  "extend_public": true,
  "bucket_names": ["EngineeringDocs", "Runbooks"]
}
```

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `question` | string | Yes | Natural-language question to search for |
| `limit` | integer | No | Number of source results requested; must be `>= 1` when provided |
| `similarity_threshold` | float | No | Relevance threshold between `0.0` and `1.0` |
| `extend_public` | boolean | No | Allows public/general model extension when enabled |
| `bucket_names` | string array | No | Bucket collection names used to scope the RAG search |

<h3 style="color:#4a77b4;">Response</h3>

Successful responses are returned from the RAG service directly. Expected shape:

```json
{
  "answer": [
    {
      "score": 0.87,
      "text": "Relevant source text..."
    }
  ]
}
```

Current failure shape for downstream HTTP errors:

```json
{
  "answer": [],
  "error": "failure details"
}
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `model_details` | Direct read | Active text model configuration. The endpoint reads `ModelName` and `API_Key` where `Model_Type` matches the selected model type, `Usage` is `text`, and `Status` is `active`. This shared platform table is intentionally outside the application-owned `db/schema.sql`. |
| `nnp_km_buckets` | Indirect search scope | Bucket metadata. Bucket names are used as RAG collection names. This endpoint does not query the table directly. |
| Milvus bucket collections | Downstream vector search | Vectorized Knowledge Base content searched by the downstream RAG query service. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| `ai-rag-query-service` | External service | Performs retrieval and answer generation |
| Milvus | External vector database | Stores and searches Knowledge Base embeddings through the RAG service |
| PostgreSQL | Database | Stores active model configuration in `model_details` |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Model provider config | Runtime configuration | Supplies selected model type, optional model name, API key, and public/local timeout behavior |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Error handling | Return proper non-2xx HTTP responses when the RAG service fails instead of returning `200` with `{ "answer": [], "error": "..." }`. |
| Contract clarity | Add explicit backend response models for success and error responses. |
| Bucket validation | Validate that requested `bucket_names` are active and visible to the requesting account before forwarding to RAG. |
| Observability | Log downstream latency, selected model type, source count, bucket count, and downstream status code. |
| Security | Avoid forwarding raw API keys to downstream services where possible; prefer server-side credential references. |
| Resilience | Add retry and circuit-breaker behavior for transient downstream failures. |
| Search history | Move Knowledge Base search-history ownership into a dedicated Knowledge Base history API instead of relying on SQL-query history APIs. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  2. GET /manageBucket/getDetails/{account_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint loads Knowledge Base buckets mapped to an account.
  It is used to determine which buckets are visible and available for Knowledge Base operations.
</div>

### Endpoint Summary

| Item | Detail |
|------|--------|
| Method | `GET` |
| Path | `/manageBucket/getDetails/{account_id}` |
| Router | `manageBucket` |
| Handler | `get_details` |
| Main Responsibility | Return bucket rows mapped to a Portal account |
| Database Access | PostgreSQL through `bucket_repo.get_by_account` |

<h3 style="color:#4a77b4;">Complete Working Flow</h3>

1. **Request is received**
   - The API receives `account_id` as a path parameter.
   - Optional `includeDeleted` can be passed as a query parameter.

2. **Repository call is scheduled**
   - The router calls `bucket_repo.get_by_account`.
   - The synchronous repository call runs through `run_in_threadpool`.

3. **Database connection is checked out**
   - The repository uses the shared PostgreSQL pool.
   - The cursor helper sets `search_path` to the configured schema, usually `"nnp-rag", public`.

4. **Bucket/account mapping is queried**
   - `nnp_km_buckets` is joined with `nnp_account_bucket_map`.
   - Only rows mapped to the supplied `account_id` are returned.

5. **Lifecycle and backend filters are applied**
   - `DELETED` buckets are excluded unless `includeDeleted=true`.
   - Embedding backend visibility is applied:
     - `MODEL_TYPE=local` returns only `local` buckets.
     - Other model types return `openai` and `public` buckets.

6. **Rows are sorted and returned**
   - Results are ordered by `created_at DESC`.
   - The endpoint returns the bucket rows as JSON.

### Related Backend Flow

```text
GET /manageBucket/getDetails/{account_id}
  -> get_details(account_id, includeDeleted)
  -> run_in_threadpool(bucket_repo.get_by_account)
  -> PostgreSQL connection pool
  -> SET search_path
  -> JOIN nnp_km_buckets + nnp_account_bucket_map
  -> apply status and embedding_backend filters
  -> return bucket rows
```

<h3 style="color:#4a77b4;">Path and Query Parameters</h3>

| Parameter | Location | Type | Default | Purpose |
|-----------|----------|------|---------|---------|
| `account_id` | Path | string | Required | Portal account/user identifier used to find mapped buckets |
| `includeDeleted` | Query | boolean | `false` | Includes `DELETED` buckets when set to `true` |

<h3 style="color:#4a77b4;">Response</h3>

Returns an array of bucket rows.

```json
[
  {
    "id": "2f0611d5-c70d-448c-84ae-842f2b9ff4df",
    "bucket_category": "Engineering",
    "bucket_name": "EngineeringDocs",
    "bucket_desc": "Engineering knowledge articles and runbooks",
    "bucket_size": 0,
    "bucket_spec": null,
    "bucket_url": null,
    "status": "ACTIVE",
    "error_detail": null,
    "created_at": "2026-07-17T08:00:00Z",
    "updated_at": "2026-07-17T08:00:00Z",
    "created_by": "user1",
    "updated_by": "user1",
    "embedding_backend": "local"
  }
]
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_buckets` | Direct read | Top-level Knowledge Base bucket metadata: category, name, description, size, spec, URL, lifecycle status, error details, audit fields, and embedding backend. `bucket_name` also acts as the Milvus collection name. Its complete definition is in `db/schema.sql`. |
| `nnp_account_bucket_map` | Direct read | Many-to-many mapping between Portal account IDs and bucket IDs. It decides which buckets an account can see. The copied DDL defines `account_id` and `bucket_id`; repository code also references an `ownership` column in related bucket create/update/account lookup flows, so the deployed schema should be checked for drift. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores bucket metadata and account-bucket mapping rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| CoreComp schema | Database schema | Provides `nnp_km_buckets` and `nnp_account_bucket_map` |
| Model backend setting | Runtime configuration | Controls visible bucket embedding backends through `MODEL_TYPE` |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Authorization | Do not trust only the `account_id` path parameter. Compare it with authenticated identity or Portal claims. |
| Response contract | Return an explicit bucket response model instead of raw database rows. |
| Pagination/search | Add pagination, sorting, and filters for accounts with many buckets. |
| Active-only option | Add a query parameter such as `status=ACTIVE` so clients can request active buckets directly. |
| Ownership clarity | Include ownership information when access level matters. |
| Schema consistency | Reconcile copied base schema, migrations, and repository expectations, especially `embedding_backend` and `nnp_account_bucket_map.ownership`. |
| Indexing | Add or verify indexes for common filters such as `(account_id, bucket_id)`, `bucket_id`, `status`, and `embedding_backend`. |
| Naming consistency | Align account identity terminology across path parameters, request headers, and Portal conventions. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  3. GET /manageBucket/getAccountIds/{bucket_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint returns the non-owner account IDs mapped to a bucket.
  It is used when bucket access assignments need to be displayed or edited.
</div>

### Complete Working Flow

1. **Request is received**
   - The API receives `bucket_id` as a path parameter.

2. **Account mappings are queried**
   - The repository reads `nnp_account_bucket_map`.
   - It filters rows by `bucket_id`.
   - It excludes mappings where `ownership = 'owner'`.

3. **Response is returned**
   - The endpoint returns a simple string array of account IDs ordered by account ID.

### Related Backend Flow

```text
GET /manageBucket/getAccountIds/{bucket_id}
  -> bucket_repo.get_account_ids_by_bucket(bucket_id)
  -> SELECT account_id FROM nnp_account_bucket_map
  -> exclude owner mappings
  -> return string[]
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_account_bucket_map` | Direct read | Account-to-bucket mapping rows. Code expects an `ownership` column to distinguish `owner` and `readonly` access. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores account-to-bucket mapping rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| CoreComp schema | Database schema | Provides bucket access mapping structure |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Schema consistency | Ensure `ownership` exists in the deployed schema and copied DDL. |
| Authorization | Confirm the caller is allowed to inspect bucket account mappings. |
| Response clarity | Return mapping objects with `account_id` and `ownership` if multiple roles are needed later. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  4. POST /manageBucket/createBucket
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint creates a Knowledge Base bucket and starts Milvus collection provisioning.
  The bucket row is returned immediately with provisioning status while collection creation runs in the background.
</div>

### Complete Working Flow

1. **Request is validated**
   - `bucket_name` is validated against Milvus collection naming rules.
   - `account_id` identifies the owner account mapping.

2. **Bucket row is inserted**
   - A row is inserted into `nnp_km_buckets`.
   - Status starts as `PROVISIONING`.
   - `embedding_backend` is selected from `MODEL_TYPE`.
   - Audit columns are filled from the current user header.

3. **Owner mapping is inserted**
   - `nnp_account_bucket_map` receives the `(account_id, bucket_id)` owner mapping.
   - The bucket insert and mapping insert happen in one repository transaction.

4. **Milvus provisioning starts**
   - A background task calls `milvus_client.create_collection`.
   - Collection dimension is `384` for local embeddings and `3072` for OpenAI embeddings.

5. **Provisioning result is written**
   - Success updates bucket status to `ACTIVE`.
   - Failure updates bucket status to `FAILED` and stores `error_detail`.

### Related Backend Flow

```text
POST /manageBucket/createBucket
  -> BucketCreate validation
  -> INSERT nnp_km_buckets status=PROVISIONING
  -> INSERT nnp_account_bucket_map ownership=owner
  -> background Milvus create_collection(bucket_name)
  -> update nnp_km_buckets status ACTIVE/FAILED
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_buckets` | Direct write/update | Bucket metadata, provisioning status, embedding backend, audit fields, and provisioning errors. |
| `nnp_account_bucket_map` | Direct write | Owner account mapping for the new bucket. |
| Milvus collection | Direct create | Vector collection named by `bucket_name`, using the standard KM vector schema. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores the bucket row and account mapping |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Stores the per-bucket vector collection |
| Embedding backend setting | Runtime configuration | Selects collection dimension and `embedding_backend` value |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Uniqueness | Enforce global uniqueness for `bucket_name` in DB or before Milvus provisioning. |
| Idempotency | Add idempotency keys to avoid duplicate bucket creation on retries. |
| Provision audit | Store provisioning timestamps and operation request IDs. |
| Rollback behavior | Decide whether DB rows should be rolled back or retained when Milvus provisioning fails. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  5. PUT /manageBucket/updateBucket/{bucket_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint updates bucket metadata and optionally replaces readonly account mappings.
  The bucket name is intentionally immutable because it is also the Milvus collection name.
</div>

### Complete Working Flow

1. **Request is validated**
   - Allowed fields include category, description, spec, URL, status, and optional account mappings.
   - `bucket_name` is not accepted.

2. **Bucket metadata is updated**
   - The repository builds an update statement using only allowed fields.
   - `updated_by` is set from the current user.

3. **Account mappings are replaced when supplied**
   - New readonly account mappings are inserted.
   - Removed readonly account mappings are deleted.
   - Owner mappings are preserved.

4. **Response is returned**
   - Updated bucket row is returned.
   - If no row is found, the endpoint returns `404`.

### Related Backend Flow

```text
PUT /manageBucket/updateBucket/{bucket_id}
  -> BucketUpdate validation
  -> UPDATE nnp_km_buckets
  -> optional replace readonly mappings in nnp_account_bucket_map
  -> return updated bucket row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_buckets` | Direct update | Mutable bucket metadata, status, and audit fields. |
| `nnp_account_bucket_map` | Optional write/delete | Readonly account mappings for the bucket. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores bucket updates and access mappings |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| CoreComp schema | Database schema | Defines allowed bucket and mapping columns |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Access control | Restrict who can update bucket metadata and account mappings. |
| Mapping safety | Validate account IDs against Portal before storing them. |
| Audit trail | Store before/after account mapping changes for traceability. |
| Status control | Restrict manual status transitions to valid operational flows. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  6. DELETE /manageBucket/deleteBucket/{bucket_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint soft-deletes a bucket and starts asynchronous Milvus collection deletion.
  PostgreSQL deletion state is updated before the vector collection deletion runs.
</div>

### Complete Working Flow

1. **Bucket is soft-deleted**
   - The repository updates `nnp_km_buckets.status` to `DELETED`.
   - The updated row is returned.

2. **Missing bucket is handled**
   - If no bucket exists for the ID, the endpoint returns `404`.

3. **Milvus deletion starts**
   - A background task calls `milvus_client.delete_collection(bucket_name)`.
   - Missing Milvus collections are treated as successful.

4. **Response is returned**
   - The endpoint returns the soft-deleted bucket row.
   - Milvus deletion errors are logged but do not change the HTTP response.

### Related Backend Flow

```text
DELETE /manageBucket/deleteBucket/{bucket_id}
  -> UPDATE nnp_km_buckets status=DELETED
  -> background Milvus drop_collection(bucket_name)
  -> return bucket row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_buckets` | Direct update | Bucket lifecycle status and bucket name needed for Milvus deletion. |
| Milvus collection | Direct delete | Per-bucket vector collection to be dropped after soft-delete. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores bucket deletion state |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Drops the collection backing the deleted bucket |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Delete audit | Capture who deleted the bucket and when. |
| Cascade visibility | Make downstream document/Q&A impact explicit in response or audit logs. |
| Retry cleanup | Add retry/repair job for failed Milvus collection deletion. |
| Hard-delete policy | Define retention period and eventual hard-delete behavior. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  7. GET /manageBucketDetails/getDetails/{bucket_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint lists document/source rows registered under a bucket.
  It supports optional filtering by source category, lifecycle status, and deleted visibility.
</div>

### Complete Working Flow

1. **Request is received**
   - The API receives `bucket_id` as a path parameter.
   - Optional filters are `includeDeleted`, `category`, and `status`.

2. **Source rows are queried**
   - The repository reads `nnp_bucket_details`.
   - It filters by bucket, deleted visibility, category, and status.

3. **Rows are returned**
   - Results are ordered by `created_at DESC`.
   - Each row contains source metadata and ingestion/Milvus observability fields.

### Related Backend Flow

```text
GET /manageBucketDetails/getDetails/{bucket_id}
  -> bucket_detail_repo.get_by_bucket
  -> SELECT nnp_bucket_details
  -> apply bucket/category/status/deleted filters
  -> return source rows
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_bucket_details` | Direct read | Source metadata, source type, status, error details, Milvus source ID, chunk counts, ingest request ID, and audit fields. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores source/document metadata and ingestion state |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Pagination | Add paging for buckets with many source rows. |
| Filter validation | Validate category and status values against allowed vocabularies. |
| Source summary | Add aggregate counts by status/category for faster UI summaries. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  8. POST /manageBucketDetails/createBucketDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint registers a document or web page source under a bucket and starts ingestion.
  It extracts text, creates a pending source row, chunks and embeds content, stores vectors in Milvus, and updates ingestion status.
</div>

### Complete Working Flow

1. **Multipart request is received**
   - Required form field: `bucket_id`.
   - Optional fields: `doc_category`, `doc_name`, `url`, `file`.

2. **Content is extracted**
   - Uploaded files are read as PDF, DOCX, or UTF-8 text.
   - URLs are fetched and parsed into readable text.

3. **Bucket is verified**
   - The endpoint reads `nnp_km_buckets` by ID.
   - Missing bucket returns `404`.

4. **Source row is created**
   - A row is inserted into `nnp_bucket_details`.
   - Status starts as `PENDING`.

5. **Ingestion runs in background**
   - Content is split into chunks.
   - Chunks are embedded using local or OpenAI embedding backend based on bucket config.
   - Vectors are inserted into the bucket's Milvus collection.

6. **Ingestion result is saved**
   - Success updates status to `INGESTED`, stores `milvus_source_id`, chunk counts, and `ingested_at`.
   - Failure updates status to `FAILED` and stores `error_detail`.

### Related Backend Flow

```text
POST /manageBucketDetails/createBucketDetails
  -> extract file/url text
  -> verify bucket exists
  -> INSERT nnp_bucket_details status=PENDING
  -> background chunk/embed/store in Milvus
  -> UPDATE nnp_bucket_details status INGESTED/FAILED
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_buckets` | Direct read | Bucket existence, bucket collection name, and embedding backend. |
| `nnp_bucket_details` | Direct write/update | Source metadata, ingestion lifecycle state, Milvus source ID, chunk counts, errors, and audit fields. |
| Milvus collection | Direct write | Embedded chunks for the uploaded document or web source. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores source metadata and ingestion result |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Stores embedded document/web chunks |
| OpenAI embeddings | External model provider | Generates 3072-dimensional embeddings when bucket backend is OpenAI/public |
| Local HuggingFace embeddings | Local model runtime | Generates 384-dimensional embeddings when bucket backend is local |
| PDF/DOCX/text readers | Document parsing | Extracts text from uploaded files |
| Web page parser | Content extraction | Fetches and extracts readable text from URLs |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| File validation | Enforce allowed file types and size limits before reading content. |
| URL ingestion | Support JavaScript-rendered pages or explicitly report unsupported pages. |
| Re-ingestion | Add full re-ingestion support for updated sources. |
| Duplicate handling | Detect duplicate source URLs/files before creating new rows. |
| Async visibility | Add ingestion progress states beyond `PENDING`, `INGESTED`, and `FAILED`. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  9. POST /manageBucketDetails/createGitBucketDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint registers a Git repository as a Knowledge Base source and ingests code-aware repository knowledge into Milvus.
</div>

### Complete Working Flow

1. **Request is validated**
   - Required fields are `bucket_id` and `repo_url`.
   - Optional fields include branch, file extensions, username, and token.

2. **Bucket is verified**
   - The endpoint reads the bucket row.
   - Missing bucket returns `404`.

3. **Git source row is created**
   - A row is inserted into `nnp_bucket_details`.
   - `doc_category` is set to `git`.
   - Status starts as `PENDING`.

4. **Repository ingestion runs**
   - Repository files are cloned/read.
   - Supported code files are parsed into structured documents.
   - Documents are chunked with code-aware metadata.
   - Embeddings are generated and stored in Milvus.

5. **Result is saved**
   - Success marks the row `INGESTED`.
   - Failure marks the row `FAILED` and stores a sanitized error message.

### Related Backend Flow

```text
POST /manageBucketDetails/createGitBucketDetails
  -> verify bucket
  -> INSERT nnp_bucket_details doc_category=git status=PENDING
  -> clone/read repository
  -> parse code units
  -> chunk/embed/store in Milvus
  -> UPDATE nnp_bucket_details status INGESTED/FAILED
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_buckets` | Direct read | Bucket collection name and embedding backend. |
| `nnp_bucket_details` | Direct write/update | Git source row, status, description, format, Milvus source ID, and errors. |
| Milvus collection | Direct write | Embedded repository knowledge chunks. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores Git source metadata and ingestion result |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Stores embedded code/repository chunks |
| Git repository access | External source | Provides repository files to ingest |
| Tree-sitter parsers | Code parser | Extracts structured code units for supported languages |
| OpenAI or local embeddings | Model provider/runtime | Generates embeddings according to bucket backend |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Credential handling | Store Git credentials securely instead of passing raw tokens through request flow. |
| Incremental sync | Re-ingest only changed files after the initial repository ingestion. |
| Language coverage | Expand parser support and clearly report unsupported file types. |
| Source metadata | Store branch, commit SHA, and file count in structured columns. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  10. POST /manageBucketDetails/createRedmineBucketDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint registers Redmine issues as a Knowledge Base source and ingests issue content into Milvus for incident-style retrieval.
</div>

### Complete Working Flow

1. **Request is validated**
   - Required fields are `bucket_id`, `redmine_url`, and `api_key`.
   - Optional fields include project ID, issue status, and limit.

2. **Bucket is verified**
   - Missing bucket returns `404`.

3. **Redmine source row is created**
   - A row is inserted into `nnp_bucket_details`.
   - `doc_category` is set to `redmine`.
   - Status starts as `PENDING`.

4. **Issue ingestion runs**
   - Redmine issues are loaded through the Redmine API.
   - Each issue is converted into a text document with metadata.
   - Documents are chunked, embedded, and inserted into Milvus.

5. **Result is saved**
   - Success marks the row `INGESTED`.
   - Failure marks the row `FAILED` and stores the error.

### Related Backend Flow

```text
POST /manageBucketDetails/createRedmineBucketDetails
  -> validate Redmine URL/API key
  -> verify bucket
  -> INSERT nnp_bucket_details doc_category=redmine status=PENDING
  -> fetch Redmine issues
  -> chunk/embed/store in Milvus
  -> UPDATE nnp_bucket_details status INGESTED/FAILED
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_buckets` | Direct read | Bucket collection name and embedding backend. |
| `nnp_bucket_details` | Direct write/update | Redmine source row, status, description, format, Milvus source ID, and errors. |
| Milvus collection | Direct write | Embedded Redmine issue chunks. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores Redmine source metadata and ingestion result |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Stores embedded issue chunks |
| Redmine API | External source | Supplies issue data for ingestion |
| OpenAI or local embeddings | Model provider/runtime | Generates embeddings according to bucket backend |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Credential handling | Store Redmine API keys securely instead of accepting raw keys per request. |
| Sync strategy | Add scheduled refresh and incremental issue updates. |
| Filter clarity | Validate project/status filters before creating source rows. |
| Metadata richness | Store Redmine project/status/limit in structured columns. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  11. PUT /manageBucketDetails/updateBucketDetails/{detail_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint updates source metadata and can mark a source as deleted.
  When a source is deleted and has vectors, vector deletion is started in the background.
</div>

### Complete Working Flow

1. **Request is validated**
   - Allowed fields include category, name, description, format, size, status, and `reingest`.
   - Status must match the document status vocabulary.

2. **Source row is updated**
   - The repository updates `nnp_bucket_details`.
   - `updated_by` is set from the current user.

3. **Deletion side effect is triggered**
   - If status is set to `DELETED` and `milvus_source_id` exists, the bucket is loaded.
   - A background task deletes vectors from Milvus by source ID.

4. **Response is returned**
   - Updated row is returned.
   - Missing row returns `404`.
   - `reingest=true` is logged but not fully implemented yet.

### Related Backend Flow

```text
PUT /manageBucketDetails/updateBucketDetails/{detail_id}
  -> BucketDetailUpdate validation
  -> UPDATE nnp_bucket_details
  -> if status=DELETED, delete vectors by source
  -> return updated source row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_bucket_details` | Direct update | Mutable source metadata, status, Milvus source ID, and audit fields. |
| `nnp_km_buckets` | Conditional read | Bucket collection name needed for vector deletion. |
| Milvus collection | Conditional delete | Existing vectors for the source. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores source metadata and status |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Deletes vectors when source is marked deleted |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Re-ingestion | Implement `reingest=true` end to end. |
| Delete confirmation | Track vector deletion result in source metadata. |
| Field validation | Validate category and format values. |
| Audit trail | Record source update history and delete actor/timestamp. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  12. DELETE /manageBucketDetails/deleteBucketDetail/{detail_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint soft-deletes a document/source row and removes its vectors from the bucket collection when vectors exist.
</div>

### Complete Working Flow

1. **Source is soft-deleted**
   - The repository sets `nnp_bucket_details.status` to `DELETED`.

2. **Missing source is handled**
   - If the source row is not found, the endpoint returns `404`.

3. **Vector deletion starts**
   - If `milvus_source_id` exists, the bucket row is loaded.
   - A background task deletes Milvus vectors where source equals `km_{detail_id}`.

4. **Response is returned**
   - The soft-deleted row is returned immediately.
   - Vector deletion failure is logged separately.

### Related Backend Flow

```text
DELETE /manageBucketDetails/deleteBucketDetail/{detail_id}
  -> UPDATE nnp_bucket_details status=DELETED
  -> if milvus_source_id exists, load bucket
  -> background delete_by_source in Milvus
  -> return source row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_bucket_details` | Direct update | Source deletion status and Milvus source metadata. |
| `nnp_km_buckets` | Conditional read | Bucket collection name needed for vector deletion. |
| Milvus collection | Conditional delete | Vectors associated with the deleted source. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores source deletion state |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Milvus | Vector database | Removes source vectors from the bucket collection |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Cleanup retry | Add retry or repair flow for failed vector deletion. |
| Hard delete | Define retention and hard-delete policy. |
| Audit | Store deleted_by and deleted_at explicitly. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  13. GET /manageQuestions/getDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint loads curated Q&A pairs across one or more Knowledge Base buckets.
  Curated answers are stored as plain text and are managed separately from document ingestion.
</div>

### Complete Working Flow

1. **Request is received**
   - Required query parameter: `bucketIds`, a comma-separated UUID list.
   - Optional query parameter: `includeDeleted`.

2. **Bucket IDs are parsed**
   - Empty entries are discarded.

3. **Q&A rows are queried**
   - The repository reads `nnp_km_qa`.
   - It filters by `bucket_id = ANY(...)`.
   - It excludes deleted rows unless requested.

4. **Rows are returned**
   - Results are ordered by bucket ID and rank.

### Related Backend Flow

```text
GET /manageQuestions/getDetails?bucketIds=id1,id2
  -> parse bucketIds
  -> SELECT nnp_km_qa WHERE bucket_id = ANY(ids)
  -> exclude DELETED unless includeDeleted=true
  -> return curated Q&A rows
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_qa` | Direct read | Curated question, answer, rank, status, match threshold, optional embedding ID, usage count, and audit fields. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores curated Q&A rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Empty input handling | Return clear validation error when `bucketIds` is missing or empty. |
| Published filter | Add status filters such as `PUBLISHED` for retrieval-only use cases. |
| Search | Add keyword search across curated questions. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  14. POST /manageQuestions/addQDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint creates a curated Q&A pair inside a Knowledge Base bucket.
  It stores plain-text answers and leaves question embedding to a separate process.
</div>

### Complete Working Flow

1. **Request is validated**
   - Required fields are `bucket_id`, `question`, and `answer`.
   - `rank` must be between `1` and `5` when supplied.
   - `match_threshold` must be between `0.0` and `1.0` when supplied.
   - `status` must match the curation status vocabulary.

2. **Q&A row is inserted**
   - A row is inserted into `nnp_km_qa`.
   - Default status is `DRAFT` when no status is supplied.
   - `created_by` and `updated_by` are set from the current user.

3. **Response is returned**
   - The inserted Q&A row is returned with status `201`.

### Related Backend Flow

```text
POST /manageQuestions/addQDetails
  -> QuestionCreate validation
  -> INSERT nnp_km_qa
  -> default status DRAFT
  -> return created row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_qa` | Direct write | Curated Q&A content, ranking, status, match threshold, optional embedding pointer, usage count, and audit fields. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores curated Q&A pairs |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| External embedding process | Separate service/process | Responsible for embedding curated questions later; this endpoint does not embed them. |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Bucket validation | Verify bucket existence before inserting Q&A. |
| Embedding workflow | Trigger or enqueue question embedding after creation. |
| Answer format | Define whether answers support markdown, plain text only, or rich text. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  15. PUT /manageQuestions/updateQDetails/{qa_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint updates an existing curated Q&A pair, including content, rank, status, and match threshold.
</div>

### Complete Working Flow

1. **Request is validated**
   - Optional fields are question, answer, rank, status, and match threshold.
   - Rank, threshold, and status validators are applied when fields are provided.

2. **Q&A row is updated**
   - The repository updates only supplied allowed fields.
   - `updated_by` is set from the current user.

3. **Response is returned**
   - Updated row is returned.
   - Missing row returns `404`.

### Related Backend Flow

```text
PUT /manageQuestions/updateQDetails/{qa_id}
  -> QuestionUpdate validation
  -> UPDATE nnp_km_qa
  -> return updated row or 404
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_qa` | Direct update | Curated question, answer, rank, status, match threshold, and audit fields. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores curated Q&A updates |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Re-embedding | Trigger re-embedding when question text changes. |
| Status transitions | Restrict invalid status transitions if a publishing workflow is introduced. |
| Versioning | Keep previous answer versions for audit and rollback. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  16. DELETE /manageQuestions/deleteQDetail/{qa_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint soft-deletes a curated Q&A pair by setting its status to <strong>DELETED</strong>.
</div>

### Complete Working Flow

1. **Delete request is received**
   - The API receives `qa_id` as a path parameter.

2. **Q&A row is soft-deleted**
   - The repository updates `nnp_km_qa.status` to `DELETED`.

3. **Response is returned**
   - The deleted row is returned.
   - Missing row returns `404`.

### Related Backend Flow

```text
DELETE /manageQuestions/deleteQDetail/{qa_id}
  -> UPDATE nnp_km_qa status=DELETED
  -> return deleted row or 404
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_qa` | Direct update | Curated Q&A lifecycle status and audit-related row data. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores soft-delete state for curated Q&A |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| External embedding process | Separate service/process | Should remove or ignore any embedded version of the deleted question if embeddings exist. |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Embedding cleanup | Delete or deactivate related question embeddings when a Q&A is deleted. |
| Audit | Store deleted_by and deleted_at explicitly. |
| Restore flow | Add an undelete/restore path if soft-delete is intended to be reversible. |

---

<h1 style="color:#1f4e79; border-bottom:3px solid #53a7ba; padding-bottom:8px;">
  SQL Query APIs
</h1>

<p>
  This section covers SQL data-source configuration, Vanna training context, NL-to-SQL generation, query history, and feedback APIs.
</p>

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  17. GET /manageDataSql/getDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint loads SQL databases registered under one or more buckets.
  Each database is returned with nested saved SQL queries, DDL entries, and business rules.
</div>

### Complete Working Flow

1. **Request is received**
   - Required query parameter: `bucketIds`, a comma-separated UUID list.
   - Optional query parameter: `includeDeleted`.

2. **Databases are loaded**
   - `nnp_km_database` is queried for the requested bucket IDs.
   - Deleted databases are excluded unless requested.

3. **Nested training context is loaded**
   - Saved SQL queries are loaded from `nnp_database_q`.
   - DDL rows are loaded from `nnp_database_ddl`.
   - Rule rows are loaded from `nnp_database_rule`.

4. **Response is returned**
   - Each database row includes `queries`, `ddl`, and `rules` arrays.

### Related Backend Flow

```text
GET /manageDataSql/getDetails?bucketIds=id1,id2
  -> parse bucketIds
  -> SELECT nnp_km_database
  -> SELECT nnp_database_q / nnp_database_ddl / nnp_database_rule
  -> attach nested arrays
  -> return database list
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_database` | Direct read | Registered database metadata, connection URL, training script, keywords, status, Vanna embedding backend, and audit fields. |
| `nnp_database_q` | Nested read | Curated SQL question/query pairs for each database. |
| `nnp_database_ddl` | Nested read | DDL/schema training entries for each database. |
| `nnp_database_rule` | Nested read | Business-rule/documentation training entries for each database. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores SQL database registry and nested training context |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| CoreComp schema + migrations | Database schema | Base schema provides database/query tables; migrations add DDL/rule tables and Vanna backend fields |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Empty input handling | Return clear validation errors when `bucketIds` is missing or empty. |
| Pagination | Add paging for large database/training-context sets. |
| Filtering | Add status, area, database type, and keyword filters. |
| Schema alignment | Fold SQL migrations into the canonical schema file. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  18. POST /manageDataSql/addDBDetails
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint registers a SQL database under a bucket and optionally starts Vanna training from the database training script.
</div>

### Complete Working Flow

1. **Request is validated**
   - `bucket_id` and `database_name` are required.
   - `connection_url` must not contain inline credentials.
   - Status is validated against database lifecycle values.

2. **Database row is inserted**
   - A row is inserted into `nnp_km_database`.
   - `vanna_embedding_backend` is selected from `MODEL_TYPE`.
   - Default status is `ACTIVE` when not supplied.

3. **Training starts in background**
   - If `training_script` exists, `sql_query_service.train_from_script` is called.
   - Vanna parses schema, rules, and examples.
   - Vectors are written into PGVector collections.

4. **Response is returned**
   - The created database row is returned immediately.

### Related Backend Flow

```text
POST /manageDataSql/addDBDetails
  -> DatabaseCreate validation
  -> INSERT nnp_km_database
  -> background Vanna train_from_script
  -> return database row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_database` | Direct write | SQL database registry row, training script, connection metadata, area, keywords, status, and audit fields. |
| PGVector tables | Training write | Vanna vector collections for SQL examples, DDL, and documentation/rules. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores the registered database row |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna | NL-to-SQL framework | Trains database-specific retrieval context |
| PGVector / LangChain Postgres | Vector store | Stores Vanna SQL, DDL, and documentation embeddings |
| Ollama | Local LLM runtime | Powers SQL generation through Vanna |
| OpenAI or local HuggingFace embeddings | Model provider/runtime | Embeds Vanna training content depending on backend configuration |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Credential safety | Avoid storing `connection_credential`; move credentials to a secret manager or runtime-only flow. |
| Bucket validation | Verify bucket existence and access before insert. |
| Training status | Store training status, last trained timestamp, and training errors. |
| Connection testing | Add optional connection test before saving the database. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  19. PUT /manageDataSql/updateDBDetails/{db_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint updates a registered SQL database and retrains Vanna context when a training script is present.
</div>

### Complete Working Flow

1. **Request is validated**
   - Connection URLs are checked for inline credentials.
   - Status values are validated.

2. **Database row is updated**
   - Allowed fields are updated in `nnp_km_database`.
   - `updated_by` is set from current user context.

3. **Training starts in background**
   - The updated `training_script` is sent to Vanna training.
   - The cached Vanna instance is cleared after training.

4. **Response is returned**
   - Updated row is returned.
   - Missing row returns `404`.

### Related Backend Flow

```text
PUT /manageDataSql/updateDBDetails/{db_id}
  -> DatabaseUpdate validation
  -> UPDATE nnp_km_database
  -> background Vanna train_from_script
  -> return database row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_database` | Direct update | Mutable database metadata, connection details, training script, keywords, and status. |
| PGVector tables | Training refresh | Database-specific Vanna training vectors. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores database metadata updates |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training | Rebuilds or refreshes database-specific training context |
| Ollama | Local LLM runtime | Used later by trained Vanna instances for SQL generation |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Training observability | Persist retraining result instead of only logging failures. |
| Partial retraining | Retrain only changed sections of the training script. |
| Concurrency | Prevent overlapping training jobs for the same database. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  20. DELETE /manageDataSql/deleteDBDetail/{db_id}
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint soft-deletes a registered SQL database and clears its Vanna training vectors in the background.
</div>

### Complete Working Flow

1. **Database is soft-deleted**
   - `nnp_km_database.status` is set to `DELETED`.

2. **Training cleanup starts**
   - A background task calls `vanna_service.clear_training`.
   - Existing Vanna training data for the database is removed best-effort.

3. **Response is returned**
   - Deleted row is returned.
   - Missing row returns `404`.

### Related Backend Flow

```text
DELETE /manageDataSql/deleteDBDetail/{db_id}
  -> UPDATE nnp_km_database status=DELETED
  -> background clear Vanna training
  -> return database row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_database` | Direct update | Database lifecycle state. |
| PGVector tables | Training delete | Vanna vectors associated with the deleted database. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores database soft-delete state |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training store | Removes database-specific training vectors |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Cleanup tracking | Store vector-cleanup status and failures. |
| Cascade policy | Decide how saved queries, DDL, rules, history, and feedback should behave after DB deletion. |
| Restore path | Define whether deleted database rows can be restored and retrained. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  21-23. Saved SQL Query APIs
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  These endpoints manage curated SQL query examples for a database.
  Saved query pairs can also train Vanna so future natural-language questions retrieve better SQL examples.
</div>

### Endpoints Covered

| # | Endpoint | Purpose |
|---|----------|---------|
| 21 | `POST /manageDataSql/addSQLDetails` | Create a saved SQL query and train it when question + SQL are present |
| 22 | `PUT /manageDataSql/updateSQLDetails/{sql_id}` | Update a saved SQL query and retrain it |
| 23 | `DELETE /manageDataSql/deleteSQLDetail/{sql_id}` | Soft-delete a saved SQL query and remove matching Vanna training data |

### Complete Working Flow

1. **Create**
   - Inserts a row into `nnp_database_q`.
   - Defaults status to `DRAFT`.
   - If `query_context` and `query_text` exist, Vanna is trained with question/SQL.

2. **Update**
   - Updates allowed fields in `nnp_database_q`.
   - If query context and SQL exist after update, Vanna is trained again.

3. **Delete**
   - Sets status to `DELETED`.
   - If the row has question/SQL, Vanna training data is searched and matching vector data is removed.

### Related Backend Flow

```text
POST addSQLDetails
  -> INSERT nnp_database_q
  -> optional Vanna train(question, sql)

PUT updateSQLDetails/{sql_id}
  -> UPDATE nnp_database_q
  -> optional Vanna train(question, sql)

DELETE deleteSQLDetail/{sql_id}
  -> UPDATE nnp_database_q status=DELETED
  -> optional Vanna remove_training_data
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_database_q` | Direct write/update | Curated SQL query name, description, natural-language context, SQL text, status, rank, quality score, and audit fields. |
| `nnp_km_database` | Conditional read | Parent database details needed to select the Vanna instance. |
| PGVector tables | Training write/delete | Vanna question/SQL example vectors. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores saved query rows and parent DB metadata |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training | Stores/removes curated question-to-SQL examples |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Vector mapping | Store returned Vanna vector IDs reliably for exact cleanup. |
| Validation | Validate SQL text is read-only or conforms to allowed patterns. |
| Versioning | Preserve previous SQL versions after edits. |
| Duplicate detection | Prevent duplicate question/SQL examples per database. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  24-26. DDL Training APIs
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  These endpoints manage DDL/schema training text for a registered database.
  DDL text is trained into Vanna so SQL generation understands table and column structure.
</div>

### Endpoints Covered

| # | Endpoint | Purpose |
|---|----------|---------|
| 24 | `POST /manageDataSql/addDDLDetails` | Add DDL text and train it into Vanna |
| 25 | `PUT /manageDataSql/updateDDLDetails/{ddl_id}` | Update DDL text and retrain the vector |
| 26 | `DELETE /manageDataSql/deleteDDLDetail/{ddl_id}` | Soft-delete DDL text and remove its Vanna vector |

### Complete Working Flow

1. **Create**
   - Inserts a row into `nnp_database_ddl`.
   - Trains Vanna with `ddl_text`.
   - Stores returned `vanna_vector_id` when available.

2. **Update**
   - Updates DDL row fields.
   - If `ddl_text` changes, old Vanna vector is removed and new DDL is trained.

3. **Delete**
   - Sets DDL status to `DELETED`.
   - Removes Vanna training data using `vanna_vector_id` when present.

### Related Backend Flow

```text
POST addDDLDetails
  -> INSERT nnp_database_ddl
  -> Vanna train(ddl)
  -> UPDATE vanna_vector_id

PUT updateDDLDetails/{ddl_id}
  -> UPDATE nnp_database_ddl
  -> remove old vector and train new DDL

DELETE deleteDDLDetail/{ddl_id}
  -> UPDATE status=DELETED
  -> remove Vanna vector
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_database_ddl` | Direct write/update | DDL text, table name, status, Vanna vector ID, and audit fields. |
| `nnp_km_database` | Conditional read | Parent database used to locate the Vanna instance. |
| PGVector tables | Training write/delete | Vanna DDL embeddings. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores DDL rows and parent DB metadata |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training | Stores/removes DDL training vectors |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| DDL validation | Validate DDL syntax or extract table names automatically. |
| Batch training | Train multiple table DDL entries in one operation. |
| Cleanup reliability | Reconcile rows whose Vanna vector update failed after DB insert. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  27-29. Business Rule Training APIs
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  These endpoints manage business rules and documentation that guide SQL generation.
  Rules are trained into Vanna as documentation context.
</div>

### Endpoints Covered

| # | Endpoint | Purpose |
|---|----------|---------|
| 27 | `POST /manageDataSql/addRuleDetails` | Add a business rule and train it as documentation |
| 28 | `PUT /manageDataSql/updateRuleDetails/{rule_id}` | Update a business rule and retrain it |
| 29 | `DELETE /manageDataSql/deleteRuleDetail/{rule_id}` | Soft-delete a rule and remove its Vanna vector |

### Complete Working Flow

1. **Create**
   - Inserts a row into `nnp_database_rule`.
   - Trains Vanna with `documentation=rule_text`.
   - Stores returned `vanna_vector_id` when available.

2. **Update**
   - Updates rule fields.
   - If rule text changes, old Vanna vector is removed and new rule text is trained.

3. **Delete**
   - Sets rule status to `DELETED`.
   - Removes Vanna training data using `vanna_vector_id` when present.

### Related Backend Flow

```text
POST addRuleDetails
  -> INSERT nnp_database_rule
  -> Vanna train(documentation)
  -> UPDATE vanna_vector_id

PUT updateRuleDetails/{rule_id}
  -> UPDATE nnp_database_rule
  -> remove old vector and train updated rule

DELETE deleteRuleDetail/{rule_id}
  -> UPDATE status=DELETED
  -> remove Vanna vector
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_database_rule` | Direct write/update | Rule name, rule text, status, Vanna vector ID, and audit fields. |
| `nnp_km_database` | Conditional read | Parent database used to locate the Vanna instance. |
| PGVector tables | Training write/delete | Vanna documentation/rule embeddings. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores business-rule rows and parent DB metadata |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training | Stores/removes documentation training vectors |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Rule categories | Add category/priority fields for rule organization. |
| Conflict checks | Detect conflicting rules for a database. |
| Approval flow | Add review/publish lifecycle before rules affect SQL generation. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  30. POST /manageSqlQuery/query
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint converts a natural-language question into SQL, selects or uses a target database, optionally executes the SQL, and returns generated SQL plus result data.
</div>

### Complete Working Flow

1. **Request is validated**
   - `question` must not be empty.
   - `bucket_ids` must not be empty.
   - Optional fields are `db_id` and `area`.

2. **Candidate databases are loaded**
   - Databases are loaded from `nnp_km_database` for the provided bucket IDs.
   - Area filter is applied when supplied.

3. **Database is selected**
   - If `db_id` is supplied, that database is used when found.
   - If only one database exists, it is selected.
   - Otherwise local embeddings compare the question with database descriptions to choose the closest match.

4. **SQL is generated**
   - Vanna generates SQL using database-specific PGVector context and Ollama.
   - Generated SQL must start with `SELECT`.

5. **SQL is optionally executed**
   - PostgreSQL targets execute through `psycopg2`.
   - ClickHouse/SigNoz targets execute through ClickHouse client.
   - At most 200 rows are returned.

6. **Response is returned**
   - Response includes selected database, generated SQL, result rows, row count, match counts, and any execution error.

### Related Backend Flow

```text
POST /manageSqlQuery/query
  -> validate question and bucket_ids
  -> load candidate DBs from nnp_km_database
  -> select DB by db_id / single DB / local embedding similarity
  -> Vanna generate_sql(question)
  -> optional execute SQL against target DB
  -> return SQL and result data
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_km_database` | Direct read | Candidate databases, connection URLs, credentials, area, database type, and Vanna backend. |
| `nnp_database_q` | Nested read via database loading | Saved query examples included in database context. |
| `nnp_database_ddl` | Nested read via database loading | DDL context for SQL generation. |
| `nnp_database_rule` | Nested read via database loading | Rule/documentation context for SQL generation. |
| PGVector tables | Retrieval | Vanna SQL, DDL, and documentation embeddings. |
| Target database | Query execution | Business/observability data queried by generated SQL. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores registered DB metadata and Vanna PGVector collections |
| `psycopg2-binary` | Python package | Executes generated SQL against PostgreSQL targets and supports backend repository DB access |
| ClickHouse / SigNoz | External database | Optional target database for generated SQL execution |
| Vanna + PGVector | NL-to-SQL engine | Retrieves context and generates SQL |
| Ollama | Local LLM runtime | Generates SQL through Vanna |
| Local HuggingFace embeddings | Local model runtime | Selects the most relevant database when multiple candidates exist |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| SQL safety | Add a stronger SQL parser/allowlist beyond `SELECT` prefix validation. |
| Credentials | Move target DB credentials out of stored JSON. |
| Execution limits | Add timeout, row limit, and cost controls per target database. |
| Auto-training | Keep self-training disabled unless correctness feedback is available. |
| Explainability | Return why a database was selected and which context matched. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  31. POST /manageSqlQuery/promoteQuery
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint promotes a generated SQL result into a curated saved query and trains that question/SQL pair into Vanna.
</div>

### Complete Working Flow

1. **Request is received**
   - Required fields are `database_id`, `question`, and `sql`.
   - Optional fields are query name and description.

2. **Saved query is created**
   - A row is inserted into `nnp_database_q`.
   - Status is `PUBLISHED`.
   - `quality_score` is `1.0`.
   - Rank is `1`.

3. **Vanna training runs**
   - Parent database is loaded.
   - Vanna trains the promoted question/SQL pair.
   - Training failures are logged but do not block response.

### Related Backend Flow

```text
POST /manageSqlQuery/promoteQuery
  -> INSERT nnp_database_q status=PUBLISHED quality_score=1.0
  -> Vanna train(question, sql)
  -> return saved query row
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table / Store | Usage | What It Holds |
|---------------|-------|---------------|
| `nnp_database_q` | Direct write | Promoted curated SQL query. |
| `nnp_km_database` | Conditional read | Parent database needed for Vanna training. |
| PGVector tables | Training write | Promoted question/SQL vectors. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores promoted saved query and parent DB metadata |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |
| Vanna + PGVector | NL-to-SQL training | Trains promoted question/SQL pair |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| SQL validation | Validate promoted SQL before training. |
| Duplicate handling | Prevent multiple promoted rows for the same question/SQL pair. |
| Review workflow | Add approval before promoted queries become training examples. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  32. POST /manageSqlQuery/saveHistory
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint saves a query-history row for the current user.
  It is intentionally best-effort: failures are logged and return a soft failure payload.
</div>

### Complete Working Flow

1. **Request is received**
   - Payload includes question, optional SQL text, database info, area, row count, and error flag.

2. **User is resolved**
   - Current user is read from request headers.

3. **History row is inserted**
   - A row is inserted into `nnp_km_query_history`.

4. **Response is returned**
   - Created row is returned.
   - On failure, endpoint returns `{ "saved": false }`.

### Related Backend Flow

```text
POST /manageSqlQuery/saveHistory
  -> current user
  -> INSERT nnp_km_query_history
  -> return row or saved=false
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_query_history` | Direct write | User query history, SQL text, DB metadata, row count, and error flag. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores query history rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| API ownership | Split Knowledge Base history and SQL history if their retention/display rules differ. |
| Retention | Add retention policy and cleanup job. |
| Failure semantics | Return proper error status when history save is critical. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  33. POST /manageSqlQuery/submitFeedback
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint records thumbs-up or thumbs-down feedback for a generated SQL result.
</div>

### Complete Working Flow

1. **Request is validated**
   - `feedback` must be `1` or `-1`.

2. **User is resolved**
   - Current user is read from request headers.

3. **Feedback row is inserted**
   - A row is inserted into `nnp_km_query_feedback`.

4. **Response is returned**
   - Created row is returned.
   - On failure, endpoint returns `{ "saved": false }`.

### Related Backend Flow

```text
POST /manageSqlQuery/submitFeedback
  -> validate feedback in (1, -1)
  -> INSERT nnp_km_query_feedback
  -> return row or saved=false
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_query_feedback` | Direct write | User ID, question, SQL text, database ID, numeric feedback, comment, and created timestamp. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores query feedback rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Feedback learning | Use positive feedback to promote examples and negative feedback to suppress bad patterns. |
| Linkage | Store history ID or query run ID for stronger correlation. |
| Validation | Validate that referenced DB/query belongs to the user scope. |

---

<h2 style="color:#375623; border-left:5px solid #70ad47; padding-left:10px;">
  34. GET /manageSqlQuery/getHistory
</h2>

<h3 style="color:#4a77b4;">Objective</h3>

<div style="border-left:4px solid #4a77b4; background:#f3f8fc; padding:10px 14px; margin:10px 0;">
  This endpoint returns recent query-history rows for the current user.
</div>

### Complete Working Flow

1. **Request is received**
   - Optional `limit` defaults to `30`.
   - Limit must be between `1` and `100`.

2. **User is resolved**
   - Current user is read from request headers.

3. **History is loaded**
   - `nnp_km_query_history` is queried for that user.
   - Rows are ordered by newest first.

4. **Response is returned**
   - History rows are returned.
   - On failure, endpoint returns an empty array.

### Related Backend Flow

```text
GET /manageSqlQuery/getHistory?limit=30
  -> current user
  -> SELECT nnp_km_query_history
  -> ORDER BY created_at DESC
  -> return rows or []
```

<h3 style="color:#4a77b4;">Tables</h3>

| Table | Usage | What It Holds |
|-------|-------|---------------|
| `nnp_km_query_history` | Direct read | Recent user query history across SQL and currently shared history use cases. |

<h3 style="color:#4a77b4;">Dependencies</h3>

| Dependency | Type | Purpose |
|------------|------|---------|
| PostgreSQL | Database | Stores query history rows |
| `psycopg2-binary` | Python package | PostgreSQL driver used by the service connection pool and repository cursor layer |

<h3 style="color:#4a77b4;">Improvement Scope</h3>

| Area | Future Improvement |
|------|--------------------|
| Type separation | Add a source/type field to distinguish Knowledge Base history from SQL history. |
| Search/filter | Filter history by area, DB, error status, or query type. |
| Pagination | Add cursor-based pagination for long histories. |
