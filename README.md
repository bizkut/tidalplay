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
    A(Download Track)-->B(Apply -8 db Gain<br/>To Avoid Intersample Overloading);
    B-->C(Resample To<br/>Maximum Sample Rate);
    C-->D(Apply PCM headroom<br/>To Avoid DAC Overloading);
    D-->E(Convert To<br/>The Maximum Bit Depth)
    E-->F(Estimate Loudness);
    F-->G(Ajust Hardware Volume Control<br/>To Achieve Target Loudness);
    G-->I(Play);
```

## Dependencies
keyring (<https://github.com/jaraco/keyring>) with cryptfile backend(<https://github.com/frispete/keyrings.cryptfile>) 
pasuspender (part of pulseaudio-utils)
aplay, amixer (part of alsa-utils)
ffmpeg (<https://www.ffmpeg.org/)
sox (<http://sox.sourceforge.net/>)

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


