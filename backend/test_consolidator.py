#!/usr/bin/env python3
"""
Unit tests for merge_history.py.
Run with: pixi run python backend/test_consolidator.py
"""

import sys
import os
import unittest

# Adjust path to import backend modules
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)
sys.path.append(os.path.join(backend_dir, "scripts"))

from merge_history import (
    strip_watched,
    parse_yt_entry,
    parse_ytm_timestamp,
    normalize,
    merge_histories,
    deduplicate_myactivity
)

class TestConsolidator(unittest.TestCase):

    def test_strip_watched(self):
        self.assertEqual(strip_watched("Watched The Summoning"), "The Summoning")
        self.assertEqual(strip_watched("The Summoning"), "The Summoning")
        self.assertEqual(strip_watched(""), "")

    def test_parse_yt_entry(self):
        # 1. Standard watch-history.json format (topic channel)
        std_valid = {
            "header": "YouTube Music",
            "title": "Watched The Summoning",
            "subtitles": [{"name": "Sleep Token - Topic"}]
        }
        artist, title = parse_yt_entry(std_valid)
        self.assertEqual(artist, "Sleep Token")
        self.assertEqual(title, "The Summoning")

        # 2. Excludes header == "YouTube" (now ignored to prevent noise)
        myact_details = {
            "header": "YouTube",
            "title": "Watched The Summoning",
            "subtitles": [{"name": "Sleep Token - Topic"}]
        }
        artist, title = parse_yt_entry(myact_details)
        self.assertEqual(artist, None)
        self.assertEqual(title, None)

        # 3. Invalid: generic YouTube video
        invalid_yt = {
            "header": "YouTube",
            "title": "Watched Funny Cats Video",
            "subtitles": [{"name": "Cat channel"}]
        }
        self.assertEqual(parse_yt_entry(invalid_yt), (None, None))

    def test_parse_ytm_timestamp(self):
        time_str = "2026-05-28T01:23:28.084Z"
        ts = parse_ytm_timestamp(time_str)
        # Expected unix timestamp for 2026-05-28 01:23:28 UTC is 1779931408
        self.assertEqual(ts, 1779931408)

    def test_normalize(self):
        self.assertEqual(normalize("Sleep Token"), "sleeptoken")
        self.assertEqual(normalize("The Summoning (Remix)"), "thesummoningremix")
        self.assertEqual(normalize(""), "")

    def test_merge_histories(self):
        # 3 YTM entries
        ytm_list = [
            {"artist": "Sleep Token", "title": "The Summoning", "unix_ts": 1000},
            {"artist": "Spiritbox", "title": "Cellar Door", "unix_ts": 2000},
            {"artist": "Loathe", "title": "Is It Really You?", "unix_ts": 3000}
        ]

        # 3 Last.fm entries:
        # 1. Matches first YTM entry (exact match, timestamp identical)
        # 2. Matches second YTM entry (slight timestamp offset, slightly different casing/topic)
        # 3. Does NOT match any YTM entry (e.g. 2010 track)
        lfm_list = [
            {"artist": "Sleep Token", "title": "The Summoning", "unix_ts": 1000},
            {"artist": "Spiritbox", "title": "Cellar Door", "unix_ts": 2001},
            {"artist": "The Beatles", "title": "Yesterday", "unix_ts": 500}
        ]

        merged = merge_histories(ytm_list, lfm_list)

        # Result should have 4 items: the 3 YTM items + the 1 unmatched Last.fm item (Yesterday)
        self.assertEqual(len(merged), 4)

        # Yesterday should be first (sorted by timestamp 500)
        self.assertEqual(merged[0]["title"], "Yesterday")
        self.assertEqual(merged[0]["source"], "last_fm")

        # The others should preserve their details and order
        self.assertEqual(merged[1]["title"], "The Summoning")
        self.assertEqual(merged[1]["source"], "youtube_music")
        self.assertEqual(merged[2]["title"], "Cellar Door")
        self.assertEqual(merged[2]["source"], "youtube_music")
        self.assertEqual(merged[3]["title"], "Is It Really You?")
        self.assertEqual(merged[3]["source"], "youtube_music")

    def test_deduplicate_myactivity(self):
        # 1. Exact match (0s difference)
        watch_1 = [{"artist": "Taylor Swift", "title": "seven", "unix_ts": 10000}]
        myact_1 = [{"artist": "Taylor Swift", "title": "seven", "unix_ts": 10000}]
        added, skipped = deduplicate_myactivity(watch_1, myact_1)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(added), 0)

        # 2. Shifted duplicate within 12h (e.g. 1h 44m offset = 6240s)
        watch_2 = [{"artist": "American Football", "title": "Blood On My Blood", "unix_ts": 10000 + 6240}]
        myact_2 = [{"artist": "American Football", "title": "Blood On My Blood", "unix_ts": 10000}]
        added, skipped = deduplicate_myactivity(watch_2, myact_2)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(added), 0)

        # 3. Genuine repeat (watch has 1 play, myact has 2 plays: 1h 44m offset and 8h later)
        # 10000 + 6240 = 16240 (watch)
        # 10000 (myact, dup)
        # 10000 + 28800 = 38800 (myact, genuine repeat 8h later)
        watch_3 = [{"artist": "American Football", "title": "Blood On My Blood", "unix_ts": 16240}]
        myact_3 = [
            {"artist": "American Football", "title": "Blood On My Blood", "unix_ts": 10000},
            {"artist": "American Football", "title": "Blood On My Blood", "unix_ts": 38800}
        ]
        added, skipped = deduplicate_myactivity(watch_3, myact_3)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["unix_ts"], 38800)

        # 4. Greedy closest matching
        # Watch play at 12:00 (ts=10000). MyAct plays at 11:58 (ts=9880) and 11:30 (ts=8200)
        # 9880 is closer to 10000 than 8200, so it gets matched/skipped. 8200 is kept.
        watch_4 = [{"artist": "Sleep Token", "title": "The Summoning", "unix_ts": 10000}]
        myact_4 = [
            {"artist": "Sleep Token", "title": "The Summoning", "unix_ts": 8200},
            {"artist": "Sleep Token", "title": "The Summoning", "unix_ts": 9880}
        ]
        added, skipped = deduplicate_myactivity(watch_4, myact_4)
        self.assertEqual(skipped, 1)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["unix_ts"], 8200)

        # 5. Outside window (12h + 1s = 43201s offset)
        watch_5 = [{"artist": "Loathe", "title": "Is It Really You?", "unix_ts": 10000 + 43201}]
        myact_5 = [{"artist": "Loathe", "title": "Is It Really You?", "unix_ts": 10000}]
        added, skipped = deduplicate_myactivity(watch_5, myact_5)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["unix_ts"], 10000)

if __name__ == "__main__":
    unittest.main()
