-- SCHEMA: nnp-rag
-- PostgreSQL 14+ (requires the pgvector extension to be installed on the server).

BEGIN;

-- Install pgvector in this database when the server has the extension package.
-- Installing the server/OS package itself cannot be performed from portable SQL.
DO $block$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_available_extensions
            WHERE name = 'vector'
        ) THEN
            RAISE EXCEPTION USING
                MESSAGE = 'pgvector is not installed on the PostgreSQL server',
                HINT = 'Install the pgvector server package for this PostgreSQL version, then rerun this script.';
        END IF;

        EXECUTE 'CREATE EXTENSION vector';
    END IF;
END;
$block$;

-- DROP SCHEMA IF EXISTS "nnp-rag" ;

CREATE SCHEMA IF NOT EXISTS "nnp-rag"
    AUTHORIZATION postgres;

CREATE OR REPLACE FUNCTION "nnp-rag".set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$function$;

CREATE SEQUENCE IF NOT EXISTS "nnp-rag".nnp_km_query_feedback_id_seq
    AS bigint;

CREATE SEQUENCE IF NOT EXISTS "nnp-rag".nnp_km_query_history_id_seq
    AS bigint;

-- Table: nnp-rag.langchain_pg_collection

-- DROP TABLE IF EXISTS "nnp-rag".langchain_pg_collection;

