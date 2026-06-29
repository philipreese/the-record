import sys
import os
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Hermetic tests: neutralize DATABASE_URL before importing project code. Several
# modules call load_dotenv() at import (app.main, merge_history) and Alembic's
# env.py does too (via init_db in setUp); a populated local .env would otherwise
# point the tests — and the schema migrations they run — at PRODUCTION. Empty is
# treated as SQLite by get_engine()/db_helpers, and load_dotenv's default
# override=False won't replace an already-set key.
os.environ["DATABASE_URL"] = ""

from sqlalchemy import text

import app.repository as database
import app.db as db

class TestDatabaseQueries(unittest.TestCase):
    def setUp(self):
        self.test_db_path = "test_history.db"
        db.DB_PATH = self.test_db_path
        db.init_db()

        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM listens"))

        self.now = datetime.now()

        self.ts_now = int(self.now.timestamp())
        self.ts_yesterday = int((self.now - timedelta(days=1)).timestamp())
        self.ts_2_days_ago = int((self.now - timedelta(days=2)).timestamp())
        self.ts_10_days_ago = int((self.now - timedelta(days=10)).timestamp())
        self.ts_100_days_ago = int((self.now - timedelta(days=100)).timestamp())

        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source, duration_secs, album)"
                " VALUES (:artist, :title, :unix_ts, :source, :duration_secs, :album)"
            ),
            [
                {"artist": "Artist A", "title": "Track 1", "unix_ts": self.ts_now, "source": "youtube_music", "duration_secs": 180, "album": "Album A"},
                {"artist": "Artist A", "title": "Track 1", "unix_ts": self.ts_now - 10, "source": "youtube_music", "duration_secs": None, "album": "Album A"},
                {"artist": "Artist A", "title": "Track 2", "unix_ts": self.ts_yesterday, "source": "last_fm", "duration_secs": 240, "album": "Album B"},
                {"artist": "Artist A", "title": "Track 1", "unix_ts": self.ts_100_days_ago, "source": "last_fm", "duration_secs": None, "album": None},
                {"artist": "Artist B", "title": "Track 3", "unix_ts": self.ts_yesterday - 60, "source": "youtube_music", "duration_secs": 200, "album": None},
                {"artist": "Artist B", "title": "Track 4", "unix_ts": self.ts_10_days_ago, "source": "last_fm", "duration_secs": None, "album": "Album C"},
                {"artist": "Artist C", "title": "Track 5", "unix_ts": self.ts_2_days_ago, "source": "youtube_music", "duration_secs": 300, "album": "Album D"},
            ],
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_stats_summary(self):
        stats = database.get_stats_summary()
        self.assertEqual(stats.total_listens, 7)
        self.assertEqual(stats.unique_artists, 3)  # A, B, C
        self.assertEqual(stats.unique_tracks, 5)   # A-1, A-2, B-3, B-4, C-5
        self.assertEqual(stats.top_source, "youtube_music")
        # 5 distinct days of scrobbles: now (includes 2 plays), yesterday (includes 2 plays), 2 days ago, 10 days ago, 100 days ago
        self.assertEqual(stats.days_active, 5)
        self.assertEqual(stats.avg_per_day, 1.4)  # 7 / 5 = 1.4

    def test_top_artists(self):
        # All time
        top_data = database.get_top_artists(time_range="all", limit=5)
        top = top_data.items
        self.assertEqual(top_data.total_count, 3)
        self.assertEqual(len(top), 3)
        self.assertEqual(top[0].artist, "Artist A")
        self.assertEqual(top[0].play_count, 4)
        self.assertEqual(top[0].rank, 1)
        self.assertEqual(top[1].artist, "Artist B")
        self.assertEqual(top[1].play_count, 2)
        self.assertEqual(top[1].rank, 2)

        # Last 30 days (should exclude the play 100 days ago)
        # Plays remaining: now (2), yesterday (2), 2 days ago (1), 10 days ago (1). Total = 6 plays.
        # Artist A has 3 plays within 30 days. Artist B has 2. Artist C has 1.
        top_30d_data = database.get_top_artists(time_range="30", limit=5)
        top_30d = top_30d_data.items
        self.assertEqual(top_30d_data.total_count, 3)
        self.assertEqual(len(top_30d), 3)
        self.assertEqual(top_30d[0].artist, "Artist A")
        self.assertEqual(top_30d[0].play_count, 3)
        self.assertEqual(top_30d[0].rank, 1)

        # Test Search
        top_search_data = database.get_top_artists(time_range="all", limit=5, search="Artist B")
        top_search = top_search_data.items
        self.assertEqual(top_search_data.total_count, 1)
        self.assertEqual(len(top_search), 1)
        self.assertEqual(top_search[0].artist, "Artist B")
        self.assertEqual(top_search[0].rank, 2)  # true absolute rank is 2 overall

        # Test Pagination (Page 2, limit 1)
        top_page_2_data = database.get_top_artists(time_range="all", limit=1, page=2)
        top_page_2 = top_page_2_data.items
        self.assertEqual(top_page_2_data.total_count, 3)
        self.assertEqual(len(top_page_2), 1)
        self.assertEqual(top_page_2[0].artist, "Artist B")
        self.assertEqual(top_page_2[0].rank, 2)

    def test_top_tracks(self):
        top_data = database.get_top_tracks(time_range="all", limit=5)
        top = top_data.items
        self.assertEqual(top_data.total_count, 5)
        self.assertEqual(len(top), 5)
        # Track 1 has 3 plays
        self.assertEqual(top[0].title, "Track 1")
        self.assertEqual(top[0].play_count, 3)
        self.assertEqual(top[0].rank, 1)

        # Test Search by artist or title
        top_search_title_data = database.get_top_tracks(time_range="all", limit=5, search="Track 3")
        top_search_title = top_search_title_data.items
        self.assertEqual(top_search_title_data.total_count, 1)
        self.assertEqual(len(top_search_title), 1)
        self.assertEqual(top_search_title[0].title, "Track 3")
        self.assertEqual(top_search_title[0].rank, 2)  # Tied at rank 2

        top_search_artist_data = database.get_top_tracks(time_range="all", limit=5, search="Artist C")
        top_search_artist = top_search_artist_data.items
        self.assertEqual(top_search_artist_data.total_count, 1)
        self.assertEqual(len(top_search_artist), 1)
        self.assertEqual(top_search_artist[0].title, "Track 5")
        self.assertEqual(top_search_artist[0].rank, 2)

        # Test Pagination (Page 2, limit 2)
        top_page_2_data = database.get_top_tracks(time_range="all", limit=2, page=2)
        top_page_2 = top_page_2_data.items
        self.assertEqual(top_page_2_data.total_count, 5)
        self.assertEqual(len(top_page_2), 2)
        # Verify pagination ordering:
        # Rank 1: Artist A Track 1
        # Rank 2: Artist A Track 2, Artist B Track 3, Artist B Track 4, Artist C Track 5 (sorted by artist, title)
        # Page 1 (limit 2): Artist A Track 1, Artist A Track 2
        # Page 2 (limit 2): Artist B Track 3, Artist B Track 4
        self.assertEqual(top_page_2[0].title, "Track 3")
        self.assertEqual(top_page_2[1].title, "Track 4")

    def test_heatmap_data(self):
        current_year = self.now.year
        heatmap = database.get_heatmap_data(year=current_year)

        today_str = self.now.strftime("%Y-%m-%d")
        yesterday_str = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")

        self.assertIn(today_str, heatmap)
        self.assertEqual(heatmap[today_str], 2)
        self.assertIn(yesterday_str, heatmap)
        self.assertEqual(heatmap[yesterday_str], 2)

    def test_hourly_trends(self):
        trends = database.get_hourly_trends()
        self.assertEqual(len(trends), 24)
        self.assertEqual(sum(trends.values()), 7)

    def test_monthly_trends(self):
        trends = database.get_monthly_trends()
        self.assertTrue(len(trends) >= 1)
        self.assertEqual(sum(t.count for t in trends), 7)

    def test_streak_stats(self):
        # We have listening on: now, now-1, now-2. That forms a 3-day consecutive streak.
        # now-10 is a gap. now-100 is a gap.
        streaks = database.get_streak_stats()
        self.assertEqual(streaks.current_streak, 3)
        self.assertTrue(streaks.longest_streak >= 3)

    def test_wrapped_data(self):
        current_year = self.now.year
        wrapped = database.get_wrapped_data(year=current_year)

        self.assertEqual(wrapped.total_plays, 7)
        self.assertIsNotNone(wrapped.top_artist)
        self.assertEqual(wrapped.top_artist.name, "Artist A")
        self.assertEqual(wrapped.top_artist.plays, 4)
        self.assertIsNotNone(wrapped.top_track)
        self.assertEqual(wrapped.top_track.title, "Track 1")
        self.assertEqual(wrapped.top_track.plays, 3)
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
        self.assertEqual(wrapped.minutes_listened, 26)
        # On-repeat peak: Track 1 has 2 plays today (ts_now and ts_now-10)
        self.assertIsNotNone(wrapped.on_repeat_peak)
        self.assertEqual(wrapped.on_repeat_peak.title.lower(), "track 1")
        self.assertEqual(wrapped.on_repeat_peak.count, 2)

    def test_on_repeat_peak_case_insensitive(self):
        # Casing variants of the same track on the same day must be merged.
        # Without func.lower() grouping, "artist a"/"ARTIST A" would be separate
        # buckets and the max would stay at 2 instead of 4.
        # Anchor to local midday so the extra plays are always the same local
        # day as ts_now, regardless of what time the suite runs (a relative
        # offset like ts_now - 3600 crosses midnight when run just after 00:00).
        midday = self.now.replace(hour=12, minute=0, second=0, microsecond=0)
        base_ts = int(midday.timestamp())
        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source, duration_secs, album)"
                " VALUES (:artist, :title, :unix_ts, :source, :duration_secs, :album)"
            ),
            [
                {"artist": "artist a", "title": "track 1", "unix_ts": base_ts - 100, "source": "youtube_music", "duration_secs": None, "album": None},
                {"artist": "ARTIST A", "title": "Track 1", "unix_ts": base_ts - 200, "source": "youtube_music", "duration_secs": None, "album": None},
            ],
        )
        self.conn.commit()

        current_year = self.now.year
        wrapped = database.get_wrapped_data(year=current_year)
        peak = wrapped.on_repeat_peak
        self.assertIsNotNone(peak)
        # 2 from setUp (ts_now, ts_now-10) + 2 casing variants, all on the same day
        self.assertEqual(peak.count, 4)

    def test_track_stats(self):
        # Without album parameter
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1")
        self.assertEqual(play_count, 3)
        self.assertEqual(duration, 180)  # first non-null duration

        # With album parameter: includes null-album rows (unknown album != different song)
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1", album="Album A")
        self.assertEqual(play_count, 3)  # 2 Album A + 1 null-album
        self.assertEqual(duration, 180)

        # Album B has no exact matches, but null-album row is still included
        play_count, duration = database.get_track_stats(artist="Artist A", title="Track 1", album="Album B")
        self.assertEqual(play_count, 1)  # 0 Album B + 1 null-album
        self.assertIsNone(duration)

    def test_track_stats_by_recording_mbid(self):
        # Canonical identity via recording_mbid merges inconsistent artist-credit
        # variants of the same recording (the #95 bug).
        mbid = "11111111-1111-1111-1111-111111111111"
        other_mbid = "22222222-2222-2222-2222-222222222222"
        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source, recording_mbid)"
                " VALUES (:artist, :title, :unix_ts, :source, :recording_mbid)"
            ),
            [
                {"artist": "Beartooth & Hardy", "title": "The Better Me", "unix_ts": self.ts_now + 1, "source": "listenbrainz_sync", "recording_mbid": mbid},
                {"artist": "Beartooth", "title": "The Better Me", "unix_ts": self.ts_now + 2, "source": "listenbrainz_sync", "recording_mbid": mbid},
                {"artist": "Beartooth", "title": "The Better Me", "unix_ts": self.ts_now + 3, "source": "youtube_music", "recording_mbid": None},
                {"artist": "Someone Else", "title": "The Better Me", "unix_ts": self.ts_now + 4, "source": "listenbrainz_sync", "recording_mbid": other_mbid},
            ],
        )
        self.conn.commit()

        # By MBID: 2 MBID rows + 1 null-MBID string match = 3
        count, _ = database.get_track_stats(
            artist="Beartooth", title="The Better Me", recording_mbid=mbid
        )
        self.assertEqual(count, 3)

        # Without MBID: plain (artist, title) match for "Beartooth" only = 2
        # ("Beartooth & Hardy" excluded by exact string match)
        count_str, _ = database.get_track_stats(artist="Beartooth", title="The Better Me")
        self.assertEqual(count_str, 2)

    def test_track_stats_batch(self):
        tracks = [
            {"artist": "Artist A", "title": "Track 1"},
            {"artist": "artist a", "title": "track 2"},  # test lower casing
            {"artist": "NonExistent", "title": "Track"}, # test non-existent
        ]
        res = database.get_track_stats_batch(tracks)
        self.assertEqual(len(res), 3)

        self.assertEqual(res[0].artist, "Artist A")
        self.assertEqual(res[0].title, "Track 1")
        self.assertEqual(res[0].play_count, 3)
        self.assertEqual(res[0].duration_secs, 180)

        self.assertEqual(res[1].artist, "artist a")
        self.assertEqual(res[1].title, "track 2")
        self.assertEqual(res[1].play_count, 1)
        self.assertEqual(res[1].duration_secs, 240)

        self.assertEqual(res[2].artist, "NonExistent")
        self.assertEqual(res[2].title, "Track")
        self.assertEqual(res[2].play_count, 0)
        self.assertIsNone(res[2].duration_secs)

    def test_recent_listens_with_anchor_date(self):
        yesterday_date_str = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        listens = database.get_recent_listens(limit=10, anchor_date=yesterday_date_str)
        self.assertEqual(len(listens), 5)
        for item in listens:
            self.assertNotEqual(item.unix_ts, self.ts_now)
            self.assertNotEqual(item.unix_ts, self.ts_now - 10)


