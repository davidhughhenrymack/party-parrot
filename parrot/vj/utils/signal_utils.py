#!/usr/bin/env python3

import random
from beartype import beartype
from parrot.director.frame import FrameSignal


@beartype
def get_random_frame_signal() -> FrameSignal:
    """
    Returns a randomly selected FrameSignal with weighted probabilities.

    Frequency signals (freq_all, freq_high, freq_low) are weighted 3x higher
    than other signals to favor audio-reactive behavior.

    This utility function provides a centralized way for VJ effects to
    randomly select which Frame signal to listen to during their generate() method.

    Returns:
        A randomly chosen FrameSignal enum value
    """
    available_signals = [
        FrameSignal.freq_all,
        FrameSignal.freq_high,
        FrameSignal.freq_low,
        FrameSignal.sustained_low,
        FrameSignal.sustained_high,
        FrameSignal.strobe,
        FrameSignal.big_blinder,
        FrameSignal.small_blinder,
        FrameSignal.pulse,
    ]
    weights = [
        3,  # freq_all
        3,  # freq_high
        3,  # freq_low
        2,  # sustained_low
        2,  # sustained_high
        1,  # strobe
        1,  # big_blinder
        1,  # small_blinder
        1,  # pulse
    ]
    return random.choices(available_signals, weights=weights, k=1)[0]
