import importlib.util
from importlib.machinery import SourceFileLoader
import json
import pathlib
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_loader(
    "powerswitch", SourceFileLoader("powerswitch", "powerswitch")
)
mod = importlib.util.module_from_spec(SPEC)
sys.modules["powerswitch"] = mod
SPEC.loader.exec_module(mod)
class CpuUtilizationTests(unittest.TestCase):
    """Intent: derive normalized CPU capacity use from controlled procfs snapshots."""

    def test_parses_aggregate_cpu_and_counts_iowait_as_idle(self):
        snapshot = "cpu  100 10 30 400 20 5 5 0 0 0\ncpu0 1 2 3 4 5 6 7 8\n"

        self.assertEqual(mod.parse_cpu_times(snapshot), (570, 420))

    def test_computes_busy_fraction_between_two_snapshots(self):
        previous = (1000, 600)
        current = (1100, 620)

        self.assertAlmostEqual(mod.cpu_utilization(previous, current), 0.8)

    def test_rejects_snapshot_without_elapsed_cpu_time(self):
        self.assertIsNone(mod.cpu_utilization((1000, 600), (1000, 600)))

    def test_rejects_empty_proc_stat(self):
        with self.assertRaises(ValueError):
            mod.parse_cpu_times("")


class TrayIconTests(unittest.TestCase):
    def test_uses_gnome_icon_for_each_power_profile(self):
        self.assertEqual(mod.profile_icon("performance"), "power-profile-performance-symbolic")
        self.assertEqual(mod.profile_icon("balanced"), "power-profile-balanced-symbolic")
        self.assertEqual(mod.profile_icon("power-saver"), "power-profile-power-saver-symbolic")


class AutoPerformancePolicyTests(unittest.TestCase):
    """Intent: switch only after sustained load and keep time as an explicit input."""

    def test_enters_performance_after_five_consecutive_hot_samples(self):
        policy = mod.AutoPerformancePolicy()

        for sample_number in range(4):
            self.assertEqual(policy.observe(0.8, sample_number * 2), "balanced")
        self.assertEqual(policy.observe(0.8, 8), "performance")
        self.assertEqual(vars(policy), {
            "profile": "performance",
            "hot_samples": 0,
            "cool_samples": 0,
            "last_switch_at": 8,
        })

    def test_a_cool_sample_breaks_the_hot_streak(self):
        policy = mod.AutoPerformancePolicy()

        for now, utilization in enumerate((0.8, 0.8, 0.79, 0.8, 0.8, 0.8, 0.8)):
            self.assertEqual(policy.observe(utilization, now * 2), "balanced")
        self.assertEqual(policy.observe(0.8, 14), "performance")

    def test_returns_to_balanced_after_thirty_consecutive_cool_samples(self):
        policy = mod.AutoPerformancePolicy()
        for sample_number in range(5):
            policy.observe(0.8, sample_number * 2)

        for sample_number in range(29):
            self.assertEqual(policy.observe(0.35, 10 + sample_number * 2), "performance")
        self.assertEqual(policy.observe(0.35, 68), "balanced")

    def test_minimum_dwell_blocks_an_immediate_second_switch(self):
        policy = mod.AutoPerformancePolicy()
        for sample_number in range(5):
            policy.observe(0.8, sample_number * 2)
        for sample_number in range(30):
            policy.observe(0.35, 10 + sample_number * 2)

        for now in (70, 72, 74, 76, 78):
            self.assertEqual(policy.observe(0.9, now), "balanced")
        self.assertEqual(policy.observe(0.9, 128), "performance")

    def test_reset_samples_preserves_the_selected_profile(self):
        policy = mod.AutoPerformancePolicy()
        for sample_number in range(5):
            policy.observe(0.8, sample_number * 2)
        policy.observe(0.1, 10)

        policy.reset_samples()

        self.assertEqual(policy.profile, "performance")
        for sample_number in range(29):
            self.assertEqual(policy.observe(0.1, 12 + sample_number * 2), "performance")


class ManualOverrideTests(unittest.TestCase):
    """Intent: an unheld external profile change pauses AC automation for the session."""

    def test_unheld_external_change_pauses_auto_mode(self):
        self.assertTrue(mod.should_pause_auto(
            auto_enabled=True,
            on_battery=False,
            was_held=False,
            held=False,
            active="performance",
            requested="balanced",
        ))

    def test_own_write_and_hold_release_do_not_pause_auto_mode(self):
        common = {"auto_enabled": True, "on_battery": False, "held": False}
        self.assertFalse(mod.should_pause_auto(
            **common, was_held=False, active="performance", requested="performance"
        ))
        self.assertFalse(mod.should_pause_auto(
            **common, was_held=True, active="performance", requested="balanced"
        ))


class ConfigTests(unittest.TestCase):
    """Intent: accept the new boolean without breaking existing profile-only configs."""

    def setUp(self):
        self.original_config = mod.CONFIG
        self.temp_dir = tempfile.TemporaryDirectory()
        mod.CONFIG = pathlib.Path(self.temp_dir.name) / "powerswitch.json"

    def tearDown(self):
        mod.CONFIG = self.original_config
        self.temp_dir.cleanup()

    def write(self, value):
        mod.CONFIG.write_text(json.dumps(value))

    def test_existing_config_defaults_auto_mode_off(self):
        self.write({"ac": "performance", "battery": "balanced"})

        self.assertEqual(mod.load(), {
            "ac": "performance",
            "battery": "balanced",
            "auto_performance_ac": False,
        })

    def test_loads_boolean_auto_mode(self):
        self.write({"auto_performance_ac": True})

        self.assertEqual(mod.load(), {
            "ac": "balanced",
            "battery": "power-saver",
            "auto_performance_ac": True,
        })

    def test_rejects_string_auto_mode(self):
        self.write({"auto_performance_ac": "yes"})

        self.assertEqual(mod.load(), mod.DEFAULTS)


if __name__ == "__main__":
    unittest.main()
