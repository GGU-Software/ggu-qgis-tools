# -*- coding: utf-8 -*-
"""
Settings Dialog

Configuration dialog for GGU QGIS Tools plugin settings:
- CLI executable path
- Database profile
- Default project for creating boreholes
"""

import os

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
        profile_layout.addWidget(self.db_profile_combo)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_profiles)
        profile_layout.addWidget(refresh_btn)

        db_layout.addRow("Database Profile:", profile_layout)

        # Default Project ID
        self.project_id_edit = QLineEdit()
        self.project_id_edit.setPlaceholderText("GUID of default project for new boreholes")
        db_layout.addRow("Default Project ID:", self.project_id_edit)

        # Help text
        help_label = QLabel(
            "<small>The default project is used when creating new boreholes from planning points.</small>"
        )
        help_label.setWordWrap(True)
        db_layout.addRow("", help_label)

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

        import subprocess

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

        if not cli_path or not os.path.exists(cli_path):
            return

        import subprocess
        import json

        try:
            result = subprocess.run(
                [cli_path, "config", "profile", "list", "-f", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                current_text = self.db_profile_combo.currentText()
                self.db_profile_combo.clear()

                try:
                    profiles = json.loads(result.stdout)
                    for profile in profiles:
                        name = profile.get("name", "")
                        if name:
                            self.db_profile_combo.addItem(name)
                except json.JSONDecodeError:
                    pass

                # Restore previous selection
                if current_text:
                    idx = self.db_profile_combo.findText(current_text)
                    if idx >= 0:
                        self.db_profile_combo.setCurrentIndex(idx)
                    else:
                        self.db_profile_combo.setCurrentText(current_text)

        except Exception:
            pass

    def load_settings(self):
        """Load settings from QSettings."""
        cli_path = self.settings.value("ggu_qgis_tools/cli_path", "")
        db_profile = self.settings.value("ggu_qgis_tools/db_profile", "")
        project_id = self.settings.value("ggu_qgis_tools/default_project_id", "")

        self.cli_path_edit.setText(cli_path)
        self.db_profile_combo.setCurrentText(db_profile)
        self.project_id_edit.setText(project_id)

        # Try to load profiles if CLI path is set
        if cli_path and os.path.exists(cli_path):
            self.refresh_profiles()
            # Restore the profile selection after refresh
            if db_profile:
                self.db_profile_combo.setCurrentText(db_profile)

    def save_settings(self):
        """Save settings to QSettings."""
        self.settings.setValue("ggu_qgis_tools/cli_path", self.cli_path_edit.text().strip())
        self.settings.setValue("ggu_qgis_tools/db_profile", self.db_profile_combo.currentText().strip())
        self.settings.setValue("ggu_qgis_tools/default_project_id", self.project_id_edit.text().strip())

        self.accept()
