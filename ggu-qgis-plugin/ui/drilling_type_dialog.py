# -*- coding: utf-8 -*-
"""
Drilling Type Selection Dialog

Dialog for selecting the type of drilling to create:
- Borehole (Bohrung)
- Cone Penetration Test / CPT (Drucksondierung)
- Dynamic Probing Test / DPT (Rammsondierung)
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QButtonGroup,
    QPushButton,
    QGroupBox,
)


class DrillingTypeDialog(QDialog):
    """Dialog for selecting drilling type."""

    # Drilling type definitions: (id, label, description)
    DRILLING_TYPES = [
        ("borehole", "Borehole (Bohrung)", "Standard borehole / core drilling"),
        ("cpt", "Cone Penetration Test (CPT)", "Drucksondierung - measures cone resistance"),
        ("dpt", "Dynamic Probing Test (DPT)", "Rammsondierung - percussion/hammer sounding"),
    ]

    def __init__(self, point_count=1, parent=None):
        """Initialize the dialog.

        Args:
            point_count: Number of points selected (for info display)
            parent: Parent widget
        """
        super().__init__(parent)
        self.point_count = point_count
        self.selected_type = "borehole"  # Default
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Create Drilling")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Info label
        info_text = f"Creating drilling(s) from {self.point_count} selected point(s)."
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Drilling type selection group
        type_group = QGroupBox("Select Drilling Type")
        type_layout = QVBoxLayout(type_group)

        self.button_group = QButtonGroup(self)

        for i, (type_id, label, description) in enumerate(self.DRILLING_TYPES):
            radio = QRadioButton(label)
            radio.setToolTip(description)

            # Select first option by default
            if i == 0:
                radio.setChecked(True)

            self.button_group.addButton(radio, i)
            type_layout.addWidget(radio)

            # Add description as smaller label
            desc_label = QLabel(f"  <small><i>{description}</i></small>")
            desc_label.setTextFormat(Qt.RichText)
            type_layout.addWidget(desc_label)

        layout.addWidget(type_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        create_btn = QPushButton("Create")
        create_btn.setDefault(True)
        create_btn.clicked.connect(self.accept)
        button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def get_selected_type(self):
        """Get the selected drilling type ID.

        Returns:
            str: Drilling type ID ('borehole', 'cpt', or 'dpt')
        """
        checked_id = self.button_group.checkedId()
        if 0 <= checked_id < len(self.DRILLING_TYPES):
            return self.DRILLING_TYPES[checked_id][0]
        return "borehole"  # Default fallback
