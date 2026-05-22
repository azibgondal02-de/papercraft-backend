-- Question Options
CREATE TABLE question_options_bank (
    option_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    question_id INT NOT NULL,
    option_en VARCHAR(500),
    option_ur VARCHAR(500),
    is_correct TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



