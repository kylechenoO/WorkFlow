USE workflow;

## v0.0.3: Password Policy — user profile for password expiry tracking
CREATE TABLE IF NOT EXISTS wf_user_profile (
    id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id             INT NOT NULL UNIQUE,
    password_changed_at DATETIME(3) DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_up_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
