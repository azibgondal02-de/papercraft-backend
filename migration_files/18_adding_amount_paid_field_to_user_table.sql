ALTER TABLE users ADD COLUMN amount_paid DECIMAL(10,2) DEFAULT 0.00 AFTER subscription_end;
