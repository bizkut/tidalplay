# tidalplay
Tidal player for command line derived from [tidalbar](https://github.com/bsilvereagle/tidalbar)

## Scope
The main idea of this project is to stream music from Tidal with target loudness (defined in EBU R 128) and the highest possible quality for the given equipment. To achieve this goal a player needs to know the following parameters of the playback equipment:
- output voltage at 0 db
- output impedance
- headphones/speakers impedance
- headphones/speakers sensitivity
- maximum sample rate of DAC
- maximum bit depth of DAC
- ALSA name of the hardware volume control of the DAC

## Signal path

```mermaid
graph LR
    A(Download Track) --> B(Resample To<br/>Maximum Sample Rate <br/>and Bit Depth);
    B-->C(Estimate Loudness);
    C-->D(Ajust<br/>Hardware Volume Control);
    D-->E(Play);
```

## Dependencies
keyring (<https://github.com/jaraco/keyring>)<br/>
pasuspender (part of pulseaudio-utils)<br/>
aplay, amixer (part of alsa-utils)<br/>
ffmpeg(<https://www.ffmpeg.org/)<br/>
sox(<http://sox.sourceforge.net/>)<br/>

## Usage
1. Adjust MySink, MySource, CARD and target_SPL variables in `tidalplay.py` to match your playback setup and target loundess, respectively.
4. Open terminal.
5. cd to the tidalplay folder.
6. Type, e.g.,  
`./tidalplay.py playlist/4d056fb5-99f9-46ec-8ff3-f2dddd41821f` or  
`./tidalplay.py artist/7144334` or  
`./tidalplay.py album/33376720` or  
`./tidalplay.py track/60815627` or
`./tidalplay.py`


