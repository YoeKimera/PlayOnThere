"""
Tests for PlayOnThere utility functions and core logic.

These tests cover the pure helper functions that can run without a display
or a real VLC/libvlc installation.
"""

import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers imported directly from the module
# ---------------------------------------------------------------------------
import sys
import os

# Ensure the project root is on the path when tests are run from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playonthere import format_time, build_screen_list, enumerate_audio_outputs


# ---------------------------------------------------------------------------
# format_time
# ---------------------------------------------------------------------------

class TestFormatTime(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(format_time(0), "0:00")

    def test_negative(self):
        self.assertEqual(format_time(-1), "0:00")

    def test_seconds(self):
        self.assertEqual(format_time(7000), "0:07")

    def test_one_minute(self):
        self.assertEqual(format_time(60_000), "1:00")

    def test_mixed(self):
        self.assertEqual(format_time(187_000), "3:07")

    def test_large(self):
        # 1 h 2 min 3 s  →  3723 s  → 62 min 3 s
        self.assertEqual(format_time(3_723_000), "62:03")


# ---------------------------------------------------------------------------
# build_screen_list
# ---------------------------------------------------------------------------

class TestBuildScreenList(unittest.TestCase):
    def _make_monitor(self, name, x, y, width, height):
        m = MagicMock()
        m.name = name
        m.x = x
        m.y = y
        m.width = width
        m.height = height
        return m

    def test_single_primary_screen(self):
        monitors = [self._make_monitor("HDMI-1", 0, 0, 1920, 1080)]
        screens = build_screen_list(monitors)
        self.assertEqual(len(screens), 1)
        self.assertIn("1920×1080", screens[0]["label"])
        self.assertEqual(screens[0]["x"], 0)
        self.assertEqual(screens[0]["y"], 0)
        self.assertEqual(screens[0]["width"], 1920)
        self.assertEqual(screens[0]["height"], 1080)

    def test_two_screens(self):
        monitors = [
            self._make_monitor("eDP-1", 0, 0, 1920, 1080),
            self._make_monitor("HDMI-1", 1920, 0, 2560, 1440),
        ]
        screens = build_screen_list(monitors)
        self.assertEqual(len(screens), 2)
        self.assertIn("HDMI-1", screens[1]["label"])
        self.assertEqual(screens[1]["x"], 1920)

    def test_monitor_without_name_gets_fallback(self):
        m = MagicMock()
        m.name = None
        m.x, m.y, m.width, m.height = 0, 0, 800, 600
        screens = build_screen_list([m])
        self.assertIn("Pantalla 1", screens[0]["label"])

    def test_empty_monitor_list(self):
        screens = build_screen_list([])
        self.assertEqual(screens, [])


# ---------------------------------------------------------------------------
# enumerate_audio_outputs
# ---------------------------------------------------------------------------

class TestEnumerateAudioOutputs(unittest.TestCase):
    def _vlc_instance_no_devices(self):
        inst = MagicMock()
        inst.audio_output_list_get.return_value = []
        return inst

    def _make_ao(self, name, description):
        ao = MagicMock()
        ao.name = name.encode() if isinstance(name, str) else name
        ao.description = description.encode() if isinstance(description, str) else description
        return ao

    def _make_device(self, device_id, description):
        dev = MagicMock()
        dev.device = device_id.encode() if isinstance(device_id, str) else device_id
        dev.description = description.encode() if isinstance(description, str) else description
        return dev

    def test_always_returns_default_entry(self):
        inst = self._vlc_instance_no_devices()
        outputs = enumerate_audio_outputs(inst)
        self.assertGreaterEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["label"], "Predeterminado")
        self.assertIsNone(outputs[0]["module"])
        self.assertIsNone(outputs[0]["device"])

    def test_empty_ao_list_returns_only_default(self):
        inst = self._vlc_instance_no_devices()
        outputs = enumerate_audio_outputs(inst)
        self.assertEqual(len(outputs), 1)

    def test_ao_without_devices(self):
        inst = MagicMock()
        ao = self._make_ao("pulse", "PulseAudio")
        inst.audio_output_list_get.return_value = [ao]
        inst.audio_output_device_list_get.return_value = None
        outputs = enumerate_audio_outputs(inst)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[1]["label"], "PulseAudio")
        self.assertEqual(outputs[1]["module"], "pulse")
        self.assertIsNone(outputs[1]["device"])

    def test_ao_with_devices(self):
        inst = MagicMock()
        ao = self._make_ao("pulse", "PulseAudio")
        inst.audio_output_list_get.return_value = [ao]
        dev = self._make_device("hw:0,0", "Built-in Audio")
        inst.audio_output_device_list_get.return_value = [dev]
        outputs = enumerate_audio_outputs(inst)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[1]["label"], "Built-in Audio")
        self.assertEqual(outputs[1]["module"], "pulse")
        self.assertEqual(outputs[1]["device"], "hw:0,0")

    def test_exception_returns_default_only(self):
        inst = MagicMock()
        inst.audio_output_list_get.side_effect = RuntimeError("libvlc error")
        outputs = enumerate_audio_outputs(inst)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs[0]["label"], "Predeterminado")


if __name__ == "__main__":
    unittest.main()
