import os
import platform
import math
import numpy as np


def goertzel(samples, sample_rate, *freqs):

    """
    Implementation of the Goertzel algorithm, useful for calculating individual
    terms of a discrete Fourier transform.

    `samples` is a windowed one-dimensional signal originally sampled at `sample_rate`.

    The function returns 2 arrays, one containing the actual frequencies calculated,
    the second the coefficients `(real part, imag part, power)` for each of those frequencies.
    For simple spectral analysis, the power is usually enough.

    Example of usage :
        
        freqs, results = goertzel(some_samples, 44100, (400, 500), (1000, 1100))
    """

    window_size = len(samples)
    f_step = sample_rate / float(window_size)
    f_step_normalized = 1.0 / window_size

    # Calculate all the DFT bins we have to compute to include frequencies
    # in `freqs`.
    bins = set()
    for f_range in freqs:
        f_start, f_end = f_range
        k_start = int(math.floor(f_start / f_step))
        k_end = int(math.ceil(f_end / f_step))

        if k_end > window_size - 1: raise ValueError('frequency out of range %s' % k_end)
        bins = bins.union(range(k_start, k_end))

    # For all the bins, calculate the DFT term
    n_range = range(0, window_size)
    freqs = []
    results = []
    for k in bins:

        # Bin frequency and coefficients for the computation
        f = k * f_step_normalized
        w_real = 2.0 * math.cos(2.0 * math.pi * f)
        w_imag = math.sin(2.0 * math.pi * f)

        # Doing the calculation on the whole sample
        d1, d2 = 0.0, 0.0
        for n in n_range:
            y  = samples[n] + w_real * d1 - d2
            d2, d1 = d1, y

        # Storing results `(real part, imag part, power)`
        results.append((
            0.5 * w_real * d1 - d2, w_imag * d1,
            d2**2 + d1**2 - w_real * d1 * d2)
        )

        freqs.append(f * sample_rate)

    return freqs, results


def find_closest_freq(n, freqs, deviation=0):

    """
    Finds the closest frequency to <n> in a list of frequencies <freqs>
    with an optional deviation.
    """

    closest_normal = min(freqs, key=lambda f: abs(f - n))
    upper_deviation = closest_normal + deviation
    lower_deviation = closest_normal - deviation

    if n <= upper_deviation and n >= lower_deviation:
        return closest_normal
    else:
        return None


def get_frequency_energy_pairs(freqs, results):

    """
    Get the two frequencies with the highest energy from
    goertzel filtered results. This can then be used to determine
    the DTMF signal based on the lower and higher frequencies.

    More info:
     - https://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling#Keypad
    """

    np_results = np.array(results)[:,2]
    np_freqs = np.array(freqs)

    # Sort from lowest->highest frequency energy
    sorted_energies = np_results.argsort()

    # Get the two highest energy levels along with their associated frequency
    f1_energy = np_results[sorted_energies[-2]]
    f2_energy = np_results[sorted_energies[-1]]

    # Get the associated frequencies
    f1_idx = np.where(np_results == f1_energy)
    f2_idx = np.where(np_results == f2_energy)

    f1 = np_freqs[f1_idx][0]
    f2 = np_freqs[f2_idx][0]

    if f1 < f2:
        low = [f1, f1_energy]
        high = [f2, f2_energy]
    else:
        low = [f2, f2_energy]
        high = [f1, f1_energy]

    return low, high


def clear_console():

    """
    Clears the console based on the platform
    """

    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')
