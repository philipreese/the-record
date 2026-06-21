import sqlite3
DB = r'backend/history.db'
conn = sqlite3.connect(DB)

checks = [
    ('scale the summit', 'dont mind me'),
    ('caliban', 'dystopia'),
    ('crosses', None),
    ('allison eide', None),
    ('justin starling', None),
    ('joel corry', None),
    ('cul', None),
    ('bilmuri', 'corn-fed yetis'),
    ('vanessa carlton', 'the only way to love'),
    ('thrice', 'black honey'),
    ('the midnight', 'heartbeat'),
    ('jamies elsewhere', None),
    ("jamie's elsewhere", None),
    ('dance gavin dance', 'death of a strawberry'),
]

for artist, title in checks:
    if title:
        rows = conn.execute(
            'SELECT unix_ts, artist, title FROM listens WHERE LOWER(artist) LIKE ? AND LOWER(title) LIKE ? LIMIT 3',
            ('%' + artist + '%', '%' + title + '%')
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT unix_ts, artist, title FROM listens WHERE LOWER(artist) LIKE ? LIMIT 3',
            ('%' + artist + '%',)
        ).fetchall()
    status = 'IN DB    ' if rows else 'NOT IN DB'
    t = title if title else '*'
    print(status + '  ' + artist + ' / ' + t)
    for r in rows[:2]:
        print('           -> artist=' + repr(r[1]) + ', title=' + repr(r[2]))

conn.close()
