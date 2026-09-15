from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from bs4 import BeautifulSoup
import re
import os
import database

app = Flask(__name__)
app.secret_key = 'studyvault_secure_session_secret_key_2026'

# Ensure DB initialization and demo data seeding
with app.app_context():
    database.init_db()
    database.seed_demo_data()

# Middleware: Prevent caching of protected pages (prevents back button caching after logout)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

# Context Processor: Expose current user info to Jinja templates
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        return {
            'current_user': {
                'id': user_id,
                'name': session.get('user_name', 'Student'),
                'email': session.get('user_email', '')
            }
        }
    return {'current_user': None}

# Decorator: Login Required for views and API
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({"success": False, "message": "Authentication required. Please log in."}), 401
            return redirect(url_for('login_page', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def normalize_url(url):
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# Auth View Routes
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            error = "Please enter both email and password."
        else:
            user = database.get_user_by_email(email)
            if not user or not user['password_hash'] or not check_password_hash(user['password_hash'], password):
                error = "Invalid email address or password. Please try again."
            else:
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_email'] = user['email']
                
                next_url = request.args.get('next')
                if next_url and next_url.startswith('/'):
                    return redirect(next_url)
                return redirect(url_for('dashboard'))

    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not name or not email or not password or not confirm_password:
            error = "All fields are required."
        elif not is_valid_email(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif database.get_user_by_email(email):
            error = "An account with this email address already exists. Please log in."
        else:
            try:
                pwd_hash = generate_password_hash(password)
                user_id = database.create_user(name, email, pwd_hash)
                
                session['user_id'] = user_id
                session['user_name'] = name
                session['user_email'] = email.lower()
                return redirect(url_for('dashboard'))
            except Exception as e:
                error = f"Error creating account: {str(e)}"

    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# Protected Protected Page Routes
@app.route('/')
@login_required
def dashboard():
    user_id = session['user_id']
    stats = database.get_dashboard_stats(user_id)
    return render_template('dashboard.html', stats=stats)

@app.route('/resources')
@login_required
def resources_page():
    return render_template('resources.html')

@app.route('/favorites')
@login_required
def favorites_page():
    return render_template('favorites.html')

@app.route('/archived')
@login_required
def archived_page():
    return render_template('archived.html')

@app.route('/about')
@login_required
def about_page():
    return render_template('about.html')

# Protected API Endpoints (All User Isolated)
@app.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    try:
        user_id = session['user_id']
        stats = database.get_dashboard_stats(user_id)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/check-url', methods=['GET'])
@login_required
def api_check_url():
    user_id = session['user_id']
    url = request.args.get('url', '').strip()
    exclude_id = request.args.get('exclude_id', None)
    if not url:
        return jsonify({"exists": False})
    
    clean_url = normalize_url(url)
    exists = database.check_url_exists(user_id, clean_url, exclude_id)
    return jsonify({"exists": exists, "url": clean_url})

@app.route('/api/fetch-title', methods=['POST'])
@login_required
def api_fetch_title():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({"success": False, "message": "No URL provided."}), 400

    clean_url = normalize_url(url)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        response = requests.get(clean_url, headers=headers, timeout=4)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        title = None
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
        
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
            
        if title:
            title = re.sub(r'\s+', ' ', title)
            return jsonify({"success": True, "title": title, "url": clean_url})
        else:
            return jsonify({"success": False, "message": "Title tag not found on page.", "url": clean_url})

    except requests.exceptions.Timeout:
        return jsonify({"success": False, "message": "Website took too long to respond. Enter title manually.", "url": clean_url})
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": "Could not reach website automatically. Enter title manually.", "url": clean_url})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error parsing title: {str(e)}", "url": clean_url})

@app.route('/api/resources', methods=['GET'])
@login_required
def api_get_resources():
    user_id = session['user_id']
    search = request.args.get('q')
    subject = request.args.get('subject')
    category = request.args.get('category')
    priority = request.args.get('priority')
    status = request.args.get('status')
    favorite = request.args.get('favorite')
    archived = request.args.get('archived', 0)

    try:
        resources = database.get_resources(
            user_id=user_id,
            search_query=search,
            subject=subject,
            category=category,
            priority=priority,
            status=status,
            favorite=favorite,
            archived=archived
        )
        return jsonify({"success": True, "count": len(resources), "resources": resources})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/resources/<int:resource_id>', methods=['GET'])
@login_required
def api_get_resource(resource_id):
    user_id = session['user_id']
    resource = database.get_resource_by_id(user_id, resource_id)
    if not resource:
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404
    return jsonify({"success": True, "resource": resource})

@app.route('/api/resources', methods=['POST'])
@login_required
def api_add_resource():
    user_id = session['user_id']
    data = request.get_json() or {}
    
    title = data.get('title', '').strip()
    url = data.get('url', '').strip()
    subject = data.get('subject', '').strip()

    if not title or not url or not subject:
        return jsonify({"success": False, "message": "Title, URL, and Subject are required fields."}), 400

    clean_url = normalize_url(url)
    data['url'] = clean_url

    if database.check_url_exists(user_id, clean_url):
        return jsonify({
            "success": False,
            "duplicate": True,
            "message": "This resource URL has already been saved in your vault."
        }), 409

    try:
        resource_id = database.add_resource(user_id, data)
        return jsonify({"success": True, "id": resource_id, "message": "Study resource saved successfully!"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500

@app.route('/api/resources/<int:resource_id>', methods=['PUT'])
@login_required
def api_update_resource(resource_id):
    user_id = session['user_id']
    data = request.get_json() or {}
    
    existing = database.get_resource_by_id(user_id, resource_id)
    if not existing:
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404

    url = data.get('url', '').strip()
    if url:
        clean_url = normalize_url(url)
        data['url'] = clean_url
        if database.check_url_exists(user_id, clean_url, exclude_id=resource_id):
            return jsonify({
                "success": False,
                "duplicate": True,
                "message": "Another resource with this exact URL already exists in your vault."
            }), 409

    try:
        success = database.update_resource(user_id, resource_id, data)
        if success:
            return jsonify({"success": True, "message": "Resource updated successfully!"})
        return jsonify({"success": False, "message": "No changes made."}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/resources/<int:resource_id>', methods=['DELETE'])
@login_required
def api_delete_resource(resource_id):
    user_id = session['user_id']
    try:
        success = database.delete_resource(user_id, resource_id)
        if success:
            return jsonify({"success": True, "message": "Resource deleted permanently."})
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/resources/<int:resource_id>/toggle-favorite', methods=['POST'])
@login_required
def api_toggle_favorite(resource_id):
    user_id = session['user_id']
    existing = database.get_resource_by_id(user_id, resource_id)
    if not existing:
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404

    try:
        new_val = database.toggle_favorite(user_id, resource_id)
        status_text = "marked as favorite" if new_val == 1 else "removed from favorites"
        return jsonify({"success": True, "favorite": new_val, "message": f"Resource {status_text}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/resources/<int:resource_id>/toggle-archive', methods=['POST'])
@login_required
def api_toggle_archive(resource_id):
    user_id = session['user_id']
    existing = database.get_resource_by_id(user_id, resource_id)
    if not existing:
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404

    try:
        new_val = database.toggle_archive(user_id, resource_id)
        status_text = "archived" if new_val == 1 else "restored to active resources"
        return jsonify({"success": True, "archived": new_val, "message": f"Resource {status_text}."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/resources/<int:resource_id>/update-status', methods=['POST'])
@login_required
def api_update_status(resource_id):
    user_id = session['user_id']
    existing = database.get_resource_by_id(user_id, resource_id)
    if not existing:
        return jsonify({"success": False, "message": "Resource not found or access denied."}), 404

    data = request.get_json() or {}
    new_status = data.get('status', 'Not Started').strip()
    if new_status not in ['Not Started', 'In Progress', 'Completed']:
        return jsonify({"success": False, "message": "Invalid status value."}), 400
        
    try:
        success = database.update_status(user_id, resource_id, new_status)
        return jsonify({"success": True, "status": new_status, "message": f"Status updated to '{new_status}'."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/seed', methods=['POST'])
@login_required
def api_seed():
    try:
        with database.get_db() as conn:
            conn.cursor().execute("DELETE FROM resources")
            conn.cursor().execute("DELETE FROM users")
            conn.commit()
        database.seed_demo_data()
        session.clear()
        return jsonify({"success": True, "message": "Database reset with sample study resources! Please log in again."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == '__main__':
    print("Starting StudyVault Server on http://127.0.0.1:5000 ...")
    app.run(debug=True, host='127.0.0.1', port=5000)
