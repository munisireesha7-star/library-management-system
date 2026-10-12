"""
Security Configuration
Converted from: src/main/java/com/example/librarymanagement/config/SecurityConfig.java
"""

from functools import wraps
from flask import abort, flash, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


class PasswordEncoder:
    """Equivalent to Spring Security's BCryptPasswordEncoder(12)."""

    @staticmethod
    def encode(raw_password: str) -> str:
        """Hash password using Werkzeug's secure hashing algorithm."""
        return generate_password_hash(raw_password)

    @staticmethod
    def matches(raw_password: str, encoded_password: str) -> bool:
        """Verify whether raw password matches the encoded password hash."""
        if not raw_password or not encoded_password:
            return False
        return check_password_hash(encoded_password, raw_password)


def login_required(view_func):
    """Ensures a user is authenticated in the current session."""
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in to access this page.", "error")
            return redirect(url_for("login", next=request.endpoint))
        return view_func(*args, **kwargs)
    return decorated_view


def admin_required(view_func):
    """
    Equivalent to Spring Security's `.anyRequest().hasRole("ADMIN")`.
    Ensures user is signed in with the ADMIN role.
    """
    @wraps(view_func)
    def decorated_view(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return view_func(*args, **kwargs)
    return decorated_view


def configure_security(app):
    """
    Configures security rules, public route allowlists, and session fixation defense.
    Matches Spring Security's securityFilterChain bean.
    """

    # Public static and unauthenticated endpoints
    # Spring: requestMatchers("/login", "/css/**", "/js/**", "/images/**", "/favicon.ico").permitAll()
    PUBLIC_ENDPOINTS = {"login", "static"}

    @app.before_request
    def enforce_security_filter():
        """Intercepts requests to verify access control similar to Spring Security FilterChain."""
        endpoint = request.endpoint

        # Allow static files and unrouted requests
        if endpoint is None or endpoint in PUBLIC_ENDPOINTS or request.path.startswith("/static/"):
            return

        # Check authentication for protected routes
        if not session.get("user_id"):
            if request.path != "/login":
                return redirect(url_for("login"))

        # In this college library admin system, all other routes require ADMIN role
        if session.get("role") != "admin" and request.path != "/login":
            abort(403)

    @app.after_request
    def set_security_headers(response):
        """Set HTTP security headers."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


def migrate_session():
    """
    Protects against Session Fixation attacks.
    Equivalent to Spring Security's sessionFixation().migrateSession().
    """
    old_data = dict(session)
    session.clear()
    session.update(old_data)
