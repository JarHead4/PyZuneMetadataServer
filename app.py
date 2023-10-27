from flask import Flask, request, abort, Response, redirect
import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError
import utils

from atom.factory import *

app = Flask(__name__)
musicbrainzngs.set_useragent("Zune", "4.8")

import re

def gen_mdrcd_xml(album, album_name, artist, genre, release_date, numoftracks, releasenum, mediumnum, MBID):
    # Start building XML with new data
    xml = "<METADATA><MDR-CD><version>5.0</version><WMCollectionID>" + MBID + "</WMCollectionID><WMCollectionGroupID>" + MBID + "</WMCollectionGroupID><ZuneAlbumMediaID>" + MBID + "</ZuneAlbumMediaID><uniqueFileID>UMGa_id=R   123480</uniqueFileID><albumTitle>" + album_name + "</albumTitle><albumArtist>" + artist + "</albumArtist>" 
    
    # Remove the release date if it's incomplete or unavailable
    if release_date != "Unknown":
        xml = xml + "<releaseDate>" + release_date + "</releaseDate>"

    xml = xml + "<label>UMG</label>"
    
    # Remove the genre if it's unavailable
    if genre != "Unknown":
        xml = xml + "<genre>" + genre + "</genre>"
        
    xml = xml + "<providerStyle>Pop/Rock</providerStyle><publisherRating>5</publisherRating><buyParams>providerName=UMG&amp;albumID=" + MBID + "&amp;a_id=R%20%20%20123480&amp;album=Go%20West%20Young%20Man&amp;artistID=D82033BF-D711-4442-94D6-1196E76223F4&amp;p_id=P%20%20%20%20%202400&amp;artist=Michael%20W.%20Smith</buyParams><largeCoverParams>/large/album.jpg?id=" + MBID + "</largeCoverParams><smallCoverParams>/small/album.jpg?id=" + MBID + "</smallCoverParams><moreInfoParams>" + MBID + "</moreInfoParams><dataProvider>AMG</dataProvider><dataProviderParams>Provider=AMG</dataProviderParams><dataProviderLogo>Provider=AMG</dataProviderLogo><needIDs>0</needIDs>"
    
    # Add track info to XML for each track
    for i in range(numoftracks):
        # There's probably a better way to do all this, but no
        x = int("%d" % (i))
        tracknum: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['number']
        try:
            trackid: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['id']
        except:
            trackid: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['recording']['id']
        try:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['title']
        except:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['recording']['title']
        tracktitle = utils.escape(tracktitle)
        xml = xml + "<track><WMContentID>" + trackid + "</WMContentID><ZuneMediaID>" + trackid + "</ZuneMediaID><trackTitle>" + tracktitle + "</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>" + tracknum + "</trackNumber><trackPerformer>" + artist + "</trackPerformer><trackComposer>" + artist + "</trackComposer><explicitLyrics>0</explicitLyrics></track>"
    
    # Finalize XML
    xml = xml + "</MDR-CD><Backoff><Time>5</Time></Backoff></METADATA>"
    print("Converted " + album_name + " to MDR-CD XML")
    return xml

def gen_wmp7_xml(album, album_name, artist, genre, numoftracks, releasenum, mediumnum):
    # Start building XML with new data
    # Note: A lot of assumptions are being made about how these files are structured, this is incredibly unlikely to be accurate
    xml = "<METADATA><version>1.0</version><name>" + album_name + "</name><author>" + artist + "</author>" 
    
    # Remove the genre if it's unavailable
    if genre != "Unknown":
        xml = xml + "<genre>" + genre + "</genre>"
    
    # Add track info to XML for each track
    for i in range(numoftracks):
        # There's probably a better way to do all this, but no
        x = int("%d" % (i))
        tracknum: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['number']
        try:
            trackid: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['id']
        except:
            trackid: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['recording']['id']
        try:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['title']
        except:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-list'][x]['recording']['title']
        tracktitle = utils.escape(tracktitle)
        xml = xml + "<track><name>" + tracktitle + "</name><number>" + tracknum + "</number><composer>" + artist + "</composer></track>"
    
    # Finalize XML
    xml = xml + "</METADATA>"
    print("Converted " + album_name + " to WMP 7 XML")
    return xml

@app.route("/")
def default():
    with open(f'default.html', 'r') as file:
        data: str = file.read().replace('\n', '')
        return Response(data)

