"""
QC (Quality Control) widget for registration visualizations.

Provides checkboxes for QC plot types and a "Plot QC" button so the user
selects what to show, then triggers computation/display with one action.
"""

from qtpy.QtWidgets import (
    QCheckBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class QCWidget(QWidget):
    """Widget for QC visualization options and actions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.red_green_checkbox = QCheckBox("Red-Green Overlay")
        self.red_green_checkbox.setToolTip(
            "Overlay atlas (red) and registered/moving (green); "
            "yellow where they overlap. Use Plot QC to apply."
        )
        self.layout().addWidget(self.red_green_checkbox)

        self.plot_qc_button = QPushButton("Plot QC")
        self.plot_qc_button.setToolTip(
            "Apply selected QC visualizations (e.g. red-green overlay)."
        )
        self.layout().addWidget(self.plot_qc_button)

        self.clear_qc_button = QPushButton("Clear QC Images")
        self.clear_qc_button.setToolTip(
            "Restore original layer display settings and clear QC overlays."
        )
        self.layout().addWidget(self.clear_qc_button)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all QC controls."""
        self.red_green_checkbox.setEnabled(enabled)
        self.plot_qc_button.setEnabled(enabled)
        self.clear_qc_button.setEnabled(enabled)
