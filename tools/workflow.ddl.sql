DROP DATABASE IF EXISTS workflow;
CREATE DATABASE workflow;

USE workflow;

CREATE TABLE wf_flow (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    flow_name VARCHAR(128) NOT NULL UNIQUE,
    flow_procedures JSON NOT NULL,
    enabled TINYINT(1) DEFAULT 0,
    deleted TINYINT(1) DEFAULT 0,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_flow_name (flow_name),
    KEY idx_created_at (created_at),
    KEY idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_syslog (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    level VARCHAR(16) NOT NULL,
    logger_name VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    PRIMARY KEY (id),
    KEY idx_created_at (created_at),
    KEY idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_role (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_user_role (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_id BIGINT UNSIGNED NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_role_user (role_id, user_id),
    KEY idx_role_id (role_id),
    KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_audit_log (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id INT DEFAULT NULL,
    action VARCHAR(32) NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_name VARCHAR(128) NOT NULL,
    detail JSON DEFAULT NULL,
    ip_address VARCHAR(45) DEFAULT NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_user_id (user_id),
    KEY idx_action (action),
    KEY idx_target_type (target_type),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_permission (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    page       VARCHAR(64)  NOT NULL,
    action     VARCHAR(64)  NOT NULL,
    created_at DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_perm (page, action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_role_permission (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    role_id       BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rp (role_id, permission_id),
    KEY idx_role_id (role_id),
    KEY idx_permission_id (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_group_permission (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    group_id      INT UNSIGNED    NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_gp (group_id, permission_id),
    KEY idx_group_id (group_id),
    KEY idx_gperm_id (permission_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_run_history (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    flow_name   VARCHAR(128)    NOT NULL,
    status      VARCHAR(16)     NOT NULL DEFAULT 'running',
    trigger_by  VARCHAR(64)     DEFAULT NULL,
    start_time  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    end_time    DATETIME(3)     DEFAULT NULL,
    duration_ms INT UNSIGNED    DEFAULT NULL,
    error_msg   TEXT            DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_rh_flow_name (flow_name),
    KEY idx_rh_status (status),
    KEY idx_rh_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_run_step (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    run_id      BIGINT UNSIGNED NOT NULL,
    step_name   VARCHAR(128)    NOT NULL,
    step_order  INT UNSIGNED    NOT NULL DEFAULT 0,
    status      VARCHAR(16)     NOT NULL DEFAULT 'pending',
    start_time  DATETIME(3)     DEFAULT NULL,
    end_time    DATETIME(3)     DEFAULT NULL,
    duration_ms INT UNSIGNED    DEFAULT NULL,
    result_data JSON            DEFAULT NULL,
    error_msg   TEXT            DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_rs_run_id (run_id),
    KEY idx_rs_step_name (step_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_job (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    job_name    VARCHAR(128)    NOT NULL UNIQUE,
    flow_name   VARCHAR(128)    NOT NULL,
    job_type    VARCHAR(16)     NOT NULL DEFAULT 'cron',
    cron_expr   VARCHAR(128)    DEFAULT NULL,
    run_date    DATETIME(3)     DEFAULT NULL,
    enabled     TINYINT(1)      DEFAULT 1,
    created_by  VARCHAR(64)     DEFAULT NULL,
    next_run    DATETIME(3)     DEFAULT NULL,
    last_run    DATETIME(3)     DEFAULT NULL,
    last_status VARCHAR(16)     DEFAULT NULL,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_job_flow (flow_name),
    KEY idx_job_enabled (enabled),
    KEY idx_job_type (job_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS system_setting (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `key`      VARCHAR(128)    NOT NULL UNIQUE,
    value      TEXT            NOT NULL,
    updated_at DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_ss_key (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS system_devtool_request (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user        VARCHAR(150)    NOT NULL,
    method      VARCHAR(10)     NOT NULL,
    url         TEXT            NOT NULL,
    headers     JSON            NOT NULL,
    body        TEXT            NOT NULL,
    status_code INT             DEFAULT NULL,
    response    TEXT            NOT NULL,
    duration_ms INT             DEFAULT NULL,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_dr_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS system_api_key (
    id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name        VARCHAR(128)    NOT NULL,
    key_prefix  VARCHAR(8)      NOT NULL,
    key_hash    VARCHAR(64)     NOT NULL,
    created_by  VARCHAR(150)    NOT NULL,
    last_used   DATETIME(3)     DEFAULT NULL,
    enabled     TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    KEY idx_key_hash (key_hash),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_version (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    type        VARCHAR(16)     NOT NULL,
    target_name VARCHAR(192)    NOT NULL,
    version     INT UNSIGNED    NOT NULL,
    content     LONGTEXT        NOT NULL,
    changed_by  VARCHAR(64)     DEFAULT NULL,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    PRIMARY KEY (id),
    UNIQUE KEY uq_target_version (type, target_name, version),
    KEY idx_vr_type (type),
    KEY idx_vr_target (target_name),
    KEY idx_vr_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS wf_reqlog (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    level       VARCHAR(16)     NOT NULL DEFAULT 'INFO',
    method      VARCHAR(10)     NOT NULL,
    path        VARCHAR(512)    NOT NULL,
    status      INT             NOT NULL DEFAULT 0,
    duration_ms INT             DEFAULT NULL,
    message     TEXT            DEFAULT NULL,
    PRIMARY KEY (id),
    KEY idx_reqlog_created (created_at),
    KEY idx_reqlog_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
