DROP DATABASE IF EXISTS workflow;
CREATE DATABASE workflow;

USE workflow;

CREATE TABLE workflow_flow (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    flow_name VARCHAR(128) NOT NULL UNIQUE,
    flow_json JSON NOT NULL,
    enabled TINYINT(1) DEFAULT 0,
    deleted TINYINT(1) DEFAULT 0,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_flow_name (flow_name),
    KEY idx_created_at (created_at),
    KEY idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS workflow_syslog (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    level VARCHAR(16) NOT NULL,
    logger_name VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    PRIMARY KEY (id),
    KEY idx_created_at (created_at),
    KEY idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


