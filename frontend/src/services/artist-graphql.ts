import type { ArtistStatsInfo } from './api';

const ARTIST_QUERY = `
  query ArtistStats($name: String!, $timeRange: String) {
    artist(name: $name, timeRange: $timeRange) {
      artist
      totalPlays
      rank
      firstListenTs
      playsSinceDiscovery
      topTracks {
        title
        playCount
        album
        durationSecs
        firstListenTs
        lastListenTs
        representativeListenId
      }
      topAlbums {
        name
        playCount
      }
      monthlyTrends {
        month
        count
      }
      peakDay {
        date
        plays
      }
      hourly {
        hour
        count
      }
    }
  }
`;

export interface ArtistAlbumInfo {
  name: string;
  playCount: number;
}

export interface ArtistStatsWithAlbums extends ArtistStatsInfo {
  top_albums: ArtistAlbumInfo[];
}

interface GqlArtistStats {
  artist: string;
  totalPlays: number;
  rank: number | null;
  firstListenTs: number | null;
  playsSinceDiscovery: number | null;
  topTracks: {
    title: string;
    playCount: number;
    album: string | null;
    durationSecs: number | null;
    firstListenTs: number | null;
    lastListenTs: number | null;
    representativeListenId: number | null;
  }[];
  topAlbums: { name: string; playCount: number }[];
  monthlyTrends: { month: string; count: number }[];
  peakDay: { date: string; plays: number } | null;
  hourly: { hour: string; count: number }[];
}

export async function fetchArtistStatsGql(
  name: string,
  timeRange: string = 'all',
): Promise<ArtistStatsWithAlbums | null> {
  const res = await fetch('/api/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: ARTIST_QUERY, variables: { name, timeRange } }),
  });
  if (!res.ok) throw new Error(`GraphQL request failed: ${res.status}`);

  const json = (await res.json()) as {
    data?: { artist?: GqlArtistStats | null };
    errors?: { message: string }[];
  };
  if (json.errors?.length) throw new Error(`GraphQL errors: ${json.errors[0].message}`);

  const gql = json.data?.artist;
  if (!gql) return null;

  return {
    artist: gql.artist,
    total_plays: gql.totalPlays,
    rank: gql.rank ?? undefined,
    first_listen_ts: gql.firstListenTs ?? undefined,
    plays_since_discovery: gql.playsSinceDiscovery ?? undefined,
    top_tracks: gql.topTracks.map((t) => ({
      title: t.title,
      play_count: t.playCount,
      album: t.album ?? undefined,
      duration_secs: t.durationSecs ?? undefined,
      first_listen_ts: t.firstListenTs ?? undefined,
      last_listen_ts: t.lastListenTs ?? undefined,
      representative_listen_id: t.representativeListenId ?? undefined,
    })),
    top_albums: gql.topAlbums,
    monthly_trends: gql.monthlyTrends,
    peak_day: gql.peakDay ?? undefined,
    hourly: Object.fromEntries(gql.hourly.map((h) => [h.hour, h.count])),
  };
}
