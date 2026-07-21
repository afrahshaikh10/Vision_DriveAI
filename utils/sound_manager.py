import os
import math
import numpy as np
import pygame
from utils.logger import logger

class SoundManager:
    """Arcade sound effects and engine audio manager powered by Pygame mixer,
    featuring warm low-frequency V8 engine audio, smooth envelopes, and soft-clipped arcade effects."""
    
    def __init__(self):
        self.initialized = False
        self.muted = False
        self.volume = 0.25  # Smooth, pleasant default volume
        self.sounds = {}
        self.engine_channel = None
        self.screech_channel = None

        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
            self.initialized = True
            logger.info("Pygame Mixer initialized successfully.")
            self._generate_arcade_sounds()
        except Exception as e:
            logger.warning(f"Pygame Mixer init skipped or failed: {e}")
            self.initialized = False

    def _lowpass_filter(self, data: np.ndarray, alpha: float = 0.15) -> np.ndarray:
        """Applies a simple single-pole IIR lowpass filter to eliminate harsh high-frequency noise."""
        filtered = np.zeros_like(data)
        prev = 0.0
        for i in range(len(data)):
            prev = prev + alpha * (data[i] - prev)
            filtered[i] = prev
        return filtered

    def _make_sound_from_array(self, arr: np.ndarray) -> pygame.mixer.Sound:
        """Converts floating point numpy audio buffer [-1, 1] to a 16-bit Pygame Sound."""
        arr = np.clip(arr, -1.0, 1.0)
        arr_int16 = (arr * 32767).astype(np.int16)
        stereo = np.column_stack((arr_int16, arr_int16))
        return pygame.mixer.Sound(stereo)

    def _generate_arcade_sounds(self) -> None:
        if not self.initialized:
            return
        try:
            sample_rate = 44100

            # 1. Warm V8 Engine Low-Frequency Rumble Loop (0.6 seconds seamless loop)
            dur_eng = 0.6
            t = np.linspace(0, dur_eng, int(sample_rate * dur_eng), False)
            # Low fundamental frequency (55Hz sub-rumble + 110Hz + 165Hz harmonics)
            sub_rumble = 0.5 * np.sin(2 * np.pi * 55 * t)
            mid_thrum = 0.3 * np.sin(2 * np.pi * 110 * t)
            top_harmonic = 0.15 * np.sin(2 * np.pi * 165 * t)
            raw_engine = sub_rumble + mid_thrum + top_harmonic
            
            # Filter out harsh highs
            smooth_engine = self._lowpass_filter(raw_engine, alpha=0.12)
            self.sounds["engine"] = self._make_sound_from_array(smooth_engine)

            # 2. Smooth Nitro WHOOSH Sweep (0.6 seconds soft jet sweep)
            dur_nitro = 0.6
            tn = np.linspace(0, dur_nitro, int(sample_rate * dur_nitro), False)
            envelope = np.sin(np.pi * tn / dur_nitro) ** 2
            sweep_freq = 200 + 400 * (tn / dur_nitro)
            synth_wave = np.sin(2 * np.pi * sweep_freq * tn)
            noise_subtle = self._lowpass_filter(np.random.normal(0, 0.25, len(tn)), alpha=0.10)
            nitro_wave = envelope * (0.5 * synth_wave + 0.5 * noise_subtle)
            self.sounds["nitro"] = self._make_sound_from_array(nitro_wave)

            # 3. Soft Tire Friction Screech (0.35 seconds)
            dur_scr = 0.35
            ts = np.linspace(0, dur_scr, int(sample_rate * dur_scr), False)
            env_scr = np.sin(np.pi * ts / dur_scr)
            scr_noise = self._lowpass_filter(np.random.normal(0, 0.3, len(ts)), alpha=0.20)
            screech_wave = env_scr * scr_noise * 0.7
            self.sounds["screech"] = self._make_sound_from_array(screech_wave)

            # 4. Deep Crash Thud & Bass Impact (0.6 seconds)
            dur_cr = 0.6
            tc = np.linspace(0, dur_cr, int(sample_rate * dur_cr), False)
            env_cr = np.exp(-6 * tc)
            thud = np.sin(2 * np.pi * (65 - 40 * tc) * tc)
            body_boom = self._lowpass_filter(np.random.normal(0, 0.5, len(tc)), alpha=0.10)
            crash_wave = env_cr * (0.6 * thud + 0.4 * body_boom)
            self.sounds["crash"] = self._make_sound_from_array(crash_wave)

            # 5. Pleasant Arcade Dodge Chime (Pentatonic 523Hz -> 659Hz double beep)
            dur_ch = 0.25
            tch = np.linspace(0, dur_ch, int(sample_rate * dur_ch), False)
            chime_wave = np.zeros_like(tch)
            mid_p = len(tch) // 2
            chime_wave[:mid_p] = np.sin(2 * np.pi * 523.25 * tch[:mid_p]) * np.sin(np.pi * tch[:mid_p] / (dur_ch/2))
            chime_wave[mid_p:] = np.sin(2 * np.pi * 659.25 * tch[mid_p:]) * np.sin(np.pi * (tch[mid_p:] - dur_ch/2) / (dur_ch/2))
            self.sounds["dodge"] = self._make_sound_from_array(chime_wave * 0.4)

            self.engine_channel = pygame.mixer.Channel(0)
            self.screech_channel = pygame.mixer.Channel(1)

        except Exception as e:
            logger.warning(f"Failed to synthesize arcade sound effects: {e}")

    def play_nitro(self) -> None:
        if self.initialized and not self.muted and "nitro" in self.sounds:
            snd = self.sounds["nitro"]
            snd.set_volume(self.volume * 0.8)
            snd.play()

    def play_screech(self) -> None:
        if self.initialized and not self.muted and "screech" in self.sounds:
            if not self.screech_channel or not self.screech_channel.get_busy():
                snd = self.sounds["screech"]
                snd.set_volume(self.volume * 0.5)
                if self.screech_channel:
                    self.screech_channel.play(snd)
                else:
                    snd.play()

    def play_crash(self) -> None:
        if self.initialized and not self.muted and "crash" in self.sounds:
            if self.engine_channel:
                self.engine_channel.stop()
            snd = self.sounds["crash"]
            snd.set_volume(self.volume * 1.0)
            snd.play()

    def play_dodge(self) -> None:
        if self.initialized and not self.muted and "dodge" in self.sounds:
            snd = self.sounds["dodge"]
            snd.set_volume(self.volume * 0.6)
            snd.play()

    def update_engine_sound(self, speed_mph: float, is_accelerating: bool) -> None:
        if not self.initialized or self.muted or "engine" not in self.sounds:
            return

        if speed_mph > 2.0:
            if self.engine_channel and not self.engine_channel.get_busy():
                self.engine_channel.play(self.sounds["engine"], loops=-1)
            target_vol = min(0.6, 0.10 + (speed_mph / 140.0) * 0.35) * self.volume
            if self.engine_channel:
                self.engine_channel.set_volume(target_vol)
        else:
            if self.engine_channel and self.engine_channel.get_busy():
                self.engine_channel.stop()

    def stop_all(self) -> None:
        if self.initialized:
            pygame.mixer.stop()

    def set_muted(self, muted: bool) -> None:
        self.muted = muted
        if muted:
            self.stop_all()

    def toggle_mute(self) -> bool:
        self.set_muted(not self.muted)
        return self.muted

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))

sound_manager = SoundManager()