class TestDeduplicateCaseInsensitive(unittest.TestCase):
    """Verify that deduplicate_listens() merges rows differing only in casing."""

    def setUp(self):
        self.test_db_path = "test_dedup_casing.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None
        db.init_db()
        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM listens"))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_merges_rows_differing_only_in_casing_within_60s(self):
        self.conn.execute(
            text("INSERT INTO listens (artist, title, unix_ts, source) VALUES (:artist, :title, :unix_ts, :source)"),
            [
                {"artist": "Boards of Canada", "title": "The Past Is Dead", "unix_ts": 1_000_000, "source": "youtube_music"},
                {"artist": "Boards of Canada", "title": "The Past is Dead", "unix_ts": 1_000_030, "source": "listenbrainz_sync"},
            ],
        )
        self.conn.commit()

        deleted = database.deduplicate_listens()
        self.assertEqual(deleted, 1)

        row = db.get_engine().connect().execute(text("SELECT COUNT(*) FROM listens")).fetchone()
        assert row is not None
        self.assertEqual(row[0], 1)

    def test_does_not_merge_rows_beyond_60s(self):
        self.conn.execute(
            text("INSERT INTO listens (artist, title, unix_ts, source) VALUES (:artist, :title, :unix_ts, :source)"),
            [
                {"artist": "Boards of Canada", "title": "The Past Is Dead", "unix_ts": 1_000_000, "source": "youtube_music"},
                {"artist": "Boards of Canada", "title": "The Past is Dead", "unix_ts": 1_000_061, "source": "listenbrainz_sync"},
            ],
        )
        self.conn.commit()

        deleted = database.deduplicate_listens()
        self.assertEqual(deleted, 0)

        row = db.get_engine().connect().execute(text("SELECT COUNT(*) FROM listens")).fetchone()
        assert row is not None
        self.assertEqual(row[0], 2)


