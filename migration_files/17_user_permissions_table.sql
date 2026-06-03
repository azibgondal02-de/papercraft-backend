CREATE TABLE user_board_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_code VARCHAR(100) NOT NULL,
    class_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_class (user_code, class_id),
    FOREIGN KEY (class_id) REFERENCES classes_bank(class_id)
);