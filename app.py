from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash, current_app
from passlib.hash import sha256_crypt
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode
import os
from werkzeug.utils import secure_filename
import hashlib
import json

def init_db():
    """Initialize the database."""
    db = sqlite3.connect('/home/root/app_data/database.sqlite')
    db.row_factory = sqlite3.Row
    
    # Create users table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Create user_profiles table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            name TEXT,
            age INTEGER,
            school TEXT,
            skills TEXT,
            hackathon TEXT,
            preferred_jobs TEXT,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    
    # Create hackathons table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS hackathons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            location TEXT,
            max_participants INTEGER NOT NULL,
            created_by TEXT NOT NULL,
            image_path TEXT,
            FOREIGN KEY (created_by) REFERENCES users(username)
        )
    """)
    
    # Create participants table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            FOREIGN KEY (hackathon_id) REFERENCES hackathons(id),
            FOREIGN KEY (username) REFERENCES users(username),
            UNIQUE(hackathon_id, username)
        )
    """)
    
    # Create job_posts table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS job_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            url TEXT,
            username TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    """)
    
    # Create hackathon_updates table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS hackathon_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hackathon_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (hackathon_id) REFERENCES hackathons(id)
        )
    """)
    
    # Create badges table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            badge_type TEXT NOT NULL,
            badge_name TEXT NOT NULL,
            awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users(username),
            UNIQUE(username, badge_type)
        )
    """)
    
    # Create skill_endorsements table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS skill_endorsements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            endorsed_user TEXT NOT NULL,
            endorser TEXT NOT NULL,
            skill TEXT NOT NULL,
            endorsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (endorsed_user) REFERENCES users(username),
            FOREIGN KEY (endorser) REFERENCES users(username),
            UNIQUE(endorsed_user, endorser, skill)
        )
    """)
    
    # Create connections table if it doesn't exist
    db.execute("""
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1 TEXT NOT NULL,
            user2 TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1) REFERENCES users(username),
            FOREIGN KEY (user2) REFERENCES users(username),
            UNIQUE(user1, user2)
        )
    """)
    
    db.commit()
    db.close()

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            '/home/root/app_data/database.sqlite',
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key
app.config['DATABASE'] = '/home/root/app_data/database.sqlite'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize database at startup
with app.app_context():
    init_db()

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def query_db(query, args=(), one=False):
     cur = get_db().execute(query, args)
     rv = cur.fetchall()
     cur.close()
     return (rv[0] if rv else None) if one else rv

def insert_db(query, args=()):
     db = get_db()
     db.execute(query, args)
     db.commit()
     db.close()

