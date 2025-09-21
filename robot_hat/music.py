"""
A module for playing music, sound effects, and controlling musical notes.

- Play sound effects and music files.
- Generate and play musical notes.
- Control musical parameters like tempo, time signature, and key signature.

"""

import logging
import math
import os
import sys
import threading
import time
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, List, Optional, Tuple, Union

_log = logging.getLogger(__name__)


@dataclass(init=False)
class Music:
    """
    A class for playing music, sound effects, and controlling musical notes.

    Example:

    ```python
    # Initialize the Music class
    music = Music()

    # Play a sound effect
    music.sound_play("path_to_sound.wav")

    # Set and get tempo
    music.tempo(120)
    ```
    """

    _time_signature: Tuple[int, int] = field(init=False, repr=False)
    _tempo: Tuple[float, float] = field(init=False, repr=False)
    _key_signature: int = field(init=False, repr=False)
    beat_unit: float = field(init=False, repr=False)

    CHANNELS: ClassVar[int] = 1
    RATE: ClassVar[int] = 44100

    KEY_G_MAJOR: ClassVar[int] = 1
    KEY_D_MAJOR: ClassVar[int] = 2
    KEY_A_MAJOR: ClassVar[int] = 3
    KEY_E_MAJOR: ClassVar[int] = 4
    KEY_B_MAJOR: ClassVar[int] = 5
    KEY_F_SHARP_MAJOR: ClassVar[int] = 6
    KEY_C_SHARP_MAJOR: ClassVar[int] = 7

    KEY_F_MAJOR: ClassVar[int] = -1
    KEY_B_FLAT_MAJOR: ClassVar[int] = -2
    KEY_E_FLAT_MAJOR: ClassVar[int] = -3
    KEY_A_FLAT_MAJOR: ClassVar[int] = -4
    KEY_D_FLAT_MAJOR: ClassVar[int] = -5
    KEY_G_FLAT_MAJOR: ClassVar[int] = -6
    KEY_C_FLAT_MAJOR: ClassVar[int] = -7

    KEY_SIGNATURE_SHARP: ClassVar[int] = 1
    KEY_SIGNATURE_FLAT: ClassVar[int] = -1

    WHOLE_NOTE: ClassVar[float] = 1.0
    HALF_NOTE: ClassVar[float] = 1.0 / 2.0
    QUARTER_NOTE: ClassVar[float] = 1.0 / 4.0
    EIGHTH_NOTE: ClassVar[float] = 1.0 / 8.0
    SIXTEENTH_NOTE: ClassVar[float] = 1.0 / 16.0

    NOTE_BASE_FREQ: ClassVar[float] = 440.0
    NOTE_BASE_INDEX: ClassVar[int] = 69

    NOTES: ClassVar[List[Optional[str]]] = [
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "A0",
        "A#0",
        "B0",
        "C1",
        "C#1",
        "D1",
        "D#1",
        "E1",
        "F1",
        "F#1",
        "G1",
        "G#1",
        "A1",
        "A#1",
        "B1",
        "C2",
        "C#2",
        "D2",
        "D#2",
        "E2",
        "F2",
        "F#2",
        "G2",
        "G#2",
        "A2",
        "A#2",
        "B2",
        "C3",
        "C#3",
        "D3",
        "D#3",
        "E3",
        "F3",
        "F#3",
        "G3",
        "G#3",
        "A3",
        "A#3",
        "B3",
        "C4",
        "C#4",
        "D4",
        "D#4",
        "E4",
        "F4",
        "F#4",
        "G4",
        "G#4",
        "A4",
        "A#4",
        "B4",
        "C5",
        "C#5",
        "D5",
        "D#5",
        "E5",
        "F5",
        "F#5",
        "G5",
        "G#5",
        "A5",
        "A#5",
        "B5",
        "C6",
        "C#6",
        "D6",
        "D#6",
        "E6",
        "F6",
        "F#6",
        "G6",
        "G#6",
        "A6",
        "A#6",
        "B6",
        "C7",
        "C#7",
        "D7",
        "D#7",
        "E7",
        "F7",
        "F#7",
        "G7",
        "G#7",
        "A7",
        "A#7",
        "B7",
        "C8",
    ]

    def __init__(self) -> None:
        """Initialize pygame (if available) and set defaults."""
        original_stdout = sys.stdout
        try:
            sys.stdout = open(os.devnull, "w")
            import pygame
        finally:
            sys.stdout.close()
            sys.stdout = original_stdout
        self.pygame = pygame

        self.time_signature(4, 4)

        self.tempo(120.0, self.QUARTER_NOTE)
        self.key_signature(0)

    def _pygame_mixer_ensure(self) -> None:
        """
        Ensures the pygame mixer is initialized properly.

        This method reinitializes the mixer in case it is not already initialized,
        to avoid errors during playback operations.
        """

        try:
            if not self.pygame.mixer.get_init():
                self.pygame.mixer.init()
        except self.pygame.error as err:
            _log.error("Failed to initialize pygame mixer: %s", err)
            raise

    def time_signature(
        self, top: Optional[int] = None, bottom: Optional[int] = None
    ) -> Tuple[int, int]:
        """
        Get or set time signature.
        If both top and bottom are None, returns the current (top, bottom).
        If bottom is None when setting, bottom is set equal to top.
        """
        if top is None and bottom is None:
            return self._time_signature
        if top is None:
            raise TypeError("top must be provided when setting time_signature")
        if bottom is None:
            bottom = top
        if not (isinstance(top, int) and isinstance(bottom, int)):
            raise TypeError("time signature components must be integers")
        if top <= 0 or bottom <= 0:
            raise ValueError("time signature components must be positive")
        self._time_signature = (top, bottom)
        return self._time_signature

    def key_signature(self, key: Optional[Union[int, str]] = None) -> int:
        """
        Get or set key signature.

        Accepts integers or strings composed solely of '#' or 'b' characters
        to represent the number of sharps or flats respectively.
        """
        if key is None:
            return self._key_signature
        if isinstance(key, str):
            if all(c == "#" for c in key):
                key = len(key) * self.KEY_SIGNATURE_SHARP
            elif all(c == "b" for c in key):
                key = len(key) * self.KEY_SIGNATURE_FLAT
            else:
                raise ValueError(
                    "key string must consist solely of '#' or 'b' characters"
                )
        if not isinstance(key, int):
            raise TypeError("key signature must be int or string of '#'/'b'")
        self._key_signature = key
        return self._key_signature

    def tempo(
        self, tempo: Optional[float] = None, note_value: float = QUARTER_NOTE
    ) -> Tuple[float, float]:
        """
        Get or set tempo.

        - If tempo is None: return current (bpm, note_value).
        - When setting: tempo must be positive and note_value must be positive.
        """
        if tempo is None:
            return self._tempo

        try:
            tempo_f = float(tempo)
        except (TypeError, ValueError):
            raise TypeError("tempo must be a real number")
        if tempo_f <= 0:
            raise ValueError("tempo must be positive")

        try:
            note_value_f = float(note_value)
        except (TypeError, ValueError):
            raise TypeError("note_value must be a positive real number")
        if note_value_f <= 0:
            raise ValueError("note_value must be positive")

        self._tempo = (tempo_f, note_value_f)
        self.beat_unit = 60.0 / tempo_f
        return self._tempo

    def beat(self, beat: float) -> float:
        """
        Convert beats (can be fractional) into seconds using current tempo.
        """
        try:
            beat_f = float(beat)
        except (TypeError, ValueError):
            raise TypeError("beat must be a real number")

        bpm_note_value = self._tempo[1]
        if bpm_note_value == 0:
            raise ZeroDivisionError("tempo note value is zero")
        seconds = beat_f / bpm_note_value * self.beat_unit
        return seconds

    def note(self, note: Union[str, int], natural: bool = False) -> float:
        """
        Return frequency (Hz) for a given note.

        If note is a string, it must be one of Music.NOTES.
        If natural is False, the current key signature is applied as an integer offset.
        """
        if isinstance(note, str):
            if note not in self.NOTES:
                raise ValueError(f"Note {note} not found, note must be in Music.NOTES")
            index = self.NOTES.index(note)
        elif isinstance(note, int):
            index = int(note)
        else:
            raise TypeError("note must be a string or integer index")

        if not natural:
            offset = self.key_signature()
            index = index + offset
            index = max(0, min(index, len(self.NOTES) - 1))

        delta = index - self.NOTE_BASE_INDEX
        freq = float(self.NOTE_BASE_FREQ) * (2.0 ** (delta / 12.0))
        return freq

    def _ensure_pygame(self) -> None:
        if self.pygame is None:
            raise RuntimeError("pygame is not available or failed to initialize")

    def sound_play(
        self, filename: Union[str, os.PathLike, Path], volume: Optional[float] = None
    ) -> None:
        """
        Play a short sound effect synchronously (blocks for sound length).
        volume: 0-100 scale when provided.
        """
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        sound = self.pygame.mixer.Sound(str(filename))
        if volume is not None:
            try:
                vol_f = float(volume)
            except (TypeError, ValueError):
                raise TypeError("volume must be a number between 0 and 100")
            vol = max(0.0, min(100.0, vol_f))
            sound.set_volume(round(vol / 100.0, 2))
        time_delay = round(sound.get_length(), 2)
        sound.play()
        time.sleep(time_delay)

    def sound_play_threading(
        self, filename: Union[str, os.PathLike, Path], volume: Optional[float] = None
    ) -> None:
        """
        Play a sound effect asynchronously in a daemon thread.
        """
        thread = threading.Thread(
            target=self.sound_play, kwargs={"filename": filename, "volume": volume}
        )
        thread.daemon = True
        thread.start()

    def music_play(
        self,
        filename: Union[str, os.PathLike, Path],
        loops: int = 1,
        start: float = 0.0,
        volume: Optional[float] = None,
    ) -> None:
        """
        Play a music file. Non-blocking.

        loops: number of times to play (1 = play once, 0 = loop forever in pygame's API).
        start: start position in seconds.
        volume: 0-100 scale (optional).
        """
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        if volume is not None:
            self.music_set_volume(volume)
        self.pygame.mixer.music.load(str(filename))
        self.pygame.mixer.music.play(loops, float(start))

    def music_get_volume(self) -> float:
        """Get the music volume level (0-100)."""
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        value = round(self.pygame.mixer.music.get_volume() * 100.0, 2)
        return float(value)

    def music_set_volume(self, value: float) -> None:
        """Set the music volume in 0-100 scale."""
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        try:
            vol_f = float(value)
        except (TypeError, ValueError):
            raise TypeError("volume must be a number between 0 and 100")
        vol = max(0.0, min(100.0, vol_f))
        self.pygame.mixer.music.set_volume(round(vol / 100.0, 2))

    def music_stop(self) -> None:
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        self.pygame.mixer.music.stop()

    def music_pause(self) -> None:
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        self.pygame.mixer.music.pause()

    def music_resume(self) -> None:
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        self.pygame.mixer.music.unpause()

    def music_unpause(self) -> None:
        self.music_resume()

    def sound_length(self, filename: Union[str, os.PathLike, Path]) -> float:
        self._ensure_pygame()
        self._pygame_mixer_ensure()
        s = self.pygame.mixer.Sound(str(filename))
        return round(s.get_length(), 2)

    def get_tone_data(self, freq: float, duration: float) -> bytes:
        """
        Generate raw PCM tone data for the given frequency and duration.

        Uses array('h').tobytes() for efficient packing. Ensures little-endian
        output by calling byteswap() on big-endian hosts.
        """
        try:
            freq_f = float(freq)
        except (TypeError, ValueError):
            raise TypeError("Frequency must be a real number")
        if freq_f <= 0:
            raise ValueError("Frequency must be a positive number")

        try:
            duration_f = float(duration)
        except (TypeError, ValueError):
            raise TypeError("Duration must be a real number")
        if duration_f <= 0:
            raise ValueError("Duration must be a positive number")

        frame_count = int(self.RATE * duration_f)

        remainder_frames = frame_count % self.RATE
        wavedata: List[int] = []

        for i in range(frame_count):
            a = self.RATE / freq_f
            b = i / a
            c = b * (2.0 * math.pi)
            d = math.sin(c) * 32767.0
            e = int(d)
            wavedata.append(e)

        for _ in range(remainder_frames):
            wavedata.append(0)

        arr = array("h", wavedata)
        if sys.byteorder != "little":
            arr.byteswap()
        return arr.tobytes()


