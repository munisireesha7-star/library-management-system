# Web Endpoint Reference

LeafLibrary currently uses Spring MVC and Thymeleaf. These endpoints render HTML or process HTML forms; they are not JSON REST endpoints. All routes require an authenticated `ADMIN` session except `GET /login`, `POST /login`, and static assets. Form POSTs must include the CSRF token provided by Thymeleaf/Spring Security.

## Authentication

| Method | Path | Description |
|---|---|---|
| `GET` | `/login` | Show the public login form. |
| `POST` | `/login` | Authenticate using configured admin credentials. |
| `POST` | `/logout` | Invalidate the authenticated session. |

## Dashboard

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Show catalogue, availability, issue, member, overdue, and recent activity totals. |
| `GET` | `/dashboard` | Redirect to `/`. |

## Books

| Method | Path | Description |
|---|---|---|
| `GET` | `/books?q={term}` | List books; optional `q` searches title, author, ISBN, category, and publisher. |
| `GET` | `/books/new` | Show the add-book form. |
| `POST` | `/books` | Validate and add a book. |
| `GET` | `/books/{id}/edit` | Show the edit form. |
| `POST` | `/books/{id}/edit` | Validate and update a book. |
| `POST` | `/books/{id}/delete` | Delete a book if it has no issue history. |

## Members

| Method | Path | Description |
|---|---|---|
| `GET` | `/members?q={term}` | List members; optional `q` searches name, email, phone, and department. |
| `GET` | `/members/new` | Show the registration form. |
| `POST` | `/members` | Validate and register a member. |
| `GET` | `/members/{id}/edit` | Show the edit form. |
| `POST` | `/members/{id}/edit` | Validate and update a member. |
| `POST` | `/members/{id}/delete` | Delete a member if they have no issue history. |

## Issues

| Method | Path | Description |
|---|---|---|
| `GET` | `/loans/new` | Show available books and registered members for checkout. |
| `POST` | `/loans/issue` | Create an issue, set issue/due dates, and decrement available quantity. |
| `GET` | `/loans/history` | Show all issue and return records. |
| `GET` | `/loans/current` | Show currently issued books. |
| `GET` | `/loans/overdue` | Show issues still open after their due date. |
| `POST` | `/loans/{id}/return` | Record return, restore availability, and calculate ₹5 per late day. |

The history, current, and overdue views are also mapped under `/issues` (`/issues/history`, `/issues/current`, and `/issues/overdue`). Issue creation and return are transactional; book rows are locked while availability is changed.
