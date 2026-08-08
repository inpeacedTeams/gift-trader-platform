ALTER TABLE alert_events ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ;
ALTER TABLE alert_events ADD COLUMN IF NOT EXISTS notification_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE alert_events ADD COLUMN IF NOT EXISTS notification_error TEXT;
CREATE INDEX IF NOT EXISTS ix_alert_events_delivery ON alert_events(notification_sent_at, notification_attempts);
