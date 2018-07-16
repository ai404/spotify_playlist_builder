import logging
import sqlite3
import time
from datetime import date, timedelta

import requests
import spotipy
import spotipy.util as util
from bs4 import BeautifulSoup
from spotipy.oauth2 import SpotifyClientCredentials

logging.getLogger().setLevel(logging.INFO)


username = "khalifa123"
playlist_station = {"2acVhe4HzyefSG6WKPDN3h": 36, }

SPOTIPY_CLIENT_ID = "714c9446e70e491fb9a7bb60f956f46f"
SPOTIPY_CLIENT_SECRET = "5c36609ad2ee40609b8b506b928124c6"
SPOTIPY_REDIRECT_URI = "http://google.com"


# Utility

def diff(a, b):
    return list(set(a).difference(b))


def chunks(l, n):
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]


# Scraping

def ScrapSongs(station):
    # Entry object
    class Entry:
        def __init__(self, channel, artist, title, date, time):
            self.channel = channel
            self.artist = artist
            self.title = title
            self.date = date
            self.time = time

        def prettify(self):
            return "{0} - {1}".format(self.artist, self.title)

    # Gets the page and initializes soup on it
    def parse(url):
        response = requests.get(url)
        return BeautifulSoup(response.text, "html.parser")

    # Gets all the entries from the page (ignoring ads)
    def get_entries(soup):
        # Output list
        entries = []

        # Get the second table's rows
        entries_rows = soup.select("table")[1].select("tr")

        # Skip headers (first 3)
        entries_rows = entries_rows[3:]

        # Skip footers (last 1)
        entries_rows = entries_rows[:-1]

        # Loop through them
        for entry_row in entries_rows:
            # Get row cells for this row
            cells = entry_row.select("td")

            # Get all the data
            channel = cells[0].get_text()
            artist = cells[1].get_text()
            title = cells[2].get_text()
            date = cells[3].get_text()
            time = cells[4].get_text()

            # Ignore ads
            ads = ["@", "fb.com", "sirusxm", "new -", "critical cut", "on demand", "#Alt", "am ET", "pm ET",
                   "AltNation", "altnation", "sirius"]  # change these to add/remove
            has_ads = False
            for ad in ads:
                if ad in artist or ad in title:
                    has_ads = True
                    break
            if has_ads: continue

            # Append an entry object to the output list
            entries.append(Entry(channel, artist, title, date, time))

        return entries

    # Get yesterday's date
    yday = date.today() - timedelta(days=1)

    # Template for GET request
    url_template = "http://www.dogstarradio.com/search_playlist.php?channel={0}&month={1}&date={2}&page={3}"

    # Start the process
    output = []
    cur_page = 0
    while True:
        url = url_template.format(station, yday.month, yday.day, cur_page)
        entries = get_entries(parse(url))

        # Break if no entries obtained (page is empty <=> this is last page)
        if (len(entries) <= 0): break

        # Append to output prettified entries
        for entry in entries:
            pretty = entry.prettify()
            if not pretty in output:  # check for duplicates
                output.append(pretty)
                # print(pretty) # uncomment for debug

        # Next page
        cur_page += 1

    return output

# connect to the sqlite db/get tracks from it and create it if it doesn't exist
conn = sqlite3.connect("db.sqlite")

c = conn.cursor()
q = """CREATE TABLE IF NOT EXISTS tracks (  
    name varchar(250) NOT NULL,
    artist varchar(250) NOT NULL,
    stat varchar(10) NOT NULL,
    tID varchar(100),
    pID varchar(100),
    rDate int(10),
    PRIMARY KEY(name,artist,pID)
    )"""

c.execute(q)

scope = 'playlist-modify-public'

client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                      client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

for playlist_id, station in playlist_station.items():

    tracks_on_station = ScrapSongs(station)
    logging.info(" [+] found %d tracks on station %d" % (len(tracks_on_station), station))

    # get playlist tracks IDs from spotify
    # playlist_on_spotify=[id["track"]["id"] for id in sp.user_playlist_tracks(username,playlist_id)["items"]]
    playlist = []

    try:
        q = "SELECT name,artist FROM tracks WHERE stat='success' and pID=?"
        lib = c.execute(q, [playlist_id]).fetchall()

        artists = {}
        for tmp_title in lib:
            tmp_name, tmp_artist = tmp_title
            artists[tmp_artist] = artists.get(tmp_artist, 0) + 1

        lib = [str(i[1]) + " - " + str(i[0]) for i in lib]
    except:
        lib = []
        artists = {}

    # open and remove any entries already found in the library
    tracks_on_station = diff(tracks_on_station, lib)

    # searching for tracks in the spotify catalog
    for track_title in tracks_on_station:
        # Currently searches in the format "Artist-Title" but it should be in the format: artist:"ArtistName"
        # album:"AlbumName". May need to change the way the scraper returns as an array instead of the current
        # prettified version to work better
        results = sp.search(q=track_title, limit=1)

        track_artist, track_name = track_title.split(" - ")
        if results['tracks']['items'] == []:
            logging.info(" [+] Not found! - Track name: %40s" % (track_name))
            try:
                q = "INSERT INTO `tracks` VALUES (?,?,?,'',?,'')"
                c.execute(q, [track_name, track_artist, "fails", playlist_id])
                conn.commit()
            except:
                pass
        elif track_artist in artists and artists[track_artist] <= 5 or track_artist not in artists:
            if track_artist in artists and artists[track_artist] == 5:
                q = "SELECT tID FROM tracks WHERE artist=? and pID=? and rDate=(SELECT min(rDate) FROM tracks WHERE artist=? and pID=?) LIMIT 1"
                oldest_from_curent_artist = c.execute(q, [track_artist, playlist_id, track_artist, playlist_id])
                tid = str(oldest_from_curent_artist.fetchone()[0])
                c.execute("DELETE FROM tracks WHERE tID=?", [tid])

                token = util.prompt_for_user_token(username, scope, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET,
                                                   SPOTIPY_REDIRECT_URI)
                sp = spotipy.Spotify(auth=token)
                res = sp.user_playlist_remove_all_occurrences_of_tracks(username, playlist_id, [tid])

            for index, item in enumerate(results['tracks']['items']):
                release_date = int(sp.album(item["album"]["id"])["release_date"].split("-")[0])
                c.execute("INSERT INTO `tracks` VALUES (?,?,?,?,?,?)",
                          [track_name, track_artist, "success", item['id'], playlist_id, release_date])
                conn.commit()
                logging.info(" [+] Count: %3d - Track name: %40s - %s - Release date: %4d" % (
                len(playlist), track_name, "success", release_date))
                playlist.append(item['id'])

            artists[track_artist] = artists.get(track_artist, 0) + 1
        # snooze for rate limits but the snooze is a bit too long. also not sure if there is a better way to do this
        # time.sleep(1)

    token = util.prompt_for_user_token(username, scope, SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI)
    sp = spotipy.Spotify(auth=token)
    sp.trace = False

    # Sending to playlist
    # have to chunk results because you can only add 100 tracks per request
    updatechunks = chunks(playlist, 100)
    for song in updatechunks:
        # for each chunk, send a request to add the songs to the right playlist
        res = sp.user_playlist_add_tracks(username, playlist_id, song)

    time.sleep(5)  # snooze for rate limits
conn.close()
