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

        self.jacobian_checkbox = QCheckBox("Jacobian Determinant Map")
        self.jacobian_checkbox.setToolTip(
            "Show |J| from non-rigid transform: 1=no change, >1=expansion, "
            "<1=contraction, <=0=folding. Only for BSpline. Use Plot QC."
        )
        self.layout().addWidget(self.jacobian_checkbox)

        self.save_jacobian_checkbox = QCheckBox(
            "Save Jacobian determinant to output (BSpline only)"
        )
        self.save_jacobian_checkbox.setToolTip(
            "When running registration with BSpline, also write "
            "jacobian_determinant.tiff to the output directory. Optional; "
            "adds compute time."
        )
        self.save_jacobian_checkbox.setChecked(False)
        self.layout().addWidget(self.save_jacobian_checkbox)

        self.plot_qc_button = QPushButton("Plot QC")
        self.plot_qc_button.setToolTip(
            "Generate selected QC visualizations (e.g. Jacobian map)."
        )
        self.layout().addWidget(self.plot_qc_button)

        self.clear_qc_button = QPushButton("Clear QC Images")
        self.clear_qc_button.setToolTip(
            "Remove QC layers and clear selection."
        )
        self.layout().addWidget(self.clear_qc_button)

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all QC controls."""
        self.jacobian_checkbox.setEnabled(enabled)
        self.save_jacobian_checkbox.setEnabled(enabled)
        self.plot_qc_button.setEnabled(enabled)
        self.clear_qc_button.setEnabled(enabled)

    def set_jacobian_enabled(self, enabled: bool) -> None:
        """Enable Jacobian option only when registration used BSpline."""
        self.jacobian_checkbox.setEnabled(enabled)
