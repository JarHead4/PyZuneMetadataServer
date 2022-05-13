import genres
import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError

def to_mb_toc(toc: str) -> str:
    parts = toc.split('+')
    count: int = len(parts)
    
    for i in range(count):
        part: str = parts[i]

        # Convert from hex to decimal
        parts[i] = str(int(part, 16))

    # Move section offset to position two
    parts.insert(1, parts.pop(count - 1))

    # Add first track
    parts.insert(0, "1")

    return '+'.join(parts)

def get_country(geoid):
    match geoid:
        case "292d":
            return "XE"
        case "7c":
            return "JP"
        case "27":
            return "CA"
        case "f2":
            return "GB"
        case "54":
            return "FR"
        case "b0":
            return "NL"
        case "dd":
            return "SE"
        case "xe":
            return "AT"
        case "5e":
            return "DE"
        case "989e":
            return "XW"
        case "68":
            return "HK"
        case "a7":
            return "MY"
        case "d7":
            return "SG"
        case "xc":
            return "AU"
        case _:
            return "US"
            
def get_release_by_country(country, album):
    releases = int(album['release-count'])-int("1")
    try:
        for i in range(releases):
            x = int("%d" % (i))
            if album["release-list"][x]["country"] == country:
                return x
            elif x == releases:
                return 0
    except:
        return 0

table = str.maketrans({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
})
def escape(txt):
    return txt.translate(table)
    
def get_genre_by_id(id):
    try:
        tags = musicbrainzngs.get_release_by_id(id, includes=["tags"])
        priority = max(tags['release']['tag-list'], key=lambda ev: ev['count'])
        genre = priority['name']
        zuneID = genres.get_zune_genre_id(genre)
        zuneName = genres.get_zune_genre_name(zuneID)
        if (zuneName == genre):
            genre = genre.title()
            print("Set CD genre to " + genre)
            return genre
        else:
            print("Could not find a genre for CD, continuing with no genre")
            return "Unknown"
    except:
        print("Could not find a genre for CD, continuing with no genre")
        return "Unknown"