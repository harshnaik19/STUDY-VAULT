import sqlite3
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'studyvault.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create users table with OAuth columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                auth_provider TEXT NOT NULL DEFAULT 'local',
                provider_user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create resources table with user_id foreign key
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                subject TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'Other',
                tags TEXT,
                description TEXT,
                task TEXT,
                deadline TEXT,
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Not Started',
                favorite INTEGER DEFAULT 0,
                archived INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

def dict_from_row(row):
    if row is None:
        return None
    return dict(row)

# User Management Functions (Email & OAuth)
def create_user(name, email, password_hash=None, auth_provider='local', provider_user_id=None):
    clean_email = email.strip().lower()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, auth_provider, provider_user_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name.strip(), clean_email, password_hash, auth_provider, provider_user_id, now, now)
        )
        conn.commit()
        return cursor.lastrowid

def get_user_by_email(email):
    clean_email = email.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (clean_email,))
        row = cursor.fetchone()
        return dict_from_row(row)

def get_user_by_provider(auth_provider, provider_user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE auth_provider = ? AND provider_user_id = ?",
            (auth_provider, str(provider_user_id))
        )
        row = cursor.fetchone()
        return dict_from_row(row)

def link_oauth_user(user_id, auth_provider, provider_user_id):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET auth_provider = ?, provider_user_id = ?, updated_at = ? WHERE id = ?",
            (auth_provider, str(provider_user_id), now, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0

def get_user_by_id(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, auth_provider, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict_from_row(row)

# Resource Management Functions (User Isolated)
def check_url_exists(user_id, url, exclude_id=None):
    clean_url = url.strip().rstrip('/')
    with get_db() as conn:
        cursor = conn.cursor()
        if exclude_id:
            cursor.execute(
                "SELECT id FROM resources WHERE user_id = ? AND (LOWER(url) = LOWER(?) OR LOWER(url) = LOWER(?)) AND id != ?",
                (user_id, clean_url, clean_url + '/', exclude_id)
            )
        else:
            cursor.execute(
                "SELECT id FROM resources WHERE user_id = ? AND (LOWER(url) = LOWER(?) OR LOWER(url) = LOWER(?))",
                (user_id, clean_url, clean_url + '/')
            )
        return cursor.fetchone() is not None

def add_resource(user_id, data):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO resources (
                user_id, title, url, subject, category, tags, description,
                task, deadline, priority, status, favorite, archived
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            data.get('title', '').strip(),
            data.get('url', '').strip(),
            data.get('subject', '').strip(),
            data.get('category', 'Other').strip(),
            data.get('tags', '').strip(),
            data.get('description', '').strip(),
            data.get('task', '').strip(),
            data.get('deadline', '').strip(),
            data.get('priority', 'Medium').strip(),
            data.get('status', 'Not Started').strip(),
            1 if data.get('favorite') in [1, '1', True] else 0,
            1 if data.get('archived') in [1, '1', True] else 0
        ))
        conn.commit()
        return cursor.lastrowid

def get_resources(user_id, search_query=None, subject=None, category=None, priority=None, status=None, favorite=None, archived=0):
    with get_db() as conn:
        cursor = conn.cursor()
        sql = "SELECT * FROM resources WHERE user_id = ?"
        params = [user_id]

        if archived is not None and archived != '':
            sql += " AND archived = ?"
            params.append(1 if archived in [1, '1', True] else 0)

        if favorite is not None and favorite != '' and int(favorite) == 1:
            sql += " AND favorite = 1"

        if subject:
            sql += " AND LOWER(subject) = LOWER(?)"
            params.append(subject.strip())

        if category:
            sql += " AND LOWER(category) = LOWER(?)"
            params.append(category.strip())

        if priority:
            sql += " AND LOWER(priority) = LOWER(?)"
            params.append(priority.strip())

        if status:
            sql += " AND LOWER(status) = LOWER(?)"
            params.append(status.strip())

        if search_query and search_query.strip():
            q = f"%{search_query.strip().lower()}%"
            sql += """ AND (
                LOWER(title) LIKE ? OR 
                LOWER(subject) LIKE ? OR 
                LOWER(tags) LIKE ? OR 
                LOWER(description) LIKE ? OR 
                LOWER(task) LIKE ?
            )"""
            params.extend([q, q, q, q, q])

        sql += " ORDER BY CASE WHEN deadline IS NOT NULL AND deadline != '' THEN deadline ELSE '9999-12-31' END ASC, created_at DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]

def get_resource_by_id(user_id, resource_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM resources WHERE id = ? AND user_id = ?", (resource_id, user_id))
        row = cursor.fetchone()
        return dict_from_row(row)

def update_resource(user_id, resource_id, data):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            UPDATE resources SET
                title = ?,
                url = ?,
                subject = ?,
                category = ?,
                tags = ?,
                description = ?,
                task = ?,
                deadline = ?,
                priority = ?,
                status = ?,
                favorite = ?,
                archived = ?,
                updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (
            data.get('title', '').strip(),
            data.get('url', '').strip(),
            data.get('subject', '').strip(),
            data.get('category', 'Other').strip(),
            data.get('tags', '').strip(),
            data.get('description', '').strip(),
            data.get('task', '').strip(),
            data.get('deadline', '').strip(),
            data.get('priority', 'Medium').strip(),
            data.get('status', 'Not Started').strip(),
            1 if data.get('favorite') in [1, '1', True] else 0,
            1 if data.get('archived') in [1, '1', True] else 0,
            now,
            resource_id,
            user_id
        ))
        conn.commit()
        return cursor.rowcount > 0

def delete_resource(user_id, resource_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM resources WHERE id = ? AND user_id = ?", (resource_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def toggle_favorite(user_id, resource_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE resources SET favorite = CASE WHEN favorite = 1 THEN 0 ELSE 1 END WHERE id = ? AND user_id = ?", (resource_id, user_id))
        conn.commit()
        cursor.execute("SELECT favorite FROM resources WHERE id = ? AND user_id = ?", (resource_id, user_id))
        row = cursor.fetchone()
        return row['favorite'] if row else 0

def toggle_archive(user_id, resource_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE resources SET archived = CASE WHEN archived = 1 THEN 0 ELSE 1 END WHERE id = ? AND user_id = ?", (resource_id, user_id))
        conn.commit()
        cursor.execute("SELECT archived FROM resources WHERE id = ? AND user_id = ?", (resource_id, user_id))
        row = cursor.fetchone()
        return row['archived'] if row else 0

def update_status(user_id, resource_id, new_status):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE resources SET status = ? WHERE id = ? AND user_id = ?", (new_status.strip(), resource_id, user_id))
        conn.commit()
        return cursor.rowcount > 0

def get_dashboard_stats(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total active resources
        cursor.execute("SELECT COUNT(*) FROM resources WHERE user_id = ? AND archived = 0", (user_id,))
        total_resources = cursor.fetchone()[0]
        
        # Completed
        cursor.execute("SELECT COUNT(*) FROM resources WHERE user_id = ? AND archived = 0 AND status = 'Completed'", (user_id,))
        completed_resources = cursor.fetchone()[0]
        
        # In Progress
        cursor.execute("SELECT COUNT(*) FROM resources WHERE user_id = ? AND archived = 0 AND status = 'In Progress'", (user_id,))
        in_progress_resources = cursor.fetchone()[0]
        
        # Pending Tasks
        cursor.execute("SELECT COUNT(*) FROM resources WHERE user_id = ? AND archived = 0 AND status != 'Completed' AND task IS NOT NULL AND TRIM(task) != ''", (user_id,))
        pending_tasks = cursor.fetchone()[0]
        
        # Favorites count
        cursor.execute("SELECT COUNT(*) FROM resources WHERE user_id = ? AND archived = 0 AND favorite = 1", (user_id,))
        favorite_count = cursor.fetchone()[0]

        # Upcoming deadlines
        cursor.execute("""
            SELECT id, title, subject, task, deadline, priority, status
            FROM resources 
            WHERE user_id = ? AND archived = 0 AND deadline IS NOT NULL AND TRIM(deadline) != '' AND status != 'Completed'
            ORDER BY deadline ASC
            LIMIT 6
        """, (user_id,))
        upcoming_deadlines = [dict_from_row(r) for r in cursor.fetchall()]

        # Subject breakdown
        cursor.execute("""
            SELECT subject, COUNT(*) as count 
            FROM resources 
            WHERE user_id = ? AND archived = 0 
            GROUP BY LOWER(subject) 
            ORDER BY count DESC
        """, (user_id,))
        subject_breakdown = [{"subject": r["subject"], "count": r["count"]} for r in cursor.fetchall()]

        return {
            "total_resources": total_resources,
            "completed_resources": completed_resources,
            "in_progress_resources": in_progress_resources,
            "pending_tasks": pending_tasks,
            "favorite_count": favorite_count,
            "upcoming_deadlines": upcoming_deadlines,
            "subject_breakdown": subject_breakdown
        }

def seed_demo_data():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] > 0:
            return

    # Seed User 1: Harsh (demo@studyvault.edu / demo123)
    user1_id = create_user("Harsh", "demo@studyvault.edu", generate_password_hash("demo123"), auth_provider="local")
    
    # Seed User 2: Alex Student (alex@studyvault.edu / alex123)
    user2_id = create_user("Alex Student", "alex@studyvault.edu", generate_password_hash("alex123"), auth_provider="local")

    sample_items_user1 = [
        {
            "title": "Python Flask Tutorial & Documentation",
            "url": "https://flask.palletsprojects.com/en/stable/",
            "subject": "Python",
            "category": "Tutorial",
            "tags": "flask, web, python, backend",
            "description": "Official documentation covering Flask fundamentals, application context, blue-prints, and request handling.",
            "task": "Complete authentication section",
            "deadline": "2026-09-20",
            "priority": "High",
            "status": "In Progress",
            "favorite": 1,
            "archived": 0
        },
        {
            "title": "React Documentation & Hooks Guide",
            "url": "https://react.dev/learn",
            "subject": "Web Dev",
            "category": "Documentation",
            "tags": "react, frontend, javascript, hooks",
            "description": "Interactive guide on modern React, functional components, useEffect, and custom hooks.",
            "task": "Read hooks documentation",
            "deadline": "2026-09-18",
            "priority": "High",
            "status": "In Progress",
            "favorite": 1,
            "archived": 0
        },
        {
            "title": "DBMS Normalization Notes & Exercises",
            "url": "https://www.geeksforgeeks.org/dbms-normalization-1nf-2nf-3nf-bcnf/",
            "subject": "DBMS",
            "category": "Notes",
            "tags": "database, normalization, 3NF, BCNF",
            "description": "Comprehensive reference guide explaining Functional Dependencies, 1NF, 2NF, 3NF, and BCNF with step-by-step table examples.",
            "task": "Practice 3NF and BCNF normal form examples",
            "deadline": "2026-09-22",
            "priority": "Medium",
            "status": "Not Started",
            "favorite": 0,
            "archived": 0
        }
    ]

    sample_items_user2 = [
        {
            "title": "Java Object-Oriented Programming Principles",
            "url": "https://docs.oracle.com/javase/tutorial/java/concepts/",
            "subject": "Java",
            "category": "Documentation",
            "tags": "java, oop, inheritance",
            "description": "Oracle Java guide on objects, classes, encapsulation, inheritance, and interfaces.",
            "task": "Implement polymorphism lab",
            "deadline": "2026-09-25",
            "priority": "High",
            "status": "In Progress",
            "favorite": 1,
            "archived": 0
        }
    ]

    for item in sample_items_user1:
        add_resource(user1_id, item)

    for item in sample_items_user2:
        add_resource(user2_id, item)