CREATE TABLE IF NOT EXISTS "nnp-rag".langchain_pg_collection
(
    uuid uuid NOT NULL,
    name character varying COLLATE pg_catalog."default" NOT NULL,
    cmetadata json,
    CONSTRAINT langchain_pg_collection_pkey PRIMARY KEY (uuid),
    CONSTRAINT langchain_pg_collection_name_key UNIQUE (name)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".langchain_pg_collection
    OWNER to postgres;

-- Table: nnp-rag.langchain_pg_embedding

-- DROP TABLE IF EXISTS "nnp-rag".langchain_pg_embedding;

CREATE TABLE IF NOT EXISTS "nnp-rag".langchain_pg_embedding
(
    id character varying COLLATE pg_catalog."default" NOT NULL,
    collection_id uuid,
    embedding vector,
    document character varying COLLATE pg_catalog."default",
    cmetadata jsonb,
    CONSTRAINT langchain_pg_embedding_pkey PRIMARY KEY (id),
    CONSTRAINT langchain_pg_embedding_collection_id_fkey FOREIGN KEY (collection_id)
        REFERENCES "nnp-rag".langchain_pg_collection (uuid) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".langchain_pg_embedding
    OWNER to postgres;
-- Index: ix_cmetadata_gin

-- DROP INDEX IF EXISTS "nnp-rag".ix_cmetadata_gin;

CREATE INDEX IF NOT EXISTS ix_cmetadata_gin
    ON "nnp-rag".langchain_pg_embedding USING gin
    (cmetadata jsonb_path_ops)
    WITH (fastupdate=True, gin_pending_list_limit=4194304)
    TABLESPACE pg_default;

-- Table: nnp-rag.model_details

-- DROP TABLE IF EXISTS "nnp-rag".model_details;

CREATE TABLE IF NOT EXISTS "nnp-rag".model_details
(
    "ModelName" character varying COLLATE pg_catalog."default" NOT NULL,
    "API_Key" character varying COLLATE pg_catalog."default",
    "Status" character varying COLLATE pg_catalog."default" NOT NULL,
    "Model_Type" character varying COLLATE pg_catalog."default" NOT NULL,
    "Usage" character varying COLLATE pg_catalog."default",
    CONSTRAINT model_details_pkey PRIMARY KEY ("ModelName")
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".model_details
    OWNER to postgres;

-- Table: nnp-rag.nnp_account_bucket_map

-- DROP TABLE IF EXISTS "nnp-rag".nnp_account_bucket_map;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_account_bucket_map
(
    account_id character varying(64) COLLATE pg_catalog."default" NOT NULL,
    bucket_id uuid NOT NULL,
    ownership character varying(20) COLLATE pg_catalog."default",
    CONSTRAINT pk_account_bucket_map PRIMARY KEY (account_id, bucket_id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_account_bucket_map
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_account_bucket_map
    IS 'Many-to-many mapping of external PORTAL accounts to knowledge buckets.';

COMMENT ON COLUMN "nnp-rag".nnp_account_bucket_map.account_id
    IS 'External PORTAL account identifier; intentionally has no database foreign key.';

COMMENT ON COLUMN "nnp-rag".nnp_account_bucket_map.bucket_id
    IS 'FK -> nnp_km_buckets.id (ON DELETE CASCADE). Implicitly NOT NULL as part of the PK.';

COMMENT ON COLUMN "nnp-rag".nnp_account_bucket_map.ownership
    IS 'Bucket access role used by the API: owner or readonly.';
-- Index: ix_abm_bucket

-- DROP INDEX IF EXISTS "nnp-rag".ix_abm_bucket;

CREATE INDEX IF NOT EXISTS ix_abm_bucket
    ON "nnp-rag".nnp_account_bucket_map USING btree
    (bucket_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Table: nnp-rag.nnp_bucket_details

-- DROP TABLE IF EXISTS "nnp-rag".nnp_bucket_details;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_bucket_details
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    bucket_id uuid,
    doc_category character varying(32) COLLATE pg_catalog."default",
    doc_name character varying(512) COLLATE pg_catalog."default",
    description text COLLATE pg_catalog."default",
    format character varying(32) COLLATE pg_catalog."default",
    doc_size bigint,
    status character varying(20) COLLATE pg_catalog."default" DEFAULT 'PENDING'::character varying,
    error_detail text COLLATE pg_catalog."default",
    milvus_source_id character varying(512) COLLATE pg_catalog."default",
    milvus_chunks_stored integer DEFAULT 0,
    milvus_chunks_duplicated integer DEFAULT 0,
    ingest_request_id character varying(16) COLLATE pg_catalog."default",
    ingested_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(128) COLLATE pg_catalog."default",
    updated_by character varying(128) COLLATE pg_catalog."default",
    CONSTRAINT pk_nnp_bucket_details PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_bucket_details
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_bucket_details
    IS 'Document metadata mirrored from bucket ingestion into Milvus.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.id
    IS 'Primary key (UUID).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.bucket_id
    IS 'FK -> nnp_km_buckets.id (ON DELETE CASCADE).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.doc_category
    IS 'Source type, aligned to the ingestion endpoints: document/web/git/gdrive/redmine/argocd. Free text in v1.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.doc_name
    IS 'Display name: filename for uploads, URL for web, repo path for git, etc.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.description
    IS 'Optional human description/summary.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.format
    IS 'File format/extension (pdf/docx/yaml/yml/json/html/md/txt).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.doc_size
    IS 'Original document size in bytes (pre-chunking).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.status
    IS 'Ingestion lifecycle. Created as PENDING; the async ingestion callback flips it to INGESTED (success) or FAILED (failure). Also DELETED. Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.error_detail
    IS 'Last error message captured on ingestion failure. NULL when healthy.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.milvus_source_id
    IS 'Ingestion service source_id (e.g. upload:<sha256>, google_drive://<id>, <repo>/<path>, <redmine_url>/issues/<id>). Enables delete_by_source round-trip.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.milvus_chunks_stored
    IS 'Vectors actually written to Milvus (details.vectors_stored).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.milvus_chunks_duplicated
    IS 'Chunks skipped as duplicates (details.duplicates_skipped).';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.ingest_request_id
    IS 'Ingestion service X-Request-ID (8 chars) for backend log correlation.';

COMMENT ON COLUMN "nnp-rag".nnp_bucket_details.ingested_at
    IS 'Timestamp of the successful ingest call (distinct from created_at if row created PENDING first).';
-- Index: ix_bd_bucket

-- DROP INDEX IF EXISTS "nnp-rag".ix_bd_bucket;

CREATE INDEX IF NOT EXISTS ix_bd_bucket
    ON "nnp-rag".nnp_bucket_details USING btree
    (bucket_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_bd_bucket_cat

-- DROP INDEX IF EXISTS "nnp-rag".ix_bd_bucket_cat;

CREATE INDEX IF NOT EXISTS ix_bd_bucket_cat
    ON "nnp-rag".nnp_bucket_details USING btree
    (bucket_id ASC NULLS LAST, doc_category COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_bd_bucket_source

-- DROP INDEX IF EXISTS "nnp-rag".ix_bd_bucket_source;

CREATE INDEX IF NOT EXISTS ix_bd_bucket_source
    ON "nnp-rag".nnp_bucket_details USING btree
    (bucket_id ASC NULLS LAST, milvus_source_id COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_bd_bucket_status

-- DROP INDEX IF EXISTS "nnp-rag".ix_bd_bucket_status;

CREATE INDEX IF NOT EXISTS ix_bd_bucket_status
    ON "nnp-rag".nnp_bucket_details USING btree
    (bucket_id ASC NULLS LAST, status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Trigger: trg_bd_updated_at

-- DROP TRIGGER IF EXISTS trg_bd_updated_at ON "nnp-rag".nnp_bucket_details;

CREATE OR REPLACE TRIGGER trg_bd_updated_at
    BEFORE UPDATE 
    ON "nnp-rag".nnp_bucket_details
    FOR EACH ROW
    EXECUTE FUNCTION "nnp-rag".set_updated_at();

-- Table: nnp-rag.nnp_database_ddl

-- DROP TABLE IF EXISTS "nnp-rag".nnp_database_ddl;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_database_ddl
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    database_id uuid NOT NULL,
    table_name character varying(255) COLLATE pg_catalog."default",
    ddl_text text COLLATE pg_catalog."default" NOT NULL,
    vanna_vector_id character varying COLLATE pg_catalog."default",
    status character varying(50) COLLATE pg_catalog."default" DEFAULT 'ACTIVE'::character varying,
    created_by character varying(100) COLLATE pg_catalog."default",
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    updated_by character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT nnp_database_ddl_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_database_ddl
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_database_ddl
    IS 'DDL training entries associated with a registered database.';
-- Index: idx_nnp_database_ddl_db

-- DROP INDEX IF EXISTS "nnp-rag".idx_nnp_database_ddl_db;

CREATE INDEX IF NOT EXISTS idx_nnp_database_ddl_db
    ON "nnp-rag".nnp_database_ddl USING btree
    (database_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Table: nnp-rag.nnp_database_q

-- DROP TABLE IF EXISTS "nnp-rag".nnp_database_q;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_database_q
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    database_id uuid,
    query_name character varying(255) COLLATE pg_catalog."default",
    query_desc text COLLATE pg_catalog."default",
    query_context text COLLATE pg_catalog."default",
    query_text text COLLATE pg_catalog."default",
    status character varying(20) COLLATE pg_catalog."default" DEFAULT 'DRAFT'::character varying,
    rank smallint,
    milvus_exemplar_id character varying(128) COLLATE pg_catalog."default",
    quality_score numeric(3,2) DEFAULT 1.00,
    times_used bigint DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(128) COLLATE pg_catalog."default",
    updated_by character varying(128) COLLATE pg_catalog."default",
    CONSTRAINT pk_nnp_database_q PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_database_q
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_database_q
    IS 'Curated SQL queries and Vanna question-to-SQL exemplars per registered database.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.id
    IS 'Primary key (UUID).';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.database_id
    IS 'FK -> nnp_km_database.id (ON DELETE CASCADE).';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.query_name
    IS 'Display name of the saved query.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.query_desc
    IS 'Free-text description.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.query_context
    IS 'Either the natural-language question (Vanna training pair) or a free-text label/grouping. Semantics to be finalised.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.query_text
    IS 'The SQL query text.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.status
    IS 'Curation lifecycle. Expected DRAFT/PUBLISHED/ARCHIVED. Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.rank
    IS 'User-supplied priority, expected 1..5 (same scale as nnp_km_qa.rank). Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.milvus_exemplar_id
    IS 'If promoted from a SQL-service auto-exemplar, the source Milvus primary key.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.quality_score
    IS 'Curated quality, expected 0..1. Default 1.00 distinguishes hand-curated from the 0.70 auto-captured exemplars in Milvus.';

COMMENT ON COLUMN "nnp-rag".nnp_database_q.times_used
    IS 'Usage counter for most-used saved-query reporting.';
-- Index: ix_dq_database

-- DROP INDEX IF EXISTS "nnp-rag".ix_dq_database;

CREATE INDEX IF NOT EXISTS ix_dq_database
    ON "nnp-rag".nnp_database_q USING btree
    (database_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_dq_database_rank

-- DROP INDEX IF EXISTS "nnp-rag".ix_dq_database_rank;

CREATE INDEX IF NOT EXISTS ix_dq_database_rank
    ON "nnp-rag".nnp_database_q USING btree
    (database_id ASC NULLS LAST, rank ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_dq_database_status

-- DROP INDEX IF EXISTS "nnp-rag".ix_dq_database_status;

CREATE INDEX IF NOT EXISTS ix_dq_database_status
    ON "nnp-rag".nnp_database_q USING btree
    (database_id ASC NULLS LAST, status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Trigger: trg_dq_updated_at

-- DROP TRIGGER IF EXISTS trg_dq_updated_at ON "nnp-rag".nnp_database_q;

CREATE OR REPLACE TRIGGER trg_dq_updated_at
    BEFORE UPDATE 
    ON "nnp-rag".nnp_database_q
    FOR EACH ROW
    EXECUTE FUNCTION "nnp-rag".set_updated_at();

-- Table: nnp-rag.nnp_database_rule

-- DROP TABLE IF EXISTS "nnp-rag".nnp_database_rule;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_database_rule
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    database_id uuid NOT NULL,
    rule_name character varying(255) COLLATE pg_catalog."default",
    rule_text text COLLATE pg_catalog."default" NOT NULL,
    vanna_vector_id character varying COLLATE pg_catalog."default",
    status character varying(50) COLLATE pg_catalog."default" DEFAULT 'ACTIVE'::character varying,
    created_by character varying(100) COLLATE pg_catalog."default",
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    updated_by character varying(100) COLLATE pg_catalog."default",
    CONSTRAINT nnp_database_rule_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_database_rule
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_database_rule
    IS 'Natural-language Vanna training rules associated with a registered database.';
-- Index: idx_nnp_database_rule_db

-- DROP INDEX IF EXISTS "nnp-rag".idx_nnp_database_rule_db;

CREATE INDEX IF NOT EXISTS idx_nnp_database_rule_db
    ON "nnp-rag".nnp_database_rule USING btree
    (database_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Table: nnp-rag.nnp_km_buckets

-- DROP TABLE IF EXISTS "nnp-rag".nnp_km_buckets;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_km_buckets
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    bucket_category character varying(64) COLLATE pg_catalog."default",
    bucket_name character varying(255) COLLATE pg_catalog."default",
    bucket_desc text COLLATE pg_catalog."default",
    bucket_size bigint DEFAULT 0,
    bucket_spec text COLLATE pg_catalog."default",
    bucket_url character varying(2048) COLLATE pg_catalog."default",
    status character varying(20) COLLATE pg_catalog."default" DEFAULT 'PROVISIONING'::character varying,
    error_detail text COLLATE pg_catalog."default",
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(128) COLLATE pg_catalog."default",
    updated_by character varying(128) COLLATE pg_catalog."default",
    embedding_backend character varying(20) COLLATE pg_catalog."default" DEFAULT 'openai'::character varying,
    CONSTRAINT pk_nnp_km_buckets PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_km_buckets
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_km_buckets
    IS 'Top-level knowledge bucket. Account linkage is through nnp_account_bucket_map.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.id
    IS 'Primary key (UUID). Implicitly NOT NULL as a PK.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_category
    IS 'Classification/grouping label shown as the "Bucket Category" dropdown in the UI. Free text in v1.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_name
    IS 'Display name and Milvus collection name. Naming and uniqueness are application-validated.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_desc
    IS 'Free-form bucket description.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_size
    IS 'Denormalised total size (bytes) of documents in the bucket. Maintenance strategy TBD (trigger vs recompute).';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_spec
    IS 'Free-form bucket configuration stored as text (e.g. default top_k / similarity_threshold / source weights). Concrete shape TBD.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.bucket_url
    IS 'Optional pointer (external schema doc or Milvus reference). Semantics TBD.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.status
    IS 'Lifecycle state. Created as PROVISIONING; the async Milvus-provision callback flips it to ACTIVE (success) or FAILED (failure). Also INACTIVE/ARCHIVED/DELETED. Soft-delete is the intended delete mechanism. Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.error_detail
    IS 'Last error message captured on failure (primarily Milvus collection provisioning). NULL when healthy.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.created_by
    IS 'PORTAL user identifier that created the row (from the X-User-Name cookie/header).';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.updated_by
    IS 'PORTAL user identifier that last updated the row.';

COMMENT ON COLUMN "nnp-rag".nnp_km_buckets.embedding_backend
    IS 'Embedding backend for the bucket Milvus collection: openai (3072 dimensions) or local (384 dimensions).';
-- Index: ix_bucket_name

-- DROP INDEX IF EXISTS "nnp-rag".ix_bucket_name;

CREATE INDEX IF NOT EXISTS ix_bucket_name
    ON "nnp-rag".nnp_km_buckets USING btree
    (bucket_name COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_bucket_status

-- DROP INDEX IF EXISTS "nnp-rag".ix_bucket_status;

CREATE INDEX IF NOT EXISTS ix_bucket_status
    ON "nnp-rag".nnp_km_buckets USING btree
    (status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Trigger: trg_bucket_updated_at

-- DROP TRIGGER IF EXISTS trg_bucket_updated_at ON "nnp-rag".nnp_km_buckets;

CREATE OR REPLACE TRIGGER trg_bucket_updated_at
    BEFORE UPDATE 
    ON "nnp-rag".nnp_km_buckets
    FOR EACH ROW
    EXECUTE FUNCTION "nnp-rag".set_updated_at();

-- Table: nnp-rag.nnp_km_database

-- DROP TABLE IF EXISTS "nnp-rag".nnp_km_database;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_km_database
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    bucket_id uuid,
    database_name character varying(255) COLLATE pg_catalog."default",
    database_type character varying(32) COLLATE pg_catalog."default",
    database_desc text COLLATE pg_catalog."default",
    connection_url character varying(2048) COLLATE pg_catalog."default",
    training_script text COLLATE pg_catalog."default",
    keywords text[] COLLATE pg_catalog."default",
    status character varying(20) COLLATE pg_catalog."default" DEFAULT 'ACTIVE'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(128) COLLATE pg_catalog."default",
    updated_by character varying(128) COLLATE pg_catalog."default",
    connection_credential text COLLATE pg_catalog."default",
    area character varying(100) COLLATE pg_catalog."default",
    vanna_embedding_backend character varying(20) COLLATE pg_catalog."default" DEFAULT 'openai'::character varying,
    CONSTRAINT pk_nnp_km_database PRIMARY KEY (id),
    CONSTRAINT nnp_km_database_bucket_id_fkey FOREIGN KEY (bucket_id)
        REFERENCES "nnp-rag".nnp_km_buckets (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_km_database
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_km_database
    IS 'Per-bucket registry of databases available to the SQL query service.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.id
    IS 'Primary key (UUID).';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.bucket_id
    IS 'FK -> nnp_km_buckets.id (ON DELETE CASCADE).';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.database_name
    IS 'Logical database name as known to the SQL service (e.g. nnp_devsecops, signoz_nnp). Matches metadata.database in query responses. Uniqueness per bucket is a UI responsibility in v1.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.database_type
    IS 'Engine type (postgres/clickhouse/mysql/mongodb/signoz). No DB CHECK in v1; validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.database_desc
    IS 'Free-text description. (Corrects the ERD typo DATABESE_DESC.)';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.connection_url
    IS 'Credential-less connection URL. Runtime credentials are handled separately.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.training_script
    IS 'Schema and context used for Vanna training.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.keywords
    IS 'Natural-language routing keywords; intended to replace DatabaseLoader.select_database hardcoding in the SQL service. GIN-indexed.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.status
    IS 'Lifecycle state. Expected ACTIVE/INACTIVE/ARCHIVED/DELETED. Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_km_database.vanna_embedding_backend
    IS 'Vanna embedding backend: openai (3072 dimensions) or local (384 dimensions). Local collections use the nnp_local_{db_id[:8]} prefix.';
-- Index: ix_db_bucket

-- DROP INDEX IF EXISTS "nnp-rag".ix_db_bucket;

CREATE INDEX IF NOT EXISTS ix_db_bucket
    ON "nnp-rag".nnp_km_database USING btree
    (bucket_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_db_bucket_name

-- DROP INDEX IF EXISTS "nnp-rag".ix_db_bucket_name;

CREATE INDEX IF NOT EXISTS ix_db_bucket_name
    ON "nnp-rag".nnp_km_database USING btree
    (bucket_id ASC NULLS LAST, database_name COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_db_bucket_status

-- DROP INDEX IF EXISTS "nnp-rag".ix_db_bucket_status;

CREATE INDEX IF NOT EXISTS ix_db_bucket_status
    ON "nnp-rag".nnp_km_database USING btree
    (bucket_id ASC NULLS LAST, status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_db_keywords

-- DROP INDEX IF EXISTS "nnp-rag".ix_db_keywords;

CREATE INDEX IF NOT EXISTS ix_db_keywords
    ON "nnp-rag".nnp_km_database USING gin
    (keywords COLLATE pg_catalog."default")
    WITH (fastupdate=True, gin_pending_list_limit=4194304)
    TABLESPACE pg_default;

-- Trigger: trg_db_updated_at

-- DROP TRIGGER IF EXISTS trg_db_updated_at ON "nnp-rag".nnp_km_database;

CREATE OR REPLACE TRIGGER trg_db_updated_at
    BEFORE UPDATE 
    ON "nnp-rag".nnp_km_database
    FOR EACH ROW
    EXECUTE FUNCTION "nnp-rag".set_updated_at();

-- Table: nnp-rag.nnp_km_qa

-- DROP TABLE IF EXISTS "nnp-rag".nnp_km_qa;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_km_qa
(
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    bucket_id uuid,
    question text COLLATE pg_catalog."default",
    answer text COLLATE pg_catalog."default",
    rank smallint,
    status character varying(20) COLLATE pg_catalog."default" DEFAULT 'DRAFT'::character varying,
    question_embedding_id character varying(128) COLLATE pg_catalog."default",
    match_threshold numeric(4,3),
    times_matched bigint DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by character varying(128) COLLATE pg_catalog."default",
    updated_by character varying(128) COLLATE pg_catalog."default",
    CONSTRAINT pk_nnp_km_qa PRIMARY KEY (id),
    CONSTRAINT nnp_km_qa_bucket_id_fkey FOREIGN KEY (bucket_id)
        REFERENCES "nnp-rag".nnp_km_buckets (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE CASCADE
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_km_qa
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_km_qa
    IS 'Curated question and answer pairs scoped to a knowledge bucket.';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.id
    IS 'Primary key (UUID).';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.bucket_id
    IS 'FK -> nnp_km_buckets.id (ON DELETE CASCADE).';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.question
    IS 'Canonical question text.';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.answer
    IS 'Curated answer, PLAIN TEXT (no HTML/Markdown rendering assumed).';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.rank
    IS 'User-supplied priority, expected 1..5. Validated in UI (no DB CHECK in v1).';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.status
    IS 'Curation lifecycle. Expected DRAFT/PUBLISHED/ARCHIVED. Validated in UI.';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.question_embedding_id
    IS 'Milvus primary key if the question is also embedded for similarity short-circuiting.';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.match_threshold
    IS 'Optional per-row similarity threshold (expected 0..1) above which this answer auto-returns.';

COMMENT ON COLUMN "nnp-rag".nnp_km_qa.times_matched
    IS 'Usage counter: increment when this Q&A short-circuits a query.';
-- Index: ix_qa_bucket

-- DROP INDEX IF EXISTS "nnp-rag".ix_qa_bucket;

CREATE INDEX IF NOT EXISTS ix_qa_bucket
    ON "nnp-rag".nnp_km_qa USING btree
    (bucket_id ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_qa_bucket_rank

-- DROP INDEX IF EXISTS "nnp-rag".ix_qa_bucket_rank;

CREATE INDEX IF NOT EXISTS ix_qa_bucket_rank
    ON "nnp-rag".nnp_km_qa USING btree
    (bucket_id ASC NULLS LAST, rank ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;
-- Index: ix_qa_bucket_status

-- DROP INDEX IF EXISTS "nnp-rag".ix_qa_bucket_status;

CREATE INDEX IF NOT EXISTS ix_qa_bucket_status
    ON "nnp-rag".nnp_km_qa USING btree
    (bucket_id ASC NULLS LAST, status COLLATE pg_catalog."default" ASC NULLS LAST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Trigger: trg_qa_updated_at


-- DROP TRIGGER IF EXISTS trg_qa_updated_at ON "nnp-rag".nnp_km_qa;

CREATE OR REPLACE TRIGGER trg_qa_updated_at
    BEFORE UPDATE 
    ON "nnp-rag".nnp_km_qa
    FOR EACH ROW
    EXECUTE FUNCTION "nnp-rag".set_updated_at();

-- Table: nnp-rag.nnp_km_query_feedback

-- DROP TABLE IF EXISTS "nnp-rag".nnp_km_query_feedback;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_km_query_feedback
(
    id bigint NOT NULL DEFAULT nextval('"nnp-rag".nnp_km_query_feedback_id_seq'::regclass),
    user_id character varying(100) COLLATE pg_catalog."default" NOT NULL,
    question text COLLATE pg_catalog."default",
    sql_text text COLLATE pg_catalog."default",
    db_id character varying(100) COLLATE pg_catalog."default",
    feedback smallint NOT NULL,
    comment text COLLATE pg_catalog."default",
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT nnp_km_query_feedback_pkey PRIMARY KEY (id),
    CONSTRAINT nnp_km_query_feedback_feedback_check CHECK (feedback = ANY (ARRAY[1, '-1'::integer]))
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_km_query_feedback
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_km_query_feedback
    IS 'Positive or negative user feedback for generated SQL.';

-- Table: nnp-rag.nnp_km_query_history

-- DROP TABLE IF EXISTS "nnp-rag".nnp_km_query_history;

CREATE TABLE IF NOT EXISTS "nnp-rag".nnp_km_query_history
(
    id bigint NOT NULL DEFAULT nextval('"nnp-rag".nnp_km_query_history_id_seq'::regclass),
    user_id character varying(100) COLLATE pg_catalog."default" NOT NULL,
    question text COLLATE pg_catalog."default",
    sql_text text COLLATE pg_catalog."default",
    db_id character varying(100) COLLATE pg_catalog."default",
    db_name character varying(255) COLLATE pg_catalog."default",
    area character varying(100) COLLATE pg_catalog."default",
    row_count integer,
    has_error boolean NOT NULL DEFAULT false,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    CONSTRAINT nnp_km_query_history_pkey PRIMARY KEY (id)
)

TABLESPACE pg_default;

ALTER TABLE IF EXISTS "nnp-rag".nnp_km_query_history
    OWNER to postgres;

COMMENT ON TABLE "nnp-rag".nnp_km_query_history
    IS 'Per-user natural-language SQL query execution history.';
-- Index: idx_nnp_km_query_history_user_created

-- DROP INDEX IF EXISTS "nnp-rag".idx_nnp_km_query_history_user_created;

CREATE INDEX IF NOT EXISTS idx_nnp_km_query_history_user_created
    ON "nnp-rag".nnp_km_query_history USING btree
    (user_id COLLATE pg_catalog."default" ASC NULLS LAST, created_at DESC NULLS FIRST)
    WITH (fillfactor=100, deduplicate_items=True)
    TABLESPACE pg_default;

-- Add forward-reference foreign keys after all referenced tables exist.
DO $block$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'nnp_account_bucket_map_bucket_id_fkey'
          AND conrelid = '"nnp-rag".nnp_account_bucket_map'::regclass
    ) THEN
        ALTER TABLE "nnp-rag".nnp_account_bucket_map
            ADD CONSTRAINT nnp_account_bucket_map_bucket_id_fkey
            FOREIGN KEY (bucket_id) REFERENCES "nnp-rag".nnp_km_buckets (id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'nnp_bucket_details_bucket_id_fkey'
          AND conrelid = '"nnp-rag".nnp_bucket_details'::regclass
    ) THEN
        ALTER TABLE "nnp-rag".nnp_bucket_details
            ADD CONSTRAINT nnp_bucket_details_bucket_id_fkey
            FOREIGN KEY (bucket_id) REFERENCES "nnp-rag".nnp_km_buckets (id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'nnp_database_q_database_id_fkey'
          AND conrelid = '"nnp-rag".nnp_database_q'::regclass
    ) THEN
        ALTER TABLE "nnp-rag".nnp_database_q
            ADD CONSTRAINT nnp_database_q_database_id_fkey
            FOREIGN KEY (database_id) REFERENCES "nnp-rag".nnp_km_database (id)
            ON DELETE CASCADE;
    END IF;
END;
$block$;

ALTER SEQUENCE "nnp-rag".nnp_km_query_feedback_id_seq
    OWNED BY "nnp-rag".nnp_km_query_feedback.id;
ALTER SEQUENCE "nnp-rag".nnp_km_query_history_id_seq
    OWNED BY "nnp-rag".nnp_km_query_history.id;

COMMIT;