class TestCasingNormalisationMigration(unittest.TestCase):
    """Integration test for migration 005: verify LB casing wins and duplicates are removed."""

    def setUp(self):
        from alembic.config import Config
        from alembic import command

        self.test_db_path = "test_migration_005.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None

        backend_dir = Path(db.APP_DIR).parent
        cfg = Config(str(backend_dir / "alembic.ini"))
        cfg.set_main_option("script_location", str(backend_dir / "migrations"))
        command.upgrade(cfg, "004")

        with db.get_engine().connect() as conn:
            conn.execute(
                text("INSERT INTO listens (artist, title, unix_ts, source) VALUES (:artist, :title, :unix_ts, :source)"),
                [
                    # Casing conflict: YT import vs LB sync for the same listen
                    {"artist": "Boards of Canada", "title": "The Past Is Dead", "unix_ts": 1_000_000, "source": "youtube_music"},
                    {"artist": "Boards of Canada", "title": "The Past is Dead", "unix_ts": 1_000_000, "source": "listenbrainz_sync"},
                    # True duplicate (same casing, same listen) — should also be removed
                    {"artist": "Boards of Canada", "title": "Roygbiv", "unix_ts": 2_000_000, "source": "listenbrainz_sync"},
                    {"artist": "Boards of Canada", "title": "Roygbiv", "unix_ts": 2_000_000, "source": "listenbrainz_sync"},
                    # Unique listen — untouched
                    {"artist": "Boards of Canada", "title": "Aquarius", "unix_ts": 3_000_000, "source": "listenbrainz_sync"},
                ],
            )
            conn.commit()

        self.cfg = cfg

    def tearDown(self):
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_lb_casing_wins_and_duplicates_removed(self):
        from alembic import command

        command.upgrade(self.cfg, "005")

        with db.get_engine().connect() as conn:
            count_row = conn.execute(text("SELECT COUNT(*) FROM listens")).fetchone()
            assert count_row is not None
            self.assertEqual(count_row[0], 3)

            title_row = conn.execute(text("SELECT title FROM listens WHERE unix_ts = 1000000")).fetchone()
            assert title_row is not None
            self.assertEqual(title_row[0], "The Past is Dead")


