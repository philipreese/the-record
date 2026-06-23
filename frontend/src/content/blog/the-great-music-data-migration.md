---
title: I Spent Two Weeks Untangling 55,000 Songs So a Robot Could Finally Tell Me What I Listen To
slug: the-great-music-data-migration
date: 2026-06-19
blurb: How a simple wish for better music charts turned into two weeks of Python scripts, YouTube metadata nightmares, and a SQLite trap I'll never forget.
---

There's a specific kind of madness that sets in when you decide your music
listening history _matters_. Not in a vague, sentimental way — in a "this is data
and I want it correct" way. This is the story of how a simple wish ("I'd like a
nice chart of my favorite bands") turned into two weeks of untangling 55,000
plays across three music services and more Python scripts than I'd like to admit.

---

## What scrobbling is, and why I cared

Every time you play a song, that's a data point: _this person, listened to this
track, at this moment._ **Scrobbling** is the act of recording that data point to
a service that collects them all. Do it for years and you get something genuinely
cool — a diary of your life written in songs. The summer you played one album to
death. The artist you discovered in March and abandoned by June. Your actual
taste, measured instead of guessed.

The most famous home for this is **Last.fm**. The open-source, you-own-your-data
alternative is **ListenBrainz**. Both turn "I think I listen to a lot of metal"
into "you played Architects 1,200 times last year, here's the receipt."

I wanted the receipts.

---

## The history that's just gone

I started tracking my music listening in 2011 on **Google Play Music**. Nearly a
decade of plays — every phase, every obsession, every album I put on repeat for
three weeks straight. A genuine record of who I was musically from my early
twenties onward.

In June 2020, Google announced Play Music was shutting down and migrated everyone
to YouTube Music. I made the switch. In December 2020, Play Music went dark for
good.

The listening history did not come with me. There is no export, no recovery path,
no way to get it back. It's just gone.

I'm still a little mad about it.

---

## Why I thought this would be easy

A coworker said something that stuck: the fun of having AI on tap is how cheap
it's become to go poking at someone else's data model — find an API, write a
throwaway script, see what falls out. That got me wondering what my own listening
history actually looked like.

Surely YouTube Music had an API.

It does not.

This barely exists as a problem for **Spotify** users — Spotify exposes your
history, the **Last.fm** integrations are mature, **ListenBrainz** imports are
well-trodden. YouTube Music treats your listening history as Google's data, not
yours.

---

## Getting the data out

So what I actually had was YouTube Music history starting from mid-2020, plus a
couple of days' worth of Last.fm scrobbles from when I'd briefly tried that route
before discovering it couldn't accept historical imports (more on that shortly).
Getting even that turned out to be its own ordeal.

Google does provide a data export tool called **Takeout**. The process for getting your data out:

- navigate to the export page
- check the specific data types you want
- submit the request
- wait anywhere from a few hours to a few days for Google to compile it
- receive an email
- follow a link to a download page
- download one or more zip files
- extract them
- hunt through the extracted folders for the file you actually wanted.

That part is annoying but manageable. The worse part is that YouTube Music
Takeout data appears to be silently truncated. Each export goes back to a
different point in time — sometimes a few months, sometimes a couple of years —
with no explanation and no warning. This is apparently a known issue. The file
just ends wherever it ends.

I ran Takeout **nineteen times** hoping to eventually reach further back. The
furthest I got was around mid-2021. I eventually gave up and used a separate
Google activity export — different format, different structure — to fill in
2020-2021, then merged that with the Takeout data and whatever Last.fm had
recorded, using scripts to normalize all three into a single unified history file.

It arrived. A history file with every song I'd played since 2020, stitched
together from three different sources. After nineteen attempts and days of
wrangling, it felt like I'd cracked a safe.

```
   What I thought I had:            What I actually had:

   +------------------+            +------------------+
   |  clean history   |            | "Novelists (FR)" |
   |  ready to import |            | "Song (Official  |
   |        **        |            |  Music Video)"   |
   |                  |            | "Artist - Topic" |
   +------------------+            |  ...55,000 of    |
                                   |  this hot garbage|
                                   +------------------+
```

---

## The Last.fm problem

The plan was embarrassingly straightforward:

1. Export data.
2. Import data.
3. Generate charts.
4. Feel validated by statistics.

Last.fm ruined step two.

You can scrobble new plays to Last.fm all day long. What you can't do is take
years of listening history from a YouTube Music export and bulk-import it after
the fact.

I discovered this after creating the account, configuring everything, testing it,
and generally feeling very pleased with myself.

So now I had a Last.fm account containing my future and a JSON file containing my
past. Both worked. Neither talked to the other.

As engineering failures go, it wasn't catastrophic. It was just the particular
kind of mistake that makes you stare at a screen and quietly say, "well, that's
annoying."

---

## Choosing ListenBrainz

ListenBrainz — the open one — _does_ let you import historical data. So I made the
call: ListenBrainz would be the **single source of truth**. Everything, past and
present, lives there. One home for the whole story.

