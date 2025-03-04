import unittest
from unittest.mock import patch
import tempfile
import os
import sqlite3
from app import app, get_db, query_db, insert_db

class ProfileTestCase(unittest.TestCase):
    def setUp(self):
        # Creating a temporary file for the test database.
        self.db_fd, self.temp_db = tempfile.mkstemp()
        
        # Capturing the original sqlite3.connect function.
        original_connect = sqlite3.connect
        
        # Patching the sqlite3.connect used in app.py so that it always uses the temporary file.
        self.sqlite_connect_patcher = patch(
            'app.sqlite3.connect',
            new=lambda *args, **kwargs: original_connect(self.temp_db, *args[1:], **kwargs)
        )
        self.sqlite_connect_patcher.start()

        app.config['TESTING'] = True
        self.client = app.test_client()

        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            
            # Dropping tables if they exist.
            cursor.execute("DROP TABLE IF EXISTS user_profiles")
            cursor.execute("DROP TABLE IF EXISTS job_posts")
            
            # Creating the user_profiles table.
            cursor.execute("""
                CREATE TABLE user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    name TEXT,
                    age INTEGER,
                    school TEXT,
                    skills TEXT, 
                    hackathon TEXT,
                    preferred_jobs TEXT
                )
            """)
            
            # Creating the job_posts table to satisfy queries in home view.
            cursor.execute("""
                CREATE TABLE job_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    posted_date TEXT
                )
            """)
            
            db.commit()

    def tearDown(self):
        # Stop patching and remove the temporary database file.
        self.sqlite_connect_patcher.stop()
        os.close(self.db_fd)
        os.unlink(self.temp_db)


    @patch('app.session', {'username': 'testuser'})
    def test_profile_access_logged_in(self):
        """Test accessing profile while logged in (should return 200)"""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO user_profiles (username, name, age, school, skills, hackathon, preferred_jobs)
                VALUES ('testuser', 'John Doe', 25, 'Oxford', 'Python, Flask', 'Yes', 'Software Engineer')
            """)
            db.commit()

        response = self.client.get('/profile')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'John Doe', response.data)


    @patch('app.session', {'username': 'testuser'})
    def test_profile_update_existing_user(self):
        """Test updating an existing user profile"""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO user_profiles (username, name, age, school, skills, hackathon, preferred_jobs)
                VALUES ('testuser', 'John Doe', 25, 'Oxford', 'Python, Flask', 'Yes', 'Software Engineer')
            """)
            db.commit()

        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'testuser'

            response = client.post('/profile', data={
                'name': 'Updated Name',
                'age': '30',
                'school': 'Harvard',
                'skills': 'Django, SQL',
                'hackathon': 'No',
                'preferred_jobs': 'Data Scientist'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            # Checking that the flash message indicating success was added to the session.
            with client.session_transaction() as session:
                flash_messages = session.get('_flashes', [])
                self.assertIn(('success', 'Profile updated successfully!'), flash_messages)

    @patch('app.session', {'username': 'newuser'})
    def test_profile_create_new_user(self):
        """Test creating a new user profile"""
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['username'] = 'newuser'

            response = client.post('/profile', data={
                'name': 'New User',
                'age': '22',
                'school': 'MIT',
                'skills': 'Java, React',
                'hackathon': 'Yes',
                'preferred_jobs': 'Frontend Developer'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            # Verifying that the profile creation flash message is present.
            with client.session_transaction() as session:
                flash_messages = session.get('_flashes', [])
                self.assertIn(('success', 'Profile updated successfully!'), flash_messages)

if __name__ == '__main__':
    unittest.main()