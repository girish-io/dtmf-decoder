"""

Useful resources:
-----------------

 - https://rfmw.em.keysight.com/rfcomms/refdocs/cdma2k/cdma2000_meas_dtmf_desc.html#:~:text=The%20duration%20of%20DTMF%20symbols,be%20at%20least%2010%20ms.
 - https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling
 - https://www.infineon.com/dgdl/Infineon-AN2122_Analog_Standard_DTMF_Detector-ApplicationNotes-v08_00-EN.pdf?fileId=8ac78c8c7cdc391c017d0736b28259bd
 - https://www.ti.com/lit/an/spra096a/spra096a.pdf?ts=1650572130118#:~:text=DTMF%20Tone%20Generator,-The%20encoder%20portion&text=As%20typical%20DTMF%20frequencies%20range,area%20of%20the%20Nyquist%20criteria.

"""

import sys
import math
import time
import numpy as np
import sounddevice as sd
import matplotlib
import matplotlib.pyplot as plt
from dtmf_decoder.command_decoder import CommandDecoder
from dtmf_decoder.helpers import clear_console, goertzel, \
    find_closest_freq, get_frequency_energy_pairs

# We use 8 kHz as our sampling frequency as defined by the G.711 specification which is
# used by most telephone systems. Human speech is contained in the 100 Hz-4 kHz range,
# thus using a sampling rate of 8 kHz puts us in a safe area of the Nyquist criteria.
FS = 8000

# How many seconds to read data from the source input before detecting signals (in seconds)
SAMPLE_WINDOW = 15 / 1000.0

SAMPLE_SIZE = math.ceil(FS * SAMPLE_WINDOW)

# Tone detection criteria
MIN_TONE_ENERGY = 1
MAX_TONE_DEVIATION = 50

# Minimum energy for the low and high frequencies of the DTMF signal to be considered as a keypress
MIN_LOW_F_ENERGY = 5
MIN_HIGH_F_ENERGY = 5

# Minimum duration of a signal for it to be considered as a keypress (in seconds)
MIN_SIGNAL_DURATION = 50 / 1000.0  # 50 ms

# Time to wait in-between consecutive signals (in seconds)
SYMBOL_SPACING_DURATION = 100 / 1000.0  # 100 ms

#
# With the MIN_SIGNAL_DURATION and SYMBOL_SPACING_DURATION set to 50ms and 10ms respectively,
# I was able to decode the number in this dial-up modem handshake video:
#
#   https://www.youtube.com/watch?v=vvr9AMWEU-c
#

KEYMAP = {
    (697, 1209): '1',
    (697, 1336): '2',
    (697, 1477): '3',
    (697, 1633): 'A',
    (770, 1209): '4',
    (770, 1336): '5',
    (770, 1477): '6',
    (770, 1633): 'B',
    (852, 1209): '7',
    (852, 1336): '8',
    (852, 1477): '9',
    (852, 1633): 'C',
    (941, 1209): '*',
    (941, 1336): '0',
    (941, 1477): '#',
    (941, 1633): 'D'
}

LOW = [697, 770, 852, 941]
HIGH = [1209, 1336, 1477, 1633]

BANNER = r'''
                    _
                    | |
                    |_|
                    /_\    \ | /
                    .-"""------.----.
                    |          U    |
                    |               |
                    | ====o======== |
                    | ============= |
                    |               |
                    |_______________|
                    | ________GF337 |
                    ||   Welcome   ||
                    ||             ||
                    ||_____________||
                    |__.---"""---.__|
                    |---------------|
                    |[Yes][(|)][ No]|
                    | ___  ___  ___ |
                    |[<-'][CLR][.->]|
                    | ___  ___  ___ |
                    |[1__][2__][3__]|
                    | ___  ___  ___ |
                    |[4__][5__][6__]|
                    | ___  ___  ___ |
                    |[7__][8__][9__]|
                    | ___  ___  ___ |
                    |[*__][0__][#__]|
                    `--------------'
                    {__|""|_______'-
                    `---------------'

                      DTMF DECODER
'''


