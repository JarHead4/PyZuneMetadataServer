from flask import Flask, request, abort, Response, redirect
import musicbrainzngs
from musicbrainzngs.musicbrainz import ResponseError
import utils

from atom.factory import *

from locale import getdefaultlocale
sys_locale = getdefaultlocale()[0]

app = Flask(__name__)
musicbrainzngs.set_useragent("Zune", "4.8")

import re
@app.after_request
def allow_zunestk_cors(response):
    return response

@app.route(f"/cdinfo/GetMDRCD.aspx")
def cd_get_album():
    # Get CD header from Zune request
    ToC = request.args.get('CD')
    
    # Get geoId header from Zune request
    geoid = request.args.get('geoid')
    
    # Get country abbreviation from geoid
    country = utils.get_country(geoid)
    print("Client region is " + country)
    
    # Replace spaces with +, so the MusicBrainz ToC script works
    ToC = ToC.replace(" ", "+")
    print("User inserted a CD with the ToC: " + ToC)
    
    # Convert Zune ToC to MusicBrainz ToC
    MBToC = utils.to_mb_toc(ToC)
    print("Converted ToC to MusicBrainz ToC: " + MBToC)
    
    # Get album info from MusicBrainz
    album = musicbrainzngs.get_releases_by_discid(MBToC, toc=MBToC, includes=["artists", "recordings"])

    print("Matching CD region to client region (" + country + ")")
    releasenum = utils.get_release_by_country(country, album)
    print("Found best match, using release " + str(releasenum))
    
    album_name = album["release-list"][releasenum]["title"]
    artist = album['release-list'][releasenum]['artist-credit'][0]['artist']['name']
    album_name = utils.escape(album_name)
    artist = utils.escape(artist)
    
    # Check if MusicBrainz has a release date, if not set release_date to Unknown
    try:
        release_date: str = album['release-list'][releasenum]['date']
    except:
        release_date: str = "Unknown"

    # Zune will discard the entire XML if the release date is invalid, so we only send it if it's complete
    if len(release_date) != 10:
        release_date: str = "Unknown"
    
    numoftracks: str = album['release-list'][releasenum]['medium-list'][0]['track-count']
    MBID: str = album["release-list"][releasenum]["id"]

    print("Identified CD as: " + album_name + " by " + artist)
    
    # Start building XML with new data
    xml = "<METADATA><MDR-CD><version>5.0</version><WMCollectionID>" + MBID + "</WMCollectionID><WMCollectionGroupID>" + MBID + "</WMCollectionGroupID><ZuneAlbumMediaID>" + MBID + "</ZuneAlbumMediaID><uniqueFileID>UMGa_id=R   123480</uniqueFileID><albumTitle>" + album_name + "</albumTitle><albumArtist>" + artist + "</albumArtist>" 
    
    # Remove the release date if it's incomplete or unavailable
    if release_date != "Unknown":
        xml = xml + "<releaseDate>" + release_date + "</releaseDate>"

    xml = xml + "<label>UMG</label><genre>Pop</genre><providerStyle>Pop/Rock</providerStyle><publisherRating>5</publisherRating><buyParams>providerName=UMG&amp;albumID=" + MBID + "&amp;a_id=R%20%20%20123480&amp;album=Go%20West%20Young%20Man&amp;artistID=D82033BF-D711-4442-94D6-1196E76223F4&amp;p_id=P%20%20%20%20%202400&amp;artist=Michael%20W.%20Smith</buyParams><largeCoverParams>/large/album.jpg?id=" + MBID + "</largeCoverParams><smallCoverParams>/small/album.jpg?id=" + MBID + "</smallCoverParams><moreInfoParams>" + MBID + "</moreInfoParams><dataProvider>AMG</dataProvider><dataProviderParams>Provider=AMG</dataProviderParams><dataProviderLogo>Provider=AMG</dataProviderLogo><needIDs>0</needIDs>"
    
    # Add track info to XML for each track
    for i in range(numoftracks):
        # There's probably a better way to do all this, but no
        x = int("%d" % (i))
        tracknum: str = album['release-list'][releasenum]['medium-list'][0]['track-list'][x]['number']
        try:
            trackid: str = album['release-list'][releasenum]['medium-list'][0]['track-list'][x]['id']
        except:
            trackid: str = album['release-list'][releasenum]['medium-list'][0]['track-list'][x]['recording']['id']
        try:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][0]['track-list'][x]['title']
        except:
            tracktitle: str = album['release-list'][releasenum]['medium-list'][0]['track-list'][x]['recording']['title']
        tracktitle = utils.escape(tracktitle)
        xml = xml + "<track><WMContentID>" + trackid + "</WMContentID><ZuneMediaID>" + trackid + "</ZuneMediaID><trackTitle>" + tracktitle + "</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>" + tracknum + "</trackNumber><trackPerformer>" + artist + "</trackPerformer><trackComposer>" + artist + "</trackComposer><explicitLyrics>0</explicitLyrics></track>"
    
    # Finalize XML
    xml = xml + "</MDR-CD><Backoff><Time>5</Time></Backoff></METADATA>"
    print("Converted " + album_name + " to XML")
    return Response(xml, mimetype=MIME_XML)
    print("Sent XML to client")

@app.route(f"/cdinfo/GetMDRCDPOSTURL.aspx")
def get_post_url():
    return 'Unimplemented Feature', 500

# Get large image information
@app.route(f"/cover/large/album.jpg")
def cd_get_large():
    # Get id header from Zune request
    AlbumId = request.args.get('id')
    try:
        print("Getting Album Art for " + AlbumId)
        image = musicbrainzngs.get_image_front(AlbumId, size=1200)
    except:
        print("The Album Art was not found on MusicBrainz")
        return 'Not Found', 404

    return Response(image, mimetype=MIME_JPG)

# Get small image information
@app.route(f"/cover/small/album.jpg")
def cd_get_small():
    # Get id header from Zune request
    AlbumId = request.args.get('id')

    try:
        image = musicbrainzngs.get_image_front(AlbumId, size=500)
    except:
        return 'Not Found', 404

    return Response(image, mimetype=MIME_JPG)

if __name__ == "__main__":
    app.run(port=80, host="127.0.0.3")
