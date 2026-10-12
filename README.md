# Library Management System

## Project description

LeafLibrary is a web-based library management system for a college library. Administrators can maintain the book catalogue and member directory, issue and return books, review overdue items, and monitor library activity from one dashboard.

The application is built as a Java 17+ Spring Boot Maven project with server-rendered Thymeleaf pages and MySQL persistence.

## Features

- Admin sign-in with session-based authentication and BCrypt password hashing.
- Admin account initialized from environment variables; no default password is stored in the project.
- Dashboard with total copies, available copies, active issues, members, overdue issues, and recent activity.
- Book create, list, search, update, and delete.
- Member registration, list, search, update, and delete.
- Issue available books and record returns.
- Issue history, currently issued books, and overdue issue views.
- Fine calculation at **₹5 per late day**, stored with the issue.
- Validation, user-friendly business error messages, and delete/return confirmation.
- Responsive custom HTML/CSS and lightweight JavaScript; no frontend framework.
- Transactional inventory changes with database row locks to prevent concurrent checkouts from overselling a book.

## Technologies

- Java 17
- Spring Boot 3.4
- Spring MVC
- Spring Security
- Spring Data JPA / Hibernate
- MySQL 8+
- Maven
- Thymeleaf
- HTML, CSS, JavaScript
- JUnit 5 and Mockito (tests)

## Architecture

```text
Thymeleaf browser pages
        ↓
Controller → Service → Spring Data JPA Repository → Entity → MySQL
                 ↓
        Validation and business rules
```

Controllers bind and validate web forms and choose a view or redirect. Services contain business rules and transaction boundaries. Repositories provide database access. JPA entities describe persisted records and their relationships. Spring Security protects application pages and uses an HTTP session for authenticated administrators. The dashboard fetches only the five most recent issue rows rather than loading the full history.

### Project structure

```text
src/
├── main/
│   ├── java/com/example/librarymanagement/
│   │   ├── config/       # Security, web and initial admin setup
│   │   ├── controller/   # MVC routes and form handling
│   │   ├── dto/          # Validated form objects
│   │   ├── entity/       # JPA entities and relationships
│   │   ├── exception/    # Application exceptions and MVC error handling
│   │   ├── repository/   # Spring Data JPA repositories
│   │   └── service/      # Business logic and transactions
│   └── resources/
│       ├── static/css/   # Responsive application styles
│       ├── static/js/    # Confirmation and mobile navigation
│       └── templates/    # Thymeleaf pages and shared fragments
└── test/
    └── java/             # Unit tests
```

## Database structure

The application uses the MySQL database `library_management`. Hibernate creates or updates tables in local development using `spring.jpa.hibernate.ddl-auto=update`.

| Table | Important columns | Relationships |
|---|---|---|
| `users` | `id`, `username`, `password`, `role` | Admin login records; passwords are BCrypt hashes. |
| `books` | `id`, `title`, `author`, `isbn`, `category`, `publisher`, `publication_year`, `quantity`, `available_quantity` | One book can appear in many issue records. |
| `members` | `id`, `name`, `email`, `phone`, `department`, `registration_date` | One member can have many issue records. |
| `issues` | `id`, `book_id`, `member_id`, `issue_date`, `due_date`, `return_date`, `status`, `fine` | Each issue references one book and one member. |

`issues.book_id` and `issues.member_id` are non-null foreign keys. ISBN and member email are unique. Book quantity is the total number of copies; available quantity is adjusted when a copy is issued or returned.

## Installation and MySQL setup

Install:

- JDK 17 or newer
- Maven 3.6 or newer
- MySQL Server 8 or newer
- VS Code with the Java Extension Pack, or IntelliJ IDEA

Start the MySQL server, then connect as a MySQL administrator and run:

```sql
CREATE DATABASE library_management
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'library_app'@'localhost' IDENTIFIED BY 'replace-with-a-strong-database-password';
GRANT ALL PRIVILEGES ON library_management.* TO 'library_app'@'localhost';
FLUSH PRIVILEGES;
```

If the database or user already exists, keep it and grant the configured application user privileges on `library_management`. The JDBC URL also enables database creation if the configured MySQL account has permission.

## Configuration and test credentials

Database and admin passwords must be supplied through environment variables; do not commit credentials to source control. The application does **not** ship with a usable default admin password. Set up a unique admin password (12 or more characters) before the first run:

