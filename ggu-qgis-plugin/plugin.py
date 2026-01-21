# -*- coding: utf-8 -*-
"""
GGU QGIS Tools - Main Plugin Class

Provides toolbar actions and menu integration for GGU-CONNECT CLI operations.
"""

import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsProject

from .services.selection_reader import SelectionReader
from .services.cli_runner import CliRunner
from .ui.settings_dialog import SettingsDialog
from .ui.drilling_type_dialog import DrillingTypeDialog


class GguQgisToolsPlugin:
    """Main plugin class for GGU QGIS Tools."""

    def __init__(self, iface):
        """Initialize the plugin.

        Args:
            iface: QGIS interface instance
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        # Initialize services
        self.selection_reader = SelectionReader(iface)
        self.cli_runner = CliRunner()

        # Actions will be set up in initGui
        self.actions = []
        self.menu = self.tr("&GGU Tools")
        self.toolbar = None

    def tr(self, message):
        """Get the translation for a string."""
        return QCoreApplication.translate("GguQgisToolsPlugin", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon and menu item."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)

        if add_to_toolbar and self.toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons."""
        # Create toolbar
        self.toolbar = self.iface.addToolBar(self.tr("GGU Tools"))
        self.toolbar.setObjectName("GguToolsToolbar")

        icon_base = os.path.join(self.plugin_dir, "resources")

        # Action: Open in GGU-STRATIG
        self.add_action(
            os.path.join(icon_base, "icon_open.svg"),
            self.tr("Open in GGU-STRATIG"),
            self.open_in_stratig,
            status_tip=self.tr("Open selected boreholes in GGU-STRATIG"),
            parent=self.iface.mainWindow(),
        )

        # Action: Create Drilling (opens type selection dialog)
        self.add_action(
            os.path.join(icon_base, "icon_create_borehole.svg"),
            self.tr("Create Drilling"),
            self.create_drilling,
            status_tip=self.tr("Create new drilling (borehole, CPT, DPT) from selected points"),
            parent=self.iface.mainWindow(),
        )

        # Separator
        if self.toolbar:
            self.toolbar.addSeparator()

        # Action: Settings
        self.add_action(
            os.path.join(icon_base, "icon_settings.svg"),
            self.tr("Settings"),
            self.show_settings,
            status_tip=self.tr("Configure GGU QGIS Tools"),
            parent=self.iface.mainWindow(),
        )

    def unload(self):
        """Remove the plugin menu items and toolbar."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

        if self.toolbar:
            del self.toolbar

    def _check_cli_configured(self):
        """Check if CLI is configured, show settings if not."""
        settings = QSettings()
        cli_path = settings.value("ggu_qgis_tools/cli_path", "")

        if not cli_path or not os.path.exists(cli_path):
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("Configuration Required"),
                self.tr(
                    "GGU-CONNECT CLI path is not configured.\n\n"
                    "Please configure the path to GGU.Apps.ConnectCLI.exe in the settings."
                ),
            )
            self.show_settings()
            return False
        return True

    def open_in_stratig(self):
        """Open selected boreholes in GGU-STRATIG."""
        if not self._check_cli_configured():
            return

        # Get selected features with required attributes
        selection = self.selection_reader.get_selected_boreholes()

        if not selection["features"]:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("No Selection"),
                self.tr(
                    "Please select one or more boreholes from a layer with "
                    "'LocationID' and 'ProjectID' attributes."
                ),
            )
            return

        # Extract IDs
        location_ids = [f["LocationID"] for f in selection["features"] if f.get("LocationID")]
        project_id = selection["features"][0].get("ProjectID") if selection["features"] else None

        if not location_ids:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("Missing Attribute"),
                self.tr("Selected features do not have 'LocationID' attribute."),
            )
            return

        if not project_id:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("Missing Attribute"),
                self.tr("Selected features do not have 'ProjectID' attribute."),
            )
            return

        # Run CLI command
        settings = QSettings()
        db_profile = settings.value("ggu_qgis_tools/db_profile", "")

        success, message = self.cli_runner.open_in_stratig(
            location_ids=location_ids,
            project_id=project_id,
            db_profile=db_profile,
        )

        if not success:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr("CLI Error"),
                self.tr(f"Failed to open in GGU-STRATIG:\n\n{message}"),
            )

    def create_drilling(self):
        """Create new drilling from selected planning points.

        Shows a dialog to select drilling type, then creates the drilling(s).
        """
        if not self._check_cli_configured():
            return

        # Get selected points with coordinates
        selection = self.selection_reader.get_selected_points()

        if not selection["features"]:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("No Selection"),
                self.tr("Please select one or more points from a layer."),
            )
            return

        # Get settings
        settings = QSettings()
        db_profile = settings.value("ggu_qgis_tools/db_profile", "")
        default_project_id = settings.value("ggu_qgis_tools/default_project_id", "")

        if not default_project_id:
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr("Configuration Required"),
                self.tr(
                    "Default project ID is not configured.\n\n"
                    "Please set a default project in the settings for creating new drillings."
                ),
            )
            self.show_settings()
            return

        # Show drilling type selection dialog
        dialog = DrillingTypeDialog(
            point_count=len(selection["features"]),
            parent=self.iface.mainWindow(),
        )

        if dialog.exec_() != dialog.Accepted:
            return  # User cancelled

        drilling_type = dialog.get_selected_type()

        # Prepare point data
        points = []
        for feature in selection["features"]:
            point_data = {
                "name": feature.get("name") or feature.get("BoreholeName") or f"NEW-{len(points)+1}",
                "x": feature["x"],
                "y": feature["y"],
                "crs": selection["crs"],
            }
            if feature.get("z") is not None:
                point_data["z"] = feature["z"]
            points.append(point_data)

        # Run CLI command
        success, message = self.cli_runner.create_drillings(
            points=points,
            drilling_type=drilling_type,
            project_id=default_project_id,
            db_profile=db_profile,
        )

        # Get display name for the drilling type
        type_names = {
            "borehole": self.tr("borehole(s)"),
            "cpt": self.tr("cone penetration test(s)"),
            "dpt": self.tr("dynamic probing test(s)"),
        }
        type_display = type_names.get(drilling_type, drilling_type)

        if success:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("Success"),
                self.tr(f"Created {len(points)} {type_display} successfully."),
            )
        else:
            QMessageBox.critical(
                self.iface.mainWindow(),
                self.tr("CLI Error"),
                self.tr(f"Failed to create {type_display}:\n\n{message}"),
            )

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self.iface.mainWindow())
        dialog.exec_()
