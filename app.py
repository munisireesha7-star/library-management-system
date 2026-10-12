import os
import re
import secrets
import sqlite3
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.security import check_password_hash, generate_password_hash


from config import Config
from admin_initializer import seed_admin_account

BASE_DIR = Config.BASE_DIR
DATABASE = Config.DATABASE_PATH
FINE_PER_DAY = Config.FINE_PER_DAY

app = Flask(__name__)
app.config.from_object(Config)
CSRFProtect(app)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def refresh_session_user():
    user_id = session.get("user_id")
    if user_id is None:
        return False
    user = get_db().execute(
        "SELECT name, email, role FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if user is None or user["role"] != session.get("role"):
        session.clear()
        return False
    session["user_name"] = user["name"]
    session["user_email"] = user["email"]
    return True


def init_db():
    """Create the current schema, migrate the first Flask schema, then add examples."""
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(app.config["DATABASE"], timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        db.execute("BEGIN IMMEDIATE")
        existing = {
            row["name"]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        legacy = "books" in existing and "total_copies" not in {
            row["name"] for row in db.execute("PRAGMA table_info(books)")
        }
        legacy_users = False
        if legacy:
            for table in ("loans", "books", "students", "users"):
                if table in existing:
                    archive = f"legacy_{table}"
                    suffix = 1
                    while archive in existing:
                        suffix += 1
                        archive = f"legacy_{table}_{suffix}"
                    db.execute(f"ALTER TABLE {table} RENAME TO {archive}")
                    existing.add(archive)
                    if table == "users":
                        legacy_users = True
        elif "users" in existing:
            user_schema = db.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
            ).fetchone()["sql"].lower()
            if "'student'" not in user_schema and '"student"' not in user_schema:
                archive = "legacy_users"
                if archive in existing:
                    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                        db.execute("DROP TABLE users")
                        existing.remove("users")
                    else:
                        archive = "legacy_users_migration"
                        suffix = 1
                        while archive in existing:
                            suffix += 1
                            archive = f"legacy_users_migration_{suffix}"
                if "users" in existing:
                    db.execute(f"ALTER TABLE users RENAME TO {archive}")
                    existing.add(archive)
                legacy_users = True

        schema = (
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                email TEXT NOT NULL COLLATE NOCASE UNIQUE
                    CHECK (length(trim(email)) > 0 AND instr(email, '@') > 1),
                password_hash TEXT NOT NULL CHECK (length(trim(password_hash)) > 0),
                role TEXT NOT NULL DEFAULT 'student'
                    CHECK (role IN ('admin', 'student'))
            )""",
            """CREATE TABLE IF NOT EXISTS books (
                book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                author TEXT NOT NULL CHECK (length(trim(author)) > 0),
                isbn TEXT NOT NULL COLLATE NOCASE UNIQUE CHECK (length(trim(isbn)) > 0),
                category TEXT NOT NULL CHECK (length(trim(category)) > 0),
                total_copies INTEGER NOT NULL CHECK (total_copies >= 0),
                available_copies INTEGER NOT NULL DEFAULT 0
                    CHECK (available_copies >= 0 AND available_copies <= total_copies),
                publisher TEXT NOT NULL DEFAULT '',
                publication_year INTEGER,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            )""",
            """CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL CHECK (length(trim(name)) > 0),
                email TEXT NOT NULL COLLATE NOCASE UNIQUE
                    CHECK (length(trim(email)) > 0 AND instr(email, '@') > 1),
                phone TEXT NOT NULL CHECK (length(trim(phone)) > 0),
                department TEXT NOT NULL CHECK (length(trim(department)) > 0),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
            )""",
            """CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(book_id) ON DELETE RESTRICT,
                student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE RESTRICT,
                issue_date TEXT NOT NULL CHECK (date(issue_date) IS NOT NULL),
                due_date TEXT NOT NULL CHECK (date(due_date) IS NOT NULL AND due_date >= issue_date),
                return_date TEXT,
                status TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('issued', 'returned')),
                fine_amount REAL NOT NULL DEFAULT 0 CHECK (fine_amount >= 0),
                CHECK (
                    (status = 'issued' AND return_date IS NULL) OR
                    (status = 'returned' AND return_date IS NOT NULL AND date(return_date) IS NOT NULL)
                )
            )""",
            "CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status, due_date)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_book ON transactions(book_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_student ON transactions(student_id)",
            """CREATE TRIGGER IF NOT EXISTS prevent_unavailable_issue
                BEFORE INSERT ON transactions
                WHEN NEW.status = 'issued'
                BEGIN
                    SELECT CASE WHEN
                        (SELECT available_copies FROM books WHERE book_id = NEW.book_id) IS NULL
                        THEN RAISE(ABORT, 'book does not exist')
                    END;
                    SELECT CASE WHEN
                        (SELECT available_copies FROM books WHERE book_id = NEW.book_id) < 1
                        THEN RAISE(ABORT, 'no copies available')
                    END;
                END""",
            """CREATE TRIGGER IF NOT EXISTS decrement_available_copy
                AFTER INSERT ON transactions
                WHEN NEW.status = 'issued'
                BEGIN
                    UPDATE books SET available_copies = available_copies - 1
                    WHERE book_id = NEW.book_id;
                END""",
            """CREATE TRIGGER IF NOT EXISTS change_available_copy_on_return
                AFTER UPDATE OF status ON transactions
                WHEN OLD.status = 'issued' AND NEW.status = 'returned'
                BEGIN
                    UPDATE books SET available_copies = available_copies + 1
                    WHERE book_id = NEW.book_id;
                END""",
            """CREATE TRIGGER IF NOT EXISTS restore_copy_on_issue_delete
                AFTER DELETE ON transactions
                WHEN OLD.status = 'issued'
                BEGIN
                    UPDATE books SET available_copies = available_copies + 1
                    WHERE book_id = OLD.book_id;
                END""",
            """CREATE TRIGGER IF NOT EXISTS prevent_reissuing_returned_transaction
                BEFORE UPDATE OF status ON transactions
                WHEN OLD.status = 'returned' AND NEW.status = 'issued'
                BEGIN
                    SELECT RAISE(ABORT, 'a returned transaction cannot be reissued');
                END""",
            """CREATE TRIGGER IF NOT EXISTS prevent_changing_transaction_borrower
                BEFORE UPDATE OF book_id, student_id ON transactions
                WHEN OLD.book_id != NEW.book_id OR OLD.student_id != NEW.student_id
                BEGIN
                    SELECT RAISE(ABORT, 'transaction book and student are immutable');
                END""",
            """CREATE TRIGGER IF NOT EXISTS keep_total_copies_valid
                BEFORE UPDATE OF total_copies ON books
                WHEN NEW.total_copies < (
                    SELECT COUNT(*) FROM transactions
                    WHERE book_id = OLD.book_id AND status = 'issued'
                )
                BEGIN
                    SELECT RAISE(ABORT, 'total copies cannot be less than copies on loan');
                END""",
            """CREATE TRIGGER IF NOT EXISTS sync_available_after_total_change
                AFTER UPDATE OF total_copies ON books
                WHEN NEW.total_copies != OLD.total_copies
                BEGIN
                    UPDATE books SET available_copies = NEW.total_copies - (
                        SELECT COUNT(*) FROM transactions
                        WHERE book_id = NEW.book_id AND status = 'issued'
                    ) WHERE book_id = NEW.book_id;
                END""",
        )
        for statement in schema:
            db.execute(statement)

        book_columns = {row["name"] for row in db.execute("PRAGMA table_info(books)")}
        if "is_active" not in book_columns:
            db.execute(
                "ALTER TABLE books ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 "
                "CHECK (is_active IN (0, 1))"
            )
        student_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(students)")
        }
        if "is_active" not in student_columns:
            db.execute(
                "ALTER TABLE students ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1 "
                "CHECK (is_active IN (0, 1))"
            )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_students_active_department "
            "ON students(is_active, department)"
        )

        archive_tables = {
            row["name"]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'legacy\\_%' ESCAPE '\\'"
            )
        }
        book_archives = sorted(name for name in archive_tables if name.startswith("legacy_books"))
        student_archives = sorted(name for name in archive_tables if name.startswith("legacy_students"))
        loan_archives = sorted(name for name in archive_tables if name.startswith("legacy_loans"))
        user_archives = sorted(name for name in archive_tables if name.startswith("legacy_users"))
        for table in book_archives:
            db.execute(
                f"""INSERT OR IGNORE INTO books
                    (book_id, title, author, isbn, category, total_copies,
                     available_copies, publisher, publication_year)
                    SELECT id, title, author, isbn, category, quantity,
                           quantity, publisher, publication_year FROM {table}"""
            )
        for table in student_archives:
            db.execute(
                f"""INSERT OR IGNORE INTO students
                    (student_id, name, email, phone, department)
                    SELECT id, name, email, phone, department FROM {table}"""
            )
        for table in user_archives:
            source_columns = {
                row["name"] for row in db.execute(f"PRAGMA table_info({table})")
            }
            source_id = "user_id" if "user_id" in source_columns else "id"
            role_expr = (
                "CASE WHEN role IN ('admin', 'student') THEN role ELSE 'admin' END"
                if "role" in source_columns else "'admin'"
            )
            db.execute(
                f"""INSERT OR IGNORE INTO users
                    (user_id, name, email, password_hash, role)
                    SELECT {source_id}, name, email, password_hash, {role_expr}
                    FROM {table}"""
            )
        for table in loan_archives:
            db.execute(
                f"""INSERT OR IGNORE INTO transactions
                    (transaction_id, book_id, student_id, issue_date, due_date,
                     return_date, status, fine_amount)
                    SELECT id, book_id, student_id, issue_date, due_date, returned_at,
                           CASE WHEN returned_at IS NULL THEN 'issued' ELSE 'returned' END,
                           fine FROM {table}"""
            )
        for table in sorted(archive_tables):
            db.execute(f"DROP TABLE {table}")

        db.execute(
            """INSERT OR IGNORE INTO books
               (title, author, isbn, category, total_copies, available_copies, publisher)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("Braiding Sweetgrass", "Robin Wall Kimmerer", "9781571313560",
             "Nature", 4, 4, "Milkweed Editions"),
        )
        db.execute(
            """INSERT OR IGNORE INTO books
               (title, author, isbn, category, total_copies, available_copies, publisher)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("The Thursday Murder Club", "Richard Osman", "9780241425442",
             "Mystery", 3, 3, "Viking"),
        )
        db.execute(
            """INSERT OR IGNORE INTO students (name, email, phone, department)
               VALUES (?, ?, ?, ?)""",
            ("Jamie Rivera", "jamie.rivera@example.edu", "555-0142", "Literature"),
        )
        db.execute(
            """INSERT OR IGNORE INTO students (name, email, phone, department)
               VALUES (?, ?, ?, ?)""",
            ("Morgan Chen", "morgan.chen@example.edu", "555-0178", "Environmental Studies"),
        )
        demo_password = os.environ.get("LIBRARY_DEMO_PASSWORD")
        if demo_password:
            db.execute(
                """INSERT OR IGNORE INTO users (name, email, password_hash, role)
                   VALUES (?, ?, ?, 'admin')""",
                ("Demo Librarian", "demo@library.local", generate_password_hash(demo_password)),
            )
        if Config.ADMIN_PASSWORD:
            seed_admin_account(db, Config)
        if db.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0:
            sample_book = db.execute(
                "SELECT book_id FROM books WHERE isbn = '9781571313560'"
            ).fetchone()
            sample_student = db.execute(
                "SELECT student_id FROM students WHERE email = 'jamie.rivera@example.edu'"
            ).fetchone()
            if sample_book and sample_student:
                returned = date.today() - timedelta(days=10)
                due = returned - timedelta(days=3)
                issued = due - timedelta(days=14)
                db.execute(
                    """INSERT INTO transactions
                       (book_id, student_id, issue_date, due_date, return_date,
                        status, fine_amount)
                       VALUES (?, ?, ?, ?, ?, 'returned', ?)""",
                    (sample_book["book_id"], sample_student["student_id"],
                     issued.isoformat(), due.isoformat(), returned.isoformat(),
                     3 * FINE_PER_DAY),
                )
        db.execute("PRAGMA user_version = 2")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if not refresh_session_user():
            flash("Please sign in to continue.", "info")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def role_required(role):
    def decorate(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if not refresh_session_user():
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            if session.get("role") != role:
                abort(403)
            return view(**kwargs)

        return wrapped_view

    return decorate


admin_required = role_required("admin")
student_required = role_required("student")


@app.context_processor
def inject_template_helpers():
    return {
        "csrf_token": generate_csrf,
        "current_year": date.today().year,
        "is_admin": session.get("role") == "admin",
    }


def form_text(name, label, *, required=True, max_length=160):
    value = request.form.get(name, "").strip()
    if required and not value:
        raise ValueError(f"{label} is required.")
    if len(value) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer.")
    return value


def validated_email(value, label="Email"):
    email = value.strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError(f"Enter a valid {label.lower()} address.")
    return email


def parse_student_form():
    name = form_text("name", "Name")
    email = validated_email(form_text("email", "Email", max_length=254))
    phone = form_text("phone", "Phone", max_length=40)
    department = form_text("department", "Department")
    return name, email, phone, department


def parse_book_form():
    title = form_text("title", "Title")
    author = form_text("author", "Author")
    isbn = form_text("isbn", "ISBN", max_length=32)
    category = form_text("category", "Category")
    publisher = form_text("publisher", "Publisher", required=False)
    raw_year = form_text("publication_year", "Publication year", required=False)
    raw_quantity = form_text("quantity", "Quantity")
    try:
        year = int(raw_year) if raw_year else None
        quantity = int(raw_quantity)
    except ValueError as exc:
        raise ValueError("Publication year and quantity must be whole numbers.") from exc
    if year is not None and not 1000 <= year <= date.today().year + 1:
        raise ValueError("Enter a valid publication year.")
    if quantity < 0 or quantity > 100000:
        raise ValueError("Quantity must be between 0 and 100,000.")
    return title, author, isbn, category, publisher, year, quantity


def render_books(edit_book=None):
    db = get_db()
    search = request.args.get("q", "").strip()[:100]
    categories = [
        row["category"]
        for row in db.execute(
            "SELECT DISTINCT category FROM books WHERE is_active = 1 ORDER BY category COLLATE NOCASE"
        ).fetchall()
    ]
    category = request.args.get("category", "").strip()
    if category not in categories:
        category = ""
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    per_page = request.args.get("per_page", default=10, type=int)
    if per_page not in (10, 20, 50):
        per_page = 10
    if edit_book is None and request.args.get("edit", type=int) is not None:
        edit_book = get_book_or_404(request.args.get("edit", type=int))
    where = ["b.is_active = 1"]
    params = []
    if search:
        where.append("(b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? OR b.category LIKE ?)")
        term = f"%{search}%"
        params.extend((term, term, term, term))
    if category:
        where.append("b.category = ?")
        params.append(category)
    where_sql = " WHERE " + " AND ".join(where)
    total = db.execute(
        "SELECT COUNT(*) FROM books b" + where_sql, params
    ).fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    books = db.execute(
        """
        SELECT b.*, b.book_id AS id, b.total_copies AS quantity,
               b.available_copies AS available
        FROM books b
        """
        + where_sql
        + " ORDER BY b.title COLLATE NOCASE, b.book_id LIMIT ? OFFSET ?",
        (*params, per_page, (page - 1) * per_page),
    ).fetchall()
    return render_template(
        "books.html", books=books, search=search, category=category,
        categories=categories, edit_book=edit_book, page=page,
        per_page=per_page, total=total, total_pages=total_pages,
    )


def render_students(edit_student=None):
    search = request.args.get("q", "").strip()
    search = search[:100]
    departments = [
        row["department"]
        for row in get_db().execute(
            "SELECT DISTINCT department FROM students WHERE is_active = 1 "
            "ORDER BY department COLLATE NOCASE"
        ).fetchall()
    ]
    department = request.args.get("department", "").strip()
    if department not in departments:
        department = ""
    page = max(1, request.args.get("page", default=1, type=int) or 1)
    per_page = request.args.get("per_page", default=10, type=int)
    if per_page not in (10, 20, 50):
        per_page = 10
    if edit_student is None and request.args.get("edit", type=int) is not None:
        edit_student = get_student_or_404(request.args.get("edit", type=int))
    where = ["s.is_active = 1"]
    params = []
    if search:
        where.append("(s.name LIKE ? OR s.email LIKE ? OR s.phone LIKE ? OR s.department LIKE ?)")
        term = f"%{search}%"
        params.extend((term, term, term, term))
    if department:
        where.append("s.department = ?")
        params.append(department)
    where_sql = " WHERE " + " AND ".join(where)
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM students s" + where_sql, params).fetchone()[0]
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    students = db.execute(
        """
        SELECT s.*, s.student_id AS id,
               (SELECT COUNT(*) FROM transactions t
                WHERE t.student_id = s.student_id AND t.status = 'issued') AS active_loans,
               (SELECT COUNT(*) FROM transactions t
                WHERE t.student_id = s.student_id) AS total_loans
        FROM students s
        """
        + where_sql
        + " ORDER BY s.name COLLATE NOCASE, s.student_id LIMIT ? OFFSET ?",
        (*params, per_page, (page - 1) * per_page),
    ).fetchall()
    return render_template(
        "students.html", students=students, search=search, department=department,
        departments=departments, edit_student=edit_student, page=page,
        per_page=per_page, total=total, total_pages=total_pages,
    )


def get_book_or_404(book_id):
    book = get_db().execute(
        """
        SELECT b.*, b.book_id AS id, b.total_copies AS quantity,
               b.available_copies AS available
        FROM books b WHERE b.book_id = ? AND b.is_active = 1
        """,
        (book_id,),
    ).fetchone()
    if book is None:
        abort(404)
    return book


def get_student_or_404(student_id):
    student = get_db().execute(
        "SELECT *, student_id AS id FROM students WHERE student_id = ? AND is_active = 1",
        (student_id,),
    ).fetchone()
    if student is None:
        abort(404)
    return student


@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    db = get_db()
    admin_setup_available = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    if request.method == "POST":
        try:
            email = validated_email(form_text("email", "Email", max_length=254))
            password = request.form.get("password", "")
            if "@" not in email:
                raise ValueError("Enter a valid email address.")
            if len(password) < 8:
                raise ValueError("Password must contain at least 8 characters.")
            if len(password) > 256:
                raise ValueError("Password must be 256 characters or fewer.")
            if admin_setup_available:
                name = form_text("name", "Name")
                role = "admin"
            else:
                enrolled = db.execute(
                    "SELECT name FROM students WHERE email = ? AND is_active = 1", (email,)
                ).fetchone()
                if enrolled is None:
                    raise ValueError(
                        "Your email is not enrolled. Ask an administrator to add you as a student first."
                    )
                name = enrolled["name"]
                role = "student"
            db.execute("BEGIN IMMEDIATE")
            # Recheck inside the write transaction so simultaneous first signups
            # cannot create multiple public administrator accounts.
            if role == "admin" and db.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0] != 0:
                raise ValueError(
                    "An administrator account has already been created. Register using your enrolled student email."
                )
            db.execute(
                """INSERT INTO users (name, email, password_hash, role)
                   VALUES (?, ?, ?, ?)""",
                (name, email, generate_password_hash(password), role),
            )
            db.commit()
            flash(f"Your {role} account is ready. Please sign in.", "success")
            return redirect(url_for("login"))
        except ValueError as exc:
            db.rollback()
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("An account with that email already exists.", "error")
    return render_template("register.html", admin_setup_available=admin_setup_available)


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT *, user_id AS id FROM users WHERE email = ?", (email,)
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Email or password is incorrect.", "error")
        elif user["role"] == "student" and get_db().execute(
            "SELECT 1 FROM students WHERE email = ? AND is_active = 1", (user["email"],)
        ).fetchone() is None:
            flash("Your student account is no longer enrolled. Contact an administrator.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name'].split()[0]}.", "success")
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "student":
        return redirect(url_for("my_history"))
    db = get_db()
    stats = {
        "books": db.execute(
            "SELECT COALESCE(SUM(total_copies), 0) FROM books WHERE is_active = 1"
        ).fetchone()[0],
        "available": db.execute(
            "SELECT COALESCE(SUM(available_copies), 0) FROM books WHERE is_active = 1"
        ).fetchone()[0],
        "students": db.execute("SELECT COUNT(*) FROM students WHERE is_active = 1").fetchone()[0],
        "active": db.execute(
            "SELECT COUNT(*) FROM transactions WHERE status = 'issued'"
        ).fetchone()[0],
        "overdue": db.execute(
            "SELECT COUNT(*) FROM transactions WHERE status = 'issued' AND due_date < ?",
            (date.today().isoformat(),),
        ).fetchone()[0],
    }
    recent = db.execute(
        """
        SELECT t.*, t.transaction_id AS id, t.return_date AS returned_at,
               t.fine_amount AS fine, b.title AS book_title, s.name AS student_name
        FROM transactions t JOIN books b ON b.book_id = t.book_id
        JOIN students s ON s.student_id = t.student_id
        ORDER BY t.transaction_id DESC LIMIT 6
        """
    ).fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent, today=date.today().isoformat())


@app.route("/my-history")
@student_required
def my_history():
    db = get_db()
    student = db.execute(
        """SELECT s.student_id FROM students s
           JOIN users u ON u.email = s.email
           WHERE u.user_id = ? AND u.role = 'student' AND s.is_active = 1""",
        (session.get("user_id"),),
    ).fetchone()
    if student is None:
        abort(403)
    history = db.execute(
        """
        SELECT t.*, t.transaction_id AS id, t.return_date AS returned_at,
               t.fine_amount AS fine, b.title AS book_title, b.author AS book_author
        FROM transactions t JOIN books b ON b.book_id = t.book_id
        WHERE t.student_id = ?
        ORDER BY t.transaction_id DESC
        """,
        (student["student_id"],),
    ).fetchall()
    active_count = sum(1 for transaction in history if transaction["status"] == "issued")
    overdue_count = sum(
        1 for transaction in history
        if transaction["status"] == "issued" and transaction["due_date"] < date.today().isoformat()
    )
    return render_template(
        "student_history.html",
        history=history,
        active_count=active_count,
        overdue_count=overdue_count,
        today=date.today().isoformat(),
    )


@app.route("/books", methods=["GET", "POST"])
@login_required
def books():
    if request.method == "POST":
        if session.get("role") != "admin":
            abort(403)
        try:
            values = parse_book_form()
            db = get_db()
            db.execute(
                """INSERT INTO books
                   (title, author, isbn, category, publisher, publication_year,
                    total_copies, available_copies)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (*values[:-1], values[-1], values[-1]),
            )
            db.commit()
            flash("Book added to the collection.", "success")
            return redirect(url_for("books"))
        except ValueError as exc:
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            flash("That ISBN is already in the collection.", "error")
    return render_books()


