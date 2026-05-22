-- Questions
CREATE TABLE questions_bank (
    id INT PRIMARY KEY,
    chapter_id INT NOT NULL,
    topic_id VARCHAR(100) NOT NULL,
    type_id INT NOT NULL,
    medium TINYINT NOT NULL,
    statement_en TEXT,
    statement_ur TEXT,
    answer_en TEXT,
    answer_ur TEXT,
    description_en TEXT,
    description_ur TEXT,
    exercise VARCHAR(50),
    exercise_question TINYINT DEFAULT 0,
    past_paper_questions TINYINT(1) DEFAULT 0,
    paragraph_questions VARCHAR(50),
    afaq TINYINT,
    status TINYINT(1) DEFAULT 1,
    status_pef TINYINT(1) DEFAULT 1,
    is_table TINYINT(1) DEFAULT 0,
    is_creative INT DEFAULT 0,
    created_at TIMESTAMP NULL,
    INDEX idx_chapter_topic (chapter_id, topic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

