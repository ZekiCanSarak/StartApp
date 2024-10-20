from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from passlib.hash import sha256_crypt
import sqlite3
import datetime


app = Flask(__name__)
app.config['DATABASE'] = 'database.sqlite'
app.secret_key = '123456789'

def get_db():
     db = sqlite3.connect('database.sqlite')
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
          

            
               
     return render_template('index.html', logged_in=session.get('logged_in', False))

@app.route('/logout')
def logout():
     session.clear()
     flash("Logged out successfully", "success")
     return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)