"""
Module: engine/audio.py
Description: Pengelola audio dan efek suara prosedural 8-bit untuk feedback UX tanpa file eksternal.
"""

import io
import math
import struct
import wave
from typing import Dict, Optional
import pygame


class AudioManager:
    """Mengelola pemutaran efek suara game dengan generator prosedural."""

    _instance: Optional["AudioManager"] = None

    def __init__(self) -> None:
        self.enabled: bool = True
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.initialized: bool = False

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.initialized = True
            self._generate_default_sounds()
        except Exception as e:
            print(f"[AudioManager] Peringatan: Audio device tidak tersedia ({e}). Game berjalan dalam mode senyap.")
            self.initialized = False

    @classmethod
    def get_instance(cls) -> "AudioManager":
        if cls._instance is None:
            cls._instance = AudioManager()
        return cls._instance

    def _create_wav_sound(self, samples_generator) -> Optional[pygame.mixer.Sound]:
        """Helper untuk mengonversi generator sampel amplitudo ke pygame.mixer.Sound."""
        sample_rate = 44100
        buf = io.BytesIO()
        try:
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                frames = bytearray()
                for val in samples_generator(sample_rate):
                    clipped = max(-32768, min(32767, int(val)))
                    frames.extend(struct.pack("<h", clipped))
                wf.writeframes(frames)
            buf.seek(0)
            return pygame.mixer.Sound(buf)
        except Exception:
            return None

    def _generate_default_sounds(self) -> None:
        """Membuat suara 8-bit retro sintetis (klik, hit, serang, sihir, menang, kalah, puzzle)."""
        # 1. UI Click: blip singkat
        def click_gen(sr):
            duration = 0.04
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                env = math.exp(-15.0 * t / duration)
                yield 32767.0 * 0.3 * env * math.sin(2.0 * math.pi * 950.0 * t)

        # 2. Attack: whoosh tajam
        def attack_gen(sr):
            duration = 0.12
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                freq = 700.0 - 500.0 * (t / duration)
                env = math.exp(-5.0 * t / duration)
                yield 32767.0 * 0.4 * env * math.sin(2.0 * math.pi * freq * t)

        # 3. Hit: dentuman rendah berisik
        def hit_gen(sr):
            duration = 0.18
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                freq = 240.0 - 180.0 * (t / duration)
                env = math.exp(-6.0 * t / duration)
                # Tambah sedikit noise
                noise = ((i % 11) - 5) / 5.0 * 0.15
                yield 32767.0 * 0.5 * env * (math.sin(2.0 * math.pi * freq * t) + noise)

        # 4. Magic: arpeggio lonceng magis
        def magic_gen(sr):
            duration = 0.28
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                note_idx = int(t * 16) % 4
                freqs = [600.0, 800.0, 1000.0, 1200.0]
                freq = freqs[note_idx]
                env = math.exp(-3.5 * t / duration)
                yield 32767.0 * 0.35 * env * math.sin(2.0 * math.pi * freq * t)

        # 5. Heal: nada lembut meninggi
        def heal_gen(sr):
            duration = 0.25
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                freq = 440.0 + 440.0 * (t / duration)
                env = math.exp(-3.0 * t / duration)
                yield 32767.0 * 0.35 * env * math.sin(2.0 * math.pi * freq * t)

        # 6. Victory Fanfare: chord kemenangan
        def victory_gen(sr):
            duration = 0.55
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                note_idx = min(3, int(t * 7))
                notes = [523.25, 659.25, 783.99, 1046.50]  # C5, E5, G5, C6
                freq = notes[note_idx]
                env = math.exp(-2.0 * t / duration)
                yield 32767.0 * 0.45 * env * math.sin(2.0 * math.pi * freq * t)

        # 7. Defeat: chord turun
        def defeat_gen(sr):
            duration = 0.55
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                note_idx = min(2, int(t * 5))
                notes = [392.0, 369.99, 329.63]  # G4, F#4, E4
                freq = notes[note_idx]
                env = math.exp(-2.5 * t / duration)
                yield 32767.0 * 0.45 * env * math.sin(2.0 * math.pi * freq * t)

        # 8. Puzzle Move: pop ringan
        def puzzle_gen(sr):
            duration = 0.06
            total = int(sr * duration)
            for i in range(total):
                t = i / sr
                env = math.exp(-10.0 * t / duration)
                yield 32767.0 * 0.25 * env * math.sin(2.0 * math.pi * 750.0 * t)

        generators = {
            "click": click_gen,
            "attack": attack_gen,
            "hit": hit_gen,
            "magic": magic_gen,
            "heal": heal_gen,
            "victory": victory_gen,
            "defeat": defeat_gen,
            "puzzle": puzzle_gen,
        }

        for name, gen in generators.items():
            snd = self._create_wav_sound(gen)
            if snd:
                self.sounds[name] = snd

    def play(self, sound_name: str) -> None:
        """Memutar suara sesuai nama jika audio aktif."""
        if not self.enabled or not self.initialized:
            return
        snd = self.sounds.get(sound_name)
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def toggle_sound(self) -> bool:
        """Mengaktifkan / mematikan suara (Mute)."""
        self.enabled = not self.enabled
        return self.enabled
