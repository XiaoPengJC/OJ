import sqlite3

from app.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 30000")
    return connection


def _migrate_audit_logs_without_user_foreign_key(
    connection: sqlite3.Connection,
) -> None:
    foreign_keys = connection.execute(
        "PRAGMA foreign_key_list(audit_logs)"
    ).fetchall()
    if not foreign_keys:
        return

    connection.execute(
        """
        CREATE TABLE audit_logs_new (
            id           TEXT PRIMARY KEY,
            operator_id  TEXT NOT NULL,
            action       TEXT NOT NULL,
            target_type  TEXT NOT NULL,
            target_id    TEXT NOT NULL,
            success      INTEGER NOT NULL CHECK (success IN (0, 1)),
            detail       TEXT,
            created_at   TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO audit_logs_new (
            id, operator_id, action, target_type,
            target_id, success, detail, created_at
        )
        SELECT
            id, operator_id, action, target_type,
            target_id, success, detail, created_at
        FROM audit_logs
        """
    )
    connection.execute("DROP TABLE audit_logs")
    connection.execute("ALTER TABLE audit_logs_new RENAME TO audit_logs")


def _create_submission_state_triggers(
    connection: sqlite3.Connection,
) -> None:
    valid_state_expression = """
        (
            NEW.status IN ('pending', 'running')
            AND NEW.result IS NULL
        )
        OR (
            NEW.status = 'finished'
            AND NEW.result IN ('AC', 'WA', 'RE', 'TLE')
        )
        OR (
            NEW.status = 'failed'
            AND NEW.result = 'SE'
        )
    """

    connection.execute("DROP TRIGGER IF EXISTS submissions_validate_insert")
    connection.execute("DROP TRIGGER IF EXISTS submissions_validate_update")

    connection.execute(
        f"""
        CREATE TRIGGER submissions_validate_insert
        BEFORE INSERT ON submissions
        WHEN NOT ({valid_state_expression})
        BEGIN
            SELECT RAISE(ABORT, 'invalid submission state/result combination');
        END
        """
    )
    connection.execute(
        f"""
        CREATE TRIGGER submissions_validate_update
        BEFORE UPDATE OF status, result ON submissions
        WHEN NOT ({valid_state_expression})
        BEGIN
            SELECT RAISE(ABORT, 'invalid submission state/result combination');
        END
        """
    )


def initialize_database() -> None:
    connection = get_connection()

    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL
                              CHECK (role IN ('student', 'teacher', 'admin')),
                is_active     INTEGER NOT NULL DEFAULT 1
                              CHECK (is_active IN (0, 1)),
                created_at    TEXT NOT NULL,
                updated_at    TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS problems (
                id                  TEXT PRIMARY KEY,
                title               TEXT NOT NULL,
                description         TEXT NOT NULL,
                input_description   TEXT NOT NULL,
                output_description  TEXT NOT NULL,
                samples             TEXT NOT NULL,
                constraints_text    TEXT NOT NULL,
                time_limit          REAL NOT NULL CHECK (time_limit > 0),
                memory_limit        INTEGER NOT NULL CHECK (memory_limit > 0),
                difficulty          TEXT NOT NULL
                                    CHECK (difficulty IN ('easy', 'medium', 'hard')),
                tags                TEXT NOT NULL,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS test_cases (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_id       TEXT NOT NULL,
                case_id          TEXT NOT NULL,
                input_data       TEXT NOT NULL,
                expected_output  TEXT NOT NULL,
                score            INTEGER NOT NULL CHECK (score >= 0),
                is_hidden        INTEGER NOT NULL DEFAULT 0
                                 CHECK (is_hidden IN (0, 1)),
                FOREIGN KEY (problem_id)
                    REFERENCES problems(id)
                    ON DELETE CASCADE,
                UNIQUE (problem_id, case_id)
            )
            """
        )
        # problem_id intentionally has no foreign key, so deleting a problem
        # never deletes or invalidates historical submissions.
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id           TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL,
                problem_id   TEXT NOT NULL,
                language     TEXT NOT NULL CHECK (language = 'python'),
                source_code  TEXT NOT NULL,
                status       TEXT NOT NULL
                             CHECK (status IN ('pending', 'running', 'finished', 'failed')),
                result       TEXT,
                score        INTEGER NOT NULL DEFAULT 0 CHECK (score >= 0),
                total_time   REAL,
                created_at   TEXT NOT NULL,
                started_at   TEXT,
                finished_at  TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS judge_logs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id    TEXT NOT NULL,
                case_id          TEXT NOT NULL,
                result           TEXT NOT NULL
                                 CHECK (result IN ('AC', 'WA', 'RE', 'TLE', 'SE')),
                score            INTEGER NOT NULL DEFAULT 0 CHECK (score >= 0),
                time_used        REAL NOT NULL DEFAULT 0 CHECK (time_used >= 0),
                memory_used      INTEGER,
                exit_code        INTEGER,
                input_data       TEXT NOT NULL,
                stdout           TEXT NOT NULL,
                stderr           TEXT NOT NULL,
                expected_output  TEXT NOT NULL,
                message          TEXT NOT NULL,
                is_hidden        INTEGER NOT NULL DEFAULT 0
                                 CHECK (is_hidden IN (0, 1)),
                created_at       TEXT NOT NULL,
                FOREIGN KEY (submission_id)
                    REFERENCES submissions(id)
                    ON DELETE CASCADE,
                UNIQUE (submission_id, case_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id           TEXT PRIMARY KEY,
                operator_id  TEXT NOT NULL,
                action       TEXT NOT NULL,
                target_type  TEXT NOT NULL,
                target_id    TEXT NOT NULL,
                success      INTEGER NOT NULL CHECK (success IN (0, 1)),
                detail       TEXT,
                created_at   TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS backups (
                id          TEXT PRIMARY KEY,
                path        TEXT NOT NULL,
                created_at  TEXT NOT NULL
            )
            """
        )

        _migrate_audit_logs_without_user_foreign_key(connection)
        _create_submission_state_triggers(connection)

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_user_id "
            "ON submissions(user_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_problem_id "
            "ON submissions(problem_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_created_at "
            "ON submissions(created_at)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_judge_logs_submission_id "
            "ON judge_logs(submission_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at "
            "ON audit_logs(created_at)"
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
