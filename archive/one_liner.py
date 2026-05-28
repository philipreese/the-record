import pickle
from datetime import datetime, timezone
c = pickle.load(open('scrobble_checkpoint.pkl', 'rb'))
ts = sorted(c['submitted_timestamps'])
for t in ts[-10:]:
    print(datetime.fromtimestamp(t, tz=timezone.utc))