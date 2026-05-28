#!/usr/bin/env python3
"""
Debug: submits a single batch of 5 old scrobbles and prints the raw Last.fm response.
Usage: python debug_scrobble.py watch-history.json
"""

import json
import sys
import hashlib
import urllib.request
import urllib.parse
import time

try:
    import pylast
except ImportError:
    print("pip install pylast")
    sys.exit(1)

API_BASE = "https://ws.audioscrobbler.com/2.0/"

def md5(s):
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def api_sig(params, secret):
    keys = sorted(k for k in params if k != "format")
    sig_str = "".join(k + str(params[k]) for k in keys) + secret
    return md5(sig_str)

def api_post(api_key, api_secret, session_key, **params):
    params["api_key"] = api_key
    params["sk"]      = session_key
    params["api_sig"] = api_sig(params, api_secret)
    params["format"]  = "json"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(API_BASE, data=data, method="POST")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_session_key(api_key, api_secret, username, password):
    network = pylast.LastFMNetwork(
        api_key=api_key,
        api_secret=api_secret,
        username=username,
        password_hash=pylast.md5(password),
    )
    network.get_authenticated_user()
    return network.session_key

def parse_entry(entry):
    raw_title = entry.get("title", "")
    if raw_title.startswith("Watched "):
        raw_title = raw_title[8:]
    subtitles = entry.get("subtitles", [])
    subtitle_name = subtitles[0]["name"] if subtitles else None
    if raw_title.startswith("http") or not subtitle_name:
        return None, None
    if subtitle_name.endswith(" - Topic"):
        return subtitle_name[:-8], raw_title
    return None, None

def parse_timestamp(time_str):
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        return int(dt.timestamp())
    except Exception:
        return None

# ── Main ───────────────────────────────────────────────────────────────────────

print(f"Loading {sys.argv[1]}...")
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

entries = []
for entry in data:
    if entry.get("header") != "YouTube Music":
        continue
    artist, title = parse_entry(entry)
    if not artist or not title:
        continue
    ts = parse_timestamp(entry.get("time", ""))
    if not ts:
        continue
    entries.append({"artist": artist, "title": title, "unix_ts": ts})

entries.sort(key=lambda e: e["unix_ts"])
print(f"Total clean entries: {len(entries):,}")

# Pick 5 oldest entries
batch = entries[:5]
print("\nWill attempt to scrobble these 5 entries:")
from datetime import datetime, timezone
for e in batch:
    dt = datetime.fromtimestamp(e["unix_ts"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"  {dt}  {e['artist']} — {e['title']}")

print("\nCredentials:")
api_key    = input("API key    : ").strip()
api_secret = input("API secret : ").strip()
username   = input("Username   : ").strip()
password   = input("Password   : ").strip()

print("Authenticating...")
session_key = get_session_key(api_key, api_secret, username, password)
print(f"Session key: {session_key[:8]}... ✓\n")

# Build scrobble params
params = {"method": "track.scrobble"}
for idx, e in enumerate(batch):
    params[f"artist[{idx}]"]    = e["artist"]
    params[f"track[{idx}]"]     = e["title"]
    params[f"timestamp[{idx}]"] = str(e["unix_ts"])

print("Sending batch...")
try:
    response = api_post(api_key, api_secret, session_key, **params)
    print("\nRaw Last.fm response:")
    print(json.dumps(response, indent=2))
except Exception as ex:
    print(f"Exception: {ex}")
