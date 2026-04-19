# Job Automation Bot Manager

A beautiful, automated resume rotation and update system for the Naukri.com platform.

## Features
- **Modern Dashboard**: High-level overview of bot status and recent activity.
- **Resume Management**: CRUD operations for your resume pool via a glassmorphism UI.
- **Log Viewer**: Live execution logs accessible from the browser.
- **Secure Access**: SQLite-backed authentication with JWT session management.
- **Scheduled Bot**: Automated Naukri updates via system cron jobs.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy (SQLite), Jinja2
- **Automation**: Selenium (Chrome Headless)
- **Deployment**: GitHub Actions to AWS EC2

## Getting Started
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file with `EMAIL` and `PASSWORD` (Naukri credentials).
3. Run the manager: `python main.py`
4. Visit `http://localhost:8000`

### Default Login
- **Username**: `admin`
- **Password**: `admin123`
*Note: You can change these in the database or main.py.*