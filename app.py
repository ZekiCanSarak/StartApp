from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from passlib.hash import sha256_crypt
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['DATABASE'] = 'database.sqlite'
app.secret_key = '123456789'

# Configure upload folder
UPLOAD_FOLDER = 'static/hackathon_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
     db = sqlite3.connect('database.sqlite')
     db.row_factory = sqlite3.Row
     return db

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
        if 'signup' in request.form:
            username = request.form['username']
            email = request.form['email']
            password = sha256_crypt.hash(request.form['password'])
            role = request.form.get('role', 'user')  

            try:
                insert_db("INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)", 
                          (username, email, password, role))
                flash("Signup successful! You can now login", "success")
            except sqlite3.IntegrityError:
                flash("Username or email already exists", "error")

        elif 'login' in request.form:
            username = request.form['login_username']
            password = request.form['login_password']

            user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
            if user and sha256_crypt.verify(password, user['password']):
                session['logged_in'] = True
                session['username'] = user['username']
                session['role'] = user['role'] 
                flash("Login successful!", "success")
                return redirect(url_for('home'))
            else:
                flash("Invalid username or password!", "error")
        else:
            flash("User does not exist. Please signup.", "error")

    if 'username' in session:
        username = session['username']
        user_profile = query_db("SELECT preferred_jobs FROM user_profiles WHERE username = ?", [username], one=True)
        preferred_jobs = user_profile[0].split(',') if user_profile and user_profile[0] else []

        job_conditions = " OR ".join(["title LIKE ? OR description LIKE ?" for _ in preferred_jobs])
        job_params = [f"%{job.strip()}%" for job in preferred_jobs for _ in range(2)]

        personalised_jobs = query_db(f"""
            SELECT * FROM job_posts
            WHERE {job_conditions}
            ORDER BY id DESC
        """, job_params) if job_params else []

        general_jobs = query_db(f"""
            SELECT * FROM job_posts
            WHERE NOT ({job_conditions})
            ORDER BY id DESC
        """, job_params) if job_params else query_db("SELECT * FROM job_posts ORDER BY id DESC")

        return render_template('index.html', logged_in=True, personalised_jobs=personalised_jobs, general_jobs=general_jobs)

    all_jobs = query_db("SELECT * FROM job_posts ORDER BY id DESC")
    guest_hackathons = query_db("SELECT * FROM hackathons ORDER BY id DESC LIMIT 3")  # Adjust LIMIT as needed
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
    user_skills = user_profile[0].split(',') if user_profile and user_profile[0] else []

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
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    location = request.form['location']
    max_participants = request.form.get('max_participants', type=int)
    hackathon_id = request.form.get('hackathon_id')
    username = session.get('username')
    current_image_path = request.form.get('current_image_path')
    
    # Handle image upload
    image_path = None
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add timestamp to filename to make it unique
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            # Save file and store relative path
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f'hackathon_images/{filename}'  # Store relative path
    elif current_image_path:  # Keep existing image if no new one is uploaded
        image_path = current_image_path.replace('static/', '') if current_image_path.startswith('static/') else current_image_path

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
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(hackathon['image_path']))
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
        user_skills = user_profile[0].split(',') if user_profile and user_profile[0] else []

        if any(skill.strip().lower() in (title + description).lower() for skill in user_skills):
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
     

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash("Please log in to access your profile", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        
        name = request.form.get('name')
        age = request.form.get('age')
        school = request.form.get('school')
        skills = request.form.get('skills')
        hackathon = request.form.get('hackathon')
        preferred_jobs = request.form.get('preferred_jobs')
        try:
            existing_profile = query_db("SELECT * FROM user_profiles WHERE username = ?", [session['username']], one=True)
            if existing_profile:
                insert_db("UPDATE user_profiles SET name = ?, age = ?, school = ?, skills = ?, hackathon = ?, preferred_jobs = ? WHERE username = ?",
                          (name, age, school, skills, hackathon, preferred_jobs, session['username']))
            else:
                insert_db("INSERT INTO user_profiles (username, name, age, school, skills, hackathon, preferred_jobs) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (session['username'], name, age, school, skills, hackathon, preferred_jobs))
            flash("Profile updated successfully!", "success")
        except Exception as e:
            flash("Error updating profile: " + str(e), "error")
        return redirect(url_for('profile'))  

    
    user_details = query_db("SELECT name, age, school, skills, hackathon, preferred_jobs FROM user_profiles WHERE username = ?", [session['username']], one=True)
    return render_template('profile.html', user_details=user_details)


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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)