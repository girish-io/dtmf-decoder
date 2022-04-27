# DTMF Decoder
Decoder for [dual-tone multi-frequency (DTMF)](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling) signals.

## Setup
1. Install dependencies
```
pip install -r requirements.txt
```

2. Run the demo

The script comes with 3 demos;

 One for decoding the signals as they are detected, another one for live plotting the signals, and lastly one for executing commands when a predefined signal was detected.

Live decode:
```
python -m dtmf_decoder
```

Live plot:
```
python -m dtmf_decoder live-plot
```

Command decoder:
```
python -m dtmf_decoder command-decoder
```

## Implementation Details
The decoding process works in the following series of steps:

1. The input signal is fed into a [Goertzel filter](https://en.wikipedia.org/wiki/Goertzel_algorithm) which allows us to unravel the signal into frequencies and their associated energy levels.

2. The two frequencies with the highest energy levels are picked and mapped to the closest lower and higher frequencies according to the [DTMF keypad matrix](https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling#Keypad).

3. Finally the mapped frequencies are looked up in a "keypad table" with the result being the key that was encoded in the DTMF signal.

### Plot for a DTMF Signal 
<p align="center">
    <img src="https://i.imgur.com/tvjifzG.png" />
    <i>Example plot for a DTMF signal representing the key "7" along with its <a href="https://en.wikipedia.org/wiki/Goertzel_algorithm" Goertzel filtered>Goertzel filtered</a> output.</i>
</p>

## Note
I am by no means an expert in the domain of Digital Signal Processing;

I thought this was a fun project to do in my free time to get the basic idea of how DTMF signaling works and was mainly inspired by [this scene](https://www.youtube.com/watch?v=tOLr1pkdr9Q) from The Hummingbird Project where Anton sent commands to his computer over a telephone network from jail.
