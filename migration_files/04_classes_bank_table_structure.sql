-- Classes
CREATE TABLE classes_bank (
    class_id INT PRIMARY KEY,
    board_id INT NOT NULL,
    class_name VARCHAR(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;