class TestGetArtistStats(unittest.TestCase):
    """get_artist_stats: total_track_count and time-range filtering."""

    def setUp(self):
        self.test_db_path = "test_artist_stats.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None
        db.init_db()
        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM listens"))

        import time
        now = int(time.time())
        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source)"
                " VALUES (:a, :t, :ts, :s)"
            ),
            [
                {"a": "Radiohead", "t": "Creep", "ts": now - 100, "s": "youtube_music"},
                {"a": "Radiohead", "t": "Creep", "ts": now - 200, "s": "last_fm"},
                {"a": "Radiohead", "t": "Karma Police", "ts": now - 300, "s": "youtube_music"},
                {"a": "Radiohead", "t": "Fake Plastic Trees", "ts": now - 400, "s": "last_fm"},
            ],
        )
        self.now = now
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_total_track_count_all_time(self):
        stats = database.get_artist_stats(artist="Radiohead")
        self.assertEqual(stats.total_plays, 4)
        self.assertEqual(stats.total_track_count, 3)

    def test_total_track_count_with_time_range(self):
        old_ts = self.now - (400 * 86400)
        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source)"
                " VALUES ('Radiohead', 'Paranoid Android', :ts, 'last_fm')"
            ),
            {"ts": old_ts},
        )
        self.conn.commit()

        stats_all = database.get_artist_stats(artist="Radiohead", time_range="all")
        self.assertEqual(stats_all.total_track_count, 4)

        stats_365 = database.get_artist_stats(artist="Radiohead", time_range="365")
        self.assertEqual(stats_365.total_track_count, 3)

    def test_unknown_artist_returns_zero_counts(self):
        stats = database.get_artist_stats(artist="Unknown Artist")
        self.assertEqual(stats.total_plays, 0)
        self.assertEqual(stats.total_track_count, 0)


