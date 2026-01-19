# -*- coding: utf-8 -*-
"""
CLI Runner Service

Handles execution of GGU-CONNECT CLI commands via subprocess.
All business logic remains in the CLI - this service only handles:
- Building command arguments
- Creating temporary files for data transfer
- Executing the CLI and capturing output
- Error handling and reporting
"""

import csv
import os
import subprocess
import tempfile
from typing import List, Dict, Tuple, Optional

from qgis.PyQt.QtCore import QSettings


class CliRunner:
    """Executes GGU-CONNECT CLI commands."""

    def __init__(self):
        """Initialize the CLI runner."""
        self.settings = QSettings()

    def _get_cli_path(self) -> str:
        """Get the configured CLI executable path."""
        return self.settings.value("ggu_qgis_tools/cli_path", "")

    def _run_command(self, args: List[str]) -> Tuple[bool, str]:
        """Run a CLI command and return result.

        Args:
            args: Command arguments (without the executable path)

        Returns:
            Tuple of (success: bool, message: str)
        """
        cli_path = self._get_cli_path()
        if not cli_path:
            return False, "CLI path not configured"

        if not os.path.exists(cli_path):
            return False, f"CLI executable not found: {cli_path}"

        full_command = [cli_path] + args

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout or f"Exit code: {result.returncode}"
                return False, error_msg

        except subprocess.TimeoutExpired:
            return False, "Command timed out after 5 minutes"
        except FileNotFoundError:
            return False, f"CLI executable not found: {cli_path}"
        except Exception as e:
            return False, f"Error running CLI: {str(e)}"

    def open_in_stratig(
        self,
        location_ids: List[str],
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Open boreholes in GGU-STRATIG.

        Uses the CLI command:
        ggu-connect export ggu-app --app stratig --mode open
            --project <project_id> --filter-drilling-ids <ids>
            --db-profile <profile> --output <temp_dir>

        Args:
            location_ids: List of borehole LocationID GUIDs
            project_id: Project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not location_ids:
            return False, "No boreholes specified"

        if not project_id:
            return False, "Project ID is required"

        # Create temp directory for output (required by CLI even in open mode)
        temp_dir = tempfile.mkdtemp(prefix="ggu_qgis_")

        # Build command arguments
        args = [
            "export", "ggu-app",
            "--app", "stratig",
            "--mode", "open",
            "--project", project_id,
            "--filter-drilling-ids", ",".join(location_ids),
            "--output", temp_dir,
        ]

        if db_profile:
            args.extend(["--db-profile", db_profile])

        return self._run_command(args)

    def create_drillings(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Create new drillings (boreholes or soundings) from points.

        Uses the CLI command:
        ggu-connect import coordinates --input <csv_file>
            --project <project_id> --db-profile <profile>
            --col-name 0 --col-x 1 --col-y 2 [--col-z 3] --start-row 2

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole' or 'cpt')
            project_id: Target project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not points:
            return False, "No points specified"

        if not project_id:
            return False, "Project ID is required"

        # Create CSV file with point data
        csv_path = self._create_csv_file(points)
        if not csv_path:
            return False, "Failed to create temporary CSV file"

        try:
            # Determine if we have Z coordinates
            has_z = any(p.get("z") is not None for p in points)

            # Get EPSG code from first point (all should be same CRS)
            crs = points[0].get("crs", "EPSG:25832")
            epsg_code = crs.replace("EPSG:", "") if crs.startswith("EPSG:") else "25832"

            # Build command arguments
            args = [
                "import", "coordinates",
                "--input", csv_path,
                "--project", project_id,
                "--col-name", "0",
                "--col-x", "1",
                "--col-y", "2",
                "--start-row", "2",  # Skip header row
                "--epsg", epsg_code,
            ]

            if has_z:
                args.extend(["--col-z", "3"])

            if db_profile:
                args.extend(["--db-profile", db_profile])

            # TODO: Add drilling type parameter when CLI supports it
            # Currently the CLI creates boreholes by default
            # args.extend(["--type", drilling_type])

            return self._run_command(args)

        finally:
            # Clean up temp file
            try:
                os.remove(csv_path)
            except OSError:
                pass

    def _create_csv_file(self, points: List[Dict]) -> Optional[str]:
        """Create a temporary CSV file with point data.

        Args:
            points: List of dicts with keys: name, x, y, z (optional)

        Returns:
            Path to the created CSV file, or None on error
        """
        try:
            # Create temp file
            fd, csv_path = tempfile.mkstemp(suffix=".csv", prefix="ggu_points_")

            has_z = any(p.get("z") is not None for p in points)

            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                if has_z:
                    fieldnames = ["name", "x", "y", "z"]
                else:
                    fieldnames = ["name", "x", "y"]

                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
                writer.writeheader()

                for point in points:
                    row = {
                        "name": point.get("name", ""),
                        "x": point["x"],
                        "y": point["y"],
                    }
                    if has_z:
                        row["z"] = point.get("z", "")
                    writer.writerow(row)

            return csv_path

        except Exception:
            return None

    def get_available_profiles(self) -> Tuple[bool, List[str]]:
        """Get list of available database profiles from CLI.

        Returns:
            Tuple of (success: bool, profiles: List[str])
        """
        success, output = self._run_command(["config", "profile", "list", "-f", "json"])

        if not success:
            return False, []

        try:
            import json
            data = json.loads(output)
            profiles = [p.get("name", "") for p in data if p.get("name")]
            return True, profiles
        except (json.JSONDecodeError, KeyError):
            return False, []
