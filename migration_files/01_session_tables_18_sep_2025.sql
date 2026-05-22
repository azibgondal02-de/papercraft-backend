-- Table to store session details
Create Table  IF NOT EXISTS sessions (
    session_id SERIAL PRIMARY KEY,
    user_code VARCHAR(255) NOT NULL,
    user_type VARCHAR(50) NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Table to store password history
Create Table  IF NOT EXISTS password_history (
    history_id SERIAL PRIMARY KEY,
    user_code VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
