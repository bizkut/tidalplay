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
from keyrings.cryptfile.cryptfile import CryptFileKeyring
import numpy as np
import json
import re
import urllib
from shutil import which

class Source:
    Vout = 0.0  # V
    Rl = 0.0  # Ohm
    SampleRate = int(0)  # kHz
    SampleBits = int(0)
    SampleFormat = ""  # ALSA Format String
    VolumeControl = ""

    def __init__(self, Vout, Rl, SampleRate, SampleFormat, VolumeControl):
        self.Vout = Vout
        self.Rl = Rl
        self.SampleRate = SampleRate
        self.SampleFormat = SampleFormat
        self.VolumeControl = VolumeControl
        self.SampleBits = int(re.findall('^S(\d+)_*?', SampleFormat)[0])


class Sink:
    R = 0.0  # Ohm
    Sensitivity = 0.0  # db / V

    def __init__(self, R, Sensitivity):
        self.R = R
        self.Sensitivity = Sensitivity


Sources = {"Dell XPS 13 (9343)":
           Source(Vout=1.052, Rl=9.7, SampleRate=48,
                  SampleFormat="S32_LE", VolumeControl="PCM"),
           "Sabaj DA3":
           Source(Vout=1.98, Rl=3.6, SampleRate=192,
                  SampleFormat="S32_LE", VolumeControl="PCM"),
           "Dell XPS 15 (L502x)":
           Source(Vout=1.052, Rl=1.0, SampleRate=192,
                  SampleFormat="S32_LE", VolumeControl="Master"),
           "Apple USB-C to 3.5mm Headphone Adapter":
           Source(Vout=1.039, Rl=0.9, SampleRate=48,
                  SampleFormat="S24_3LE", VolumeControl="PCM"),
           "Onkyo A-9010 (TOSLINK)":
           Source(Vout=1.0, Rl=0.09, SampleRate=48,
                  SampleFormat="S32_LE", VolumeControl="Software")
           }

Sinks = {"AKG K702":
         Sink(R=67.0, Sensitivity=100.0),
         "Sennheiser HD4.30":
         Sink(R=23.0, Sensitivity=116.0),
         "AKG K514":
         Sink(R=34.4, Sensitivity=116.9),
         "Triangle Plaisir Kari":
         Sink(R=6, Sensitivity=97.0)
         }


CARD = int(1)
AUDIODEV = "hw:%d,0" % CARD

MySource = Sources["Apple USB-C to 3.5mm Headphone Adapter"]
MySink = Sinks["AKG K702"]

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

OVERLOAD_PROTECTION = -8.0  # Intersample overload protection headroom, db
PCM_loudness_headroom = -4.0  # PCM loudness headroom, db
target_SPL = 75  # target integrated loudness, db

Rtot = RL + RH
VL = Vout * (RH / Rtot)  # output voltage, when loaded, V
# maximum loudness of the headphone at 0 db gain, db
SPL_max = headphones_sensitivity + 20. * np.log10(VL)

target_SPL_relative = target_SPL - SPL_max  # relative target loudness, db

ffmpeg_loudnorm_pass1 = "ffmpeg -y -hide_banner -i temp.wav -af loudnorm=I=-24:LRA=14:TP=-4:print_format=json -f null /dev/null"

sox_48 = "sox in -t wav -e float -b 32 temp.wav gain -n %+.2g rate -a -R 198 -c 4096 -p 45 -t -b 95 %dk gain -n %+.2g" % (
    OVERLOAD_PROTECTION, MySource.SampleRate, PCM_loudness_headroom)

volume = "amixer -c %d -- sset %s playback %ddb"
softvolume = "sox temp.wav -t wav -e signed-integer -b %d final.wav gain %+.2g"

HASMQA = (which('mqadec') is not None) and (which('mqarender') is not None)
if HASMQA is True:
    print("MQA decoding is possible.")
mqadec = "mqadec in in.wav"

pasuspender = "pasuspender -- "
HASPA = which('pasuspender') is not None

aplay = "aplay -q -D %s -f %s --disable-resample --disable-channels --disable-channels --disable-softvol final.wav" % (
    AUDIODEV, MySource.SampleFormat)
if HASPA is True:
    print("Using pasuspender to bypass pulseaudio.")
    aplay = pasuspender + aplay


HASMQA = (which('mqadec') is not None) and (which('mqarender') is not None)

session = tidalapi.Session()

login_attempts = 0
allowed_attempts = 3
while login_attempts < allowed_attempts:
    kr = CryptFileKeyring()
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

    try:
        res = urllib.request.urlopen(track_url)
        filetype = res.info().get_content_type().split("/")[1]
        if filetype == 'mp4':
            print("No AAC support at the moment.")
            return
        urllib.request.urlretrieve(track_url, "in")
    except (HTTPError, TimeoutExpired, IOError):
        return

    if track.quality == tidalapi.models.Quality.hi_res and HASMQA is True:
        print("Decoding MQA")
        command = split(mqadec)
        try:
            run(command, check=True, stdin=PIPE, stdout=PIPE)
        except (CalledProcessError, TimeoutExpired):
            pass
        sox_48.replace('in','in.wav')

    command = split(sox_48)
    try:
        run(command, check=True, stdin=PIPE, stdout=PIPE)
    except (CalledProcessError, TimeoutExpired):
        pass

    command = split(ffmpeg_loudnorm_pass1)
    try:
        p_loudnorm = run(command, check=True, stdin=PIPE,
                         stdout=PIPE, stderr=STDOUT)
    except (CalledProcessError, TimeoutExpired):
        pass

    out = p_loudnorm.stdout.decode("utf-8").splitlines()[-12:]
    out = "\n".join(out)
    print(out)
    loudnorm = json.loads(out)

    gain = round(target_SPL_relative - float(loudnorm['input_i']))
    if gain > 0.:
        gain = 0.

    print("Loundess: %.3g db\tDynamic range: %.3g db\tGain: %.3g" % (
        float(loudnorm['input_i']), float(loudnorm['input_lra']), gain), end='\n')

    if MySource.VolumeControl != "Software":
        command = split(volume % (CARD, MySource.VolumeControl, int(gain)))
        try:
            run(command, check=True, stdin=PIPE, stdout=PIPE)
        except (CalledProcessError, TimeoutExpired):
            pass
        gain = int(0)

    command = split(softvolume % (MySource.SampleBits, gain))
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
