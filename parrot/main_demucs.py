#!/usr/bin/env python3

from listeners.demucs import Demucs

if __name__ == "__main__":
    audio = Demucs()
    while True:
        audio.listen()
