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
## Defaults
- 75 db target loudness to avoid hearing damage. Please note that some headphones does not give "flat" frequency response at such SPL. For instance, AKG K702 are optimized for 80-85 db. So some SPL-dependent equalization is desirable and will be implemented later.
- To avoid [ringing](https://en.wikipedia.org/wiki/Ringing_artifacts) in poorly mastered music, the (sox) upsampling uses slow rolloff slighly apodizing low-pass filter with 85% bandwidth, based on [archimago](https://archimago.blogspot.com/2018/01/musings-more-fun-with-digital-filters.html) measurements. 
- 4 db PCM headroom to avoid DAC overloading due to the internal resampling, dithering, filtering, etc, see [Benchmark®](https://benchmarkmedia.com/blogs/application_notes/intersample-overs-in-cd-recordings) and [archimago](https://archimago.blogspot.com/2018/09/musings-measurements-look-at-dacs.html) articles for clarification.

## Hardware support

<details>
<summary>Sources</summary>

+ Dell XPS 13 (9343)
+ Dell XPS 15 (L502x)
+ Sabaj DA3
+ Apple USB-C to Headphone adapter
   
</details>

<details>
<summary>Sinks</summary>

+ AKG K514
+ AKG K702
+ Sennheiser HD4.30
   
</details>

Feel free to provide corresponding parameters of any other Sources/Sinks.

## Dependencies
- keyring (<https://github.com/jaraco/keyring>) with cryptfile backend(<https://github.com/frispete/keyrings.cryptfile>) 
- pasuspender (part of pulseaudio-utils)
- aplay, amixer (part of alsa-utils)
- ffmpeg (<https://www.ffmpeg.org/)
- sox (<http://sox.sourceforge.net/>)

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


