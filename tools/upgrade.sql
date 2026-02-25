USE workflow;

## ============================================================
## v0.0.3 Upgrade: Password Policy
## ============================================================

DELIMITER //
DROP PROCEDURE IF EXISTS _upgrade_v003//
CREATE PROCEDURE _upgrade_v003()
BEGIN
    ## create wf_user_profile if it does not exist
    IF NOT EXISTS (
        SELECT 1 FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'wf_user_profile'
    ) THEN
        CREATE TABLE wf_user_profile (
            id                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            user_id             INT NOT NULL UNIQUE,
            password_changed_at DATETIME(3) DEFAULT NULL,
            PRIMARY KEY (id),
            KEY idx_up_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    END IF;

    ## seed UserProfile for every existing user (skip duplicates)
    INSERT IGNORE INTO wf_user_profile (user_id, password_changed_at)
    SELECT id, NOW(3) FROM auth_user;

    ## record Django migration as applied
    ## (consolidated 0001+0002+0003 into single 0001_initial)
    DELETE FROM django_migrations WHERE app = 'accounts';
    INSERT INTO django_migrations (app, name, applied)
    VALUES ('accounts', '0001_initial', NOW());
END//
DELIMITER ;

CALL _upgrade_v003();
DROP PROCEDURE IF EXISTS _upgrade_v003;