Decision made. I just had to import 55,000 songs. Which is when I learned that
importing data and importing _good_ data are very different projects.

---

## YouTube's garbage metadata

The underlying problem was that YouTube Music appears to treat metadata as a loose
suggestion rather than a factual record.

These are all the same artist:

```
  Novelists (FR)          -.
  Novelists               -+--  one band. four "different" artists.
  Novelists  (Official)   -|
  NOVELISTS FR            -'

  Architects              -.
  Architects - Topic       +--  one band. YouTube's auto-channels
  Architects (UK)         -'    and country tags splitting them up.
```

To a human, this is obvious. To a computer building a chart, `Novelists` and
`Novelists (FR)` are two different bands, each with half my plays. My "top
artists" list would be _wrong_ — fragmented into nonsense.

The artist problem was only the beginning. Track names were decorated with things
like:

- `(Official Music Video)`
- `(Lyric Video)`
- `[HD]`
- `[4K]`
- `[Visualizer]`
- `[Official Audio]`

Apparently every song on YouTube arrives carrying six pieces of metadata and three
pieces of marketing material.

The result was a dataset that looked complete at first glance while being quietly
wrong in dozens of ways.

_Those are the worst data problems, because they survive long enough for you to trust them._

---

## Matching against MusicBrainz

### Step 1 — Scrub the obvious junk

I wrote cleaning rules: strip `(FR)`, kill `(Official Video)`, peel off `- Topic`.
Simple text surgery, applied to all 55,000 rows. The easy 80%.

This is also where I hit my first real wall. My instinct was to split artists on
`&` — `Beartooth & HARDY` should obviously become just `Beartooth`, right? Except
`Simon & Garfunkel` is a real band. So is `Florence & The Machine`. There is no
rule that cleanly separates "featured guest stuck in the artist field" from "the
ampersand is literally part of the name." I tried a few heuristics, broke a
handful of legitimate bands, and gave up — those cases went into the manual pile.
Some things a regex just can't know.

Scrubbing names also left another hole: even with a clean name, half my plays had
**no album and no song length**. YouTube doesn't reliably tell you those, and a
listening diary without albums is a sad thing.

### Step 2 — Ask the world's biggest music encyclopedia

**MusicBrainz** is a giant, open, community-built database of basically every song
ever recorded. The plan: for each track, ask MusicBrainz "what album is this on,
and how long is it?" and fill in the blanks.

In practice, MusicBrainz answers _every_ question with a list of maybes, and you
have to figure out which maybe is right. So I built a scoring system. For each
track I ran **two** searches — one with the messy original name, one with my
cleaned-up name — and scored every candidate on:

- How closely the title matched
- How closely the artist matched
- Whether it's an album (good) vs. a bootleg or live rip (suspicious)
- Whether it even _had_ a duration

Best score wins. If both searches agreed, high confidence — apply it. If they
disagreed, or nothing scored well, flag it for me to look at by hand.

Here's how the 21,531 tracks I queried shook out:

```
  Verified (already correct)   ##########################  14,396
  Need a human's eyes          ########                     4,427
  MusicBrainz had nothing      ###.                         1,989
  Filled in automatically      #.                            648
  Too unsure to guess          .                              71
```

That **4,427 "need a human"** pile is the part nobody warns you about. The
automation flattened the easy cases — which are, of course, exactly the cases I
didn't need help with. Almost all of the genuine ambiguity got funneled into that
last 20%, where no amount of clever scoring beats a person squinting at two
nearly-identical track names and making a call.

---

## Human review

The automation got me most of the way there. The remaining 4,427 tracks contained
almost all of the ambiguity.

A machine can tell you that two strings are similar. It cannot tell you whether
the live version of a song, the remastered version, the anniversary re-release,
and the version attached to a compilation album should all count as the same thing.

So I exported everything into a spreadsheet and started making judgment calls.
Every row became a tiny investigation. Accept. Reject. Fix. Delete.

This stage took _days_. I'd open the spreadsheet with coffee in the morning and
close it at night, wondering how I had somehow spent twenty minutes researching a
song I hadn't thought about in ten years.

Somewhere around row four thousand I caught myself debating whether a live
recording should inherit metadata from the studio release. Not implementing code.
Not designing a system. Just sitting there having an argument with myself about
album identity.

That was the moment I realized the project had stopped being a data migration and
become a hobby.

The delete category turned out to be surprisingly entertaining. Buried in my
listening history: rain sounds, brown noise generators, meditation tracks, workout
mixes, ambient noise channels, and a suspicious amount of "432 Hz healing
frequency" content from a period of my life that I have no intention of
investigating further. Not music. Gone.

There was also an incident where Excel helpfully converted the Icelandic band
**Múm** into `MÃºm`, proving once again that no data-cleaning project is complete
until at least one of your tools corrupts the data you're trying to fix.

---

## The migration