if __name__ == "__main__":
    import argparse
    import os

    EXAMPLES = """Examples:
    # Play once, wait until finished (default)
    python -m robot_hat.music my_track.mp3

    # Play once with volume 60 (0-100) and wait
    python -m robot_hat.music my_track.mp3 --volume 60

    # Play starting at 30 seconds, do not wait (process will exit and playback will stop)
    python -m robot_hat.music my_track.mp3 --start 30 --no-wait

    # Loop forever
    python -m robot_hat.music my_track.mp3 --loops -1 --wait

    # Just print the track length (seconds) and exit
    python -m robot_hat.music my_track.mp3 --length
    """

    parser = argparse.ArgumentParser(
        description="Play music files",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Absolute, relative or abbreviated (e.g., ~/my-track.mp3) path to music file (mp3, wav, etc.)",
    )
    parser.add_argument(
        "--loops",
        type=int,
        default=0,
        help="Number of extra loops: 0 plays once, 1 plays twice, -1 loops forever (pygame convention).",
    )
    parser.add_argument(
        "--start", type=float, default=0.0, help="Start position in seconds (float)."
    )
    parser.add_argument(
        "--volume",
        type=float,
        default=None,
        help="Music volume 0-100 (optional). If omitted, current volume is used.",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Do not wait for playback to finish (process will exit immediately). Note: if the process exits, playback will usually stop).",
    )
    parser.add_argument(
        "--length",
        action="store_true",
        help="Print the file length (in seconds) and exit without playing.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (use -v or -vv).",
    )

    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose == 1:
        log_level = logging.INFO
    logging.basicConfig(level=log_level)

    if not args.file:
        parser.print_help()
        sys.exit(1)

    track = (
        os.path.expanduser(args.file)
        if args.file.startswith("~") and not os.path.exists(args.file)
        else args.file
    )

    music = Music()

    if args.length:
        try:
            dur = music.sound_length(track)
            print(f"{dur:.2f}")
        except Exception as e:
            _log.error("Failed to read length of %s: %s", track, e)
            sys.exit(2)
        sys.exit(0)

    if args.volume is not None:
        try:
            music.music_set_volume(args.volume)
        except Exception as e:
            _log.error("Failed to set volume: %s", e)

    try:
        music.music_play(track, loops=args.loops, start=args.start, volume=None)
    except Exception as e:
        _log.error("Failed to play %s: %s", track, e)
        sys.exit(3)

    if not args.no_wait:
        try:
            while music.pygame.mixer.music.get_busy():
                time.sleep(0.1)
        except KeyboardInterrupt:
            _log.info("Interrupted, stopping playback")
            music.music_stop()
            sys.exit(0)
