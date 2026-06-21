import re


def clean_artist(artist: str) -> str:
    return re.sub(r'\s*\((?:FR|US|UK|DE|JP|CA|AU)\)$', '', artist, flags=re.IGNORECASE).strip()


def strip_artist_prefix(title: str, artist: str) -> str:
    """Remove 'Artist - ' prefix from a title when it matches the given artist name.

    YouTube Music video titles often embed the artist name: 'Periphery - Blood Eagle
    (Official Music Video)'. Pass the raw (uncleaned) artist so country-suffixed names
    like 'Novelists (FR)' are matched correctly before clean_artist is applied.
    """
    prefix = artist + " - "
    if title.lower().startswith(prefix.lower()):
        return title[len(prefix):]
    return title


def clean_title(title: str) -> str:
    cleaned = title
    cleaned = re.sub(r'\s*[\(\[]feat\.?\s+[^\]\)]+[\)\]]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[\(\[]ft\.?\s+[^\]\)]+[\)\]]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[\(\[]with\s+[^\]\)]+[\)\]]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[\(\[]official\s+(?:video|music\s+video|audio|visualizer)[\)\]]', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[\(\[]live[\)\]]$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[\(\[]bonus\s+track[\)\]]$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()