```powershell
$env:DB_URL = 'jdbc:mysql://localhost:3306/library_management?createDatabaseIfNotExist=true&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC'
$env:DB_USERNAME = 'library_app'
$dbPassword = Read-Host 'MySQL application-user password' -AsSecureString
$env:DB_PASSWORD = (New-Object System.Net.NetworkCredential('', $dbPassword)).Password

$env:ADMIN_USERNAME = 'admin'
$adminPassword = Read-Host 'Choose an admin password (12+ characters)' -AsSecureString
$env:ADMIN_PASSWORD = (New-Object System.Net.NetworkCredential('', $adminPassword)).Password
```

The initial admin is created only when `ADMIN_PASSWORD` is set and the configured username does not already exist. Its password is encoded with BCrypt before saving. Restarting the app will not reset an existing admin password. These environment variables are the development setup credentials; there is no shared test username/password.

Set the same variables in VS Code's Java launch configuration if launching with the Run button. `SESSION_COOKIE_SECURE` defaults to `false` for local HTTP; set it to `true` when deploying behind HTTPS.

## How to run

Open the project folder in VS Code, open **Terminal → New Terminal** (PowerShell), set the environment variables as above, and run:

```powershell
mvn clean test
mvn spring-boot:run
```

Open [http://localhost:8080](http://localhost:8080) and sign in with the `ADMIN_USERNAME` and `ADMIN_PASSWORD` configured above. For a separate terminal, set the environment variables again before starting the application.

To run from an IDE, import the `pom.xml` as a Maven project, set the environment variables in the run configuration, and run `com.example.librarymanagement.LibraryManagementApplication`.

## Web endpoint documentation

The project is a server-rendered MVC application: these are browser routes and HTML form actions, not a JSON REST API. Except for the login page and static assets, routes require an authenticated `ADMIN` session. POST forms retain Spring Security CSRF protection.

See [API-ENDPOINTS.md](./API-ENDPOINTS.md) for the route reference.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/login` | Public admin login form. |
| `POST` | `/login` | Spring Security authenticates the submitted credentials. |
| `POST` | `/logout` | Ends the session and redirects to the login page. |
| `GET` | `/` or `/dashboard` | Dashboard and library totals. |
| `GET` | `/books?q={term}` | List and search books (title, author, ISBN, category, publisher). |
| `GET` | `/books/new` | Add-book form. |
| `POST` | `/books` | Create a book. |
| `GET` | `/books/{id}/edit` | Edit-book form. |
| `POST` | `/books/{id}/edit` | Update a book. |
| `POST` | `/books/{id}/delete` | Delete a book with no issue history. |
| `GET` | `/members?q={term}` | List and search members (name, email, phone, department). |
| `GET` | `/members/new` | Add-member form. |
| `POST` | `/members` | Register a member. |
| `GET` | `/members/{id}/edit` | Edit-member form. |
| `POST` | `/members/{id}/edit` | Update a member. |
| `POST` | `/members/{id}/delete` | Delete a member with no issue history. |
| `GET` | `/loans/new` | Issue-book form with available books. |
| `POST` | `/loans/issue` | Issue a book to a member. |
| `GET` | `/loans/history` | Full issue and return history. |
| `GET` | `/loans/current` | Currently issued books. |
| `GET` | `/loans/overdue` | Unreturned issues past their due date. |
| `POST` | `/loans/{id}/return` | Return an issued book and calculate its fine. |

Issue routes are also available under `/issues` (for example `/issues/history`, `/issues/current`, and `/issues/overdue`).

## Tests

Run the unit test suite with:

```powershell
mvn test
```

Tests cover book inventory behavior, issue return state, return fine calculation, and safe admin initialization. MySQL-backed end-to-end tests require a running MySQL server and configured credentials.

## Future enhancements

- REST API and API documentation with OpenAPI.
- Role-based librarian accounts and account management.
- Pagination and sorting for larger catalogues.
- Configurable loan periods and fine rates.
- Integration tests using a dedicated disposable MySQL test database.
- Audit logging, backups, and production database migrations with Flyway.

## Flask and SQLite edition

The repository also includes a standalone Flask implementation in the root directory. It can be run independently from the Spring Boot application and uses SQLite, so a separate database server is not required.

### Flask features

- Admin and Student registration/sign-in with Werkzeug password hashing, signed Flask sessions, role checks, and CSRF-protected forms.
- Dashboard totals and recent lending activity.
- Search, create, edit, and delete books and students.
- Admin book catalogue supports title/author/ISBN/category search, category filters, responsive pagination, and safe removal that preserves historical checkouts.
- Admin student directory supports validated create/edit/delete, contact/department search, department filtering, responsive pagination, and safe removal that requires active loans to be returned and preserves history.
- Issue available copies, record returns, and calculate late fines at ₹5 per day.
- Reports covering current, overdue, and completed loans.
- Students can browse books and see only their own borrowing history; only Admin accounts can manage records and lending.
- Automatic SQLite schema creation, foreign-key constraints, and a responsive mobile-friendly interface.

### SQLite database design

The Flask app initializes `database.db` automatically when `app.py` starts. It creates four related tables:

| Table | Purpose and important fields |
|---|---|
| `users` | Accounts: `user_id` primary key, name, unique email, `password_hash`, and `role` (`admin` or `student`). Passwords are stored as Werkzeug-generated hashes, never as plain text. |
| `books` | Catalogue: `book_id` primary key, title, author, unique ISBN, category, `total_copies`, and `available_copies`. Publisher and publication year are also stored for the catalogue form. |
| `students` | Borrowers: `student_id` primary key, name, unique email, phone, and department. |
| `transactions` | Checkouts: `transaction_id` primary key, required book/student foreign keys, issue/due/return dates, status, and fine amount. |

Required text values and valid dates are checked by SQLite as well as by the web forms. ISBNs are unique without regard to letter case. Foreign keys prevent deleting a book or student that has lending history. Database triggers decrement a book's available count on issue, increment it on return, reject issuing an unavailable copy, and keep inventory consistent when the total copy count changes. This protects inventory even if a transaction is inserted outside the web form. The initial database includes example books, students, and a completed sample checkout. With no existing users, the first registration creates the Admin account. Thereafter, a Student can register using an email address already enrolled by the Admin. Admin routes are also role-checked on the server; students can only browse books and view their own history. To instead provision a demo administrator, set `LIBRARY_DEMO_PASSWORD` before first startup; the demo account is `demo@library.local` and its password is stored only as a hash.

If the earlier Flask database schema exists, startup migrates its users, books, students, and loans into the new tables and retains the existing password hashes. Keep a backup of `database.db` before upgrading important data.

### Flask file guide

| File | Purpose |
|---|---|
| `app.py` | Flask application, routes, validation, authentication, lending rules, and SQLite schema/queries. |
| `database.db` | Local SQLite database created automatically on first run; it should be kept private and backed up as application data. |
| `requirements.txt` | Python dependencies needed to run the Flask edition. |
| `templates/base.html` | Shared page layout, navigation, alerts, and common metadata. |
| `templates/login.html` | Librarian sign-in page. |
| `templates/register.html` | First-admin bootstrap and enrolled-student account registration page. |
| `templates/dashboard.html` | Collection statistics and recent lending activity. |
| `templates/student_history.html` | Student dashboard showing only that student's loan history. |
| `templates/books.html` | Book catalogue search and book create/edit/delete forms. |
| `templates/students.html` | Student directory search and student create/edit/delete forms. |
| `templates/issue_book.html` | Book checkout form with issue and due dates. |
| `templates/return_book.html` | Current loans and check-in actions. |
| `templates/reports.html` | Loan history, overdue counts, and recorded fines. |
| `static/css/style.css` | Responsive visual design, layout, forms, tables, and status styles. |
| `static/js/script.js` | Mobile navigation, confirmation prompts, and dismissible alerts. |

### Run the Flask edition on Windows

Install Python 3.10 or newer, open PowerShell in the project directory, and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY = (python -c "import secrets; print(secrets.token_hex(32))")
python app.py
```

Open `http://127.0.0.1:5000`, select **Create an account**, and register the first administrator. Enroll students from the Admin-only Students page before they register student accounts; registration uses the enrolled email and assigns the Student role on the server, ignoring any submitted role field. For identity assurance beyond enrollment matching, deployments should add email verification. The SQLite schema and `database.db` are created automatically. For a deployment, set a stable, private `SECRET_KEY`; local runs without it generate a private random key each start. Optionally set `DATABASE_PATH` to store the database at a different path. Do not run Flask's debug mode on a public network.
