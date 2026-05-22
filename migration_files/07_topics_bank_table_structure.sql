-- Topics
CREATE TABLE topics_bank (
    topic_code VARCHAR(255) PRIMARY KEY,
    chapter_code VARCHAR(255),
    topic_id VARCHAR(255),
    chapter_id INT,
    topic_name_en VARCHAR(255),
    topic_name_urdu VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;