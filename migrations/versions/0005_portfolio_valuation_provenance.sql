ALTER TABLE portfolio_holdings ADD COLUMN IF NOT EXISTS valuation_source VARCHAR(64) NOT NULL DEFAULT 'unresolved';
ALTER TABLE portfolio_holdings ADD COLUMN IF NOT EXISTS valuation_confidence NUMERIC(5,2);
