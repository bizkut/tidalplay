# tidalplay
Tidal player for command line derived from [tidalbar](https://github.com/bsilvereagle/tidalbar)

## Dependencies
Audacious (<http://audacious-media-player.org/>)  
tidalapi (<https://github.com/tamland/python-tidal>)  
keyring (<https://github.com/jaraco/keyring>)  
pasuspender (part of the PulseAudio utils)

## Usage
1. Open Audacious in terminal with `pasuspender audacious`
2. Configure **ALSA** output, resampling, effects, etc.
3. Close Audactious.
4. Open terminal.
5. cd to the tidalplay folder.
6. Type, e.g.,  
`./tidalplay playlist/4d056fb5-99f9-46ec-8ff3-f2dddd41821f` or  
`./tidalplay artist/7144334` or  
`./tidalplay album/33376720` or  
`./tidalplay track/60815627`


