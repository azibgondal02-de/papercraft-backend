from web import migrate_engine as engine
from lib_utils.sql import sql
from sqlalchemy import text
import os


def migrate():
    with engine.begin() as conn:
        # Create migration tracking table if it doesn't exist
        sql(
            conn,
            """
        CREATE TABLE IF NOT EXISTS migrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            migration_number INT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        ).run()

        # Get all migration names that have already been applied
        applied_rows = sql(
            conn,
            "SELECT migration_name FROM migrations;",
        ).dicts()
        applied_migration_names = {row["migration_name"] for row in applied_rows}

        all_migration_file_names = [
            filename
            for filename in os.listdir("migration_files")
            if filename.endswith(".sql")
        ]

        sorted_migration_file_names = sorted(
            all_migration_file_names, key=lambda x: int(x.split("_")[0])
        )

        # Run any migration that is not in the migrations table (keeps order by number)
        unapplied_migrations = [
            f for f in sorted_migration_file_names if f not in applied_migration_names
        ]
        for migration_file in unapplied_migrations:
            migration_number = int(migration_file.split("_")[0])
            with open(os.path.join("migration_files", migration_file), "r") as file:
                sql_command_text = file.read()
                sql_commands = [
                    cmd.strip() for cmd in sql_command_text.split(";") if cmd.strip()
                ]
                for sql_command in sql_commands:
                    sql(conn, sql_command).run()
            sql(
                conn,
                """
            INSERT INTO migrations (migration_name, migration_number)
            VALUES (:migration_name, :migration_number);
            """,
                {
                    "migration_name": migration_file,
                    "migration_number": migration_number,
                },
            ).run()
            print(f"Applied migration: {migration_file}")


if __name__ == "__main__":
    migrate()
