-- Chapters
CREATE TABLE chapters_bank (
    chapter_code VARCHAR(255) PRIMARY KEY,
    chapter_id INT,
    subject_id INT,
    chapter_name_en VARCHAR(255),
    chapter_name_urdu VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;