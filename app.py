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

@app.route("/")
def default():
    with open(f'default.html', 'r') as file:
        data: str = file.read().replace('\n', '')
        return Response(data)
        
@app.route("/redir/getmdrcdzune/")
def zune_redir():
    path = request.full_path
    removeIndicator = "/redir/getmdrcdzune/"
    query = path.split(removeIndicator, 1)[1]
    return redirect("http://toc.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?" + query, code=302)

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
    print("Converted " + album_name + " to XML")
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
    removeIndicator = "?locale"
    AlbumId = AlbumId.split(removeIndicator, 1)[0]
    try:
        print("Getting Album Art for " + AlbumId)
        image = musicbrainzngs.get_image_front(AlbumId, size=500)
    except:
        print("The Album Art was not found on MusicBrainz")
        return 'Not Found', 404

    return Response(image, mimetype=MIME_JPG)
        
# Windows Media Player 9 redirect
@app.route(f"/redir/GetMDRCD.asp")
def wmp9_redir():
    cd = request.args.get('CD')
    locale = request.args.get('locale')
    return redirect("http://toc.music.metaservices.microsoft.com/cdinfo/GetMDRCD.aspx?CD=" + cd + "&geoid=" + locale, code=302)
    
# Windows Media Player 9 POST URL redirect
@app.route(f"/redir/GetMDRCDPOSTURLBackground.asp")
def wmp9_redir_posturl():
    cd = request.args.get('CD')
    locale = request.args.get('locale')
    return redirect("http://info.music.metaservices.microsoft.com/cdinfo/GetMDRCDPOSTURL.aspx", code=302)
        
# Windows Media Player 9 POST URL redirect
@app.route(f"/ZuneAPI/EndPoints.aspx")
def wmp9_redifr_posturl():
    post = request.data
    print(post)
    
# Tunes.com
@app.route("/tunes-cgi2/tunes/disc_info/203/cd=8+96+4E95+8B9E+C1B8+15A01+1953E+1CB74+2237D+29A90")
def win_2000_deluxe():
    # Get CD header from Zune request
    ToC = request.environ['RAW_URI']
    print(ToC)
    removeIndicator = "cd="
    ToC = ToC.split(removeIndicator, 1)[1]
    print(ToC)
    
    # Replace spaces with +, so the MusicBrainz ToC script works
    ToC = ToC.replace(" ", "+")
    print("User inserted a CD with the ToC: " + ToC)
    
    # Convert Zune ToC to MusicBrainz ToC
    MBToC = utils.to_mb_toc(ToC)
    print("Converted ToC to MusicBrainz ToC: " + MBToC)
    
    try:
        # Get album info from MusicBrainz
        album = musicbrainzngs.get_releases_by_discid(MBToC, toc=MBToC, includes=["artists", "recordings"])
    
        releasenum = 0
    
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
    
    numoftracks: str = album['release-list'][releasenum]['medium-list'][0]['track-count']
    
    print("Identified CD as: " + album_name + " by " + artist)
    
    genre = utils.get_genre_by_id(MBID)
    
    # Start building XML with new data
    xml = "[CD] Mode=0 Title=" + album_name + " Artist=" + artist + " "
    
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
        xml = xml + "Track" + tracknum + "=" + tracktitle + " "
    
    # Finalize XML
    xml = xml + "Menu1=RollingStone Biography::http://www.tunes.com/mscd.asp?t=b&id=6863 Menu2=RS News::http://www.tunes.com/mscd.asp?t=n&id=6863 Menu3=RS Photos::http://www.tunes.com/mscd.asp?t=p&id=6863 Menu4=RS Triva::http://www.tunes.com/mscd.asp?t=t&id=6863 Menu5=RS Discussions::http://www.tunes.com/mscd.asp?t=d&id=6863 Menu6=RS Discography::http://www.tunes.com/mscd.asp?t=disc&id=6863 Menu7=Get Related MP3s::http://www.tunes.com/mscd.asp?t=mp3&id=6863 "
    print("Converted " + album_name + " to XML")
    return Response(xml)
    print("Sent XML to client")
    