Now the riskiest move of the whole project.

ListenBrainz already had dirty plays in it from earlier attempts. The clean
version lived on my computer. To make ListenBrainz the source of truth, I had to
delete the dirty plays up there and re-import the clean ones in their place.

The catch — and I cannot overstate this — is **timing**. A background process
constantly syncs ListenBrainz back down to my computer. If it ran _in the middle_
of the delete-then-import dance, it would happily copy the half-finished mess back
over my clean data and undo everything.

```
   THE SAFE ORDER (do not deviate):

   mirror local DB --> delete dirty plays --> import clean plays --> resume sync
        |                    |                      |                    |
   "this is truth"     "remove the mess"      "put truth online"    "safe again"

   X  running sync anywhere in the middle = corruption
```

And then the import did nothing. Ran clean, exited happy, imported zero songs.

It took me an embarrassingly long time to find it. The importer had a safety
check: before uploading a play, compare it against what's already in the local
database so you don't double-count. Reasonable — except I'd just _rebuilt_ the
import file directly from that same database. Every single clean play matched a
row in the DB, so the importer concluded everything was already there and skipped
all 55,000 of them. The safety check was eating the entire job. One flag to switch
it off, and the real import finally ran.

I wrote the whole sequence down as a runbook afterward so future-me couldn't
fumble it. There's a special humility in writing instructions to protect yourself
from your own 11pm decisions.

---

## The part where I tried to verify it worked

After all of that, I wanted one number. Local database equals ListenBrainz count.
Done.

Three numbers came back. None of them matched.

The local database had 55,210 plays. The ListenBrainz listen-count API said
55,774. An API scan I'd run an hour earlier had returned 57,366. I spent a while
constructing elaborate explanations for each and was confidently wrong about all
of them in sequence.

Part of the answer was simple: the listen-count endpoint caches and hadn't caught
up after several thousand deletes and resubmits. The 57,366 was a mid-operation
snapshot. The real figure, once the dust cleared, should be close to 55,210.

"Close to" wasn't good enough. I wanted _equal to_.

So I wrote a diagnostic script to fetch every single listen from ListenBrainz —
all 55,756 of them — and compare against the local database row by row. The script
found 187 entries on LB that weren't in the database. Alarming. Then I looked at
the mismatches.

`Ødyssee` and `ødyssee`. `Ólafur Arnalds` and `ólafur arnalds`. `RÜFÜS DU SOL`
and `rüfüs du sol`.

SQLite's built-in `NOCASE` collation and `LOWER()` only understand ASCII by default. It cannot lowercase Ø to ø, or
Ó to ó, or Ü to ü. Every track with a non-ASCII character in the artist name was
generating a false mismatch. I switched the comparison to Python's `.lower()`,
which handles Unicode correctly, and the 187 "missing" entries collapsed to 99.
The 86 supposedly missing from LB dropped to zero — same plays, different
capitalization.

The 99 real gaps were almost all dirty scrobbles the cleaner had missed: record
label channels, VEVO accounts, tracks where the artist name had been embedded in
the title. Seven were legitimate plays genuinely absent from the local database.
I added those manually.

Then there were the duplicates. The delete-then-resubmit process had left 445
entries on ListenBrainz with two copies each — the delete queues until the top of
the hour, but the resubmit goes through immediately, so for that window both
versions existed. I wrote another script to find and remove the extras.

Finding 445 duplicates after I thought I was done was not a morale-improving moment.

Then, when I submitted the seven missing plays to ListenBrainz, I accidentally
re-submitted six that were already there, because the script was reading from a
local cache that predated all the deletes. Six new duplicates, freshly created.

So I deleted the cache and re-fetched all 55,000 entries. Again. Ran the
comparison again. Ran the delete. Ran the dedup. Uploaded the one remaining gap.
Waited for the hourly batch to process.

The math was fine. Everything else was lying — and then I kept breaking things.

---

## The payoff

At some point I stopped cleaning. Not because the data was perfect — because it
had crossed the line where the remaining work was pure diminishing returns. The
last 888 tracks were the gnarliest, most ambiguous junk in the whole pile, and
they were not worth another week of my one finite life. Good enough won.

```
  Total plays preserved            55,219
  Unique tracks identified         20,180
  Unique artists                    1,825
  Tracks with full metadata        19,181   (95.0%)
  Tracks missing album AND length     888   (4.4%)
```

Out of **20,180** unique tracks, only **888** are still missing both their album
and their duration — about 4.4%. Counting tracks missing _either_ field, it's 999,
still just 5%. A 95% complete dataset, built mostly by hand, from YouTube's finest garbage.

And now ListenBrainz is the single, clean, trustworthy home for my entire
listening life. The charts I wanted at the very beginning — top artists, what I
played on this day three years ago, the album that defined a summer — finally draw
from data I can actually believe.

Was it worth two weeks for a clean chart of bands I already know I love?

Absolutely. Don't @ me.
