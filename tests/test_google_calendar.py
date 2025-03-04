import unittest
from unittest.mock import patch
import tempfile
import os
import sqlite3
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from app import app, get_db, query_db

class GoogleCalendarTestCase(unittest.TestCase):
    def setUp(self):
        # Creating a temporary file to serve as our test database.
        self.db_fd, self.temp_db = tempfile.mkstemp()
        
        # Capturing the original sqlite3.connect function.
        original_connect = sqlite3.connect
        
        # Patching the sqlite3.connect in the app so that all connections use the temporary file.
        self.sqlite_connect_patcher = patch(
            'app.sqlite3.connect',
            new=lambda *args, **kwargs: original_connect(self.temp_db, *args[1:], **kwargs)
        )
        self.sqlite_connect_patcher.start()
        
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Setting up the hackathons table.
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute("DROP TABLE IF EXISTS hackathons")
            cursor.execute("""
                CREATE TABLE hackathons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    date TEXT,
                    location TEXT
                )
            """)
            db.commit()

    def tearDown(self):
        # Stopping patching and removing the temporary database file.
        self.sqlite_connect_patcher.stop()
        os.close(self.db_fd)
        os.unlink(self.temp_db)

    def test_add_to_google_calendar_valid(self):
        """Test that a valid hackathon returns a redirect URL with proper Google Calendar parameters."""
        # Inserting a hackathon record with known data.
        hackathon_date = "2025-08-01"
        with app.app_context():
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO hackathons (title, description, date, location) VALUES (?, ?, ?, ?)",
                ("Test Hackathon", "A fun hackathon event", hackathon_date, "Test Location")
            )
            db.commit()
            hackathon_id = cursor.lastrowid  

        # Requesting the endpoint.
        response = self.client.get(f'/add_to_google_calendar/{hackathon_id}')
        
        self.assertEqual(response.status_code, 302)

        # Extracting the URL from the Location header.
        redirect_url = response.headers.get('Location')
        self.assertIsNotNone(redirect_url)
        self.assertTrue(redirect_url.startswith("https://www.google.com/calendar/render?action=TEMPLATE&"))

        # Parsing query parameters from the URL.
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)
        
        # Verifying that the event details are present.
        self.assertEqual(query_params.get("text"), ["Test Hackathon"])
        self.assertEqual(query_params.get("details"), ["A fun hackathon event"])
        self.assertEqual(query_params.get("location"), ["Test Location"])
        self.assertEqual(query_params.get("sf"), ["true"])
        self.assertEqual(query_params.get("output"), ["xml"])

        # Calculating the expected start and end times.
        event_start = datetime.strptime(hackathon_date, "%Y-%m-%d")
        event_end = event_start + timedelta(hours=2)
        expected_start = event_start.strftime('%Y%m%dT%H%M%SZ')
        expected_end = event_end.strftime('%Y%m%dT%H%M%SZ')
        self.assertEqual(query_params.get("dates"), [f"{expected_start}/{expected_end}"])


if __name__ == '__main__':
    unittest.main()