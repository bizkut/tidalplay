#!/usr/bin/env python3

import tidalapi
import getpass
from sys import exit
from sys import argv
from requests import HTTPError
from subprocess import run, PIPE, STDOUT, Popen, TimeoutExpired, CalledProcessError
from shlex import split
from os.path import basename, dirname, exists
from os import makedirs, remove, environ
from xtermcolor import colorize
from glob import glob
import keyring as kr
import numpy as np
import json

def patch__str__(self):
    return self.name
setattr(tidalapi.models.Model, '__str__', patch__str__)

class Source:
    Vout = 0.0 # V
    Rl = 0.0 # Ohm
    SampleRate = int(0) # kHz
    SampleFormat = "" # ALSA Format String
    VolumeControl = ""
    def __init__(self, Vout, Rl, SampleRate, SampleFormat, VolumeControl):
        self.Vout = Vout
        self.Rl = Rl
        self.SampleRate = SampleRate
        self.SampleFormat = SampleFormat
        self.VolumeControl = VolumeControl

class Sink:
    R = 0.0 # Ohm 
    Sensitivity = 0.0 # db / V

    def __init__(self, R, Sensitivity):
        self.R = R
        self.Sensitivity = Sensitivity


Sources = {"Dell XPS 13 (9343)": 
            Source(Vout=1.052, Rl=9.7, SampleRate=48, SampleFormat="S32_LE", VolumeControl="PCM"),
            "Sabaj DA3":
            Source(Vout=1.98, Rl=3.6, SampleRate=192, SampleFormat="S32_LE", VolumeControl="PCM"),
            "Dell XPS 15 (L502x)":
            Source(Vout=1.052, Rl=1.0, SampleRate=192, SampleFormat="S32_LE", VolumeControl="Master"),
            }

Sinks = {"AKG K702":
            Sink(R=67.0, Sensitivity=100.0),
         "Sennheiser HD4.30":
            Sink(R=23.0, Sensitivity=116.0),
         "AKG K514":
            Sink(R=34.4, Sensitivity=116.9)
        }


CARD = int(0)
AUDIODEV = "hw:%d,0" % CARD

MySource = Sources["Dell XPS 15 (L502x)"]
MySink = Sinks["AKG K514"]

# headphones_sensitivity = 100 # db/V (AKG K 702)
# RH = 67.0 # headpones impedance, Ohm (AKG K 702)

# RH = 23.0 # headpones impedance, Ohm (Sennheiser HD4.30)
# headphones_sensitivity = 116 # db/V (Sennheiser HD4.30)

# RH = 34.4 # headpones impedance, Ohm (AKG K 514)
# headphones_sensitivity = 116.9  # db/V (AKG K 514)

# Vout = 1.052 # unloaded output voltage at 0 db gain, V (Dell XPS 13)
# RL = 9.7 # output impedance, Ohm (Dell XPS 13)

# Vout = 1.98 # unloaded output voltage at 0 db gain, V (Sabaj DA3)
# RL = 3.6 # output impedance, Ohm (Sabaj DA3)

headphones_sensitivity = MySink.Sensitivity
RH = MySink.R
Vout = MySource.Vout
RL = MySource.Rl

PCM_loudness_headroom = -4.0 # PCM loudness headroom, db
target_SPL = 75 # target integrated loudness, db

Rtot = RL + RH
VL = Vout * (RH / Rtot) # output voltage, when loaded, V
SPL_max = headphones_sensitivity + 20. * np.log10(VL) # maximum loudness of the headphone at 0 db gain, db

target_SPL_relative = target_SPL - SPL_max # relative target loudness, db

ffmpeg_download = 'ffmpeg -y -loglevel quiet -timeout 1000000000 -listen_timeout 1000000000 -i "%s" -c:a copy in.flac'

ffmpeg_loudnorm_pass1 = "ffmpeg -y -hide_banner -i final.wav -af loudnorm=I=-24:LRA=14:TP=-4:print_format=json -f null /dev/null"

