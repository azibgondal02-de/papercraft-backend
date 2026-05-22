-- Subjects
CREATE TABLE subjects_bank (
    subject_id INT PRIMARY KEY AUTO_INCREMENT,
    class_id INT NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    old_subject INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;