#!/usr/bin/env python3
"""
Check Last.fm scrobble count and recent entries.
Usage: python check_scrobbles.py
"""

import urllib.request
import urllib.parse
import json

api_key  = input("API key  : ").strip()
username = input("Username : ").strip()

def lastfm_get(method, **params):
    base = "https://ws.audioscrobbler.com/2.0/"
    params.update({
        "method": method,
        "user": username,
        "api_key": api_key,
        "format": "json",
    })
    url = base + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())

# Total scrobble count
info = lastfm_get("user.getinfo")
total = info["user"]["playcount"]
print(f"\nTotal scrobbles on Last.fm : {total}")

# Most recent 10 scrobbles
recent = lastfm_get("user.getrecenttracks", limit=10)
tracks = recent["recenttracks"]["track"]
print(f"\nMost recent 10 scrobbles:")
for t in tracks:
    # Currently playing track has no date
    date = t.get("date", {}).get("#text", "now playing")
    print(f"  {date:<25} {t['artist']['#text']} — {t['name']}")

# Oldest scrobble — fetch last page
attr = recent["recenttracks"]["@attr"]
total_pages = int(attr["totalPages"])
if total_pages > 1:
    oldest_page = lastfm_get("user.getrecenttracks", limit=1, page=total_pages)
    oldest = oldest_page["recenttracks"]["track"]
    if isinstance(oldest, list):
        oldest = oldest[-1]
    oldest_date = oldest.get("date", {}).get("#text", "unknown")
    print(f"\nOldest scrobble on record  : {oldest_date}")
    print(f"  {oldest['artist']['#text']} — {oldest['name']}")
