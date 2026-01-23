# -*- coding: utf-8 -*-
"""
Settings Dialog

Configuration dialog for GGU QGIS Tools plugin settings:
- CLI executable path
- Database profile
- Project selection for creating boreholes
- Ability to create new projects
"""

import json
import os
import subprocess
import uuid

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QFileDialog,
    QGroupBox,
    QLabel,
    QMessageBox,
    QInputDialog,
)


class SettingsDialog(QDialog):
    """Settings dialog for GGU QGIS Tools."""

    def __init__(self, parent=None):
        """Initialize the settings dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings = QSettings()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("GGU QGIS Tools - Settings")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # CLI Configuration Group
        cli_group = QGroupBox("GGU-CONNECT CLI")
        cli_layout = QFormLayout(cli_group)

        # CLI Path
        cli_path_layout = QHBoxLayout()
        self.cli_path_edit = QLineEdit()
        self.cli_path_edit.setPlaceholderText("Path to GGU.Apps.ConnectCLI.exe")
        cli_path_layout.addWidget(self.cli_path_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_cli_path)
        cli_path_layout.addWidget(browse_btn)

        cli_layout.addRow("CLI Executable:", cli_path_layout)

        # Test CLI button
        test_btn = QPushButton("Test CLI Connection")
        test_btn.clicked.connect(self.test_cli)
        cli_layout.addRow("", test_btn)

        layout.addWidget(cli_group)

        # Database Configuration Group
        db_group = QGroupBox("Database Configuration")
        db_layout = QFormLayout(db_group)

        # Database Profile
        profile_layout = QHBoxLayout()
        self.db_profile_combo = QComboBox()
        self.db_profile_combo.setEditable(True)
        self.db_profile_combo.setPlaceholderText("Enter or select database profile")
        self.db_profile_combo.currentTextChanged.connect(self.on_profile_changed)
        profile_layout.addWidget(self.db_profile_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_profiles)
        profile_layout.addWidget(refresh_btn)

        db_layout.addRow("Database Profile:", profile_layout)

        # Project Selection
        project_layout = QHBoxLayout()
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(300)
        self.project_combo.setPlaceholderText("Select a project for new boreholes")
        project_layout.addWidget(self.project_combo, 1)

        load_projects_btn = QPushButton("Load")
        load_projects_btn.setToolTip("Load projects from selected database profile")
        load_projects_btn.clicked.connect(self.load_projects)
        project_layout.addWidget(load_projects_btn)

        new_project_btn = QPushButton("New...")
        new_project_btn.setToolTip("Create a new project")
        new_project_btn.clicked.connect(self.create_new_project)
        project_layout.addWidget(new_project_btn)

        db_layout.addRow("Project:", project_layout)

        # Status label for showing errors/info
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: gray; font-size: 10px;")
        db_layout.addRow("", self.status_label)

        # Help text
        help_label = QLabel(
            "<small>Select the project where new boreholes will be created.</small>"
        )
        help_label.setWordWrap(True)
        db_layout.addRow("", help_label)

        # Store project data (id -> project info)
        self._projects = {}

        layout.addWidget(db_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def browse_cli_path(self):
        """Open file dialog to select CLI executable."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GGU-CONNECT CLI Executable",
            "",
            "Executable Files (*.exe);;All Files (*)",
        )
        if path:
            self.cli_path_edit.setText(path)

    def test_cli(self):
        """Test if the CLI is working."""
        cli_path = self.cli_path_edit.text().strip()

        if not cli_path:
            QMessageBox.warning(self, "Error", "Please enter the CLI path first.")
            return

        if not os.path.exists(cli_path):
            QMessageBox.warning(self, "Error", f"File not found: {cli_path}")
            return

        try:
            result = subprocess.run(
                [cli_path, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                version_info = result.stdout.strip()
                QMessageBox.information(
                    self,
                    "CLI Test Successful",
                    f"Successfully connected to GGU-CONNECT CLI.\n\n{version_info}",
                )
                # Also refresh profiles
                self.refresh_profiles()
            else:
                QMessageBox.warning(
                    self,
                    "CLI Test Failed",
                    f"CLI returned an error:\n\n{result.stderr or result.stdout}",
                )

        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Error", "CLI command timed out.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to run CLI: {str(e)}")

    def refresh_profiles(self):
        """Refresh the list of available database profiles from CLI."""
        cli_path = self.cli_path_edit.text().strip()

        if not cli_path:
            self._set_status("CLI path not configured", error=True)
            return

        if not os.path.exists(cli_path):
            self._set_status(f"CLI not found: {cli_path}", error=True)
            return

        try:
            result = subprocess.run(
                [cli_path, "config", "profile-list", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                current_text = self.db_profile_combo.currentText()
                self.db_profile_combo.clear()

                try:
                    # Parse JSON output from CLI
                    data = json.loads(result.stdout)

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

                    for profile in profiles:
                        name = profile.get("name", "")
                        if name:
                            self.db_profile_combo.addItem(name)

                    if profiles:
                        self._set_status(f"Found {len(profiles)} profile(s)")
                    else:
                        self._set_status("No profiles configured. Use CLI to add profiles.", error=True)

                except json.JSONDecodeError as e:
                    self._set_status(f"Invalid JSON response: {str(e)}", error=True)

                # Restore previous selection
                if current_text:
                    idx = self.db_profile_combo.findText(current_text)
                    if idx >= 0:
                        self.db_profile_combo.setCurrentIndex(idx)
                    else:
                        self.db_profile_combo.setCurrentText(current_text)
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code: {result.returncode}"
                self._set_status(f"CLI error: {error_msg}", error=True)

        except subprocess.TimeoutExpired:
            self._set_status("CLI command timed out", error=True)
        except FileNotFoundError:
            self._set_status(f"CLI not found: {cli_path}", error=True)
        except Exception as e:
            self._set_status(f"Error: {str(e)}", error=True)

    def _set_status(self, message: str, error: bool = False):
        """Set status label with message."""
        self.status_label.setText(message)
        if error:
            self.status_label.setStyleSheet("color: red; font-size: 10px;")
        else:
            self.status_label.setStyleSheet("color: green; font-size: 10px;")

    def on_profile_changed(self, profile_name: str):
        """Called when the database profile selection changes."""
        # Clear projects when profile changes
        self.project_combo.clear()
        self._projects = {}
        if profile_name:
            self._set_status(f"Profile: {profile_name} - Click 'Load' to load projects")

    def load_projects(self):
        """Load projects from the selected database profile."""
        cli_path = self.cli_path_edit.text().strip()
        db_profile = self.db_profile_combo.currentText().strip()

        if not cli_path:
            self._set_status("CLI path not configured", error=True)
            return

        if not os.path.exists(cli_path):
            self._set_status(f"CLI not found: {cli_path}", error=True)
            return

        if not db_profile:
            self._set_status("Please select a database profile first", error=True)
            return

        self._set_status("Loading projects...")
        self.project_combo.clear()
        self._projects = {}

        import tempfile

        # Use temp file for output to handle large responses
        fd, temp_output = tempfile.mkstemp(suffix=".json", prefix="ggu_projects_")
        try:
            with os.fdopen(fd, 'w') as f:
                pass  # Just close the file descriptor

            # Run CLI with output redirected to temp file (binary mode to avoid encoding issues)
            with open(temp_output, 'wb') as outfile:
                result = subprocess.run(
                    [cli_path, "search", "projects", "--db-profile", db_profile, "-f", "json"],
                    stdout=outfile,
                    stderr=subprocess.PIPE,
                    timeout=120,
                )

            if result.returncode == 0:
                try:
                    # Read output from temp file, try UTF-8 first, fall back to cp1252
                    with open(temp_output, 'rb') as f:
                        raw_data = f.read()

                    try:
                        output = raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        output = raw_data.decode('cp1252')

                    if not output:
                        self._set_status("CLI returned empty response", error=True)
                        return

                    data = json.loads(output)
                    # Handle CLI response format: {success, data: {projects: [...]}}
                    if isinstance(data, dict) and "data" in data:
                        projects = data["data"].get("projects", [])
                    else:
                        projects = data.get("projects", [])

                    for project in projects:
                        project_id = project.get("id", "")
                        name = project.get("name", "Unknown")
                        project_no = project.get("projectNo", "")

                        if project_id:
                            # Create display text
                            if project_no:
                                display_text = f"{project_no} - {name}"
                            else:
                                display_text = name

                            self.project_combo.addItem(display_text, project_id)
                            self._projects[project_id] = project

                    if projects:
                        self._set_status(f"Found {len(projects)} project(s)")
                    else:
                        self._set_status("No projects found in database")

                except json.JSONDecodeError as e:
                    self._set_status(f"Invalid JSON response: {str(e)}", error=True)
            else:
                error_msg = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
                self._set_status(f"CLI error: {error_msg}", error=True)

        except subprocess.TimeoutExpired:
            self._set_status("CLI command timed out (>120s)", error=True)
        except Exception as e:
            self._set_status(f"Error: {str(e)}", error=True)
        finally:
            try:
                os.remove(temp_output)
            except OSError:
                pass

    def create_new_project(self):
        """Create a new project via CLI."""
        cli_path = self.cli_path_edit.text().strip()
        db_profile = self.db_profile_combo.currentText().strip()

        if not cli_path or not os.path.exists(cli_path):
            QMessageBox.warning(self, "Error", "Please configure the CLI path first.")
            return

        if not db_profile:
            QMessageBox.warning(self, "Error", "Please select a database profile first.")
            return

        # Get project name
        name, ok = QInputDialog.getText(
            self,
            "New Project",
            "Project Name:",
            QLineEdit.Normal,
            ""
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        # Get project number (optional)
        project_no, ok = QInputDialog.getText(
            self,
            "New Project",
            "Project Number (optional):",
            QLineEdit.Normal,
            ""
        )
        if not ok:
            return
        project_no = project_no.strip()

        # Generate new project ID
        project_id = str(uuid.uuid4())

        # Create minimal XML for project creation
        xml_content = self._build_project_xml(project_id, name, project_no)

        # Write to temp file
        import tempfile
        try:
            fd, xml_path = tempfile.mkstemp(suffix=".xml", prefix="ggu_project_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(xml_content)

            # Run CLI import
            result = subprocess.run(
                [cli_path, "import", "xml", "--input", xml_path, "--db-profile", db_profile],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Project '{name}' created successfully."
                )
                # Reload projects to show the new one
                self.load_projects()

                # Select the newly created project
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemData(i) == project_id:
                        self.project_combo.setCurrentIndex(i)
                        break
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Failed to create project:\n{error_msg}"
                )

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to create project: {str(e)}")
        finally:
            try:
                os.remove(xml_path)
            except OSError:
                pass

    def _build_project_xml(self, project_id: str, name: str, project_no: str) -> str:
        """Build XML content for project creation."""
        from xml.sax.saxutils import escape

        xml = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml += '<ggu-connect version="1.0">\n'
        xml += f'  <project id="{project_id}">\n'
        xml += f'    <name>{escape(name)}</name>\n'
        if project_no:
            xml += f'    <project-no>{escape(project_no)}</project-no>\n'
        xml += '    <drillings>\n'
        xml += '    </drillings>\n'
        xml += '  </project>\n'
        xml += '</ggu-connect>\n'
        return xml

    def load_settings(self):
        """Load settings from QSettings."""
        cli_path = self.settings.value("ggu_qgis_tools/cli_path", "")
        db_profile = self.settings.value("ggu_qgis_tools/db_profile", "")
        project_id = self.settings.value("ggu_qgis_tools/default_project_id", "")

        self.cli_path_edit.setText(cli_path)

        # Try to load profiles if CLI path is set
        if cli_path and os.path.exists(cli_path):
            self.refresh_profiles()

        # Restore the profile selection
        if db_profile:
            self.db_profile_combo.setCurrentText(db_profile)

            # Try to load projects for this profile
            self.load_projects()

            # Try to restore project selection
            if project_id:
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemData(i) == project_id:
                        self.project_combo.setCurrentIndex(i)
                        break

    def save_settings(self):
        """Save settings to QSettings."""
        self.settings.setValue("ggu_qgis_tools/cli_path", self.cli_path_edit.text().strip())
        self.settings.setValue("ggu_qgis_tools/db_profile", self.db_profile_combo.currentText().strip())

        # Get project ID from combo box (stored as item data)
        project_id = self.project_combo.currentData() or ""
        self.settings.setValue("ggu_qgis_tools/default_project_id", project_id)

        self.accept()
