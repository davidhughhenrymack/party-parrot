#!/usr/bin/env python3

import random
from beartype import beartype
from parrot.director.frame import FrameSignal


@beartype
def get_random_frame_signal() -> FrameSignal:
    """
    Returns a randomly selected FrameSignal from all available signals.

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
        FrameSignal.dampen,
    ]
    return random.choice(available_signals)
