# -*- coding: utf-8 -*-
"""
Unit tests for CLI Runner service.

These tests can run without QGIS by mocking the QSettings.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add plugin to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ggu-qgis-plugin"))


class TestCliRunner(unittest.TestCase):
    """Tests for CliRunner service."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock QSettings before importing
        self.mock_settings = MagicMock()
        self.settings_patcher = patch("services.cli_runner.QSettings", return_value=self.mock_settings)
        self.settings_patcher.start()

        from services.cli_runner import CliRunner
        self.runner = CliRunner()

    def tearDown(self):
        """Clean up."""
        self.settings_patcher.stop()

    def test_create_csv_file_basic(self):
        """Test CSV file creation with basic point data."""
        points = [
            {"name": "BH-1", "x": 357812.12, "y": 5812341.44},
            {"name": "BH-2", "x": 357813.00, "y": 5812342.00},
        ]

        csv_path = self.runner._create_csv_file(points)

        self.assertIsNotNone(csv_path)
        self.assertTrue(os.path.exists(csv_path))

        # Read and verify content
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("name\tx\ty", content)
        self.assertIn("BH-1", content)
        self.assertIn("357812.12", content)

        # Cleanup
        os.remove(csv_path)

    def test_create_csv_file_with_z(self):
        """Test CSV file creation with Z coordinates."""
        points = [
            {"name": "BH-1", "x": 357812.12, "y": 5812341.44, "z": 45.5},
        ]

        csv_path = self.runner._create_csv_file(points)

        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("name\tx\ty\tz", content)
        self.assertIn("45.5", content)

        os.remove(csv_path)

    @patch("subprocess.run")
    def test_open_in_stratig_builds_correct_command(self, mock_run):
        """Test that open_in_stratig builds correct CLI arguments."""
        # Configure mock
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        self.mock_settings.value.side_effect = lambda key, default="": {
            "ggu_qgis_tools/cli_path": "/path/to/cli.exe",
        }.get(key, default)

        # Call method
        success, msg = self.runner.open_in_stratig(
            location_ids=["guid-1", "guid-2"],
            project_id="project-guid",
            db_profile="test-profile",
        )

        # Verify subprocess was called with correct args
        self.assertTrue(success)
        call_args = mock_run.call_args[0][0]

        self.assertIn("export", call_args)
        self.assertIn("ggu-app", call_args)
        self.assertIn("--app", call_args)
        self.assertIn("stratig", call_args)
        self.assertIn("--mode", call_args)
        self.assertIn("open", call_args)
        self.assertIn("--filter-drilling-ids", call_args)
        self.assertIn("guid-1,guid-2", call_args)
        self.assertIn("--db-profile", call_args)
        self.assertIn("test-profile", call_args)


class TestCliRunnerIntegration(unittest.TestCase):
    """Integration tests that require actual CLI executable."""

    CLI_PATH = os.environ.get(
        "GGU_CLI_PATH",
        r"C:\Develop\Git-Repos-250814\apps-desktop\ggu-connect-cli\build\Win32\Debug\GGU.Apps.ConnectCLI.exe"
    )

    @unittest.skipUnless(os.path.exists(CLI_PATH), "CLI executable not found")
    def test_cli_version(self):
        """Test that CLI responds to version command."""
        import subprocess

        result = subprocess.run(
            [self.CLI_PATH, "version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("ggu-connect", result.stdout.lower())

    @unittest.skipUnless(os.path.exists(CLI_PATH), "CLI executable not found")
    def test_cli_profile_list(self):
        """Test that CLI can list profiles."""
        import subprocess

        result = subprocess.run(
            [self.CLI_PATH, "config", "profile", "list", "-f", "json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0)
        # Should return valid JSON (even if empty list)
        import json
        profiles = json.loads(result.stdout)
        self.assertIsInstance(profiles, list)


if __name__ == "__main__":
    unittest.main()
