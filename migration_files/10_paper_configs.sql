-- Paper Configs
CREATE TABLE paper_configs_bank (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    subject_id INT UNSIGNED NOT NULL,
    sections JSON NOT NULL,
    total_dataset_questions INT UNSIGNED,
    UNIQUE KEY subject (subject_id),
    KEY idx_subject (subject_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;