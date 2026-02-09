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
import datetime
import logging
import os
import subprocess
import tempfile
import uuid
from typing import List, Dict, Tuple, Optional
from xml.etree import ElementTree as ET

from qgis.PyQt.QtCore import QSettings

# Set up logging to file
LOG_FILE = os.path.join(tempfile.gettempdir(), "ggu-qgis-plugin.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
    ]
)
logger = logging.getLogger("ggu_qgis_cli")


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
            logger.error("CLI path not configured")
            return False, "CLI path not configured"

        if not os.path.exists(cli_path):
            logger.error(f"CLI executable not found: {cli_path}")
            return False, f"CLI executable not found: {cli_path}"

        full_command = [cli_path] + args

        # Log the full command for debugging
        logger.info("=" * 80)
        logger.info(f"Executing CLI command:")
        logger.info(f"  CLI Path: {cli_path}")
        logger.info(f"  Arguments: {' '.join(args)}")
        logger.info(f"  Full command: {' '.join(full_command)}")

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            logger.info(f"  Return code: {result.returncode}")
            logger.info(f"  STDOUT length: {len(result.stdout) if result.stdout else 0}")
            logger.info(f"  STDERR length: {len(result.stderr) if result.stderr else 0}")

            if result.stdout:
                # Log first 2000 chars of stdout
                logger.debug(f"  STDOUT (first 2000 chars): {result.stdout[:2000]}")
            if result.stderr:
                logger.warning(f"  STDERR: {result.stderr}")

            if result.returncode == 0:
                logger.info("  Command completed successfully")
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout or f"Exit code: {result.returncode}"
                logger.error(f"  Command failed: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            logger.error("  Command timed out after 5 minutes")
            return False, "Command timed out after 5 minutes"
        except FileNotFoundError:
            logger.error(f"  CLI executable not found: {cli_path}")
            return False, f"CLI executable not found: {cli_path}"
        except Exception as e:
            logger.exception(f"  Error running CLI: {str(e)}")
            return False, f"Error running CLI: {str(e)}"

    def _format_guid(self, value: str) -> str:
        """Ensure GUID is properly formatted with curly braces.

        Args:
            value: GUID string, with or without braces

        Returns:
            GUID string with curly braces: {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
        """
        if not value:
            return value
        value = str(value).strip()
        if not value.startswith("{"):
            value = "{" + value
        if not value.endswith("}"):
            value = value + "}"
        return value

    def open_in_stratig(
        self,
        location_ids: List[str],
        project_id: Optional[str] = None,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Open boreholes in GGU-STRATIG.

        Uses the CLI command:
        ggu-connect export ggu-app --app stratig --mode open
            --filter-drilling-ids <ids>
            --db-profile <profile> --output <temp_dir>

        The CLI auto-resolves the project from the first drilling ID,
        so --project is no longer passed to avoid mismatch risks.

        Args:
            location_ids: List of borehole LocationID GUIDs
            project_id: Project GUID (unused, kept for backward compatibility)
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info("=" * 80)
        logger.info("open_in_stratig called")
        logger.info(f"  Input location_ids: {location_ids}")
        logger.info(f"  Input project_id: {project_id} (not passed to CLI, auto-resolved)")
        logger.info(f"  Input db_profile: {db_profile}")

        if not location_ids:
            logger.error("  No boreholes specified")
            return False, "No boreholes specified"

        # Ensure GUIDs are properly formatted with curly braces
        formatted_ids = [self._format_guid(lid) for lid in location_ids]

        logger.info(f"  Formatted drilling IDs: {formatted_ids}")

        # Create temp directory for output (required by CLI even in open mode)
        temp_dir = tempfile.mkdtemp(prefix="ggu_qgis_")
        logger.info(f"  Temp output directory: {temp_dir}")

        # Build command arguments
        # Note: --project is omitted; the CLI auto-resolves it from the first drilling ID
        args = [
            "export", "ggu-app",
            "--app", "stratig",
            "--mode", "open",
            "--filter-drilling-ids", ",".join(formatted_ids),
            "--output", temp_dir,
        ]

        if db_profile:
            args.extend(["--db-profile", db_profile])

        # Log the XML export path that CLI will use
        xml_path = os.path.join(os.environ.get('LOCALAPPDATA', tempfile.gettempdir()),
                               'Temp', 'CONNECT-GGU-STRATIG-EXPORT.XML')
        logger.info(f"  Expected XML export path: {xml_path}")

        result = self._run_command(args)

        # After command, check if XML was created and log its content summary
        if os.path.exists(xml_path):
            try:
                with open(xml_path, 'r', encoding='utf-8') as f:
                    xml_content = f.read()
                logger.info(f"  XML file exists, size: {len(xml_content)} bytes")
                # Count soil-layer elements
                soil_layer_count = xml_content.count('<soil-layer ')
                logger.info(f"  Number of <soil-layer> elements in XML: {soil_layer_count}")
                # Log first 3000 chars of XML for inspection
                logger.debug(f"  XML content (first 3000 chars):\n{xml_content[:3000]}")
            except Exception as e:
                logger.warning(f"  Could not read XML file: {e}")
        else:
            logger.warning(f"  XML file not found at: {xml_path}")

        return result

    def create_drillings(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Create new drillings (boreholes or soundings) from points.

        Tries the XML-based 'create drillings' command first, falls back to
        'import coordinates' if not available.

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole', 'cpt', or 'dpt')
            project_id: Target project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not points:
            return False, "No points specified"

        if not project_id:
            return False, "Project ID is required"

        # Try the XML-based create command first
        success, message = self._create_drillings_xml(points, drilling_type, project_id, db_profile)

        if success:
            return success, message

        # If 'create' command not available, fall back to 'import coordinates'
        if "Unknown command: create" in message or "unknown command" in message.lower():
            return self._create_drillings_csv_fallback(points, drilling_type, project_id, db_profile)

        return success, message

    def _create_drillings_xml(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Create drillings using XML-based 'create drillings' command.

        Uses the CLI command:
        ggu-connect create drillings --input <xml-file> --db-profile <profile>

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole', 'cpt', or 'dpt')
            project_id: Target project GUID
            db_profile: Database profile name (optional)

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Build XML content
        xml_content = self._build_drilling_xml(points, drilling_type, project_id)

        # Create temp XML file
        xml_path = self._create_xml_file(xml_content)
        if not xml_path:
            return False, "Failed to create temporary XML file"

        try:
            args = ["create", "drillings", "--input", xml_path]

            if db_profile:
                args.extend(["--db-profile", db_profile])

            return self._run_command(args)

        finally:
            try:
                os.remove(xml_path)
            except OSError:
                pass

    def _build_drilling_xml(
        self,
        points: List[Dict],
        drilling_type: str,
        project_id: str,
    ) -> str:
        """Build XML content for drilling creation.

        Args:
            points: List of dicts with keys: name, x, y, crs, z (optional)
            drilling_type: Type of drilling ('borehole', 'cpt', or 'dpt')
            project_id: Target project GUID

        Returns:
            XML string in GGU-CONNECT format
        """
        # Get EPSG code from first point
        crs = points[0].get("crs", "EPSG:25832") if points else "EPSG:25832"
        epsg_code = crs.replace("EPSG:", "") if crs.startswith("EPSG:") else "25832"

        # Create root element
        root = ET.Element("ggu-connect", version="1.0")

        # Create project element
        project = ET.SubElement(root, "project", id=project_id)

        # Map drilling type to XML element name and container
        type_mapping = {
            "borehole": ("drillings", "drilling"),
            "cpt": ("cone-penetrations", "cone-penetration"),
            "dpt": ("percussion-drillings", "percussion-drilling"),
        }

        container_name, element_name = type_mapping.get(drilling_type, ("drillings", "drilling"))

        # Create container element
        container = ET.SubElement(project, container_name)

        # Add each drilling
        for point in points:
            # Generate a new GUID for location-id
            location_id = str(uuid.uuid4())

            drilling_attrs = {
                "name": point.get("name", "NEW"),
                "location-id": location_id,
                "x-coordinate": str(point["x"]),
                "y-coordinate": str(point["y"]),
                "coordinatesystem-epsg-code": epsg_code,
            }

            # Add z-coordinate if present
            if point.get("z") is not None:
                drilling_attrs["z-coordinate-begin"] = str(point["z"])

            ET.SubElement(container, element_name, **drilling_attrs)

        # Convert to string with XML declaration
        xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml_str += ET.tostring(root, encoding="unicode")

        return xml_str

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

    def _create_xml_file(self, xml_content: str) -> Optional[str]:
        """Create a temporary XML file with content.

        Args:
            xml_content: XML string to write

        Returns:
            Path to the created XML file, or None on error
        """
        try:
            fd, xml_path = tempfile.mkstemp(suffix=".xml", prefix="ggu_create_")

            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(xml_content)

            return xml_path

        except Exception:
            return None

    def get_available_profiles(self) -> Tuple[bool, List[str]]:
        """Get list of available database profiles from CLI.

        Returns:
            Tuple of (success: bool, profiles: List[str])
        """
        success, output = self._run_command(["config", "profile-list", "-f", "json"])

        if not success:
            return False, []

        try:
            import json
            data = json.loads(output)

            # Handle CLI response format: {success, data: {profiles: [...]}}
            profiles = []
            if isinstance(data, list):
                profiles = data
            elif isinstance(data, dict):
                # Check for nested data.profiles (CLI format)
                if "data" in data and isinstance(data["data"], dict):
                    profiles = data["data"].get("profiles", [])
                # Also handle direct profiles key
                elif "profiles" in data:
                    profiles = data["profiles"]

            names = [p.get("name", "") for p in profiles if p.get("name")]
            return True, names
        except (json.JSONDecodeError, KeyError):
            return False, []

    def get_projects(
        self,
        db_profile: Optional[str] = None,
    ) -> Tuple[bool, List[Dict]]:
        """Get list of projects from the database.

        Args:
            db_profile: Database profile name (uses default from settings if not provided)

        Returns:
            Tuple of (success: bool, projects: List[Dict])
            Each project dict contains: id, name, projectNo, customer, status
        """
        args = ["search", "projects", "-f", "json"]

        if db_profile:
            args.extend(["--db-profile", db_profile])
        else:
            # Use profile from settings
            profile = self.settings.value("ggu_qgis_tools/db_profile", "")
            if profile:
                args.extend(["--db-profile", profile])

        success, output = self._run_command(args)

        if not success:
            return False, []

        try:
            import json
            data = json.loads(output)
            # Handle CLI response format: {success, data: {projects: [...]}}
            if isinstance(data, dict) and "data" in data:
                projects = data["data"].get("projects", [])
            else:
                projects = data.get("projects", [])
            return True, projects
        except (json.JSONDecodeError, KeyError):
            return False, []
