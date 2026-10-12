"""
Application Configuration
Converted from: src/main/resources/application.properties
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """
    Base configuration mapped from Spring Boot's application.properties.
    Values can be overridden using environment variables.
    """

    BASE_DIR = BASE_DIR

    # spring.application.name=library-management-system
    APP_NAME = os.getenv("APP_NAME", "library-management-system")

    # Secret key for Flask session signing and CSRF tokens
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)

    # Database Configuration:
    # spring.datasource.url=${DB_URL:jdbc:mysql://localhost:3306/library_management?...}
    # spring.datasource.username=${DB_USERNAME:root}
    # spring.datasource.password=${DB_PASSWORD:}
    # spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver
    DB_URL = os.getenv(
        "DB_URL",
        "mysql+pymysql://localhost:3306/library_management?charset=utf8mb4",
    )
    DB_USERNAME = os.getenv("DB_USERNAME", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # SQLite fallback configuration for local file-based database
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "database.db"))
    DATABASE = str(DATABASE_PATH)

    # JPA / Hibernate equivalents:
    # spring.jpa.hibernate.ddl-auto=update
    # spring.jpa.open-in-view=false
    # spring.jpa.show-sql=false
    # spring.jpa.properties.hibernate.format_sql=true
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = os.getenv("SHOW_SQL", "false").lower() == "true"

    # Template Engine Configuration:
    # spring.thymeleaf.cache=false
    TEMPLATES_AUTO_RELOAD = os.getenv("TEMPLATES_AUTO_RELOAD", "true").lower() == "true"

    # Server / Error Handling:
    # server.error.whitelabel.enabled=false
    PROPAGATE_EXCEPTIONS = False

    # Cookie & Session Security:
    # server.servlet.session.cookie.http-only=true
    # server.servlet.session.cookie.same-site=lax
    # server.servlet.session.cookie.secure=${SESSION_COOKIE_SECURE:false}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes session timeout

    # Admin Account Seeding:
    # library.admin.username=${ADMIN_USERNAME:admin}
    # library.admin.password=${ADMIN_PASSWORD:}
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

    # Business Rules
    FINE_PER_DAY = 5


class DevelopmentConfig(Config):
    """Configuration for local development."""
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Configuration for production deployment."""
    DEBUG = False
    TEMPLATES_AUTO_RELOAD = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Configuration for unit and integration testing."""
    TESTING = True
    DATABASE_PATH = BASE_DIR / "test_database.db"
    DATABASE = str(DATABASE_PATH)
    WTF_CSRF_ENABLED = False


# Map environment strings to config classes
CONFIG_MAP = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(env_name=None):
    """Retrieve configuration based on environment name or FLASK_ENV."""
    if env_name is None:
        env_name = os.getenv("FLASK_ENV", os.getenv("ENV", "development")).lower()
    return CONFIG_MAP.get(env_name, DevelopmentConfig)
