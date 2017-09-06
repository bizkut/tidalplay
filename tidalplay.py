#!/usr/bin/env python3

import tidalapi
import getpass
from sys import exit
from sys import argv
from requests import HTTPError
from subprocess import run, PIPE
from shlex import split
from os.path import basename, dirname, exists
from os import makedirs, remove
from xtermcolor import colorize
from glob import glob
import keyring as kr


def patch__str__(self):
    return self.name
setattr(tidalapi.models.Model, '__str__', patch__str__)
tmp = "/tmp/TIDAL/"

player = "pasuspender -- audacious -q -E --headless '%s'"
player_new = "pasuspender -- audacious -q -E --headless"
downloader = "ffmpeg -loglevel quiet -i '%s' -c copy '%s'"
# http://www.sno.phy.queensu.ca/~phil/exiftool/TagNames/Vorbis.html
download_cover = "curl -s -o %s/%s.jpg '%s'"
metadata = 'metaflac --remove-all-tags --set-tag=ARTIST="%s" --set-tag=ALBUM="%s" --set-tag=TITLE="%s" --set-tag=DATE="%s" --import-picture-from="%s" "%s"'
replaygain = "metaflac --add-replay-gain"

if not exists(tmp):
    makedirs(tmp)
else:
    objlist = glob(tmp + "*")
    for f in objlist:
        remove(f)

session = tidalapi.Session()

login_attempts = 0
allowed_attempts = 3
while login_attempts < allowed_attempts:
    kr.get_keyring()
    username = input('TIDAL username: ')
    password = kr.get_password("tidalplay", username)
    if password is None:
        password = getpass.getpass('TIDAL password: ')
        kr.set_password("tidalplay", username, password)
    try:
        # username = input('TIDAL username: ')

        if session.login(username, password):
            try:
                print(
                    '\N{EIGHTH NOTE} Successfully logged in! \N{EIGHTH NOTE}')
            except UnicodeEncodeError:
                print('Successfully logged in!')
            break
        else:
            print('Error establishing a session. Check your internet connection.')
    except HTTPError:
        print('Error logging in. Please try again.')
        login_attempts = login_attempts + 1
if login_attempts == allowed_attempts:
    print('Failed to login after three attempts. Aborting.')
    exit()


def get_playlist(playlist, tracks):
    # Accept either an id or a Playlist object
    if type(playlist) is tidalapi.Playlist:
        playlist_id = playlist.id
    else:
        playlist_id = playlist

    for track in session.get_playlist_tracks(playlist_id):
        tracks.append(track)


def get_album(album, tracks):
    # Accept either an id or a Playlist object
    if type(album) is tidalapi.Album:
        album_id = album.id
    else:
        album_id = album

    for track in session.get_album_tracks(album_id):
        tracks.append(track)


def get_top_tracks(artist, tracks):
    if type(artist) is tidalapi.Artist:
        artist_id = artist.id
    else:
        artist_id = artist

    for track in session.get_artist_top_tracks(artist_id):
        tracks.append(track)


def play_track(track):
    if session.get_media_url(track.id):
        file_path = session.get_media_url(track.id)
        # print(file_path)
        if "flac" not in file_path:
            return
        command = split(player % file_path)
        track_str = " \t" + track.artist.name + " / " + \
            track.album.name + " / " + track.name
        print(colorize("▶", ansi=46), track_str, end='\r')
        run(command, check=True, stdin=PIPE, stdout=PIPE)
        print(track_str)


def download_tracks():
    for i, track in enumerate(tracks):
        track_path = session.get_media_url(track.id)
        if "flac" not in track_path:
            continue

        flac_name = tmp + str(i) + ".flac"
        command = split(downloader % (track_path, flac_name))
        run(command, check=True, stdin=PIPE, stdout=PIPE)

        # command = split(removemetadata % flac_name)
        # run(command, check=True, stdin=PIPE, stdout=PIPE)

        coverart_url = track.album.image
        command = split(download_cover % (tmp, str(i), coverart_url))
        run(command, check=True, stdin=PIPE, stdout=PIPE)

        command = split(metadata % (track.artist.name, track.album.name,
                                    track.name, track.album.release_date,
                                    (tmp + str(i) + ".jpg"), flac_name))
        print(command)
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    return


def add_replaygain():
    command = split(replaygain)
    for filename in glob(tmp + "*.flac"):
        command.append(filename)
    run(command, check=True, stdin=PIPE, stdout=PIPE)
    return


def play_tracks():
    command = split(player_new)
    for filename in glob(tmp + "*.flac"):
        command.append(filename)
    run(command, check=True, stdin=PIPE, stdout=PIPE)
    return


def get_tracks(id):
    tracks = []
    if schema == "album":
        get_album(id, tracks)
    elif schema == "playlist":
        get_playlist(id, tracks)
    elif schema == "artist":
        get_top_tracks(id, tracks)
    elif schema == "track":
        tracks.append(session.get_track(id))
    return tracks

try:

    play_id = argv[1]
    schema = dirname(play_id)
    id = basename(play_id)

    # download_tracks()
    # add_replaygain()
    # play_tracks()

    tracks = get_tracks(id)
    for i in range(tracks.__len__()):
        ts = get_tracks(id)
        play_track(ts[i])

except Exception as e:
    print(e)
    import traceback
    traceback.print_exc()
