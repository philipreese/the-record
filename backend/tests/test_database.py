import sys
import os
import unittest
from datetime import datetime, timezone, timedelta

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.repository as database
import app.db as db

class TestDatabaseQueries(unittest.TestCase):
    def setUp(self):
        # Override the database path to use a temporary file for tests
        self.test_db_path = "test_history.db"
        db.DB_PATH = self.test_db_path
        db.init_db()
        
        self.conn = db.get_db_connection()
        self.cursor = self.conn.cursor()
        self.cursor.execute("DELETE FROM listens")
        
        # Populate in-memory database with test data
        # Let's seed plays relative to current date to test ranges
        self.now = datetime.now()
        
        # Setup timestamps
        self.ts_now = int(self.now.timestamp())
        self.ts_yesterday = int((self.now - timedelta(days=1)).timestamp())
        self.ts_2_days_ago = int((self.now - timedelta(days=2)).timestamp())
        self.ts_10_days_ago = int((self.now - timedelta(days=10)).timestamp())
        self.ts_100_days_ago = int((self.now - timedelta(days=100)).timestamp())
        
        # We will insert a mix of scrobbles with duration and album fields
        test_plays = [
            ("Artist A", "Track 1", self.ts_now, "youtube_music", 180, "Album A"),
            ("Artist A", "Track 1", self.ts_now - 10, "youtube_music", None, "Album A"),  # same day
            ("Artist A", "Track 2", self.ts_yesterday, "last_fm", 240, "Album B"),
            ("Artist A", "Track 1", self.ts_100_days_ago, "last_fm", None, None),
            ("Artist B", "Track 3", self.ts_yesterday - 60, "youtube_music", 200, None),
            ("Artist B", "Track 4", self.ts_10_days_ago, "last_fm", None, "Album C"),
            ("Artist C", "Track 5", self.ts_2_days_ago, "youtube_music", 300, "Album D"),
        ]
        
        self.cursor.executemany(
            "INSERT INTO listens (artist, title, unix_ts, source, duration_secs, album) VALUES (?, ?, ?, ?, ?, ?)",
            test_plays
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        # Clean up database file
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_stats_summary(self):
        stats = database.get_stats_summary()
        self.assertEqual(stats["total_listens"], 7)
        self.assertEqual(stats["unique_artists"], 3)  # A, B, C
        self.assertEqual(stats["unique_tracks"], 5)   # A-1, A-2, B-3, B-4, C-5
        self.assertEqual(stats["top_source"], "youtube_music")
        # 5 distinct days of scrobbles: now (includes 2 plays), yesterday (includes 2 plays), 2 days ago, 10 days ago, 100 days ago
        self.assertEqual(stats["days_active"], 5)
        self.assertEqual(stats["avg_per_day"], 1.4)  # 7 / 5 = 1.4

    def test_top_artists(self):
        # All time
        top = database.get_top_artists(time_range="all", limit=5)
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0]["artist"], "Artist A")
        self.assertEqual(top[0]["play_count"], 4)
        self.assertEqual(top[1]["artist"], "Artist B")
        self.assertEqual(top[1]["play_count"], 2)
        
        # Last 30 days (should exclude the play 100 days ago)
        # Plays remaining: now (2), yesterday (2), 2 days ago (1), 10 days ago (1). Total = 6 plays.
        # Artist A has 3 plays within 30 days. Artist B has 2. Artist C has 1.
        top_30d = database.get_top_artists(time_range="30", limit=5)
        self.assertEqual(len(top_30d), 3)
        self.assertEqual(top_30d[0]["artist"], "Artist A")
        self.assertEqual(top_30d[0]["play_count"], 3)

    def test_top_tracks(self):
        top = database.get_top_tracks(time_range="all", limit=5)
        self.assertEqual(len(top), 5)
        # Track 1 has 3 plays
        self.assertEqual(top[0]["title"], "Track 1")
        self.assertEqual(top[0]["play_count"], 3)

    def test_heatmap_data(self):
        current_year = self.now.year
        heatmap = database.get_heatmap_data(year=current_year)
        
        # Test that heatmap contains active days
        today_str = self.now.strftime("%Y-%m-%d")
        yesterday_str = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        self.assertIn(today_str, heatmap)
        self.assertEqual(heatmap[today_str], 2)
        self.assertIn(yesterday_str, heatmap)
        self.assertEqual(heatmap[yesterday_str], 2)

    def test_hourly_trends(self):
        trends = database.get_hourly_trends()
        self.assertEqual(len(trends), 24)
        # The sum of all counts should be equal to the total scrobbles
        self.assertEqual(sum(trends.values()), 7)

    def test_monthly_trends(self):
        trends = database.get_monthly_trends()
        self.assertTrue(len(trends) >= 1)
        self.assertEqual(sum(t["count"] for t in trends), 7)

    def test_streak_stats(self):
        # We have listening on: now, now-1, now-2. That forms a 3-day consecutive streak.
        # now-10 is a gap. now-100 is a gap.
        streaks = database.get_streak_stats()
        self.assertEqual(streaks["current_streak"], 3)
        self.assertTrue(streaks["longest_streak"] >= 3)

    def test_wrapped_data(self):
        current_year = self.now.year
        wrapped = database.get_wrapped_data(year=current_year)
        
        self.assertEqual(wrapped["total_plays"], 7)
        self.assertEqual(wrapped["top_artist"]["name"], "Artist A")
        self.assertEqual(wrapped["top_artist"]["plays"], 4)
        self.assertEqual(wrapped["top_track"]["title"], "Track 1")
        self.assertEqual(wrapped["top_track"]["plays"], 3)
        # Expected duration seconds:
        # - Artist A, Track 1 (now) -> 180s
        # - Artist A, Track 1 (now - 10) -> None -> 210s
        # - Artist A, Track 2 (yesterday) -> 240s
        # - Artist A, Track 1 (100_days_ago) -> None -> 210s
        # - Artist B, Track 3 (yesterday - 60) -> 200s
        # - Artist B, Track 4 (10_days_ago) -> None -> 210s
        # - Artist C, Track 5 (2_days_ago) -> 300s
        # Total = 180 + 210 + 240 + 210 + 200 + 210 + 300 = 1550 seconds
        # Minutes = round(1550 / 60) = 26
        self.assertEqual(wrapped["minutes_listened"], 26)

    def test_track_stats(self):
        # Without album parameter
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1")
        self.assertEqual(play_count, 3)
        self.assertEqual(duration, 180)  # first non-null duration

        # With album parameter matching Album A
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1", album="Album A")
        self.assertEqual(play_count, 2)
        self.assertEqual(duration, 180)

        # With album parameter matching Album B
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1", album="Album B")
        self.assertEqual(play_count, 0)
        self.assertIsNone(duration)

if __name__ == "__main__":
    unittest.main()
