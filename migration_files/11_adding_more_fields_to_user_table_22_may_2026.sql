ALTER TABLE users
    ADD COLUMN school_name VARCHAR(200) DEFAULT NULL AFTER email,
    ADD COLUMN owner_name VARCHAR(100) DEFAULT NULL AFTER school_name,
    ADD COLUMN phone_number VARCHAR(20) DEFAULT NULL AFTER owner_name,
    ADD COLUMN city VARCHAR(100) DEFAULT NULL AFTER phone_number,
    ADD COLUMN province VARCHAR(100) DEFAULT NULL AFTER city,
    ADD COLUMN subscription_plan VARCHAR(50) DEFAULT NULL AFTER province,
    ADD COLUMN subscription_start DATE DEFAULT NULL AFTER subscription_plan,
    ADD COLUMN subscription_end DATE DEFAULT NULL AFTER subscription_start,
    ADD COLUMN last_login_at TIMESTAMP DEFAULT NULL AFTER subscription_end,
    ADD COLUMN admin_notes TEXT DEFAULT NULL AFTER last_login_at;