class TestTrackListensFunctions(unittest.TestCase):
    """get_track_listens and delete_track_listens repository functions."""

    def setUp(self):
        self.test_db_path = "test_track_listens.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None
        db.init_db()
        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM listens"))

        import time
        now = int(time.time())
        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source)"
                " VALUES (:a, :t, :ts, :s)"
            ),
            [
                {"a": "Radiohead", "t": "Creep", "ts": now - 100, "s": "youtube_music"},
                {"a": "Radiohead", "t": "Creep", "ts": now - 200, "s": "last_fm"},
                {"a": "Radiohead", "t": "Creep", "ts": now - 300, "s": "youtube_music"},
                {"a": "Radiohead", "t": "Karma Police", "ts": now - 400, "s": "last_fm"},
            ],
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_get_track_listens_returns_all_matching(self):
        listens = database.get_track_listens("Radiohead", "Creep")
        self.assertEqual(len(listens), 3)
        for entry in listens:
            self.assertEqual(entry.artist, "Radiohead")
            self.assertEqual(entry.title, "Creep")

    def test_get_track_listens_ordered_newest_first(self):
        listens = database.get_track_listens("Radiohead", "Creep")
        self.assertGreaterEqual(listens[0].unix_ts, listens[1].unix_ts)
        self.assertGreaterEqual(listens[1].unix_ts, listens[2].unix_ts)

    def test_get_track_listens_case_insensitive(self):
        listens = database.get_track_listens("radiohead", "creep")
        self.assertEqual(len(listens), 3)

    def test_get_track_listens_returns_empty_for_unknown(self):
        listens = database.get_track_listens("Nobody", "Nothing")
        self.assertEqual(listens, [])

    def test_delete_track_listens_removes_all_matching(self):
        count = database.delete_track_listens("Radiohead", "Creep")
        self.assertEqual(count, 3)
        self.assertEqual(database.get_track_listens("Radiohead", "Creep"), [])

    def test_delete_track_listens_leaves_other_tracks(self):
        database.delete_track_listens("Radiohead", "Creep")
        karma = database.get_track_listens("Radiohead", "Karma Police")
        self.assertEqual(len(karma), 1)

    def test_delete_track_listens_returns_zero_for_unknown(self):
        count = database.delete_track_listens("Nobody", "Nothing")
        self.assertEqual(count, 0)


