import unittest
from unittest.mock import patch
import tempfile
import os
import sqlite3
from app import app, get_db, query_db

class PostHackathonTestCase(unittest.TestCase):
    def setUp(self):
        # Creating a temporary file to serve as our test database.
        self.db_fd, self.temp_db = tempfile.mkstemp()
        
        # Capturing the original sqlite3.connect so we can call it.
        original_connect = sqlite3.connect
        
        # Patching the sqlite3.connect used in app.py so that it always connects to our temporary file.
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

            # Dropping tables if they exist to ensure a clean slate.
            cursor.execute("DROP TABLE IF EXISTS hackathons")
            cursor.execute("DROP TABLE IF EXISTS participants")
            cursor.execute("DROP TABLE IF EXISTS user_profiles")

            # Creating the hackathons table.
            cursor.execute("""CREATE TABLE hackathons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                date TEXT,
                location TEXT,
                max_participants INTEGER,
                created_by TEXT
            )""")

            # Creating the participants table.
            cursor.execute("""CREATE TABLE participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hackathon_id INTEGER,
                username TEXT
            )""")

            # Creating the user_profiles table.
            cursor.execute("""CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                skills TEXT
            )""")

            db.commit()

    @patch('app.session', {'username': 'testuser', 'role': 'organiser'})
    def test_create_hackathon_with_missing_data(self):
        """Test creating a hackathon with missing fields"""
        response = self.client.post('/post_hackathon', data={
            'title': 'Incomplete Hack',
            'date': '2025-08-10'
        })  # Missing description, location, and max_participants

        print("Response Status Code:", response.status_code)  # Debug print
        print("Response Data:", response.get_data(as_text=True))  # Debug print

        self.assertEqual(response.status_code, 400)
        self.assertIn("Bad Request", response.get_data(as_text=True))

    @patch('app.session', {'username': 'testuser', 'role': 'organiser'})
    def test_edit_hackathon_as_owner(self):
        """Test if the owner can edit their own hackathon"""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""INSERT INTO hackathons (title, description, date, location, max_participants, created_by)
                              VALUES ('Old Title', 'Old Description', '2025-04-15', 'London', 50, 'testuser')""")
            db.commit()

        hackathon_record = query_db("SELECT id FROM hackathons WHERE created_by = ?", ['testuser'], one=True)
        hackathon_id = hackathon_record['id'] if hackathon_record else None

        response = self.client.post('/post_hackathon', data={
            'title': 'Updated Title',
            'description': 'Updated Description',
            'date': '2025-05-10',
            'location': 'Manchester',
            'max_participants': '150',
            'hackathon_id': hackathon_id
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['success'])
        self.assertEqual(response.json['hackathon']['title'], 'Updated Title')

    @patch('app.session', {'username': 'anotheruser', 'role': 'organiser'})
    def test_edit_hackathon_as_non_owner(self):
        """Test if a non-owner cannot edit a hackathon"""
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("""INSERT INTO hackathons (title, description, date, location, max_participants, created_by)
                              VALUES ('Test Hack', 'Description', '2025-06-01', 'Cambridge', 50, 'testuser')""")
            db.commit()

        hackathon_record = query_db("SELECT id FROM hackathons WHERE created_by = ?", ['testuser'], one=True)
        hackathon_id = hackathon_record['id'] if hackathon_record else None

        response = self.client.post('/post_hackathon', data={
            'title': 'Hacked Title',
            'description': 'Hacked Description',
            'date': '2025-07-01',
            'location': 'Edinburgh',
            'max_participants': '200',
            'hackathon_id': hackathon_id
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json['success'])
        self.assertIn('You do not have permission', response.json['message'])

    def tearDown(self):
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DROP TABLE hackathons")
            cursor.execute("DROP TABLE participants")
            cursor.execute("DROP TABLE user_profiles")
            db.commit()
        # Stopping the patcher and remove the temporary file.
        self.sqlite_connect_patcher.stop()
        os.close(self.db_fd)
        os.unlink(self.temp_db)

if __name__ == '__main__':
    unittest.main()