def plot_signal(signal):
    frames = signal['frames']
    freqs = signal['freqs']
    results = signal['results']
    pressed_key = signal['pressed_key']

    f_low = signal['f_low']
    closest_low = signal['closest_low']
    energy_low = signal['energy_low']

    f_high = signal['f_high']
    closest_high = signal['closest_high']
    energy_high = signal['energy_high']

    # Plot the input signal
    plt.subplot(2, 1, 1)
    plt.cla()
    t = np.linspace(0, 1, FS)[:SAMPLE_SIZE]

    plt.title('Input Signal')
    plt.plot(t, frames)

    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')

    # Plot the goertzel result on the input signal
    plt.subplot(2, 1, 2)
    plt.cla()
    plt.yscale('log')

    plt.title(
        f'Goertzel Filtered Signal (Key: {pressed_key})\n' \
            f'f_low={f_low:.1f} Hz, e_low={energy_low:.1f} / ' \
                f'f_high={f_high:.1f} Hz, e_high={energy_high:.1f}')

    plt.stem(freqs, np.array(results)[:,2], linefmt=':')

    plt.gca().annotate(
        f'{f_low:.1f} (@{closest_low} Hz)',
        xy=(f_low, energy_low),
        xytext=(f_low + 50, energy_low),
        color='purple',
        arrowprops={'arrowstyle': '<-'}
    )

    plt.gca().annotate(
        f'{f_high:.1f} (@{closest_high} Hz)',
        xy=(f_high, energy_high),
        xytext=(f_high + 50, energy_high),
        color='purple',
        arrowprops={'arrowstyle': '<-'}
    )

    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Energy')

    plt.ylim([1, 30000])

    plt.subplots_adjust(hspace=0.8)

    # Save the plot
    # plt.savefig('dtmf-plot.png')

    plt.pause(0.5)


def decoded_signals():
    stream = sd.Stream(samplerate=FS, channels=1)
    stream.start()

    current_signal_time = 0
    current_time = time.time()

    while True:

        # Returns a 2D numpy array as (frames, channels) containing
        # a column for every channel.
        frames, _ = stream.read(SAMPLE_SIZE)
        frames_np = np.array(frames)[:,0]

        freqs, results = goertzel(frames_np, FS, (697, 941), (1209, 1633))

        pair_low, pair_high = get_frequency_energy_pairs(freqs, results)

        f_low, energy_low = pair_low
        f_high, energy_high = pair_high

        closest_low = find_closest_freq(f_low, LOW, deviation=MAX_TONE_DEVIATION)
        closest_high = find_closest_freq(f_high, HIGH, deviation=MAX_TONE_DEVIATION)

        reached_energy_threshold = energy_low > MIN_LOW_F_ENERGY and energy_high > MIN_HIGH_F_ENERGY
        reached_signal_duration_threshold = current_signal_time >= MIN_SIGNAL_DURATION
        found_freq_pair = closest_low and closest_high

        if reached_energy_threshold and reached_signal_duration_threshold and found_freq_pair:
            pressed_key = KEYMAP[(closest_low, closest_high)]

            keypress_time = time.time()
            current_spaced_time = keypress_time - current_time

            if current_spaced_time >= SYMBOL_SPACING_DURATION:
                current_time = time.time()

                yield {
                    'pressed_key': pressed_key,
                    'f_low': f_low,
                    'closest_low': closest_low,
                    'energy_low': energy_low,
                    'f_high': f_high,
                    'closest_high': closest_high,
                    'energy_high': energy_high,
                    'frames': frames_np,
                    'freqs': freqs,
                    'results': results
                }

        if not reached_signal_duration_threshold and found_freq_pair:
            current_signal_time += SAMPLE_WINDOW
        else:
            current_signal_time = 0

        # Play the input signal through speakers
        # stream.write(frames)


if __name__ == '__main__':
    try:
        command = sys.argv[1]
    except IndexError:
        command = None

    live_plot = False
    enable_command_decoder = False

    if command == 'live-plot':
        live_plot = True

        matplotlib.use('TkAgg')

        plt.figure(figsize=(10, 6))

        # Get the current screen dimensions
        screen_width = plt.get_current_fig_manager().window.winfo_screenwidth()
        screen_height = plt.get_current_fig_manager().window.winfo_screenheight()

        # matplotlib window size
        window_width = 1000
        window_height = 600

        # Set the matplotlib window size and center it on screen
        plt.get_current_fig_manager().window.geometry(f'{window_width}x{window_height}')
        plt.get_current_fig_manager().window.wm_geometry(f'+{(screen_width - window_width) // 2}+{(screen_height - window_height) // 2}')

        # Set the window title
        plt.get_current_fig_manager().set_window_title('Dual-tone multi-frequency (DTMF) Decoder')

    elif command == 'command-decoder':
        enable_command_decoder = True

    if enable_command_decoder:
        command_decoder = CommandDecoder()
    else:
        clear_console()
        print(BANNER)
        print('     (keys) → ', end='', flush=True)

    for signal in decoded_signals():

        if enable_command_decoder:
            command_decoder.key(signal['pressed_key'])
        else:
            print('', end='', flush=True)
            print(signal['pressed_key'], end='', flush=True)

        if live_plot:
            plot_signal(signal)
