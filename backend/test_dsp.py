"""Lightweight synthetic checks: run with `python -m unittest test_dsp.py`."""
import unittest
import numpy as np

from main import analyze_frame, estimate_f0_fft


class FFTPitchTests(unittest.TestCase):
    sr = 48000
    duration = 0.256

    def make_tone(self, f0: float, amplitudes: list[float]) -> np.ndarray:
        t = np.arange(int(self.sr * self.duration)) / self.sr
        signal = np.zeros_like(t)
        for harmonic, amplitude in enumerate(amplitudes, start=1):
            signal += amplitude * np.sin(2 * np.pi * f0 * harmonic * t)
        return 0.1 * signal

    def test_fundamental_with_harmonics(self):
        frame = self.make_tone(240.0, [1.0, 0.6, 0.35, 0.2])
        f0, rms, confidence, spectrum, waveform = estimate_f0_fft(frame, self.sr)
        self.assertIsNotNone(f0)
        self.assertLess(abs(f0 - 240.0), 2.0)
        self.assertGreater(rms, 0.01)
        self.assertGreater(confidence, 0.1)
        self.assertGreater(len(spectrum), 100)
        self.assertEqual(len(waveform), 160)

    def test_octave_normalization_for_missing_fundamental(self):
        # The fundamental is absent; the 2nd harmonic is the strongest component.
        frame = self.make_tone(240.0, [0.0, 0.9, 0.7, 0.4])
        result = analyze_frame(frame, self.sr, 240.0, 0, 25.0)
        self.assertTrue(result["voiced"])
        self.assertLess(abs(result["comparison_f0"] - 240.0), 3.0)
        self.assertLess(abs(result["error_cents"]), 25.0)

    def test_silence_is_not_reported_as_pitch(self):
        result = analyze_frame(np.zeros(int(self.sr * self.duration)), self.sr, 240.0, 0, 25.0)
        self.assertFalse(result["voiced"])
        self.assertIsNone(result["f0"])


if __name__ == "__main__":
    unittest.main()
