Spotify Playlist Builder
==================

![alt text](https://img.shields.io/badge/python-3.6-green.svg "Python3.6")

This Script clones some existing Web Radio Stations into our Spotify Playlists.
Our source is ```dogstarradio``` from which we select a station then we clone all the tracks on that station into our Spotify Playlist. 

Dependecies:
-------------
* BeautifulSoup4

```pip install bs4```

* Requests

```pip install requests```

* Spotipy

```pip install spotipy```

* Or alternatively

```pip install -r requirements.txt```

How to start:
-------------

* Setup a Spotify Account.
* Go to Spotify Console for developer and create an Application.
* get the Client ID and Client Secret.
* Set a redirect URL.
* Update the variables ```SPOTIPY_CLIENT_ID```,```SPOTIPY_CLIENT_SECRET``` and ```SPOTIPY_REDIRECT_URI```.
* Go to ```http://www.dogstarradio.com``` and find an appropriate web station for you.
* Create a Playlist and add its ID to ```playlist_station``` dictionary as a key and the selected station ID as value.

Compatibility
-------------

Compatible with Python 3.x ,tested  on Python 3.6.