@app.route(f"/cdinfo/GetMDRCD.aspx")
@app.route(f"/cdinfo/QueryTOC.asp")
def cd_get_album():
    # Get CD header from Zune request
    ToC = request.args.get('CD')
    
    # Get geoId header from Zune request
    geoid = request.args.get('geoid')
    locale = request.args.get('locale')
    
    # Prioritize geoid over locale, as more countries are supported there
    if geoid is not None:
        country = utils.get_country_by_geoid(geoid)
        print("Matched client geoid to region " + country)
    # Use locale as a fallback (likely a WMP 7-9 client)
    elif locale is not None:
        country = utils.get_country_by_locale(locale)
        print("Matched client locale to region " + country)
    # Client didn't send locale or geoid (should never happen), default to US so things still work
    else:
        country = "US"
        print("Client didn't send geoid or locale, defaulting to US")
    
    # Replace spaces with +, so the MusicBrainz ToC script works
    ToC = ToC.replace(" ", "+")
    print("User inserted a CD with the ToC: " + ToC)
    
    # Convert Zune ToC to MusicBrainz ToC
    MBToC = utils.to_mb_toc(ToC)
    print("Converted ToC to MusicBrainz ToC: " + MBToC)
    
    try:
        # Get album info from MusicBrainz
        album = musicbrainzngs.get_releases_by_discid(MBToC, toc=MBToC, includes=["artists", "recordings"])

        print("Matching CD region to client region (" + country + ")")
        releasenum = utils.get_release_by_country(country, album)
        mediumnum = utils.get_release_by_offset(MBToC, album, releasenum)
        print("Found best match, using release " + str(releasenum) + ", disc " + str(mediumnum))
    
        MBID = album["release-list"][releasenum]["id"]
    
        album_name = album["release-list"][releasenum]["title"]
        artist = album['release-list'][releasenum]['artist-credit'][0]['artist']['name']
        album_name = utils.escape(album_name)
        artist = utils.escape(artist)
    except:
        print("An error occurred while getting MusicBrainz data (CD doesn't exist?)")
        return 'Server Error', 500
    
    # Check if MusicBrainz has a release date, if not set release_date to Unknown
    try:
        release_date: str = album['release-list'][releasenum]['date']
    except:
        release_date: str = "Unknown"

    # Zune will discard the entire XML if the release date is invalid, so we only send it if it's complete
    if len(release_date) != 10:
        release_date: str = "Unknown"
    
    numoftracks: str = album['release-list'][releasenum]['medium-list'][mediumnum]['track-count']
    
    print("Identified CD as: " + album_name + " by " + artist)
    
    genre = utils.get_genre_by_id(MBID)
    
    if (request.path == "/cdinfo/QueryTOC.asp"):
        # Client is WMP 7 compatible, so generate that flavor of XML
        xml = gen_wmp7_xml(album, album_name, artist, genre, numoftracks, releasenum, mediumnum)
    else:
        # Client isn't WMP 7 compatible, which means it's likely an MDR-CD client
        xml = gen_mdrcd_xml(album, album_name, artist, genre, release_date, numoftracks, releasenum, mediumnum, MBID)
    
    return Response(xml, mimetype=MIME_XML)
    print("Sent XML to client")

@app.route(f"/cdinfo/GetMDRCDPOSTURL.aspx")
def get_post_url():
    return Response("http://info.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?", mimetype=MIME_XML)

# Get large image information
@app.route(f"/cover/large/album.jpg")
def cd_get_large():
    # Get id header from Zune request
    AlbumId = request.args.get('id')
    removeIndicator = "?locale"
    AlbumId = AlbumId.split(removeIndicator, 1)[0]
    try:
        print("Getting Album Art for " + AlbumId)
        image = musicbrainzngs.get_image_front(AlbumId, size=250)
    except:
        print("The Album Art was not found on MusicBrainz")
        return 'Not Found', 404

    return Response(image, mimetype=MIME_JPG)

# Get small image information
@app.route(f"/cover/small/album.jpg")
def cd_get_small():
    # Get id header from Zune request
    AlbumId = request.args.get('id')
    removeIndicator = "?locale"
    AlbumId = AlbumId.split(removeIndicator, 1)[0]
    try:
        print("Getting Album Art for " + AlbumId)
        image = musicbrainzngs.get_image_front(AlbumId, size=250)
    except:
        print("The Album Art was not found on MusicBrainz")
        return 'Not Found', 404

    return Response(image, mimetype=MIME_JPG)
    
# Windows Media Player 7 redirect
@app.route(f"/redir/QueryTOC.asp")
def wmp7_redir():
    cd = request.args.get('cd')
    locale = request.args.get('locale')
    if locale is None:
        locale = "0"

    return redirect("http://windowsmedia.com/cdinfo/QueryTOC.asp?CD=" + cd + "&locale=" + locale, code=302)
        
# Windows Media Player 9 redirect
@app.route(f"/redir/GetMDRCD.asp")
def wmp9_redir():
    cd = request.args.get('CD')
    locale = request.args.get('locale')
    return redirect("http://toc.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?CD=" + cd + "&locale=" + locale, code=302)
    
# Windows Media Player 9 POST URL redirect
@app.route(f"/redir/GetMDRCDPOSTURLBackground.asp")
def wmp9_redir_posturl():
    cd = request.args.get('CD')
    locale = request.args.get('locale')
    return redirect("http://info.music.metaservices.microsoft.com/cdinfo/GetMDRCDPOSTURL.aspx", code=302)
    
# MDR-CD redirect
@app.route(f"/redir/getmdrcd/")
def mdrcd_redir():
    path = request.full_path
    removeIndicator = "/redir/getmdrcd/"
    query = path.split(removeIndicator, 1)[1]
    return redirect("http://toc.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?" + query, code=302)

# Zune redirect
@app.route("/redir/getmdrcdzune/")
def zune_redir():
    path = request.full_path
    removeIndicator = "/redir/getmdrcdzune/"
    query = path.split(removeIndicator, 1)[1]
    return redirect("http://toc.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?" + query, code=302)
        
if __name__ == "__main__":
    app.run(port=80, host="127.0.0.1")
