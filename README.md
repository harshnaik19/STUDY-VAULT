# StudyVault - Student Study Resource & Task Manager

StudyVault is a complete web application designed for college students to organize useful study resources (websites, YouTube videos, GitHub repositories, online tutorials, documentation, and research links) and connect them directly with actionable tasks, target deadlines, subjects, priorities, and completion status tracking.

---

## Key Features

- **Student Overview Dashboard**: View total study resources, completed tasks, in-progress items, pending tasks, favorite count, subject breakdown percentages, and upcoming deadlines highlighting overdue items.
- **Automatic Webpage Title Retrieval**: Built-in web scraping powered by `requests` + `BeautifulSoup4` automatically retrieves webpage titles when pasting URLs.
- **Duplicate URL Prevention**: Checks SQLite database before saving to prevent duplicate resource URLs.
- **Task & Deadline Tracking**: Every study resource links to a specific subject, category (Tutorial, YouTube, GitHub, Documentation, Research, Notes, Other), task/action item, deadline date, priority level (Low, Medium, High), and completion status.
- **Search & Multi-Filter**: Real-time keyword search and combinable filters (Subject, Category, Status, Priority) without page reloads.
- **User Authentication & Data Privacy**: Session-based registration, login, logout, password hashing (`Werkzeug`), and strict per-user resource isolation.

---

## Tech Stack

- **Frontend**: HTML5, CSS3 (Vanilla Design System), Vanilla JavaScript (Fetch API AJAX).
- **Backend**: Python 3, Flask.
- **Database**: SQLite (via Python built-in `sqlite3`).
- **Dependencies**: `Flask`, `requests`, `beautifulsoup4`, `werkzeug`.

---

## Installation & Setup Guide

### 1. Clone the Repository
```bash
git clone https://github.com/harshnaik19/studyvault.git
cd studyvault
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv venv

# On Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## Pre-configured Demo Accounts

- **Email**: `demo@studyvault.edu` | **Password**: `demo123`
- **Email**: `alex@studyvault.edu` | **Password**: `alex123`
*(Or click **"Create Account"** to register a new student account).*