sox_48 = "sox in.flac -t wav -b 32 final.wav gain -n %+.2g rate -a -v -p 45 -b 85 %dk" % (PCM_loudness_headroom, MySource.SampleRate)

volume = "amixer -c %d -- sset %s playback %ddb"

aplay = "pasuspender -- aplay -q -D %s -f %s --disable-resample --disable-channels --disable-channels --disable-softvol final.wav" % (AUDIODEV, MySource.SampleFormat)

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


def get_artist_radio_tracks(artist, tracks):
    if type(artist) is tidalapi.Artist:
        artist_id = artist.id
    else:
        artist_id = artist

    for track in session.get_artist_radio(artist_id):
        tracks.append(track)

def get_track_radio_tracks(track, tracks):
    track_id = track
    for track in session.get_track_radio(track_id):
        tracks.append(track)

def get_top_tracks(artist, tracks):
    if type(artist) is tidalapi.Artist:
        artist_id = artist.id
    else:
        artist_id = artist

    for track in session.get_artist_top_tracks(artist_id):
        tracks.append(track)

def play_stream_v2(track):
    try:
        track_url = session.get_media_url(track.id)
    except HTTPError:
        return

    track_str = " \t" + track.artist.name + " / " + \
                track.album.name + " / " + track.name
    print(colorize("▶", ansi=46), track_str, end='\t')

    command = split(ffmpeg_download % (track_url))
    try:
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    except (CalledProcessError, TimeoutExpired):
        return

    # command = split(sox_192)
    # try:
    #     run(command, check=True, stdin=PIPE, stdout=PIPE)
    # except (CalledProcessError, TimeoutExpired):
    #     pass

    # command = split(ffmpeg_loudnorm_pass1)
    # try:
    #     p_loudnorm = run(command, check=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    # except (CalledProcessError, TimeoutExpired):
    #     pass

    command = split(sox_48)
    try:
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    except (CalledProcessError, TimeoutExpired):
        pass

    command = split(ffmpeg_loudnorm_pass1)
    try:
        p_loudnorm = run(command, check=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    except (CalledProcessError, TimeoutExpired):
        pass

    out = p_loudnorm.stdout.decode("utf-8").splitlines()[-12:]
    out = "\n".join(out)
    print(out)
    loudnorm = json.loads(out)

    gain = round(target_SPL_relative - float(loudnorm['input_i']))
    if gain > 0.:
        gain = 0.

    command = split(volume % (CARD, MySource.VolumeControl, int(gain)))
    print("Loundess: %.3g db\tDynamic range: %.3g db\tGain: %.3g" % (float(loudnorm['input_i']), float(loudnorm['input_lra']), gain), end='\n')
    try:
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    except (CalledProcessError, TimeoutExpired):
        pass

    command = split(aplay)
    try:
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    except (CalledProcessError, TimeoutExpired):
        pass

    # print(track_str)
    return

def get_tracks(id=""):
    tracks = []
    if schema == "album":
        get_album(id, tracks)
    elif schema == "playlist":
        get_playlist(id, tracks)
    elif schema == "artist":
        get_top_tracks(id, tracks)
    elif schema == "track":
        tracks.append(session.get_track(id))
    elif schema == "":
        tracks = session.user.favorites.tracks()
    elif schema == "radio/artist":
        get_artist_radio_tracks(id, tracks)
    elif schema == "radio/track":
        get_track_radio_tracks(id, tracks)
    return tracks

if __name__ == '__main__':

    if argv.__len__() > 1:
        play_id = argv[1]
        schema = dirname(play_id)
        id = basename(play_id)
        tracks = get_tracks(id)
        for i in range(tracks.__len__()):
            ts = get_tracks(id)
            play_stream_v2(ts[i])
    else:
        schema = ""
        tracks = get_tracks()
        while True:
            i = np.random.choice(tracks.__len__(), 1, replace=False)
            ts = get_tracks()
            play_stream_v2(ts[i[0]])

