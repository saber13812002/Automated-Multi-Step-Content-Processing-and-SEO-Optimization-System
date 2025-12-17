-- Create tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    input_path VARCHAR(500) NOT NULL,
    output_path VARCHAR(500),
    status ENUM('pending', 'processing', 'done', 'failed') DEFAULT 'pending',
    assigned_to VARCHAR(100),
    picked_at DATETIME,
    finished_at DATETIME,
    timeout_minutes INT DEFAULT 120,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_picked_at (picked_at),
    INDEX idx_assigned_to (assigned_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

