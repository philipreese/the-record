#!/usr/bin/env python3
"""
Unit tests for merge_history.py.
Run with: pixi run python backend/test_consolidator.py
"""

import sys
import os
import unittest

# Adjust path to import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from merge_history import (
    strip_watched,
    parse_yt_entry,
    parse_ytm_timestamp,
    normalize,
    merge_histories
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

        # 2. MyActivity format with "From YouTube Music" details
        myact_details = {
            "header": "YouTube",
            "title": "Watched The Summoning",
            "subtitles": [{"name": "Sleep Token"}],
            "details": [{"name": "From YouTube Music"}]
        }
        artist, title = parse_yt_entry(myact_details)
        self.assertEqual(artist, "Sleep Token")
        self.assertEqual(title, "The Summoning")

        # 3. MyActivity format with "Watched on YouTube Music" description
        myact_desc = {
            "header": "YouTube",
            "title": "Watched The Summoning",
            "subtitles": [{"name": "Sleep Token"}],
            "description": "Watched on YouTube Music"
        }
        artist, title = parse_yt_entry(myact_desc)
        self.assertEqual(artist, "Sleep Token")
        self.assertEqual(title, "The Summoning")

        # 4. MyActivity format with generic YouTube header but "- Topic" subtitle
        myact_topic = {
            "header": "YouTube",
            "title": "Watched The Summoning",
            "subtitles": [{"name": "Sleep Token - Topic"}]
        }
        artist, title = parse_yt_entry(myact_topic)
        self.assertEqual(artist, "Sleep Token")
        self.assertEqual(title, "The Summoning")

        # 5. Invalid: generic YouTube video with no music indicators
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

if __name__ == "__main__":
    unittest.main()