class TestCoverArtUpsert(unittest.TestCase):
    """upsert_cover_art: original_url preservation and manual_override stickiness."""

    def setUp(self):
        self.test_db_path = "test_cover_art.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None
        db.init_db()
        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM cover_art_cache"))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def _fetch(self):
        return self.conn.execute(
            text(
                "SELECT url, manual_override, original_url FROM cover_art_cache"
                " WHERE artist_folded='radiohead' AND title_folded='creep'"
            )
        ).fetchone()

    def test_first_insert_sets_url_and_original_url(self):
        database.upsert_cover_art("radiohead", "creep", "https://example.com/art1.jpg")
        row = self._fetch()
        assert row is not None
        self.assertEqual(row[0], "https://example.com/art1.jpg")
        self.assertFalse(row[1])
        self.assertEqual(row[2], "https://example.com/art1.jpg")

    def test_re_upsert_updates_url_but_preserves_original_url(self):
        database.upsert_cover_art("radiohead", "creep", "https://example.com/art1.jpg")
        database.upsert_cover_art("radiohead", "creep", "https://example.com/art2.jpg")
        row = self._fetch()
        assert row is not None
        self.assertEqual(row[0], "https://example.com/art2.jpg")
        self.assertEqual(row[2], "https://example.com/art1.jpg")

    def test_manual_override_sets_flag_and_sticky(self):
        database.upsert_cover_art("radiohead", "creep", "https://example.com/original.jpg")
        database.upsert_cover_art("radiohead", "creep", "https://example.com/manual.jpg", manual_override=True)
        row = self._fetch()
        assert row is not None
        self.assertTrue(row[1])
        self.assertEqual(row[0], "https://example.com/manual.jpg")

    def test_auto_upsert_after_manual_override_does_not_overwrite(self):
        database.upsert_cover_art("radiohead", "creep", "https://example.com/original.jpg")
        database.upsert_cover_art("radiohead", "creep", "https://example.com/manual.jpg", manual_override=True)
        database.upsert_cover_art("radiohead", "creep", "https://example.com/auto.jpg", manual_override=False)
        row = self._fetch()
        assert row is not None
        self.assertEqual(row[0], "https://example.com/manual.jpg")
        self.assertTrue(row[1])

    def test_original_url_preserved_through_manual_override(self):
        """original_url captures the pre-override URL and is never overwritten."""
        database.upsert_cover_art("radiohead", "creep", "https://example.com/original.jpg")
        database.upsert_cover_art("radiohead", "creep", "https://example.com/manual.jpg", manual_override=True)
        row = self._fetch()
        assert row is not None
        self.assertEqual(row[0], "https://example.com/manual.jpg")
        self.assertEqual(row[2], "https://example.com/original.jpg")


