CREATE TABLE IF NOT EXISTS resolver_telemetry (id BIGSERIAL PRIMARY KEY, nft_address VARCHAR(128) NOT NULL, collection_address VARCHAR(128), outcome VARCHAR(32) NOT NULL, method VARCHAR(64) NOT NULL, candidate_count INTEGER NOT NULL DEFAULT 0, confidence DOUBLE PRECISION, metadata_name VARCHAR(255), metadata_model VARCHAR(255), created_at TIMESTAMPTZ NOT NULL);
CREATE INDEX IF NOT EXISTS ix_resolver_telemetry_outcome_time ON resolver_telemetry(outcome, created_at);
CREATE INDEX IF NOT EXISTS ix_resolver_telemetry_nft ON resolver_telemetry(nft_address);