# dmr.allmusic.com
@app.route("/sdkrequest", methods=['GET', 'POST'])
def PS3_CD():
    print(request.form)
    xml = "<METADATA><albumTitle>Super Mario Galaxy Official Soundtrack</albumTitle><albumArtist>Mario Galaxy Orchestra</albumArtist><releaseDate>2011-10-23</releaseDate><label>UMG</label><providerStyle>Pop/Rock</providerStyle><publisherRating>5</publisherRating><buyParams>providerName=UMG&amp;albumID=e6348cf2-3d61-4d89-acba-4b9f44039244&amp;a_id=R%20%20%20123480&amp;album=Go%20West%20Young%20Man&amp;artistID=D82033BF-D711-4442-94D6-1196E76223F4&amp;p_id=P%20%20%20%20%202400&amp;artist=Michael%20W.%20Smith</buyParams><largeCoverParams>/large/album.jpg?id=e6348cf2-3d61-4d89-acba-4b9f44039244</largeCoverParams><smallCoverParams>/small/album.jpg?id=e6348cf2-3d61-4d89-acba-4b9f44039244</smallCoverParams><moreInfoParams>e6348cf2-3d61-4d89-acba-4b9f44039244</moreInfoParams><dataProvider>MusicBrainz</dataProvider><dataProviderParams>Provider=MusicBrainz</dataProviderParams><dataProviderLogo>Provider=MusicBrainz</dataProviderLogo><needIDs>0</needIDs><track><trackTitle>Overture</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>1</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>b33123c8-3c4f-4049-81ed-f8b3608f9191</WMContentID><ZuneMediaID>b33123c8-3c4f-4049-81ed-f8b3608f9191</ZuneMediaID><trackTitle>The Star Festival</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>2</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>3be491b0-16e7-43a8-bb90-1f4b45b78743</WMContentID><ZuneMediaID>3be491b0-16e7-43a8-bb90-1f4b45b78743</ZuneMediaID><trackTitle>Attack of the Airships</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>3</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>fc6dd767-61da-4cab-879d-c4ee2d16e903</WMContentID><ZuneMediaID>fc6dd767-61da-4cab-879d-c4ee2d16e903</ZuneMediaID><trackTitle>Catastrophe</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>4</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>f73f4ceb-c179-4358-bf97-b61be683383a</WMContentID><ZuneMediaID>f73f4ceb-c179-4358-bf97-b61be683383a</ZuneMediaID><trackTitle>Peach's Castle Stolen</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>5</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>bd4084b0-467a-4f72-bb3d-181d52457ca7</WMContentID><ZuneMediaID>bd4084b0-467a-4f72-bb3d-181d52457ca7</ZuneMediaID><trackTitle>Enter the Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>6</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>c0e44f48-3a61-4092-9d24-a2486f0d2a9b</WMContentID><ZuneMediaID>c0e44f48-3a61-4092-9d24-a2486f0d2a9b</ZuneMediaID><trackTitle>Egg Planet</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>7</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>cfb4a885-feb4-4c04-a701-d9236b817001</WMContentID><ZuneMediaID>cfb4a885-feb4-4c04-a701-d9236b817001</ZuneMediaID><trackTitle>Rosalina in the Observatory 1</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>8</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>ee075270-b7ee-41ce-b8a9-aa0872a255e6</WMContentID><ZuneMediaID>ee075270-b7ee-41ce-b8a9-aa0872a255e6</ZuneMediaID><trackTitle>The Honeyhive</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>9</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>cb72cc86-b0b1-42a3-be52-66972205b8a0</WMContentID><ZuneMediaID>cb72cc86-b0b1-42a3-be52-66972205b8a0</ZuneMediaID><trackTitle>Space Junk Road</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>10</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>daf80071-344a-4157-ae61-6602fc4736ca</WMContentID><ZuneMediaID>daf80071-344a-4157-ae61-6602fc4736ca</ZuneMediaID><trackTitle>Battlerock Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>11</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>5e9b7615-3427-4d9f-b3c6-4d0038c8a8b6</WMContentID><ZuneMediaID>5e9b7615-3427-4d9f-b3c6-4d0038c8a8b6</ZuneMediaID><trackTitle>Beach Bowl Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>12</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>adba75e1-dd7b-4bf7-9402-5a0f05e67adc</WMContentID><ZuneMediaID>adba75e1-dd7b-4bf7-9402-5a0f05e67adc</ZuneMediaID><trackTitle>Rosalina in the Observatory 2</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>13</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>cd2eeb78-1772-4f52-9f70-aa9c0e33f83d</WMContentID><ZuneMediaID>cd2eeb78-1772-4f52-9f70-aa9c0e33f83d</ZuneMediaID><trackTitle>Enter Bowser Jr.!</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>14</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>7e336641-af6b-40e4-9ebe-7bbb083cba11</WMContentID><ZuneMediaID>7e336641-af6b-40e4-9ebe-7bbb083cba11</ZuneMediaID><trackTitle>Waltz of the Boos</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>15</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>d2c75d0a-cd47-4b07-84a0-45fe842692ad</WMContentID><ZuneMediaID>d2c75d0a-cd47-4b07-84a0-45fe842692ad</ZuneMediaID><trackTitle>Buoy Base Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>16</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>c05e580c-5d80-4fc1-8e99-f130e2e73903</WMContentID><ZuneMediaID>c05e580c-5d80-4fc1-8e99-f130e2e73903</ZuneMediaID><trackTitle>Gusty Garden Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>17</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>e6e39467-a52d-47ff-9760-4d6ad5b7a8aa</WMContentID><ZuneMediaID>e6e39467-a52d-47ff-9760-4d6ad5b7a8aa</ZuneMediaID><trackTitle>Rosalina in the Observatory 3</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>18</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>50f37088-88d4-41cb-854d-270c3209e830</WMContentID><ZuneMediaID>50f37088-88d4-41cb-854d-270c3209e830</ZuneMediaID><trackTitle>King Bowser</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>19</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>456f7f06-f1df-4e89-930f-4eef4a32ae3e</WMContentID><ZuneMediaID>456f7f06-f1df-4e89-930f-4eef4a32ae3e</ZuneMediaID><trackTitle>Melty Molten Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>20</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>0bdeeee6-f981-4115-a3e0-7b8edef66053</WMContentID><ZuneMediaID>0bdeeee6-f981-4115-a3e0-7b8edef66053</ZuneMediaID><trackTitle>The Galaxy Reactor</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>21</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>7c446543-998c-48b1-9917-a6f90a866ff1</WMContentID><ZuneMediaID>7c446543-998c-48b1-9917-a6f90a866ff1</ZuneMediaID><trackTitle>Final Battle with Bowser</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>22</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>d2e0482f-075b-4c7f-8729-b95c12f8ce4a</WMContentID><ZuneMediaID>d2e0482f-075b-4c7f-8729-b95c12f8ce4a</ZuneMediaID><trackTitle>Daybreak - A New Dawn</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>23</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>069d9aa9-4a8d-43c2-ae40-7675216dc64f</WMContentID><ZuneMediaID>069d9aa9-4a8d-43c2-ae40-7675216dc64f</ZuneMediaID><trackTitle>Birth</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>24</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>19db1755-5858-41ae-b671-8f3a359a06dd</WMContentID><ZuneMediaID>19db1755-5858-41ae-b671-8f3a359a06dd</ZuneMediaID><trackTitle>Super Mario Galaxy</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>25</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>5f758918-dbe4-418b-be08-7de2e32ffd42</WMContentID><ZuneMediaID>5f758918-dbe4-418b-be08-7de2e32ffd42</ZuneMediaID><trackTitle>Purple Comet</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>26</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>d7258e78-4934-4212-afc4-85fcbf750b37</WMContentID><ZuneMediaID>d7258e78-4934-4212-afc4-85fcbf750b37</ZuneMediaID><trackTitle>Blue Sky Athletic</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>27</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><track><WMContentID>40f960fd-d472-41dc-b603-95e833e3625a</WMContentID><ZuneMediaID>40f960fd-d472-41dc-b603-95e833e3625a</ZuneMediaID><trackTitle>Super Mario 2007</trackTitle><uniqueFileID>UMGp_id=P     2400;UMGt_id=T  2881042</uniqueFileID><trackNumber>28</trackNumber><trackPerformer>Mario Galaxy Orchestra</trackPerformer><trackComposer>Mario Galaxy Orchestra</trackComposer><explicitLyrics>0</explicitLyrics></track><Backoff><Time>5</Time></Backoff></METADATA>"
    return Response(xml)

if __name__ == "__main__":
    app.run(port=80, host="192.168.0.105")