class TestListenCorrectionSystem(unittest.TestCase):
    """Per-listen corrections: save, read originals, delete."""

    def setUp(self):
        self.test_db_path = "test_listen_corrections.db"
        db.DB_PATH = self.test_db_path
        db._engine = None
        db._SessionLocal = None
        db.init_db()
        self.conn = db.get_engine().connect()
        self.conn.execute(text("DELETE FROM listen_corrections"))
        self.conn.execute(text("DELETE FROM listens"))
        self.conn.commit()

        self.conn.execute(
            text(
                "INSERT INTO listens (artist, title, unix_ts, source, album, duration_secs)"
                " VALUES ('Raw Artist', 'Raw Title', 1000000, 'youtube_music', 'Raw Album', 200)"
            )
        )
        self.conn.commit()
        row = self.conn.execute(text("SELECT id FROM listens")).fetchone()
        assert row is not None
        self.listen_id = row[0]

    def tearDown(self):
        self.conn.close()
        db.get_engine().dispose()
        db._engine = None
        db._SessionLocal = None
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except Exception:
                pass

    def test_get_listen_with_originals_returns_raw_when_uncorrected(self):
        entry = database.get_listen_with_originals(self.listen_id)
        assert entry is not None
        self.assertEqual(entry.artist, "Raw Artist")
        self.assertEqual(entry.title, "Raw Title")
        self.assertFalse(entry.has_listen_correction)
        self.assertFalse(entry.has_track_correction)

    def test_save_listen_correction_overrides_artist(self):
        database.save_listen_correction(self.listen_id, {"artist": "Corrected Artist"})
        entry = database.get_listen_with_originals(self.listen_id)
        assert entry is not None
        self.assertEqual(entry.artist, "Corrected Artist")
        self.assertEqual(entry.original_artist, "Raw Artist")
        self.assertTrue(entry.has_listen_correction)

    def test_save_listen_correction_overrides_multiple_fields(self):
        database.save_listen_correction(
            self.listen_id,
            {"artist": "New Artist", "title": "New Title", "album": "New Album"},
        )
        entry = database.get_listen_with_originals(self.listen_id)
        assert entry is not None
        self.assertEqual(entry.artist, "New Artist")
        self.assertEqual(entry.title, "New Title")
        self.assertEqual(entry.album, "New Album")
        self.assertEqual(entry.original_artist, "Raw Artist")
        self.assertEqual(entry.original_title, "Raw Title")

    def test_delete_listen_correction_reverts_to_raw(self):
        database.save_listen_correction(self.listen_id, {"artist": "Corrected Artist"})
        database.delete_listen_correction(self.listen_id)
        entry = database.get_listen_with_originals(self.listen_id)
        assert entry is not None
        self.assertEqual(entry.artist, "Raw Artist")
        self.assertFalse(entry.has_listen_correction)

    def test_get_listen_with_originals_returns_none_for_unknown_id(self):
        entry = database.get_listen_with_originals(99999)
        self.assertIsNone(entry)


if __name__ == "__main__":
    unittest.main()
