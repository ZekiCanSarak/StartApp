from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from passlib.hash import sha256_crypt
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlencode



app = Flask(__name__)
app.config['DATABASE'] = 'database.sqlite'
app.secret_key = '123456789'

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
    return render_template('index.html', logged_in=False, general_jobs=all_jobs)


@app.route('/hack', methods=['GET'])
def hack():
    if 'username' not in session:
        flash("Please log in to view hackathons.", "error")
        return redirect(url_for('home'))

    username = session['username']
    today = datetime.now().strftime('%Y-%m-%d')

    active_hackathons = query_db("""SELECT id, title FROM hackathons WHERE date >= ? ORDER BY date ASC """, [today])

    user_profile = query_db("SELECT skills FROM user_profiles WHERE username = ?", [username], one=True)
    user_skills = user_profile[0].split(',') if user_profile and user_profile[0] else []

    hackathon_base_query = """
    SELECT h.id, h.title, h.description, h.date, h.location, h.max_participants,
           h.created_by,  -- Include the creator field
           COUNT(p.id) AS current_participants,
           CASE WHEN p2.username IS NOT NULL THEN 1 ELSE 0 END AS joined
    FROM hackathons h
    LEFT JOIN participants p ON h.id = p.hackathon_id
    LEFT JOIN participants p2 ON h.id = p2.hackathon_id AND p2.username = ?
    WHERE h.date >= ?
"""
    
    # Adding skill matching for personalised hackathons
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
               COUNT(p.id) AS current_participants,
               CASE WHEN p2.username IS NOT NULL THEN 1 ELSE 0 END AS joined  -- Check join status for expired hackathons
        FROM hackathons h
        LEFT JOIN participants p ON h.id = p.hackathon_id
        LEFT JOIN participants p2 ON h.id = p2.hackathon_id AND p2.username = ?
        WHERE h.date < ?
        GROUP BY h.id
        ORDER BY h.date DESC
    """, [username, today])

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

    try:
        db = get_db()
        cursor = db.cursor()

        if hackathon_id:
            # Check if the user owns this hackathon
            hackathon = query_db(
                "SELECT created_by FROM hackathons WHERE id = ?", [hackathon_id], one=True
            )
            if not hackathon or hackathon['created_by'] != username:
                return jsonify({'success': False, 'message': 'You do not have permission to edit this hackathon.'})

            # Editing existing hackathon
            cursor.execute("""
                UPDATE hackathons
                SET title = ?, description = ?, date = ?, location = ?, max_participants = ?
                WHERE id = ?
            """, (title, description, date, location, max_participants, hackathon_id))
            
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
                INSERT INTO hackathons (title, description, date, location, max_participants, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, description, date, location, max_participants, username))
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
                'current_user': session.get('username')  
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)