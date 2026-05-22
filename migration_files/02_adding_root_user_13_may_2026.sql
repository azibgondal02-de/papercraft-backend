INSERT INTO users (
    user_code,
    username,
    email,
    password_hash,
    user_type,
    is_superuser,
    is_active,
    created_by
)
SELECT
    'USR_ROOT',
    'root',
    'root@system.local',
    '$argon2id$v=19$m=65536,t=3,p=4$VQBFEXwiO3Wd8v3sLAUUZQ$ZaIFSts42ufozqJ5MfDu1psE7cOphaDN/cYJI0rFIcg',
    'admin',
    TRUE,
    TRUE,
    'system'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE username = 'root'
);