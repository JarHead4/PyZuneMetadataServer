import genres
import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError

def to_mb_toc(toc: str) -> str:
    parts = toc.split('+')
    if "-" in toc:  #Testing WM ID's
        parts = toc.split('-')
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

def get_country_by_geoid(geoid):
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
            
def get_country_by_locale(locale):
    match locale:
        case "411":
            return "JP"
        case "1009":
            return "CA"
        case "809":
            return "GB"
        case "413":
            return "NL"
        case "407":
            return "DE"
        case "1004":
            return "SG"
        case _:
            return "US"
            
def get_release_by_country(country, album):
    try:
        releases = int(album['release-count'])
        if (releases > 1):
            releases = releases-int("1")
        for i in range(releases):
            x = int("%d" % (i))
            if album["release-list"][x]["country"] == country:
                return x
            elif x + 1 >= releases:
                print("Failed to find a matching release, using the default")
                return 0
    except Exception as e:
        print("Error from get_release_by_country:", e)
        return 0
        
def get_release_by_offset(toc, album, release):
    try:
        discs = len(album['release-list'][release]['medium-list'])
        offsets = toc.split("+")
        sectors = int(offsets[2])
        for i in range(discs):
            x = int("%d" % (i))
            if int(album['release-list'][release]['medium-list'][x]['disc-list'][0]['sectors']) == sectors:
                return x
            elif x + 1 == discs:
                print("Failed to find a matching disc, using the default")
                return 0
    except Exception as e:
        print("Error from get_release_by_offset:", e)
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
   
def maxes(a, key=None):
    if key is None:
        key = lambda x: x

    a = iter(a)
    try:
        a0 = next(a)
        m, max_list = key(a0), [a0]
    except StopIteration:
        raise ValueError("maxes() arg is an empty sequence")

    for s in a:
        k = key(s)
        if k > m:
            m, max_list = k, [s]
        elif k == m:
            max_list.append(s)
    return m, max_list

def dateProc(release_date,original_date): ## WMP needs YYYY-MM-DD
    if len(release_date) == 4: #Some release dates are just years
        return release_date + "-01-01"    
    elif len(release_date) == 7 and release_date[4]=='-':#Some release dates are just years and months, but since bothe YYYY-MM and Unknown are len of 7, an extra check needs to happen
        return release_date + "-01"
    elif original_date != "Unknown" and len(release_date) != 4 and len(release_date) != 10: #When no date is associated with release, the date from release-group is grabbed
        return dateProc(original_date,"Unknown")#
    return release_date

def genreRetrieve(all_genres,key):
    if len(all_genres)==0:
        return "Unknown"
    maxs = maxes(all_genres, key)
    genre = genres.topGenre(maxs)
    zuneID = genres.get_zune_genre_id(genre)
    if genre == "Unknown":
        del all_genres[maxs[1][0]]
        return genreRetrieve(all_genres,key)
    print("Set CD genre to " + genre)
    return genre.title()#replace(" music","")
 
def get_genre_by_id(id): #Find genre in release, then release-group and then finally artist, if none have it, the genre is attempted to be grabbed from the tracks right before the XML is built
    tags = musicbrainzngs.get_release_by_id(id, includes=["tags","release-groups","artists"])
    try:
        genre = genreRetrieve(tags['release']['tag-list'],key=lambda ev: ev['count'])
        if genre != "Unknown":
            return genre
    except:
        print("No Valid Genres found with release")
    try:
        genre = genreRetrieve(tags['release']['release-group']['tag-list'],key=lambda ev: ev['count'])
        if genre != "Unknown":
            return genre
    except:
        print("No Valid Genres found with release-group")
    try:
        genre =  genreRetrieve(tags['release']["artist-credit"][0]["artist"]['tag-list'],key=lambda ev: ev['count']) #Grabs 1st artist genre
        if genre != "Unknown":
            return genre
    except:
        print("Could not find a genre for CD, continuing with no genre")
        return "Unknown"