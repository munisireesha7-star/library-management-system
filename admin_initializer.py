"""
Admin Account Initializer
Converted from: src/main/java/com/example/librarymanagement/config/AdminAccountInitializer.java
"""

import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)


class AdminAccountInitializer:
    """
    Application startup runner that initializes the default admin account
    idempotently based on configured environment variables.
    """

    def __init__(self, username="admin", password=""):
        self.username = (username or "").strip()
        self.password = password or ""

    def run(self, db_connection):
        """
        Executes the admin account initialization against a database connection.
        Compatible with SQLite and MySQL connections / cursors.
        """
        if not self.password.strip():
            logger.warning(
                "Admin account was not seeded. Set ADMIN_PASSWORD to initialize the first admin account."
            )
            return

        if not self.username or len(self.username) > 60:
            raise ValueError("ADMIN_USERNAME must contain between 1 and 60 characters.")

        password_bytes = self.password.encode("utf-8")
        if len(self.password) < 12 or len(password_bytes) > 72:
            raise ValueError(
                "ADMIN_PASSWORD must be at least 12 characters and no more than 72 UTF-8 bytes."
            )

        # Case-insensitive check for existing admin username / email
        cursor = db_connection.cursor()
        existing_user = cursor.execute(
            "SELECT 1 FROM users WHERE LOWER(name) = LOWER(?) OR LOWER(email) = LOWER(?)",
            (self.username, f"{self.username}@library.local"),
        ).fetchone()

        if existing_user:
            logger.info("Admin account '%s' already exists; its password was not changed.", self.username)
            return

        # Hash with secure password algorithm (BCrypt / PBKDF2/scrypt)
        password_hash = generate_password_hash(self.password)

        cursor.execute(
            """INSERT INTO users (name, email, password_hash, role)
               VALUES (?, ?, ?, 'admin')""",
            (self.username, f"{self.username}@library.local", password_hash),
        )
        db_connection.commit()
        logger.info(
            "Initial admin account '%s' was created with a securely hashed password.",
            self.username,
        )


def seed_admin_account(db_connection, app_config=None):
    """Convenience helper function to run the initializer using application configuration."""
    if app_config is None:
        from config import Config
        app_config = Config

    initializer = AdminAccountInitializer(
        username=getattr(app_config, "ADMIN_USERNAME", "admin"),
        password=getattr(app_config, "ADMIN_PASSWORD", ""),
    )
    initializer.run(db_connection)
