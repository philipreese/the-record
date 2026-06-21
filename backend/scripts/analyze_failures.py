import json, re, collections, os, sys
sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "backfill_failures.json"), encoding="utf-8") as f:
    failures = json.load(f)

# ---- Show Crosses entries ----
crosses = [e for e in failures if "Crosses" in e["artist"] or "†" in e["artist"]]
print(f"Crosses entries ({len(crosses)}):")
for e in crosses:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Categorize all failures ----
def categorize(e):
    artist = e["artist"]
    title = e["title"]

    if re.search(r"VEVO$", artist, re.IGNORECASE):
        return "vevo"
    if re.search(r"Records?\b|Labels?\b|Recordings?\b|Entertainment\b|Music Group\b", artist, re.IGNORECASE) and " - " in title:
        return "label"
    # "4AD", "Epitaph Records", "Equal Vision Records" etc that didn't match above
    # Detect: artist looks like a channel/label (no spaces or short abbreviation) + title has Artist - Title
    if " - " in title and re.search(r"^[A-Z0-9]{2,5}$", artist.replace(" ", "")):
        return "label"
    if re.search(r"\b(Cover|Style|Blink Style|Country Version|Pop Punk|Emo Anthem)\b", title, re.IGNORECASE):
        return "cover_remix"
    if re.search(r"432\s*hz|528\s*hz|binaural|solfeggio|healing freq", title, re.IGNORECASE):
        return "432hz"
    if re.search(r"Relaxing|Celtic Music|Nordic Music|Viking Music|Forest Sanctum|Dark Fjords", title, re.IGNORECASE):
        return "ambient_youtube"
    if re.search(r"workout|cardio|fitness", title, re.IGNORECASE):
        return "non_music"
    # Fan live recordings — title contains venue/date info
    if re.search(r"\blive\s+@|live\s+at\b|from\s+the\s+room", title, re.IGNORECASE):
        return "fan_recording"
    return "missing_mb"

categories = collections.Counter()
by_cat = collections.defaultdict(list)
for e in failures:
    cat = categorize(e)
    categories[cat] += 1
    by_cat[cat].append(e)

print("\nFull category breakdown:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {count:4d}  {cat}")

# ---- Show unique artists in label category ----
print("\nUnique artists in 'label' category:")
label_artists = sorted(set(e["artist"] for e in by_cat["label"]))
for a in label_artists:
    print(f"  {a!r}")

# ---- Show unique artists in vevo category ----
print(f"\nVEVO entries: {len(by_cat['vevo'])}")
for e in by_cat["vevo"][:5]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Show fan recordings ----
print(f"\nFan recordings ({len(by_cat['fan_recording'])}):")
for e in by_cat["fan_recording"][:10]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Show cover/remix ----
print(f"\nCover/remix ({len(by_cat['cover_remix'])}):")
for e in by_cat["cover_remix"][:10]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Show 432hz ----
print(f"\n432hz ({len(by_cat['432hz'])}):")
for e in by_cat["432hz"]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Show ambient ----
print(f"\nAmbient YouTube ({len(by_cat['ambient_youtube'])}):")
for e in by_cat["ambient_youtube"]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Show non-music ----
print(f"\nNon-music ({len(by_cat['non_music'])}):")
for e in by_cat["non_music"]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- Sample of genuinely missing ----
missing = by_cat["missing_mb"]
print(f"\nGenuinely missing from MB: {len(missing)} — first 30:")
for e in missing[:30]:
    print(f"  {e['artist']!r} / {e['title']!r}")

# ---- All unique artists in missing_mb (for review) ----
missing_artists = collections.Counter(e["artist"] for e in missing)
print(f"\nUnique artists in missing_mb: {len(missing_artists)}")
print("Top 40 by track count:")
for artist, count in missing_artists.most_common(40):
    print(f"  {count:3d}  {artist!r}")
