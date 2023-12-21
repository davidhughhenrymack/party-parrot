#!/usr/bin/env python3

from pilots.demucs import Demucs

if __name__ == '__main__':
    audio = Demucs()
    while True:
        audio.listen()