@app.post("/books/<int:book_id>/update")
@admin_required
def update_book(book_id):
    book = get_book_or_404(book_id)
    try:
        values = parse_book_form()
        active = get_db().execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id = ? AND status = 'issued'",
            (book_id,),
        ).fetchone()[0]
        if values[-1] < active:
            raise ValueError(f"Quantity cannot be lower than the {active} copies currently on loan.")
        db = get_db()
        db.execute(
            """UPDATE books SET title = ?, author = ?, isbn = ?, category = ?,
               publisher = ?, publication_year = ?, total_copies = ?,
               available_copies = ? WHERE book_id = ?""",
            (*values[:-1], values[-1], values[-1] - active, book_id),
        )
        db.commit()
        flash("Book details updated.", "success")
        return redirect(url_for("books"))
    except ValueError as exc:
        flash(str(exc), "error")
        return render_books(edit_book=book)
    except sqlite3.IntegrityError:
        flash("That ISBN is already assigned to another book.", "error")
        return render_books(edit_book=book)


@app.post("/books/<int:book_id>/delete")
@admin_required
def delete_book(book_id):
    book = get_book_or_404(book_id)
    db = get_db()
    try:
        active = db.execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id = ? AND status = 'issued'",
            (book_id,),
        ).fetchone()[0]
        if active:
            flash(
                f"Cannot remove “{book['title']}” while {active} copy/copies are on loan.",
                "error",
            )
            return redirect(url_for("books"))
        history = db.execute(
            "SELECT COUNT(*) FROM transactions WHERE book_id = ?", (book_id,)
        ).fetchone()[0]
        if history:
            db.execute("UPDATE books SET is_active = 0 WHERE book_id = ?", (book_id,))
            message = "Book removed from the catalogue; past transaction history was preserved."
        else:
            db.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
            message = "Book removed from the collection."
        db.commit()
        flash(message, "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("This book has loan history and cannot be deleted.", "error")
    return redirect(url_for("books"))


@app.route("/students", methods=["GET", "POST"])
@admin_required
def students():
    if request.method == "POST":
        try:
            values = parse_student_form()
            db = get_db()
            db.execute(
                "INSERT INTO students (name, email, phone, department) VALUES (?, ?, ?, ?)",
                values,
            )
            db.commit()
            flash("Student registered.", "success")
            return redirect(url_for("students"))
        except ValueError as exc:
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            flash("A student with that email already exists.", "error")
    return render_students()


@app.post("/students/<int:student_id>/update")
@admin_required
def update_student(student_id):
    student = get_student_or_404(student_id)
    try:
        values = parse_student_form()
        db = get_db()
        old_email = student["email"]
        db.execute(
            """UPDATE users SET name = ?, email = ?
               WHERE role = 'student' AND email = ?""",
            (values[0], values[1], old_email),
        )
        db.execute(
            "UPDATE students SET name = ?, email = ?, phone = ?, department = ? WHERE student_id = ?",
            (*values, student_id),
        )
        db.commit()
        flash("Student details updated.", "success")
        return redirect(url_for("students"))
    except ValueError as exc:
        get_db().rollback()
        flash(str(exc), "error")
        return render_students(edit_student=student)
    except sqlite3.IntegrityError:
        get_db().rollback()
        flash("That email is already assigned to another student.", "error")
        return render_students(edit_student=student)


@app.post("/students/<int:student_id>/delete")
@admin_required
def delete_student(student_id):
    student = get_student_or_404(student_id)
    db = get_db()
    try:
        active = db.execute(
            "SELECT COUNT(*) FROM transactions WHERE student_id = ? AND status = 'issued'",
            (student_id,),
        ).fetchone()[0]
        if active:
            flash(
                f"Cannot remove {student['name']} while they have {active} active loan(s).",
                "error",
            )
            return redirect(url_for("students"))
        db.execute(
            "DELETE FROM users WHERE role = 'student' AND email = ?",
            (student["email"],),
        )
        history = db.execute(
            "SELECT COUNT(*) FROM transactions WHERE student_id = ?", (student_id,)
        ).fetchone()[0]
        if history:
            db.execute("UPDATE students SET is_active = 0 WHERE student_id = ?", (student_id,))
            message = "Student removed from the directory; borrowing history was preserved."
        else:
            db.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            message = "Student removed from the directory."
        db.commit()
        flash(message, "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("This student has loan history and cannot be deleted.", "error")
    return redirect(url_for("students"))


@app.route("/issue", methods=["GET", "POST"])
@admin_required
def issue_book():
    db = get_db()
    if request.method == "POST":
        db.execute("BEGIN IMMEDIATE")
        try:
            try:
                book_id = int(request.form.get("book_id", ""))
                student_id = int(request.form.get("student_id", ""))
            except ValueError as exc:
                raise ValueError("Choose a valid book and student.") from exc
            issue_date = form_text("issue_date", "Issue date")
            due_date = form_text("due_date", "Due date")
            parsed_issue = date.fromisoformat(issue_date)
            parsed_due = date.fromisoformat(due_date)
            if parsed_due < parsed_issue:
                raise ValueError("The due date cannot be before the issue date.")
            book = get_book_or_404(book_id)
            get_student_or_404(student_id)
            if book["available"] <= 0:
                raise ValueError("No copies of that book are currently available.")
            db.execute(
                """INSERT INTO transactions (book_id, student_id, issue_date, due_date)
                   VALUES (?, ?, ?, ?)""",
                (book_id, student_id, issue_date, due_date),
            )
            db.commit()
            flash(f"“{book['title']}” issued successfully.", "success")
            return redirect(url_for("return_book"))
        except (ValueError, TypeError) as exc:
            db.rollback()
            flash(str(exc) or "Choose a valid book and student.", "error")
        except sqlite3.IntegrityError:
            db.rollback()
            flash("The issue could not be saved. Please check the selected records.", "error")
    available_books = db.execute(
        """
        SELECT b.*, b.book_id AS id, b.total_copies AS quantity,
               b.available_copies AS available
        FROM books b WHERE b.available_copies > 0 AND b.is_active = 1
        ORDER BY b.title COLLATE NOCASE
        """
    ).fetchall()
    student_rows = db.execute(
        "SELECT student_id AS id, name, email FROM students "
        "WHERE is_active = 1 ORDER BY name"
    ).fetchall()
    return render_template(
        "issue_book.html", books=available_books, students=student_rows,
        today=date.today().isoformat(), default_due=(date.today() + timedelta(days=14)).isoformat()
    )


@app.route("/returns", methods=["GET"])
@admin_required
def return_book():
    loans = get_db().execute(
        """
        SELECT t.*, t.transaction_id AS id, t.return_date AS returned_at,
               t.fine_amount AS fine, b.title AS book_title, b.author AS book_author,
               s.name AS student_name, s.email AS student_email
        FROM transactions t JOIN books b ON b.book_id = t.book_id
        JOIN students s ON s.student_id = t.student_id
        WHERE t.status = 'issued'
        ORDER BY t.due_date, t.transaction_id
        """
    ).fetchall()
    return render_template("return_book.html", loans=loans, today=date.today().isoformat())


@app.post("/returns/<int:loan_id>")
@admin_required
def process_return(loan_id):
    db = get_db()
    loan = db.execute(
        """SELECT *, transaction_id AS id, return_date AS returned_at,
                  fine_amount AS fine FROM transactions
           WHERE transaction_id = ? AND status = 'issued'""",
        (loan_id,),
    ).fetchone()
    if loan is None:
        flash("That loan is already returned or no longer exists.", "error")
        return redirect(url_for("return_book"))
    returned_at = date.today()
    days_late = max(0, (returned_at - date.fromisoformat(loan["due_date"])).days)
    fine = days_late * FINE_PER_DAY
    db.execute(
        """UPDATE transactions
           SET return_date = ?, status = 'returned', fine_amount = ?
           WHERE transaction_id = ?""",
        (returned_at.isoformat(), fine, loan_id),
    )
    db.commit()
    if fine:
        flash(f"Book returned. A fine of ₹{fine} was recorded for {days_late} overdue day(s).", "success")
    else:
        flash("Book returned successfully. No fine is due.", "success")
    return redirect(url_for("return_book"))


@app.route("/reports")
@admin_required
def reports():
    db = get_db()
    totals = db.execute(
        """
        SELECT COUNT(*) AS total_loans,
               SUM(CASE WHEN status = 'issued' THEN 1 ELSE 0 END) AS active,
               SUM(CASE WHEN status = 'issued' AND due_date < ? THEN 1 ELSE 0 END) AS overdue,
               COALESCE(SUM(fine_amount), 0) AS fines
        FROM transactions
        """,
        (date.today().isoformat(),),
    ).fetchone()
    history = db.execute(
        """
        SELECT t.*, t.transaction_id AS id, t.return_date AS returned_at,
               t.fine_amount AS fine, b.title AS book_title, s.name AS student_name
        FROM transactions t JOIN books b ON b.book_id = t.book_id
        JOIN students s ON s.student_id = t.student_id
        ORDER BY t.transaction_id DESC
        """
    ).fetchall()
    return render_template(
        "reports.html", totals=totals, history=history, today=date.today().isoformat()
    )


init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
