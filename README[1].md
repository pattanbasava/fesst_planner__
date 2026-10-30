# DBIT Fest Realm — Flask Admin & Student Portal

A shared, role-based fest planning website for Don Bosco Institute of Technology. The original dark medieval / gold UI is retained.

## Roles

**Admin** can create and remove published events, set the shared festival budget, and approve/reject student event suggestions. **Students** can register, sign in, view the shared schedule/venue information, and submit event suggestions. Student accounts cannot call admin write endpoints; role checks are enforced on the server.

## Run locally

1. Install Python 3.10+.
2. Extract this folder and open a terminal in it.
3. Run `run_windows.bat` on Windows, or `./run.sh` on macOS/Linux. Alternatively:

   ```bash
   python -m venv .venv
   # activate the virtual environment
   pip install -r requirements.txt
   export ADMIN_USERNAME=admin
   export ADMIN_PASSWORD='ChangeMe123!'
   export SECRET_KEY='use-a-long-random-secret'
   python app.py
   ```
4. Open `http://127.0.0.1:5000`.

### First admin sign-in

Default local demo credentials:
- Username: `admin`
- Password: `ChangeMe123!`

Change these using `ADMIN_USERNAME` and `ADMIN_PASSWORD` environment variables **before the first run**. The initial admin account is created once when the database is first initialized; changing environment variables later does not reset its password. Use a strong unique password before exposing the app to a network.

Students use **Student registration** on the login page to create accounts.

## Shared data

Events, budget and student suggestions are stored in `dbit_fest.db` (SQLite) on the server. Everyone accessing the same running deployment sees the same published events and budget. Each user has a separate login session. Back up the database file regularly.

## Deployment / security notes

- For public deployment, set a strong random `SECRET_KEY`, set a strong admin password, use HTTPS, and run behind a production WSGI server (for example Gunicorn); do not use Flask's development server in production.
- Restrict account registration or add college email verification before opening this to the public internet.
- SQLite is suitable for a small demo. Use PostgreSQL for a larger multi-user deployment.
- This version provides local server-side authentication and shared event data. It does not yet permanently store uploaded guideline documents or parse PDFs, and does not provide AI-generated recommendations.
- DBIT venue capacity, permissions, safety rules and budget approvals must be confirmed with the college.
