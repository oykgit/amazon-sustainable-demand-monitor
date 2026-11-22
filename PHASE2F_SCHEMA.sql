-- Phase 2F staging-only ledger. Run manually in Neon SQL Editor.
-- Creates a NEW table; does not modify existing research tables.
-- Notification fingerprint is SHA-256 of eBay notification ID, NOT a user ID.
CREATE TABLE IF NOT EXISTS public.ebay_notification_ledger (
    notification_fingerprint text PRIMARY KEY
        CHECK (length(notification_fingerprint) = 64),
    status text NOT NULL DEFAULT 'received'
        CHECK (status IN ('received', 'processing', 'completed', 'failed')),
    first_seen_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
-- No account identifiers, event bodies, or raw signatures stored.
