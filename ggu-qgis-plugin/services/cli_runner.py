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
import json
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

        Tries the new JSON-based 'create' command first, falls back to
        'import coordinates' if not available.

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

        # Try the new JSON-based create command first
        success, message = self._create_drillings_json(points, drilling_type, project_id, db_profile)

        if success:
            return success, message

        # If 'create' command not available, fall back to 'import coordinates'
        if "Unknown command: create" in message or "unknown command" in message.lower():
            return self._create_drillings_csv_fallback(points, drilling_type, project_id, db_profile)

        return success, message

    def _create_drillings_json(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Create drillings using JSON-based 'create' command.

        Uses the CLI command:
        ggu-connect create --input <json-file> --db-profile <profile>

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole' or 'cpt')
            project_id: Target project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Build JSON structure
        crs = points[0].get("crs", "EPSG:25832") if points else "EPSG:25832"

        json_data = {
            "operation": "create_drillings",
            "project_id": project_id,
            "drillings": [
                {
                    "name": p.get("name", f"NEW-{i+1}"),
                    "type": drilling_type,
                    "x": p["x"],
                    "y": p["y"],
                    "z": p.get("z"),
                    "crs": p.get("crs", crs),
                }
                for i, p in enumerate(points)
            ]
        }

        # Remove None values from drillings
        for drilling in json_data["drillings"]:
            if drilling["z"] is None:
                del drilling["z"]

        # Create temp JSON file
        json_path = self._create_json_file(json_data)
        if not json_path:
            return False, "Failed to create temporary JSON file"

        try:
            args = ["create", "--input", json_path]

            if db_profile:
                args.extend(["--db-profile", db_profile])

            return self._run_command(args)

        finally:
            try:
                os.remove(json_path)
            except OSError:
                pass

    def _create_drillings_csv_fallback(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Fallback: Create drillings using CSV-based 'import coordinates'.

        Uses the CLI command:
        ggu-connect import coordinates --input <csv_file>
            --project <project_id> --db-profile <profile>
            --col-name 0 --col-x 1 --col-y 2 [--col-z 3] --start-row 2

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole' or 'cpt') - NOTE: not supported in fallback
            project_id: Target project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
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

            # Note: drilling_type is not supported in CSV fallback mode
            # All drillings will be created as default type (borehole)

            return self._run_command(args)

        finally:
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

    def _create_json_file(self, data: Dict) -> Optional[str]:
        """Create a temporary JSON file with data.

        Args:
            data: Dictionary to serialize as JSON

        Returns:
            Path to the created JSON file, or None on error
        """
        try:
            fd, json_path = tempfile.mkstemp(suffix=".json", prefix="ggu_create_")

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return json_path

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
