# -*- coding: utf-8 -*-
"""
GGU QGIS Tools - QGIS Plugin for GGU-CONNECT CLI integration

This plugin provides integration between QGIS and the GGU-CONNECT CLI:
- Open selected boreholes in GGU-STRATIG
- Create new boreholes from planning points

Author: GGU Software
License: MIT
"""


def classFactory(iface):
    """Load the plugin class.

    Args:
        iface: A QGIS interface instance (QgisInterface)

    Returns:
        GguQgisToolsPlugin instance
    """
    from .plugin import GguQgisToolsPlugin
    return GguQgisToolsPlugin(iface)
