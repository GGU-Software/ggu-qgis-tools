# -*- coding: utf-8 -*-
"""
Selection Reader Service

Reads selected features from QGIS layers and extracts relevant attributes
for GGU-CONNECT CLI operations.
"""

from qgis.core import QgsWkbTypes


class SelectionReader:
    """Reads and processes selected features from QGIS layers."""

    # Known attribute names for borehole identification
    LOCATION_ID_FIELDS = ["LocationID", "locationid", "location_id", "borehole_location_id"]
    PROJECT_ID_FIELDS = ["ProjectID", "projectid", "project_id"]
    NAME_FIELDS = ["BoreholeName", "borehole_name", "name", "Name", "NAME"]

    def __init__(self, iface):
        """Initialize the selection reader.

        Args:
            iface: QGIS interface instance
        """
        self.iface = iface

    def get_selected_boreholes(self):
        """Get selected borehole features with LocationID and ProjectID.

        Returns:
            dict with:
                - features: list of dicts with LocationID, ProjectID, name
                - layer_name: name of the source layer
                - crs: coordinate reference system (EPSG code)
        """
        layer = self.iface.activeLayer()
        if not layer:
            return {"features": [], "layer_name": None, "crs": None}

        selected_features = layer.selectedFeatures()
        if not selected_features:
            return {"features": [], "layer_name": layer.name(), "crs": None}

        # Get CRS
        crs = layer.crs().authid()  # e.g., "EPSG:25832"

        # Find attribute indices
        fields = layer.fields()
        field_names = [f.name() for f in fields]

        location_id_field = self._find_field(field_names, self.LOCATION_ID_FIELDS)
        project_id_field = self._find_field(field_names, self.PROJECT_ID_FIELDS)
        name_field = self._find_field(field_names, self.NAME_FIELDS)

        # Extract feature data
        features = []
        for feature in selected_features:
            feature_data = {}

            if location_id_field:
                feature_data["LocationID"] = feature[location_id_field]
            if project_id_field:
                feature_data["ProjectID"] = feature[project_id_field]
            if name_field:
                feature_data["name"] = feature[name_field]

            # Get geometry centroid for coordinates
            geom = feature.geometry()
            if geom and not geom.isNull():
                point = geom.centroid().asPoint()
                feature_data["x"] = point.x()
                feature_data["y"] = point.y()

            features.append(feature_data)

        return {
            "features": features,
            "layer_name": layer.name(),
            "crs": crs,
        }

    def get_selected_points(self):
        """Get selected point features with coordinates and optional name.

        Used for creating new boreholes from planning points.

        Returns:
            dict with:
                - features: list of dicts with x, y, z (optional), name (optional)
                - layer_name: name of the source layer
                - crs: coordinate reference system (EPSG code)
        """
        layer = self.iface.activeLayer()
        if not layer:
            return {"features": [], "layer_name": None, "crs": None}

        selected_features = layer.selectedFeatures()
        if not selected_features:
            return {"features": [], "layer_name": layer.name(), "crs": None}

        # Get CRS
        crs = layer.crs().authid()

        # Find name field
        fields = layer.fields()
        field_names = [f.name() for f in fields]
        name_field = self._find_field(field_names, self.NAME_FIELDS)

        # Extract feature data
        features = []
        for feature in selected_features:
            geom = feature.geometry()
            if not geom or geom.isNull():
                continue

            # Get point coordinates
            if QgsWkbTypes.geometryType(geom.wkbType()) == QgsWkbTypes.PointGeometry:
                point = geom.asPoint()
            else:
                # For non-point geometries, use centroid
                point = geom.centroid().asPoint()

            feature_data = {
                "x": point.x(),
                "y": point.y(),
            }

            # Check for Z coordinate
            if geom.constGet() and geom.constGet().is3D():
                # For 3D geometries
                if hasattr(point, "z"):
                    feature_data["z"] = point.z()

            # Get name if available
            if name_field:
                feature_data["name"] = feature[name_field]

            features.append(feature_data)

        return {
            "features": features,
            "layer_name": layer.name(),
            "crs": crs,
        }

    def _find_field(self, field_names, candidates):
        """Find first matching field name from candidates.

        Args:
            field_names: list of field names in the layer
            candidates: list of possible field name variations

        Returns:
            Matching field name or None
        """
        field_names_lower = [f.lower() for f in field_names]
        for candidate in candidates:
            if candidate.lower() in field_names_lower:
                # Return the actual field name (with original case)
                idx = field_names_lower.index(candidate.lower())
                return field_names[idx]
        return None
