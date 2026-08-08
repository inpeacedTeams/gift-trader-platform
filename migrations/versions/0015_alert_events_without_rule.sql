-- Not every alert comes from a rule.
--
-- The sniper fires from a watch and an undercut warning fires from owning a
-- listing; neither has an alert_rules row to point at. The column has been
-- NOT NULL since the first migration, so those inserts would have been
-- rejected by the database.
ALTER TABLE alert_events ALTER COLUMN rule_id DROP NOT NULL;
