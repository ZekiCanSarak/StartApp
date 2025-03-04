import unittest
from unittest.mock import patch
import tempfile
import os
import sqlite3
from app import app, get_db, query_db
from passlib.hash import sha256_crypt  # For hashing passwords in tests

class LoginSignupTestCase(unittest.TestCase):
    def setUp(self):
        # Creating a temporary file for the test database.
        self.db_fd, self.temp_db = tempfile.mkstemp()
        
        # Capturing the original sqlite3.connect function.
        original_connect = sqlite3.connect
        
        # Patching the sqlite3.connect used in your app so that all connections use the temporary file.
        self.sqlite_connect_patcher = patch(
            'app.sqlite3.connect',
            new=lambda *args, **kwargs: original_connect(self.temp_db, *args[1:], **kwargs)
        )
        self.sqlite_connect_patcher.start()
        
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Setting up necessary tables.
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            # Dropping tables if they already exist.
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute("DROP TABLE IF EXISTS job_posts")
            cursor.execute("DROP TABLE IF EXISTS user_profiles")
            
            # Creating the 'users' table (used for login/signup) with UNIQUE constraints on username and email.
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    email TEXT UNIQUE,
                    password TEXT,
                    role TEXT
                )
            """)
            # Creating a minimal 'job_posts' table (used in the home route).
            cursor.execute("""
                CREATE TABLE job_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT
                )
            """)
            # Creating a minimal 'user_profiles' table (used when a user is logged in).
            cursor.execute("""
                CREATE TABLE user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    preferred_jobs TEXT
                )
            """)
            db.commit()
    
    def tearDown(self):
        # Stopping the patcher and remove the temporary database file.
        self.sqlite_connect_patcher.stop()
        os.close(self.db_fd)
        os.unlink(self.temp_db)
    
    def test_signup_missing_data(self):
        """
        Test signup with missing required fields.
        In this example, we omit the 'password'. Depending on your app's error handling,
        this might result in an error. Adjust the expected behavior accordingly.
        """
        response = self.client.post('/', data={
            'signup': '1',
            'username': 'newuser',
            'email': 'new@example.com'
            # 'password' is missing
        })
        # Expecting the signup process to fail.
        self.assertNotEqual(response.status_code, 200)
    
    def test_signup_success(self):
        """Test that a successful signup creates a new user and flashes a success message."""
        response = self.client.post('/', data={
            'signup': '1',
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'secret',
            'role': 'user'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Checking that the flashed message is in the response text.
        self.assertIn("Signup successful! You can now login", response.get_data(as_text=True))
        # Verifying that the user was inserted into the database.
        with app.app_context():
            user = query_db("SELECT * FROM users WHERE username = ?", ['newuser'], one=True)
            self.assertIsNotNone(user)
    
    def test_signup_duplicate_email(self):
        """Test that signing up with a duplicate email returns an error."""
        # First signup should succeed.
        response1 = self.client.post('/', data={
            'signup': '1',
            'username': 'user1',
            'email': 'duplicate@example.com',
            'password': 'secret',
            'role': 'user'
        }, follow_redirects=True)
        self.assertEqual(response1.status_code, 200)
        self.assertIn("Signup successful! You can now login", response1.get_data(as_text=True))
        
        # Second signup with a different username but the same email should trigger an error.
        response2 = self.client.post('/', data={
            'signup': '1',
            'username': 'user2',
            'email': 'duplicate@example.com',
            'password': 'secret',
            'role': 'user'
        }, follow_redirects=True)
        self.assertEqual(response2.status_code, 200)
        # Expecting the error flash message indicating the duplicate email.
        self.assertIn("Username or email already exists", response2.get_data(as_text=True))
    
    def test_login_invalid(self):
        """Test logging in with invalid credentials."""
        # Inserting a user with a known password.
        hashed_password = sha256_crypt.hash("secret")
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                ('testuser', 'test@example.com', hashed_password, 'user')
            )
            db.commit()
        # Attemptting to log in with the wrong password.
        response = self.client.post('/', data={
            'login': '1',
            'login_username': 'testuser',
            'login_password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid username or password!", response.get_data(as_text=True))
    
    def test_login_success(self):
        """Test that a valid login sets session data and shows a welcome message."""
        hashed_password = sha256_crypt.hash("secret")
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                ('testuser', 'test@example.com', hashed_password, 'user')
            )
            db.commit()
        response = self.client.post('/', data={
            'login': '1',
            'login_username': 'testuser',
            'login_password': 'secret'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Instead of checking for the flash message, check for the welcome message that appears in the rendered homepage.
        self.assertIn("Welcome, testuser!", response.get_data(as_text=True))
        # Verifying that the session now contains the username.
        with self.client.session_transaction() as session:
            self.assertEqual(session.get('username'), 'testuser')
    
    def test_logout(self):
        """Test that accessing the logout route clears the session and flashes a logout message."""
        # Manually setting session values.
        with self.client.session_transaction() as session:
            session['username'] = 'testuser'
            session['logged_in'] = True
        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Logged out successfully", response.get_data(as_text=True))
        with self.client.session_transaction() as session:
            self.assertIsNone(session.get('username'))

if __name__ == '__main__':
    unittest.main()