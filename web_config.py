"""
Web MVC Configuration
Converted from: src/main/java/com/example/librarymanagement/config/WebConfig.java
"""

from flask import render_template


def configure_web(app):
    """
    Registers Web MVC view controllers and global error handling.
    Equivalent to Spring's WebMvcConfigurer and addViewControllers.
    """

    # spring: registry.addViewController("/error").setViewName("error");
    @app.route("/error")
    def error_view():
        return render_template("error.html", message="An unexpected error occurred."), 500

    @app.errorhandler(403)
    def forbidden(error):
        return render_template("error.html", message="Access denied: Admin privileges required."), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", message="The requested page was not found."), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("error.html", message="Internal server error. Please try again later."), 500