def cleanup_old_hackathons(days_threshold=30):
    """Delete hackathons that have been expired for more than the specified number of days"""
    try:
        # Calculate the cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days_threshold)).strftime('%Y-%m-%d')
        
        # First, get the image paths of hackathons to be deleted
        old_hackathons = query_db(
            "SELECT image_path FROM hackathons WHERE date < ?", 
            [cutoff_date]
        )

        # Delete the associated images
        for hackathon in old_hackathons:
            if hackathon['image_path']:
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                        os.path.basename(hackathon['image_path']))
                if os.path.exists(image_path):
                    os.remove(image_path)

        # Delete the old hackathons and their related data
        db = get_db()
        cursor = db.cursor()
        
        # Delete from participants table first (foreign key relationships)
        cursor.execute("""
            DELETE FROM participants 
            WHERE hackathon_id IN (
                SELECT id FROM hackathons 
                WHERE date < ?
            )
        """, [cutoff_date])

        # Delete from hackathon_updates
        cursor.execute("""
            DELETE FROM hackathon_updates 
            WHERE hackathon_id IN (
                SELECT id FROM hackathons 
                WHERE date < ?
            )
        """, [cutoff_date])

        # Finally delete the hackathons
        cursor.execute("DELETE FROM hackathons WHERE date < ?", [cutoff_date])
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error cleaning up old hackathons: {str(e)}")
        return False

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'login' in request.form:
            username = request.form['login_username']
            password = request.form['login_password']
            
            user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
            
            if user and sha256_crypt.verify(password, user['password']):
                session['username'] = username
                session['logged_in'] = True
                flash("Welcome back!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid username or password!", "error")
                return redirect(url_for('home'))
        elif 'signup' in request.form:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']
            role = request.form['role']
            
            try:
                hashed_password = sha256_crypt.hash(password)
                insert_db("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                         (username, email, hashed_password, role))
                flash("Signup successful! You can now login", "success")
            except sqlite3.IntegrityError:
                flash("Username or email already exists", "error")
            return redirect(url_for('home'))

    if 'username' in session:
        username = session['username']
        user_profile = query_db("SELECT preferred_jobs FROM user_profiles WHERE username = ?", [username], one=True)
        preferred_jobs = user_profile['preferred_jobs'].split(',') if user_profile and user_profile['preferred_jobs'] else []

        if preferred_jobs:
            job_conditions = " OR ".join(["title LIKE ? OR description LIKE ?" for _ in preferred_jobs])
            job_params = [f"%{job.strip()}%" for job in preferred_jobs for _ in range(2)]

            personalised_jobs = query_db(f"""
                SELECT * FROM job_posts
                WHERE {job_conditions}
                ORDER BY id DESC
            """, job_params)

            general_jobs = query_db(f"""
                SELECT * FROM job_posts
                WHERE NOT ({job_conditions})
                ORDER BY id DESC
            """, job_params)
        else:
            personalised_jobs = []
            general_jobs = query_db("SELECT * FROM job_posts ORDER BY id DESC")

        return render_template('index.html', logged_in=True, personalised_jobs=personalised_jobs, general_jobs=general_jobs)

    all_jobs = query_db("SELECT * FROM job_posts ORDER BY id DESC")
    guest_hackathons = query_db("SELECT * FROM hackathons ORDER BY id DESC LIMIT 3")
    return render_template('index.html', logged_in=False, general_jobs=all_jobs, guest_hackathons=guest_hackathons)


@app.route('/hack', methods=['GET'])
def hack():
    if 'username' not in session:
        flash("Please log in to view hackathons.", "error")
        return redirect(url_for('home'))

    username = session['username']
    today = datetime.now().strftime('%Y-%m-%d')
    today_date = datetime.now().date()

    # Clean up old hackathons (older than 30 days)
    cleanup_old_hackathons(30)

    active_hackathons = query_db("""
        SELECT h.id, h.title, h.image_path 
        FROM hackathons h 
        WHERE h.date >= ? 
        ORDER BY h.date ASC
    """, [today])

    user_profile = query_db("SELECT skills FROM user_profiles WHERE username = ?", [username], one=True)
    user_skills = user_profile['skills'].split(',') if user_profile and user_profile['skills'] else []

    hackathon_base_query = """
    SELECT h.id, h.title, h.description, h.date, h.location, h.max_participants,
           h.created_by, h.image_path,
           COUNT(p.id) AS current_participants,
           CASE WHEN p2.username IS NOT NULL THEN 1 ELSE 0 END AS joined
    FROM hackathons h
    LEFT JOIN participants p ON h.id = p.hackathon_id
    LEFT JOIN participants p2 ON h.id = p2.hackathon_id AND p2.username = ?
    WHERE h.date >= ?
"""
    
    if user_skills:
        skill_conditions = " OR ".join([
            "(LOWER(h.title) LIKE LOWER(?) OR LOWER(h.description) LIKE LOWER(?))"
            for _ in user_skills
        ])
        skill_params = [f"%{skill.strip().lower()}%" for skill in user_skills for _ in range(2)]

        matching_hackathons = query_db(f"""
            {hackathon_base_query} AND ({skill_conditions})
            GROUP BY h.id
            ORDER BY h.date ASC
        """, [username, today] + skill_params)

        other_hackathons = query_db(f"""
            {hackathon_base_query} AND NOT ({skill_conditions})
            GROUP BY h.id
            ORDER BY h.date ASC
        """, [username, today] + skill_params)
    else:
        matching_hackathons = []
        other_hackathons = query_db(f"""
            {hackathon_base_query}
            GROUP BY h.id
            ORDER BY h.date ASC
        """, [username, today])

    expired_hackathons = query_db("""
        SELECT h.id, h.title, h.description, h.date, h.location, h.max_participants,
               h.created_by, h.image_path,
               COUNT(p.id) AS current_participants,
               CASE WHEN p2.username IS NOT NULL THEN 1 ELSE 0 END AS joined
        FROM hackathons h
        LEFT JOIN participants p ON h.id = p.hackathon_id
        LEFT JOIN participants p2 ON h.id = p2.hackathon_id AND p2.username = ?
        WHERE h.date < ?
        GROUP BY h.id
        ORDER BY h.date DESC
    """, [username, today])

    # Convert Row objects to dictionaries and calculate days since expiration
    expired_hackathons = [dict(hackathon) for hackathon in expired_hackathons]
    for hackathon in expired_hackathons:
        hackathon_date = datetime.strptime(hackathon['date'], '%Y-%m-%d').date()
        days_expired = (today_date - hackathon_date).days
        hackathon['days_expired'] = days_expired

    return render_template(
        'hack.html', 
        matching_hackathons=matching_hackathons, 
        other_hackathons=other_hackathons, 
        expired_hackathons=expired_hackathons,
        active_hackathons=active_hackathons
    )

@app.route('/post_hackathon', methods=['POST'])
def post_hackathon():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'You need to be logged in to post a hackathon'}), 401

    username = session['username']
    title = request.form.get('title')
    description = request.form.get('description')
    date = request.form.get('date')
    location = request.form.get('location')
    max_participants = request.form.get('max_participants')
    hackathon_id = request.form.get('hackathon_id')
    image = request.files.get('image')
    current_image_path = request.form.get('current_image_path')

    # Handle image upload
    image_path = current_image_path
    if image and image.filename:
        if not allowed_file(image.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Only images are allowed.'}), 400
        
        filename = secure_filename(image.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        
        # Save the file
        image_path = os.path.join('uploads', filename)  # Store relative path without 'static/'
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        image.save(full_path)

    try:
        db = get_db()
        cursor = db.cursor()

        if hackathon_id:
            # Check if the user owns this hackathon
            hackathon = query_db(
                "SELECT created_by, image_path FROM hackathons WHERE id = ?", [hackathon_id], one=True
            )
            if not hackathon or hackathon['created_by'] != username:
                return jsonify({'success': False, 'message': 'You do not have permission to edit this hackathon.'})

            # If a new image is uploaded or image is removed, delete the old one if it exists
            if ((image_path and image_path != hackathon['image_path']) or not image_path) and hackathon['image_path']:
                old_image_path = os.path.join('static', hackathon['image_path'])
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

            # If no new image is uploaded and no current_image_path is provided, keep the existing image
            if not image_path and hackathon['image_path']:
                image_path = hackathon['image_path']

            # Editing existing hackathon
            cursor.execute("""
                UPDATE hackathons
                SET title = ?, description = ?, date = ?, location = ?, max_participants = ?, image_path = ?
                WHERE id = ?
            """, (title, description, date, location, max_participants, image_path, hackathon_id))
            
            current_participants = query_db(
                "SELECT COUNT(*) FROM participants WHERE hackathon_id = ?", [hackathon_id], one=True
            )[0]
            joined = bool(query_db(
                "SELECT 1 FROM participants WHERE hackathon_id = ? AND username = ?", 
                [hackathon_id, username], one=True
            ))
        else:
            # Creating a new hackathon
            cursor.execute("""
                INSERT INTO hackathons (title, description, date, location, max_participants, created_by, image_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, description, date, location, max_participants, username, image_path))
            hackathon_id = cursor.lastrowid
            current_participants = 0
            joined = False

        db.commit()

        today = datetime.now().date()
        category = "expired" if datetime.strptime(date, "%Y-%m-%d").date() < today else "other"

        user_profile = query_db("SELECT skills FROM user_profiles WHERE username = ?", [username], one=True)
        user_skills = user_profile['skills'].split(',') if user_profile and user_profile['skills'] else []

        if user_skills and any(skill.strip().lower() in (title + description).lower() for skill in user_skills):
            category = "matching"

        updated_hackathon = query_db("SELECT * FROM hackathons WHERE id = ?", [hackathon_id], one=True)

        return jsonify({
            'success': True,
            'hackathon': {
                'id': updated_hackathon['id'],
                'title': updated_hackathon['title'],
                'description': updated_hackathon['description'],
                'date': updated_hackathon['date'],
                'location': updated_hackathon['location'],
                'current_participants': current_participants,
                'max_participants': updated_hackathon['max_participants'],
                'category': category,
                'joined': joined,
                'role': session.get('role', 'user'),
                'created_by': updated_hackathon['created_by'],
                'current_user': session.get('username'),
                'image_path': updated_hackathon['image_path']
            }
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})
    

@app.route('/edit_hackathon/<int:hackathon_id>', methods=['POST'])
def edit_hackathon(hackathon_id):
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    location = request.form['location']

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE hackathons
            SET title = ?, description = ?, date = ?, location = ?
            WHERE id = ?
        """, (title, description, date, location, hackathon_id))
        db.commit()

        # Fetching updated hackathon data to return to the client
        updated_hackathon = query_db("SELECT * FROM hackathons WHERE id = ?", [hackathon_id], one=True)
        category = "expired" if updated_hackathon['date'] < str(datetime.now().date()) else "other"

        return jsonify({
            'success': True,
            'hackathon': {
                'id': updated_hackathon['id'],
                'title': updated_hackathon['title'],
                'description': updated_hackathon['description'],
                'date': updated_hackathon['date'],
                'location': updated_hackathon['location'],
                'category': category,
                'role': 'organiser'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    

@app.route('/get_hackathon/<int:hackathon_id>', methods=['GET'])
def get_hackathon(hackathon_id):
    hackathon = query_db("SELECT * FROM hackathons WHERE id = ?", [hackathon_id], one=True)
    if hackathon:
        current_participants = query_db("SELECT COUNT(*) FROM participants WHERE hackathon_id = ?", [hackathon_id], one=True)[0]
        return jsonify({
            'success': True,
            'hackathon': {
                'id': hackathon['id'],
                'title': hackathon['title'],
                'description': hackathon['description'],
                'date': hackathon['date'],
                'location': hackathon['location'],
                'max_participants': hackathon['max_participants'],
                'current_participants': current_participants,
                'created_by': hackathon['created_by'], 
                'joined': session['username'] in [p['username'] for p in query_db("SELECT username FROM participants WHERE hackathon_id = ?", [hackathon_id])]
            }
        })
    return jsonify({'success': False, 'message': 'Hackathon not found.'})

@app.route('/create_post', methods=['POST'])
def create_post():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'You need to be logged in to create a post'}), 401

    title = request.form.get('title')
    description = request.form.get('description')
    url = request.form.get('url')
    username = session['username']
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    user_profile = query_db("SELECT preferred_jobs FROM user_profiles WHERE username = ?", [username], one=True)
    preferred_jobs = user_profile[0].split(',') if user_profile and user_profile[0] else []
    matching = any(job.strip().lower() in (title + description).lower() for job in preferred_jobs)

    category = 'personalised' if matching else 'general'

    try:
        insert_db("INSERT INTO job_posts (title, description, url, username, date) VALUES (?, ?, ?, ?, ?)",
                  (title, description, url, username, date))

        return jsonify({
            'success': True,
            'post': {
                'title': title,
                'description': description,
                'url': url,
                'username': username,
                'date': date,
                'category': category  
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': 'An error occurred while saving the job post.'}), 500
     

@app.route('/profile')
@app.route('/profile/<username>')
def profile(username=None):
    if 'username' not in session:
        return redirect(url_for('home'))

    # If no username provided, use the logged-in user's username
    if username is None:
        username = session['username']

    # Get user details from both users and user_profiles tables
    user_details = query_db("""
        SELECT u.username, u.email, u.role,
               up.name, up.age, up.school, up.skills, up.hackathon,
               up.preferred_jobs
        FROM users u
        LEFT JOIN user_profiles up ON u.username = up.username
        WHERE u.username = ?
    """, [username], one=True)

    if not user_details:
        flash('User not found!', 'error')
        return redirect(url_for('home'))

    # Check and award badges
    check_and_award_badges(username)
    
    # Get user's badges
    badges = query_db("""
        SELECT badge_type, badge_name, 
               strftime('%Y-%m-%d', awarded_at) as awarded_at 
        FROM badges 
        WHERE username = ? 
        ORDER BY awarded_at DESC
    """, [username])

    return render_template('profile.html', 
                         user_details=user_details,
                         badges=badges,
                         is_own_profile=session['username'] == username)

@app.route('/join_hackathon', methods=['POST'])
def join_hackathon():
    if 'username' not in session:
        return jsonify({"success": False, "message": "Please log in to join a hackathon."})

    data = request.get_json()
    hackathon_id = data.get('id')
    username = session['username']

    # Checking if the user is already a participant
    existing_entry = query_db("SELECT * FROM participants WHERE hackathon_id = ? AND username = ?", 
                              (hackathon_id, username), one=True)
    if existing_entry:
        return jsonify({"success": False, "message": "You have already joined this hackathon."})

    # Incrementing the current participant count if there's room
    hackathon = query_db("SELECT max_participants, current_participants FROM hackathons WHERE id = ?", [hackathon_id], one=True)
    if hackathon['current_participants'] >= hackathon['max_participants']:
        return jsonify({"success": False, "message": "This hackathon has reached the maximum number of participants."})

    try:
        # Inserting participant and incrementing current_participants
        insert_db("INSERT INTO participants (hackathon_id, username) VALUES (?, ?)", (hackathon_id, username))
        updated_count = query_db("SELECT COUNT(*) FROM participants WHERE hackathon_id = ?", [hackathon_id], one=True)[0]
        
        # Debug log for updated participant count
        print(f"Updated participant count for hackathon {hackathon_id}: {updated_count}")
        
        # Returning updated count and success status
        return jsonify({
            "success": True,
            "current_participants": updated_count,
            "max_participants": hackathon['max_participants']
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    

@app.route('/add_to_google_calendar/<int:hackathon_id>')
def add_to_google_calendar(hackathon_id):
    hackathon = query_db("SELECT title, description, date, location FROM hackathons WHERE id = ?", [hackathon_id], one=True)

    if hackathon:
        event_start = datetime.strptime(hackathon['date'], '%Y-%m-%d')
        event_end = event_start + timedelta(hours=2)

        start_time = event_start.strftime('%Y%m%dT%H%M%SZ')
        end_time = event_end.strftime('%Y%m%dT%H%M%SZ')

        google_calendar_url = (
            "https://www.google.com/calendar/render?action=TEMPLATE&" +
            urlencode({
                "text": hackathon['title'],
                "dates": f"{start_time}/{end_time}",
                "details": hackathon['description'],
                "location": hackathon['location'],
                "sf": "true",
                "output": "xml"
            })
        )

        return redirect(google_calendar_url)
    else:
        return "Hackathon not found", 404
    


@app.route('/hackathon/<int:hackathon_id>/updates')
def hackathon_page(hackathon_id):
    hackathon = query_db("SELECT * FROM hackathons WHERE id = ?", [hackathon_id], one=True)
    updates = query_db("SELECT * FROM hackathon_updates WHERE hackathon_id = ? ORDER BY created_at DESC", [hackathon_id])
    if not hackathon:
        return "Hackathon not found", 404
    
    return render_template('updates.html', hackathon=hackathon, updates=updates, is_creator=(hackathon['created_by'] == session.get('username')))


@app.route('/add_update', methods=['POST'])
def add_update():
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'Please log in to add an update.'}), 401

    hackathon_id = request.form['hackathon_id']
    content = request.form['content']
    username = session['username']
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    hackathon = query_db("SELECT created_by FROM hackathons WHERE id = ?", [hackathon_id], one=True)
    if not hackathon:
        return jsonify({'success': False, 'message': 'Hackathon not found.'}), 404
    if hackathon['created_by'] != username:
        return jsonify({'success': False, 'message': 'You are not authorised to post updates for this hackathon.'}), 403

    try:
        insert_db("INSERT INTO hackathon_updates (hackathon_id, content, created_at) VALUES (?, ?, ?)", 
                  (hackathon_id, content, created_at))
        return jsonify({'success': True, 'update': {'content': content, 'created_at': created_at}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/get_updates/<int:hackathon_id>', methods=['GET'])
def get_updates(hackathon_id):
    updates = query_db("SELECT * FROM hackathon_updates WHERE hackathon_id = ? ORDER BY created_at DESC", [hackathon_id])
    return jsonify([dict(update) for update in updates])

@app.route('/logout')
def logout():
     session.clear()
     flash("Logged out successfully", "success")
     return redirect(url_for('home'))

# User Search and Messaging Routes
@app.route('/search_users', methods=['GET'])
def search_users():
    if 'username' not in session:
        flash("Please log in to search users.", "error")
        return redirect(url_for('home'))
    
    search_query = request.args.get('q', '')
    if search_query:
        users = query_db("""
            SELECT username, email FROM users 
            WHERE username != ? AND username LIKE ? 
            ORDER BY username
        """, [session['username'], f'%{search_query}%'])
    else:
        users = []
    
    return render_template('search_users.html', users=users, search_query=search_query)

@app.route('/connections', methods=['GET'])
def connections():
    if 'username' not in session:
        flash("Please log in to view connections.", "error")
        return redirect(url_for('home'))
    
    connections = query_db("""
        SELECT 
            u.username, 
            u.email, 
            c.status, 
            c.created_at,
            CASE 
                WHEN c.user1 = ? THEN 'sent'
                WHEN c.user2 = ? THEN 'received'
            END as request_type
        FROM connections c
        JOIN users u ON (c.user1 = u.username OR c.user2 = u.username)
        WHERE (c.user1 = ? OR c.user2 = ?) AND u.username != ?
        ORDER BY c.created_at DESC
    """, [session['username'], session['username'], session['username'], session['username'], session['username']])
    
    return render_template('connections.html', connections=connections)

@app.route('/connect', methods=['POST'])
def connect():
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    target_user = request.form.get('username')
    if not target_user:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        # Check if connection already exists
        existing = query_db("""
            SELECT * FROM connections 
            WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)
        """, [session['username'], target_user, target_user, session['username']], one=True)
        
        if existing:
            return jsonify({'error': 'Connection already exists'}), 400
        
        # Create new connection
        insert_db("""
            INSERT INTO connections (user1, user2, status, created_at) 
            VALUES (?, ?, 'pending', datetime('now'))
        """, [session['username'], target_user])
        
        return jsonify({'message': 'Connection request sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/messages/<username>', methods=['GET'])
def messages(username):
    if 'username' not in session:
        flash("Please log in to view messages.", "error")
        return redirect(url_for('home'))
    
    # Check if there's a connection between users
    connection = query_db("""
        SELECT * FROM connections 
        WHERE ((user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?))
        AND status = 'accepted'
    """, [session['username'], username, username, session['username']], one=True)
    
    if not connection:
        flash("You need to be connected with this user to send messages.", "error")
        return redirect(url_for('connections'))
    
    messages = query_db("""
        SELECT * FROM messages 
        WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
        ORDER BY sent_at ASC
    """, [session['username'], username, username, session['username']])
    
    # Mark messages from this user as read
    insert_db("""
        UPDATE unread_messages 
        SET is_read = 1 
        WHERE receiver = ? 
        AND message_id IN (
            SELECT id FROM messages WHERE sender = ?
        )
    """, [session['username'], username])
    
    return render_template('messages.html', messages=messages, other_user=username)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    receiver = request.form.get('receiver')
    message = request.form.get('message')
    
    if not receiver or not message:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        # Check if there's a connection between users
        connection = query_db("""
            SELECT * FROM connections 
            WHERE ((user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?))
            AND status = 'accepted'
        """, [session['username'], receiver, receiver, session['username']], one=True)
        
        if not connection:
            return jsonify({'error': 'You need to be connected with this user to send messages'}), 403
        
        # Insert message
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO messages (sender, receiver, content, sent_at) 
            VALUES (?, ?, ?, datetime('now'))
        """, [session['username'], receiver, message])
        message_id = cursor.lastrowid
        
        # Track as unread
        cursor.execute("""
            INSERT INTO unread_messages (message_id, receiver) 
            VALUES (?, ?)
        """, [message_id, receiver])
        
        db.commit()
        db.close()
        
        return jsonify({'message': 'Message sent'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_connection_status', methods=['POST'])
def update_connection_status():
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    username = request.form.get('username')
    action = request.form.get('action')
    
    if not username or action not in ['accept', 'reject']:
        return jsonify({'error': 'Invalid request'}), 400
    
    try:
        # Check if connection exists and user is the receiver
        connection = query_db("""
            SELECT * FROM connections 
            WHERE user2 = ? AND user1 = ? AND status = 'pending'
        """, [session['username'], username], one=True)
        
        if not connection:
            return jsonify({'error': 'Connection request not found'}), 404
        
        if action == 'accept':
            insert_db("""
                UPDATE connections 
                SET status = 'accepted' 
                WHERE user2 = ? AND user1 = ?
            """, [session['username'], username])
        else:  # reject
            insert_db("""
                DELETE FROM connections 
                WHERE user2 = ? AND user1 = ?
            """, [session['username'], username])
        
        return jsonify({'message': f'Connection {action}ed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_unread_count/<username>', methods=['GET'])
def get_unread_count(username):
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    try:
        unread_count = query_db("""
            SELECT COUNT(*) as count 
            FROM unread_messages 
            WHERE receiver = ? AND is_read = 0
        """, [username], one=True)
        
        return jsonify({'count': unread_count['count']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_unread_counts', methods=['GET'])
def get_unread_counts():
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    try:
        # Get unread counts grouped by sender
        unread_counts = query_db("""
            SELECT m.sender, COUNT(*) as count 
            FROM unread_messages um 
            JOIN messages m ON um.message_id = m.id 
            WHERE um.receiver = ? AND um.is_read = 0 
            GROUP BY m.sender
        """, [session['username']])
        
        return jsonify({'counts': {row['sender']: row['count'] for row in unread_counts}})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark_messages_read/<sender>', methods=['POST'])
def mark_messages_read(sender):
    if 'username' not in session:
        return jsonify({'error': 'Please log in'}), 401
    
    try:
        # Mark all messages from this sender as read
        insert_db("""
            UPDATE unread_messages 
            SET is_read = 1 
            WHERE receiver = ? 
            AND message_id IN (
                SELECT id FROM messages WHERE sender = ?
            )
        """, [session['username'], sender])
        
        return jsonify({'message': 'Messages marked as read'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Resources routes
@app.route('/resources')
def resources():
    if 'username' not in session:
        return redirect(url_for('home'))
    return render_template('resources.html')

@app.route('/resources/<topic>')
def resource_detail(topic):
    if 'username' not in session:
        return redirect(url_for('home'))
    
    # Define content for each topic
    topics = {
        'html': {
            'title': 'HTML',
            'icon': 'fab fa-html5',
            'description': 'Learn the fundamentals of HTML, semantic markup, and best practices for structuring web content.',
            'sections': [
                {
                    'title': 'HTML Basics',
                    'content': '''
                        <p>HTML (HyperText Markup Language) is the standard markup language for creating web pages. Here are the key concepts:</p>
                        <ul>
                            <li>HTML documents are made up of elements</li>
                            <li>Elements are defined by tags</li>
                            <li>Tags usually come in pairs: opening and closing tags</li>
                            <li>Elements can contain other elements (nesting)</li>
                        </ul>
                    ''',
                    'code_example': '''
<!DOCTYPE html>
<html>
<head>
    <title>My First Page</title>
</head>
<body>
    <h1>Welcome!</h1>
    <p>This is a paragraph.</p>
</body>
</html>''',
                    'resources': [
                        {'title': 'MDN HTML Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Learn/HTML'},
                        {'title': 'W3Schools HTML Tutorial', 'url': 'https://www.w3schools.com/html/'}
                    ]
                }
            ]
        },
        'css': {
            'title': 'CSS',
            'icon': 'fab fa-css3-alt',
            'description': 'Master CSS styling, layouts, and responsive design techniques for creating beautiful web interfaces.',
            'sections': [
                {
                    'title': 'CSS Fundamentals',
                    'content': '''
                        <p>CSS (Cascading Style Sheets) is used to style and layout web pages. Key concepts include:</p>
                        <ul>
                            <li>Selectors and properties</li>
                            <li>Box model</li>
                            <li>Flexbox and Grid layouts</li>
                            <li>Responsive design with media queries</li>
                        </ul>
                    ''',
                    'code_example': '''
/* Basic CSS example */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.button {
    background-color: #0073b1;
    color: white;
    padding: 10px 20px;
    border-radius: 5px;
    transition: background-color 0.3s;
}''',
                    'resources': [
                        {'title': 'MDN CSS Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Learn/CSS'},
                        {'title': 'CSS-Tricks', 'url': 'https://css-tricks.com'}
                    ]
                }
            ]
        },
        'javascript': {
            'title': 'JavaScript',
            'icon': 'fab fa-js',
            'description': 'Learn modern JavaScript programming, from basics to advanced concepts and frameworks.',
            'sections': [
                {
                    'title': 'JavaScript Fundamentals',
                    'content': '''
                        <p>JavaScript is a versatile programming language for web development. Core concepts include:</p>
                        <ul>
                            <li>Variables and data types</li>
                            <li>Functions and scope</li>
                            <li>DOM manipulation</li>
                            <li>Asynchronous programming</li>
                        </ul>
                    ''',
                    'code_example': '''
// Basic JavaScript example
function greetUser(name) {
    return `Hello, ${name}!`;
}

const button = document.querySelector('.button');
button.addEventListener('click', () => {
    const message = greetUser('World');
    console.log(message);
});''',
                    'resources': [
                        {'title': 'MDN JavaScript Guide', 'url': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript'},
                        {'title': 'JavaScript.info', 'url': 'https://javascript.info'}
                    ]
                }
            ]
        },
        'python': {
            'title': 'Python',
            'icon': 'fab fa-python',
            'description': 'Master Python programming for web development, data science, and automation.',
            'sections': [
                {
                    'title': 'Python Basics',
                    'content': '''
                        <p>Python is a versatile, high-level programming language known for its readability and simplicity. Key concepts include:</p>
                        <ul>
                            <li>Variables and data structures</li>
                            <li>Control flow and functions</li>
                            <li>Object-oriented programming</li>
                            <li>Modules and packages</li>
                        </ul>
                    ''',
                    'code_example': '''# Python basics example
def calculate_average(numbers):
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

# List comprehension example
squares = [x**2 for x in range(10)]

# Class example
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age
        
    def greet(self):
        return f"Hello, my name is {self.name}!"''',
                    'resources': [
                        {'title': 'Python Official Documentation', 'url': 'https://docs.python.org/3/'},
                        {'title': 'Real Python Tutorials', 'url': 'https://realpython.com'}
                    ]
                }
            ]
        },
        'nodejs': {
            'title': 'Node.js',
            'icon': 'fab fa-node-js',
            'description': 'Build scalable server-side applications with Node.js and its ecosystem.',
            'sections': [
                {
                    'title': 'Node.js Fundamentals',
                    'content': '''
                        <p>Node.js is a runtime environment that executes JavaScript code outside a web browser. Important concepts include:</p>
                        <ul>
                            <li>Event-driven programming</li>
                            <li>Asynchronous I/O</li>
                            <li>NPM (Node Package Manager)</li>
                            <li>Express.js framework</li>
                        </ul>
                    ''',
                    'code_example': '''// Basic Node.js server
const express = require('express');
const app = express();
const port = 3000;

app.get('/', (req, res) => {
    res.send('Hello World!');
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});''',
                    'resources': [
                        {'title': 'Node.js Documentation', 'url': 'https://nodejs.org/docs/latest/api/'},
                        {'title': 'Express.js Guide', 'url': 'https://expressjs.com/'}
                    ]
                }
            ]
        },
        'databases': {
            'title': 'Databases',
            'icon': 'fas fa-database',
            'description': 'Learn about different database systems and how to effectively manage data.',
            'sections': [
                {
                    'title': 'Database Fundamentals',
                    'content': '''
                        <p>Understanding databases is crucial for modern web development. Key concepts include:</p>
                        <ul>
                            <li>Relational vs NoSQL databases</li>
                            <li>CRUD operations</li>
                            <li>Database design and normalization</li>
                            <li>Indexing and optimization</li>
                        </ul>
                    ''',
                    'code_example': '''-- SQL example
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Basic queries
SELECT * FROM users WHERE id = 1;
INSERT INTO users (username, email) VALUES ('john_doe', 'john@example.com');
UPDATE users SET email = 'new@example.com' WHERE username = 'john_doe';''',
                    'resources': [
                        {'title': 'PostgreSQL Documentation', 'url': 'https://www.postgresql.org/docs/'},
                        {'title': 'MongoDB Manual', 'url': 'https://docs.mongodb.com/manual/'}
                    ]
                }
            ]
        },
        'git': {
            'title': 'Git Basics',
            'icon': 'fab fa-git-alt',
            'description': 'Master version control with Git to track and manage your code changes effectively.',
            'sections': [
                {
                    'title': 'Git Fundamentals',
                    'content': '''
                        <p>Git is essential for modern software development. Important concepts include:</p>
                        <ul>
                            <li>Basic Git commands</li>
                            <li>Branching and merging</li>
                            <li>Resolving conflicts</li>
                            <li>Best practices for commits</li>
                        </ul>
                    ''',
                    'code_example': '''# Common Git commands
git init  # Initialize a new repository
git add .  # Stage all changes
git commit -m "Add new feature"  # Commit changes
git branch feature  # Create new branch
git checkout feature  # Switch to branch
git merge feature  # Merge branch
git pull origin main  # Pull updates
git push origin main  # Push changes''',
                    'resources': [
                        {'title': 'Git Documentation', 'url': 'https://git-scm.com/doc'},
                        {'title': 'Git Branching Tutorial', 'url': 'https://learngitbranching.js.org/'}
                    ]
                }
            ]
        },
        'github': {
            'title': 'GitHub',
            'icon': 'fab fa-github',
            'description': 'Learn to use GitHub for collaboration, code hosting, and project management.',
            'sections': [
                {
                    'title': 'GitHub Essentials',
                    'content': '''
                        <p>GitHub extends Git with powerful collaboration features. Key aspects include:</p>
                        <ul>
                            <li>Pull requests and code review</li>
                            <li>Issue tracking</li>
                            <li>Project boards</li>
                            <li>GitHub Actions (CI/CD)</li>
                        </ul>
                    ''',
                    'code_example': '''# GitHub workflow example
# 1. Fork a repository
# 2. Clone your fork
git clone https://github.com/username/repo.git

# 3. Create a feature branch
git checkout -b feature-name

# 4. Make changes and commit
git add .
git commit -m "Add new feature"

# 5. Push to GitHub
git push origin feature-name

# 6. Create pull request on GitHub''',
                    'resources': [
                        {'title': 'GitHub Guides', 'url': 'https://guides.github.com/'},
                        {'title': 'GitHub Learning Lab', 'url': 'https://lab.github.com/'}
                    ]
                }
            ]
        },
        'workflow': {
            'title': 'Development Workflow',
            'icon': 'fas fa-code-branch',
            'description': 'Learn best practices for efficient development workflows and collaboration.',
            'sections': [
                {
                    'title': 'Workflow Best Practices',
                    'content': '''
                        <p>A good development workflow is crucial for team success. Important aspects include:</p>
                        <ul>
                            <li>Branch naming conventions</li>
                            <li>Code review processes</li>
                            <li>Continuous Integration</li>
                            <li>Deployment strategies</li>
                        </ul>
                    ''',
                    'code_example': '''# Example Git workflow

# Feature branch naming
feature/user-authentication
bugfix/login-error
hotfix/security-patch

# Commit message format
type(scope): subject

# Examples:
feat(auth): add OAuth2 authentication
fix(ui): resolve button alignment
docs(api): update endpoint documentation''',
                    'resources': [
                        {'title': 'Git Flow', 'url': 'https://nvie.com/posts/a-successful-git-branching-model/'},
                        {'title': 'Trunk Based Development', 'url': 'https://trunkbaseddevelopment.com/'}
                    ]
                }
            ]
        },
        'agile': {
            'title': 'Agile Methodology',
            'icon': 'fas fa-tasks',
            'description': 'Understand Agile principles and practices for effective project management.',
            'sections': [
                {
                    'title': 'Agile Fundamentals',
                    'content': '''
                        <p>Agile methodology promotes iterative development and team collaboration. Key concepts include:</p>
                        <ul>
                            <li>Scrum framework</li>
                            <li>Sprint planning</li>
                            <li>Daily stand-ups</li>
                            <li>Retrospectives</li>
                        </ul>
                    ''',
                    'code_example': '''# Example Sprint Board Structure

Backlog
- User story 1
- User story 2

Sprint (Current)
- Task 1 (In Progress)
- Task 2 (To Do)
- Task 3 (Done)

Done
- Previous sprint items
- Completed features''',
                    'resources': [
                        {'title': 'Agile Manifesto', 'url': 'https://agilemanifesto.org/'},
                        {'title': 'Scrum Guide', 'url': 'https://scrumguides.org/'}
                    ]
                }
            ]
        },
        'tools': {
            'title': 'Project Management Tools',
            'icon': 'fas fa-tools',
            'description': 'Explore popular project management tools and their effective usage.',
            'sections': [
                {
                    'title': 'Popular PM Tools',
                    'content': '''
                        <p>Project management tools help teams stay organized and productive. Common tools include:</p>
                        <ul>
                            <li>Jira for issue tracking</li>
                            <li>Trello for kanban boards</li>
                            <li>Slack for communication</li>
                            <li>Confluence for documentation</li>
                        </ul>
                    ''',
                    'code_example': '''// Example Jira Issue
{
    "type": "Story",
    "priority": "High",
    "summary": "Implement user authentication",
    "description": "Add OAuth2 login with Google",
    "acceptance_criteria": [
        "Login with Google button works",
        "User data is stored securely",
        "Session management implemented"
    ],
    "story_points": 5
}''',
                    'resources': [
                        {'title': 'Atlassian Tools', 'url': 'https://www.atlassian.com/software'},
                        {'title': 'Trello Guides', 'url': 'https://trello.com/guide'}
                    ]
                }
            ]
        },
        'best-practices': {
            'title': 'Development Best Practices',
            'icon': 'fas fa-check-double',
            'description': 'Learn industry-standard best practices for writing clean, maintainable code.',
            'sections': [
                {
                    'title': 'Coding Best Practices',
                    'content': '''
                        <p>Following best practices leads to better code quality. Key principles include:</p>
                        <ul>
                            <li>Clean Code principles</li>
                            <li>SOLID principles</li>
                            <li>Code documentation</li>
                            <li>Testing strategies</li>
                        </ul>
                    ''',
                    'code_example': '''# Example of clean code principles

# Bad example
def x(a):
    return a * 24 * 60

# Good example
def convert_days_to_minutes(days):
    HOURS_PER_DAY = 24
    MINUTES_PER_HOUR = 60
    return days * HOURS_PER_DAY * MINUTES_PER_HOUR

# Example of SOLID principles
class PaymentProcessor:
    def process_payment(self, payment):
        if payment.type == "credit":
            self.process_credit_payment(payment)
        elif payment.type == "debit":
            self.process_debit_payment(payment)''',
                    'resources': [
                        {'title': 'Clean Code', 'url': 'https://www.amazon.com/Clean-Code-Handbook-Software-Craftsmanship/dp/0132350882'},
                        {'title': 'SOLID Principles', 'url': 'https://www.digitalocean.com/community/conceptual_articles/s-o-l-i-d-the-first-five-principles-of-object-oriented-design'}
                    ]
                }
            ]
        },
        'rest-api': {
            'title': 'REST APIs',
            'icon': 'fas fa-plug',
            'description': 'Learn how to design, build, and consume RESTful APIs.',
            'sections': [
                {
                    'title': 'REST API Fundamentals',
                    'content': '''
                        <p>REST APIs are fundamental to modern web development. Key concepts include:</p>
                        <ul>
                            <li>HTTP methods (GET, POST, PUT, DELETE)</li>
                            <li>Status codes and responses</li>
                            <li>API authentication</li>
                            <li>RESTful principles</li>
                        </ul>
                    ''',
                    'code_example': '''# Example REST API endpoints

# User endpoints
GET /api/users          # List all users
POST /api/users         # Create new user
GET /api/users/{id}     # Get specific user
PUT /api/users/{id}     # Update user
DELETE /api/users/{id}  # Delete user

# Example response
{
    "status": "success",
    "data": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2024-01-01T12:00:00Z"
    }
}''',
                    'resources': [
                        {'title': 'REST API Tutorial', 'url': 'https://restfulapi.net/'},
                        {'title': 'API Design Guide', 'url': 'https://google.aip.dev/'}
                    ]
                }
            ]
        },
        'authentication': {
            'title': 'Authentication',
            'icon': 'fas fa-lock',
            'description': 'Learn about different authentication methods and security best practices.',
            'sections': [
                {
                    'title': 'Authentication Basics',
                    'content': '''
                        <p>Secure authentication is crucial for web applications. Important concepts include:</p>
                        <ul>
                            <li>Session-based authentication</li>
                            <li>JWT (JSON Web Tokens)</li>
                            <li>OAuth2 and OpenID Connect</li>
                            <li>Password hashing and security</li>
                        </ul>
                    ''',
                    'code_example': '''# Example JWT implementation
import jwt

# Create JWT token
def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

# Verify JWT token
def verify_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return 'Token expired'
    except jwt.InvalidTokenError:
        return 'Invalid token' ''',
                    'resources': [
                        {'title': 'OAuth2 Specification', 'url': 'https://oauth.net/2/'},
                        {'title': 'JWT Introduction', 'url': 'https://jwt.io/introduction'}
                    ]
                }
            ]
        },
        'third-party': {
            'title': 'Third-party APIs',
            'icon': 'fas fa-puzzle-piece',
            'description': 'Learn how to integrate and work with various third-party APIs.',
            'sections': [
                {
                    'title': 'API Integration',
                    'content': '''
                        <p>Third-party APIs extend your application's capabilities. Important aspects include:</p>
                        <ul>
                            <li>API authentication</li>
                            <li>Rate limiting</li>
                            <li>Error handling</li>
                            <li>Data transformation</li>
                        </ul>
                    ''',
                    'code_example': '''# Example: Using requests library with GitHub API
import requests

def get_github_repos(username):
    url = f'https://api.github.com/users/{username}/repos'
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching repos: {e}")
        return None''',
                    'resources': [
                        {'title': 'Public APIs Directory', 'url': 'https://github.com/public-apis/public-apis'},
                        {'title': 'Postman Learning Center', 'url': 'https://learning.postman.com/'}
                    ]
                }
            ]
        }
    }
    
    if topic not in topics:
        return redirect(url_for('resources'))
        
    return render_template('resource_detail.html', **topics[topic])

@app.route('/projects')
def projects():
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']

    # Get user's projects (both created and member of)
    projects_data = query_db("""
        SELECT p.*, 
               p.created_by as creator_username,
               COUNT(DISTINCT CASE WHEN pm2.status = 'accepted' THEN pm2.id ELSE NULL END) as member_count,
               GROUP_CONCAT(DISTINCT CASE WHEN pm.status = 'accepted' THEN pm.member_role ELSE NULL END) as member_roles
        FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id
        LEFT JOIN project_members pm2 ON p.id = pm2.project_id
        WHERE (p.created_by = ? OR (pm.username = ? AND pm.status = 'accepted'))
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """, [username, username])

    # Convert SQLite Row objects to dictionaries and process member_roles
    my_projects = []
    for project in projects_data:
        project_dict = dict(project)
        project_dict['member_roles'] = (project_dict['member_roles'].split(',') 
                                      if project_dict['member_roles'] else [])
        my_projects.append(project_dict)

    # Get pending project invitations
    project_invites = query_db("""
        SELECT p.id as project_id, 
               p.title as project_title,
               p.created_by as inviter_username
        FROM project_members pm
        JOIN projects p ON pm.project_id = p.id
        WHERE pm.username = ? AND pm.status = 'pending'
    """, [username])

    return render_template('projects.html', 
                         my_projects=my_projects,
                         project_invites=project_invites)

@app.route('/create_project', methods=['POST'])
def create_project():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    title = request.form['title']
    description = request.form['description']
    github_repo = request.form.get('github_repo', '')
    weekly_commitment = request.form.get('weekly_commitment', 0)
    needed_roles = request.form.getlist('roles[]')
    required_skills = request.form.get('required_skills', '')
    username = session['username']

    db = get_db()
    try:
        # Create project
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO projects (title, description, github_repo, weekly_commitment, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (title, description, github_repo, weekly_commitment, username))
        project_id = cursor.lastrowid

        # Get creator's skills from their profile
        user_profile = query_db("""
            SELECT skills FROM user_profiles 
            WHERE username = ?
        """, [username], one=True)
        
        skills = user_profile['skills'] if user_profile and user_profile['skills'] else None

        # Add creator as project member with admin role
        cursor.execute("""
            INSERT INTO project_members (project_id, username, member_role, status, skills_utilized)
            VALUES (?, ?, 'admin', 'accepted', ?)
        """, (project_id, username, skills))

        # Create default task board
        cursor.execute("""
            INSERT INTO task_boards (project_id, title)
            VALUES (?, 'Main Board')
        """, (project_id,))
        board_id = cursor.lastrowid

        # Create default lists
        for position, list_title in enumerate(['To Do', 'In Progress', 'Done']):
            cursor.execute("""
                INSERT INTO task_lists (board_id, title, position)
                VALUES (?, ?, ?)
            """, (board_id, list_title, position))

        db.commit()
        flash("Project created successfully!", "success")
        return redirect(url_for('project_detail', project_id=project_id))
    except Exception as e:
        db.rollback()
        flash(f"Error creating project: {str(e)}", "error")
        return redirect(url_for('projects'))
    finally:
        db.close()

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']
    
    # Get project details with accepted member count
    project = query_db("""
        SELECT p.*, 
               COUNT(DISTINCT CASE WHEN pm.status = 'accepted' THEN pm.id ELSE NULL END) as member_count
        FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id
        WHERE p.id = ?
        GROUP BY p.id
    """, [project_id], one=True)

    if not project:
        flash("Project not found!", "error")
        return redirect(url_for('projects'))

    # First get members with their basic info and skills
    members_rows = query_db("""
        SELECT pm.*, u.email, pm.skills_utilized
        FROM project_members pm
        JOIN users u ON pm.username = u.username
        WHERE pm.project_id = ? AND pm.status = 'accepted'
    """, [project_id])

    # Convert SQLite Row objects to dictionaries
    members = [dict(member) for member in members_rows]

    # Then for each member, get their skill endorsements for this project
    for member in members:
        if member['skills_utilized']:
            skills = [skill.strip() for skill in member['skills_utilized'].split(',')]
            endorsements = {}
            
            # Initialize all skills with 0 endorsements
            for skill in skills:
                # Get endorsement count for each skill in this project
                endorsement_count = query_db("""
                    SELECT COUNT(*) as count
                    FROM skill_endorsements
                    WHERE endorsed_user = ? 
                    AND skill = ? 
                    AND project_id = ?
                """, [member['username'], skill, project_id], one=True)['count']
                
                endorsements[skill] = endorsement_count
            
            member['skill_endorsements'] = endorsements

    # Check if user is admin
    is_admin = check_project_admin(project_id, username)

    # Get project updates
    updates = query_db("""
        SELECT pu.*, u.email as profile_image
        FROM project_updates pu
        JOIN users u ON pu.username = u.username
        WHERE pu.project_id = ?
        ORDER BY pu.created_at DESC
        LIMIT 10
    """, [project_id])

    # Get pending invites if user is admin
    pending_invites = []
    if is_admin:
        pending_invites = query_db("""
            SELECT pm.username, u.email
            FROM project_members pm
            JOIN users u ON pm.username = u.username
            WHERE pm.project_id = ? AND pm.status = 'pending'
        """, [project_id])

    return render_template('project_detail.html',
                         project=project,
                         members=members,
                         updates=updates,
                         is_admin=is_admin,
                         pending_invites=pending_invites,
                         get_user_badges=get_user_badges)

@app.route('/project/<int:project_id>/board')
def task_board(project_id):
    if 'username' not in session:
        return redirect(url_for('home'))

    username = session['username']

    # Check if user is a project member
    member = query_db("""
        SELECT * FROM project_members 
        WHERE project_id = ? AND username = ? AND status = 'accepted'
    """, [project_id, username], one=True)

    if not member:
        flash("You must be a project member to view the task board!", "error")
        return redirect(url_for('project_detail', project_id=project_id))

    # Get project and board details
    project = query_db("SELECT * FROM projects WHERE id = ?", [project_id], one=True)
    if not project:
        flash("Project not found!", "error")
        return redirect(url_for('projects'))

    board = query_db("""
        SELECT * FROM task_boards 
        WHERE project_id = ? 
        LIMIT 1
    """, [project_id], one=True)

    if not board:
        flash("Task board not found!", "error")
        return redirect(url_for('project_detail', project_id=project_id))

    # Get lists and tasks
    lists = query_db("""
        SELECT l.*, COUNT(t.id) as task_count
        FROM task_lists l
        LEFT JOIN tasks t ON l.id = t.list_id
        WHERE l.board_id = ?
        GROUP BY l.id
        ORDER BY l.position
    """, [board['id']])

    if not lists:
        # Create default lists if none exist
        db = get_db()
        try:
            cursor = db.cursor()
            for position, list_title in enumerate(['To Do', 'In Progress', 'Done']):
                cursor.execute("""
                    INSERT INTO task_lists (board_id, title, position)
                    VALUES (?, ?, ?)
                """, (board['id'], list_title, position))
            db.commit()
            
            # Fetch the newly created lists
            lists = query_db("""
                SELECT l.*, 0 as task_count
                FROM task_lists l
                WHERE l.board_id = ?
                ORDER BY l.position
            """, [board['id']])
        except Exception as e:
            db.rollback()
            flash(f"Error creating task lists: {str(e)}", "error")
        finally:
            db.close()

    tasks = query_db("""
        SELECT t.*, u.username as assigned_name
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.username
        WHERE t.list_id IN (
            SELECT id FROM task_lists WHERE board_id = ?
        )
        ORDER BY t.position
    """, [board['id']])

    # Get project members for task assignment
    members = query_db("""
        SELECT pm.username, 
               COALESCE(up.name, pm.username) as full_name,
               pm.member_role
        FROM project_members pm
        LEFT JOIN user_profiles up ON pm.username = up.username
        WHERE pm.project_id = ? AND pm.status = 'accepted'
    """, [project_id])

    # Check if current user is admin
    is_admin = member['member_role'] == 'admin'

    return render_template('task_board.html',
                         project=project,
                         lists=lists,
                         tasks=tasks,
                         members=members,
                         is_admin=is_admin)

def check_project_admin(project_id, username):
    """Check if a user is an admin of a project."""
    admin = query_db("""
        SELECT 1 FROM project_members 
        WHERE project_id = ? AND username = ? 
        AND member_role = 'admin' AND status = 'accepted'
    """, [project_id, username], one=True)
    return bool(admin)

@app.route('/create_task', methods=['POST'])
def create_task():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    list_id = request.form.get('list_id', type=int)
    
    # Get project_id from list_id
    board = query_db("""
        SELECT tb.project_id 
        FROM task_lists tl
        JOIN task_boards tb ON tl.board_id = tb.id
        WHERE tl.id = ?
    """, [list_id], one=True)
    
    if not board:
        return jsonify({'error': 'Invalid list ID'}), 400
        
    # Check if user is admin
    if not check_project_admin(board['project_id'], session['username']):
        return jsonify({'error': 'Only project admins can create tasks'}), 403

    title = request.form['title']
    description = request.form['description']
    assigned_to = request.form.get('assigned_to', '')
    due_date = request.form.get('due_date', '')
    priority = request.form.get('priority', '')

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("""
            SELECT COALESCE(MAX(position), 0) as max_pos 
            FROM tasks WHERE list_id = ?
        """, [list_id])
        max_pos = cursor.fetchone()['max_pos']

        cursor.execute("""
            INSERT INTO tasks (list_id, title, description, assigned_to, 
                             due_date, priority, position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (list_id, title, description, assigned_to, due_date, 
              priority, max_pos + 1))
        
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/update_task_position', methods=['POST'])
def update_task_position():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    task_id = data.get('task_id')
    new_list_id = data.get('list_id')
    position = data.get('position')

    # Check if user is a project member
    board = query_db("""
        SELECT tb.project_id 
        FROM task_lists tl
        JOIN task_boards tb ON tl.board_id = tb.id
        WHERE tl.id = ?
    """, [new_list_id], one=True)
    
    if not board:
        return jsonify({'error': 'Invalid list ID'}), 400
        
    # Check if user is a project member
    member = query_db("""
        SELECT 1 FROM project_members 
        WHERE project_id = ? AND username = ? AND status = 'accepted'
    """, [board['project_id'], session['username']], one=True)
    
    if not member:
        return jsonify({'error': 'Only project members can move tasks'}), 403

    try:
        db = get_db()
        db.execute("""
            UPDATE tasks 
            SET list_id = ?, position = ?
            WHERE id = ?
        """, (new_list_id, position, task_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/update_task/<int:task_id>', methods=['POST'])
def update_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Get project_id from task_id
    board = query_db("""
        SELECT tb.project_id 
        FROM tasks t
        JOIN task_lists tl ON t.list_id = tl.id
        JOIN task_boards tb ON tl.board_id = tb.id
        WHERE t.id = ?
    """, [task_id], one=True)
    
    if not board:
        return jsonify({'error': 'Invalid task ID'}), 400
        
    # Check if user is admin
    if not check_project_admin(board['project_id'], session['username']):
        return jsonify({'error': 'Only project admins can edit tasks'}), 403

    title = request.form['title']
    description = request.form['description']
    assigned_to = request.form.get('assigned_to', '')
    due_date = request.form.get('due_date', '')
    priority = request.form.get('priority', '')

    db = get_db()
    try:
        cursor = db.cursor()
        cursor.execute("""
            UPDATE tasks 
            SET title = ?, description = ?, assigned_to = ?, 
                due_date = ?, priority = ?
            WHERE id = ?
        """, (title, description, assigned_to, due_date, priority, task_id))
        
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Get project_id from task_id
    board = query_db("""
        SELECT tb.project_id 
        FROM tasks t
        JOIN task_lists tl ON t.list_id = tl.id
        JOIN task_boards tb ON tl.board_id = tb.id
        WHERE t.id = ?
    """, [task_id], one=True)
    
    if not board:
        return jsonify({'error': 'Invalid task ID'}), 400
        
    # Check if user is admin
    if not check_project_admin(board['project_id'], session['username']):
        return jsonify({'error': 'Only project admins can delete tasks'}), 403

    try:
        db = get_db()
        db.execute("DELETE FROM tasks WHERE id = ?", [task_id])
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Gravatar filter for Jinja2
@app.template_filter('gravatar')
def gravatar_url(email, size=80):
    """Generate Gravatar URL for the given email."""
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s={size}"

# Timeago filter for Jinja2
@app.template_filter('timeago')
def timeago(date):
    """Format a date in a human-readable time-ago format."""
    if not date:
        return ''
    
    # Convert string date to datetime if needed
    if isinstance(date, str):
        try:
            # Try parsing with time
            date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Try parsing just the date
                date = datetime.strptime(date, '%Y-%m-%d')
            except ValueError:
                return ''
    
    # Ensure we're comparing in UTC
    now = datetime.utcnow()
    
    # Calculate time difference
    diff = now - date

    seconds = diff.total_seconds()
    if seconds < 0:
        return 'just now'  # Handle case where date is in future due to timezone
    if seconds < 60:
        return 'just now'
    
    minutes = int(seconds / 60)
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    hours = int(minutes / 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    days = int(hours / 24)
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    
    months = int(days / 30)
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    
    years = int(months / 12)
    return f"{years} year{'s' if years != 1 else ''} ago"

@app.route('/get_task/<int:task_id>')
def get_task(task_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    try:
        task = query_db("""
            SELECT t.*, u.username as assigned_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.username
            WHERE t.id = ?
        """, [task_id], one=True)

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify({
            'id': task['id'],
            'title': task['title'],
            'description': task['description'],
            'assigned_to': task['assigned_to'],
            'due_date': task['due_date'],
            'priority': task['priority'],
            'list_id': task['list_id']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/invite_members', methods=['POST'])
def invite_members():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    project_id = request.form.get('project_id', type=int)
    usernames = request.form['usernames'].split(',')
    role = request.form['role']

    # Check if user is admin
    if not check_project_admin(project_id, session['username']):
        flash("Only project admins can invite members!", "error")
        return redirect(url_for('project_detail', project_id=project_id))

    try:
        db = get_db()
        for username in usernames:
            username = username.strip()
            if not username:
                continue

            # Check if user exists
            user = query_db("SELECT username FROM users WHERE username = ?", 
                          [username], one=True)
            if not user:
                flash(f"User {username} not found", "error")
                continue

            # Check if already a member or has pending invitation
            existing = query_db("""
                SELECT id, status FROM project_members 
                WHERE project_id = ? AND username = ?
            """, [project_id, username], one=True)
            
            if existing:
                if existing['status'] == 'accepted':
                    flash(f"{username} is already a member of this project", "info")
                else:
                    flash(f"{username} already has a pending invitation", "info")
                continue

            # Add new invitation
            db.execute("""
                INSERT INTO project_members 
                (project_id, username, member_role, status)
                VALUES (?, ?, ?, 'pending')
            """, (project_id, username, role))
        
        db.commit()
        flash("Invitations sent successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"Error sending invitations: {str(e)}", "error")
    finally:
        db.close()
    
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/get_project/<int:project_id>')
def get_project(project_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    project = query_db("""
        SELECT p.*, COUNT(pm.id) as member_count
        FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id AND pm.status = 'accepted'
        WHERE p.id = ?
        GROUP BY p.id
    """, [project_id], one=True)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    return jsonify(dict(project))

@app.route('/get_project_members/<int:project_id>')
def get_project_members(project_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Check if user is a project member
    is_member = query_db("""
        SELECT 1 FROM project_members 
        WHERE project_id = ? AND username = ? AND status = 'accepted'
    """, [project_id, session['username']], one=True)

    if not is_member:
        return jsonify({'error': 'Not authorized'}), 403

    members = query_db("""
        SELECT pm.username, pm.member_role, u.email as avatar_url,
               CASE 
                   WHEN p.created_by = ? THEN 1
                   ELSE 0
               END as can_remove
        FROM project_members pm
        JOIN users u ON pm.username = u.username
        JOIN projects p ON pm.project_id = p.id
        WHERE pm.project_id = ? AND pm.status = 'accepted'
    """, [session['username'], project_id])

    return jsonify([dict(member) for member in members])

@app.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Check if user is project admin
    if not check_project_admin(project_id, session['username']):
        return jsonify({'error': 'Only project admins can update project details'}), 403

    title = request.form['title']
    description = request.form['description']
    github_repo = request.form.get('github_repo', '')
    weekly_commitment = request.form.get('weekly_commitment', type=int)

    try:
        db = get_db()
        db.execute("""
            UPDATE projects 
            SET title = ?, description = ?, github_repo = ?, weekly_commitment = ?
            WHERE id = ?
        """, (title, description, github_repo, weekly_commitment, project_id))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/remove_project_member', methods=['POST'])
def remove_project_member():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    project_id = data.get('project_id')
    username = data.get('username')

    # Check if user is project admin
    if not check_project_admin(project_id, session['username']):
        return jsonify({'error': 'Only project admins can remove members'}), 403

    try:
        db = get_db()
        # First check if the user is the project creator
        project = query_db("SELECT created_by FROM projects WHERE id = ?", 
                         [project_id], one=True)
        
        if project and project['created_by'] == username:
            return jsonify({'error': 'Cannot remove the project creator'}), 400

        # Delete the member
        db.execute("""
            DELETE FROM project_members 
            WHERE project_id = ? AND username = ?
        """, (project_id, username))
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    # Check if user is project creator
    project = query_db("""
        SELECT created_by FROM projects WHERE id = ?
    """, [project_id], one=True)

    if not project or project['created_by'] != session['username']:
        return jsonify({'error': 'Only project creator can delete the project'}), 403

    try:
        db = get_db()
        # Delete project members
        db.execute("DELETE FROM project_members WHERE project_id = ?", [project_id])
        # Delete project tasks
        db.execute("""
            DELETE FROM tasks 
            WHERE list_id IN (
                SELECT tl.id 
                FROM task_lists tl
                JOIN task_boards tb ON tl.board_id = tb.id
                WHERE tb.project_id = ?
            )
        """, [project_id])
        # Delete task lists
        db.execute("""
            DELETE FROM task_lists 
            WHERE board_id IN (
                SELECT id FROM task_boards WHERE project_id = ?
            )
        """, [project_id])
        # Delete task board
        db.execute("DELETE FROM task_boards WHERE project_id = ?", [project_id])
        # Delete project updates
        db.execute("DELETE FROM project_updates WHERE project_id = ?", [project_id])
        # Finally delete the project
        db.execute("DELETE FROM projects WHERE id = ?", [project_id])
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/respond_to_project_invite', methods=['POST'])
def respond_to_project_invite():
    if 'username' not in session:
        return redirect(url_for('home'))

    project_id = request.form.get('project_id', type=int)
    response = request.form.get('response')
    username = session['username']

    try:
        db = get_db()
        # Verify the invitation exists and is pending
        invite = query_db("""
            SELECT * FROM project_members 
            WHERE project_id = ? AND username = ? AND status = 'pending'
        """, [project_id, username], one=True)

        if not invite:
            flash("Invitation not found or already processed", "error")
            return redirect(url_for('projects'))

        if response == 'accept':
            # Get user's skills from their profile
            user_profile = query_db("""
                SELECT skills FROM user_profiles 
                WHERE username = ?
            """, [username], one=True)
            
            skills = user_profile['skills'] if user_profile and user_profile['skills'] else None

            # Update project member with accepted status and skills
            db.execute("""
                UPDATE project_members 
                SET status = 'accepted',
                    skills_utilized = ?
                WHERE project_id = ? AND username = ?
            """, (skills, project_id, username))
            flash("You have joined the project!", "success")
        else:
            db.execute("""
                DELETE FROM project_members 
                WHERE project_id = ? AND username = ?
            """, (project_id, username))
            flash("Invitation declined", "info")

        db.commit()
    except Exception as e:
        db.rollback()
        flash(f"Error processing invitation: {str(e)}", "error")
    
    return redirect(url_for('projects'))

# Badge types and their requirements
BADGE_TYPES = {
    'project_creator': {'name': 'Project Pioneer', 'requirement': 1},
    'team_builder': {'name': 'Team Builder', 'requirement': 5},
    'skill_master': {'name': 'Skill Master', 'requirement': 10},
    'hackathon_hero': {'name': 'Hackathon Hero', 'requirement': 3},
    'network_navigator': {'name': 'Network Navigator', 'requirement': 10},
    'task_titan': {'name': 'Task Titan', 'requirement': 20}
}

def check_and_award_badges(username):
    """Check and award badges based on user's achievements."""
    db = get_db()
    
    # Check Project Creator badge
    project_count = query_db("SELECT COUNT(*) as count FROM projects WHERE created_by = ?", 
                           [username], one=True)['count']
    if project_count >= BADGE_TYPES['project_creator']['requirement']:
        award_badge(username, 'project_creator')
    
    # Check Team Builder badge
    team_sizes = query_db("""
        SELECT p.id, COUNT(pm.id) as member_count 
        FROM projects p 
        LEFT JOIN project_members pm ON p.id = pm.project_id 
        WHERE p.created_by = ? AND pm.status = 'accepted'
        GROUP BY p.id
    """, [username])
    if any(project['member_count'] >= BADGE_TYPES['team_builder']['requirement'] for project in team_sizes):
        award_badge(username, 'team_builder')
    
    # Check Skill Master badge
    endorsements = query_db("""
        SELECT COUNT(*) as count 
        FROM skill_endorsements 
        WHERE endorsed_user = ?
    """, [username], one=True)['count']
    if endorsements >= BADGE_TYPES['skill_master']['requirement']:
        award_badge(username, 'skill_master')
    
    # Check Hackathon Hero badge
    hackathons = query_db("""
        SELECT COUNT(*) as count 
        FROM participants 
        WHERE username = ?
    """, [username], one=True)['count']
    if hackathons >= BADGE_TYPES['hackathon_hero']['requirement']:
        award_badge(username, 'hackathon_hero')
    
    # Check Network Navigator badge
    connections = query_db("""
        SELECT COUNT(*) as count 
        FROM connections 
        WHERE (user1 = ? OR user2 = ?) AND status = 'accepted'
    """, [username, username], one=True)['count']
    if connections >= BADGE_TYPES['network_navigator']['requirement']:
        award_badge(username, 'network_navigator')
    
    # Check Task Titan badge
    completed_tasks = query_db("""
        SELECT COUNT(*) as count 
        FROM tasks 
        WHERE assigned_to = ? AND status = 'completed'
    """, [username], one=True)['count']
    if completed_tasks >= BADGE_TYPES['task_titan']['requirement']:
        award_badge(username, 'task_titan')

def award_badge(username, badge_type):
    """Award a badge to a user if they don't already have it."""
    db = get_db()
    
    # Check if user already has this badge
    existing_badge = query_db("""
        SELECT id FROM badges 
        WHERE username = ? AND badge_type = ?
    """, [username, badge_type], one=True)
    
    if not existing_badge:
        db.execute("""
            INSERT INTO badges (username, badge_type, badge_name) 
            VALUES (?, ?, ?)
        """, (username, badge_type, BADGE_TYPES[badge_type]['name']))
        db.commit()
        flash(f"Congratulations! You've earned the {BADGE_TYPES[badge_type]['name']} badge!", "success")

def get_user_badges(username):
    """Get all badges earned by a user."""
    return query_db("""
        SELECT badge_type, badge_name, awarded_at 
        FROM badges 
        WHERE username = ? 
        ORDER BY awarded_at DESC
    """, [username])

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'}), 401

    try:
        db = get_db()
        
        # Get form data
        name = request.form.get('name')
        age = request.form.get('age')
        school = request.form.get('school')
        skills = request.form.get('skills')
        hackathon = request.form.get('hackathon')
        preferred_jobs = request.form.get('preferred_jobs')

        # Check if user profile exists
        existing_profile = query_db("""
            SELECT id FROM user_profiles WHERE username = ?
        """, [session['username']], one=True)

        if existing_profile:
            # Update existing profile
            db.execute("""
                UPDATE user_profiles 
                SET name = ?, age = ?, school = ?, skills = ?, 
                    hackathon = ?, preferred_jobs = ?
                WHERE username = ?
            """, (name, age, school, skills, hackathon, 
                  preferred_jobs, session['username']))
        else:
            # Create new profile
            db.execute("""
                INSERT INTO user_profiles 
                (username, name, age, school, skills, hackathon, preferred_jobs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (session['username'], name, age, school, skills, hackathon, 
                  preferred_jobs))
        
        # Update skills in all projects where the user is a member
        db.execute("""
            UPDATE project_members 
            SET skills_utilized = ?
            WHERE username = ? AND status = 'accepted'
        """, (skills, session['username']))
        
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/endorse_skill', methods=['POST'])
def endorse_skill():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Please log in to endorse skills'})

    endorsed_user = request.form.get('username')
    skill = request.form.get('skill')
    project_id = request.form.get('project_id')  # Get project_id from the form
    endorser = session['username']

    if not endorsed_user or not skill or not project_id:
        return jsonify({'success': False, 'error': 'Missing required fields'})

    if endorsed_user == endorser:
        return jsonify({'success': False, 'error': 'You cannot endorse your own skills'})

    db = get_db()
    try:
        # Check if this endorsement already exists for this project
        existing = query_db("""
            SELECT id FROM skill_endorsements 
            WHERE endorsed_user = ? AND endorser = ? AND skill = ? AND project_id = ?
        """, [endorsed_user, endorser, skill, project_id], one=True)

        if existing:
            return jsonify({'success': False, 'error': 'You have already endorsed this skill in this project'})

        # Add the endorsement with project_id
        db.execute("""
            INSERT INTO skill_endorsements (endorsed_user, endorser, skill, project_id)
            VALUES (?, ?, ?, ?)
        """, (endorsed_user, endorser, skill, project_id))
        db.commit()

        # Get the new count of endorsements for this skill in this project
        new_count = query_db("""
            SELECT COUNT(*) as count 
            FROM skill_endorsements 
            WHERE endorsed_user = ? AND skill = ? AND project_id = ?
        """, [endorsed_user, skill, project_id], one=True)['count']

        # Check if user qualifies for Skill Master badge (still based on total endorsements across all projects)
        total_endorsements = query_db("""
            SELECT COUNT(*) as count 
            FROM skill_endorsements 
            WHERE endorsed_user = ?
        """, [endorsed_user], one=True)['count']

        if total_endorsements >= BADGE_TYPES['skill_master']['requirement']:
            award_badge(endorsed_user, 'skill_master')

        return jsonify({'success': True, 'new_count': new_count})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})

def calculate_team_matching_score(user1, user2, hackathon_id):
    """Calculate a matching score between two users for a hackathon."""
    db = get_db()
    
    # Get user profiles
    profile1 = query_db("SELECT skills, preferred_jobs FROM user_profiles WHERE username = ?", [user1], one=True)
    profile2 = query_db("SELECT skills, preferred_jobs FROM user_profiles WHERE username = ?", [user2], one=True)
    
    if not profile1 or not profile2:
        return 0.0
    
    score = 0.0
    
    # Compare skills
    skills1 = set(s.strip().lower() for s in profile1['skills'].split(',')) if profile1['skills'] else set()
    skills2 = set(s.strip().lower() for s in profile2['skills'].split(',')) if profile2['skills'] else set()
    
    # Calculate Jaccard similarity for skills
    if skills1 and skills2:
        skill_similarity = len(skills1.intersection(skills2)) / len(skills1.union(skills2))
        score += skill_similarity * 0.6  # Skills are weighted at 60%
    
    # Compare preferred job types
    jobs1 = set(j.strip().lower() for j in profile1['preferred_jobs'].split(',')) if profile1['preferred_jobs'] else set()
    jobs2 = set(j.strip().lower() for j in profile2['preferred_jobs'].split(',')) if profile2['preferred_jobs'] else set()
    
    # Calculate complementary score for job preferences
    if jobs1 and jobs2:
        # Different job preferences are good (complementary skills)
        job_complementarity = 1 - (len(jobs1.intersection(jobs2)) / max(len(jobs1), len(jobs2)))
        score += job_complementarity * 0.4  # Job complementarity is weighted at 40%
    
    return min(1.0, score)

@app.route('/calculate_team_matches/<int:hackathon_id>', methods=['POST'])
def calculate_team_matches(hackathon_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Please log in to calculate team matches'})
    
    db = get_db()
    try:
        # First, clear existing matches for this hackathon
        db.execute("""
            DELETE FROM team_matching_scores 
            WHERE hackathon_id = ?
        """, [hackathon_id])
        
        # Get all participants for this hackathon
        participants = query_db("""
            SELECT username FROM participants 
            WHERE hackathon_id = ?
        """, [hackathon_id])
        
        if not participants:
            return jsonify({'success': False, 'error': 'No participants found'})
        
        # Calculate scores for all pairs
        for i, p1 in enumerate(participants):
            for p2 in participants[i+1:]:
                score = calculate_team_matching_score(p1['username'], p2['username'], hackathon_id)
                
                # Store the score
                db.execute("""
                    INSERT INTO team_matching_scores (hackathon_id, user1, user2, match_score)
                    VALUES (?, ?, ?, ?)
                """, (hackathon_id, p1['username'], p2['username'], score))
        
        db.commit()
        return jsonify({'success': True, 'message': 'Team matching scores calculated successfully'})
        
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/get_team_matches/<int:hackathon_id>/<username>')
def get_team_matches(hackathon_id, username):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Please log in to view team matches'})
    
    try:
        matches = query_db("""
            SELECT 
                CASE 
                    WHEN user1 = ? THEN user2 
                    ELSE user1 
                END as matched_user,
                match_score,
                calculated_at
            FROM team_matching_scores 
            WHERE hackathon_id = ? AND (user1 = ? OR user2 = ?)
            ORDER BY match_score DESC
        """, [username, hackathon_id, username, username])
        
        # Get user details and connection status for each match
        detailed_matches = []
        for match in matches:
            # Get user details
            user_details = query_db("""
                SELECT u.username, u.email, up.skills, up.preferred_jobs 
                FROM users u 
                LEFT JOIN user_profiles up ON u.username = up.username 
                WHERE u.username = ?
            """, [match['matched_user']], one=True)
            
            # Check connection status
            connection = query_db("""
                SELECT status 
                FROM connections 
                WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)
                AND status = 'accepted'
            """, [username, match['matched_user'], match['matched_user'], username], one=True)
            
            detailed_matches.append({
                'username': user_details['username'],
                'email': user_details['email'],
                'skills': user_details['skills'],
                'preferred_jobs': user_details['preferred_jobs'],
                'match_score': round(match['match_score'] * 100, 1),  # Convert to percentage
                'calculated_at': match['calculated_at'],
                'is_connected': bool(connection)  # True if they are already connected
            })
        
        return jsonify({'success': True, 'matches': detailed_matches})
        
    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/leave_hackathon/<int:hackathon_id>', methods=['POST'])
def leave_hackathon(hackathon_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Please log in to leave hackathons'})

    username = session['username']
    db = get_db()

    try:
        # Check if user is in the hackathon
        participant = query_db("""
            SELECT id FROM participants 
            WHERE hackathon_id = ? AND username = ?
        """, [hackathon_id, username], one=True)

        if not participant:
            return jsonify({'success': False, 'error': 'You are not a participant in this hackathon'})

        # Remove the participant
        db.execute("""
            DELETE FROM participants 
            WHERE hackathon_id = ? AND username = ?
        """, (hackathon_id, username))

        # Remove any team matching scores
        db.execute("""
            DELETE FROM team_matching_scores 
            WHERE hackathon_id = ? AND (user1 = ? OR user2 = ?)
        """, (hackathon_id, username, username))

        db.commit()
        return jsonify({'success': True})

    except sqlite3.Error as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
