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
               try:
                   insert_db("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
                   flash("Signup successful! You can now login", "success")
               except sqlite3.IntegrityError:
                   flash ("Username or email already exists", "error")

          elif 'login' in request.form:
               username = request.form['login_username']
               password = request.form['login_password']

               user = query_db("SELECT * FROM users WHERE username = ?", [username], one=True)
               if user and sha256_crypt.verify(password, user[3]):
                    session['logged_in'] = True
                    session['username'] = user[1]
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
    today = datetime.now().date()

    user_profile = query_db("SELECT skills FROM user_profiles WHERE username = ?", [username], one=True)
    user_skills = user_profile[0].split(',') if user_profile and user_profile[0] else []

    skill_conditions = " OR ".join([
        "(LOWER(title) LIKE LOWER(?) OR LOWER(description) LIKE LOWER(?))"
        for _ in user_skills
    ])
    
    skill_params = [f"%{skill.strip().lower()}%" for skill in user_skills for _ in range(2)]

    
    matching_hackathons = query_db(f"""
        SELECT h.id, h.title, h.description, h.date, h.location,
               CASE WHEN p.username IS NOT NULL THEN 1 ELSE 0 END AS joined
        FROM hackathons h
        LEFT JOIN participants p ON h.id = p.hackathon_id AND p.username = ?
        WHERE h.date >= ? AND ({skill_conditions})
        ORDER BY h.date ASC
    """, [username, today] + skill_params)

    
    other_hackathons = query_db(f"""
        SELECT h.id, h.title, h.description, h.date, h.location,
               CASE WHEN p.username IS NOT NULL THEN 1 ELSE 0 END AS joined
        FROM hackathons h
        LEFT JOIN participants p ON h.id = p.hackathon_id AND p.username = ?
        WHERE h.date >= ? AND NOT ({skill_conditions})
        ORDER BY h.date ASC
    """, [username, today] + skill_params)

    
    expired_hackathons = query_db("""
        SELECT h.id, h.title, h.description, h.date, h.location,
               CASE WHEN p.username IS NOT NULL THEN 1 ELSE 0 END AS joined
        FROM hackathons h
        LEFT JOIN participants p ON h.id = p.hackathon_id AND p.username = ?
        WHERE h.date < ?
        ORDER BY h.date DESC
    """, [username, today])

    return render_template('hack.html', matching_hackathons=matching_hackathons, other_hackathons=other_hackathons, expired_hackathons=expired_hackathons)

@app.route('/post_hackathon', methods=['POST'])
def post_hackathon():
    title = request.form['title']
    description = request.form['description']
    date = request.form['date']
    location = request.form['location']

    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO hackathons (title, description, date, location) VALUES (?, ?, ?, ?)",
                       (title, description, date, location))
        db.commit()

        hackathon_id = cursor.lastrowid  

        username = session.get('username')
        user_skills = query_db("SELECT skills FROM user_profiles WHERE username = ?", [username], one=True)[0]
        skill_keywords = [skill.strip().lower() for skill in user_skills.split(',')]

        matching = any(skill in (title + description).lower() for skill in skill_keywords)

        today = datetime.now().date()
        if datetime.strptime(date, '%Y-%m-%d').date() < today:
            category = "expired"
        else:
            category = "matching" if matching else "other"

        
        return jsonify({
            'success': True,
            'hackathon': {
                'id': hackathon_id,
                'title': title,
                'description': description,
                'date': date,
                'location': location,
                'category': category,
                'joined': False  
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
     

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
    id = data.get('id')  
    username = session['username']

    
    existing_entry = query_db("SELECT * FROM participants WHERE hackathon_id = ? AND username = ?", 
                              (id, username), one=True)

    if existing_entry:
        return jsonify({"success": False, "message": "You have already joined this hackathon."})

    try:
        insert_db("INSERT INTO participants (hackathon_id, username) VALUES (?, ?)", (id, username))
        return jsonify({"success": True})
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

@app.route('/logout')
def logout():
     session.clear()
     flash("Logged out successfully", "success")
     return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)