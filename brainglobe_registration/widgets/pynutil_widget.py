"""
PyNutil integration widget for brainglobe-registration.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import numpy as np
from qtpy.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QGroupBox,
    QCheckBox,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QProgressBar,
    QMessageBox,
)
from qtpy.QtCore import Qt, Signal, QThread
from napari.viewer import Viewer

from ..pynutil_integration import (
    export_for_pynutil,
    run_pynutil_quantification,
    run_intensity_quantification,
    QCReport,
    analyze_image_quality,
)


class PyNutilWorker(QThread):
    """Background worker for PyNutil quantification."""

    progress = Signal(str)
    finished = Signal(object, object)  # (success, result)
    error = Signal(str)

    def __init__(
        self,
        pynutil_dir: str,
        atlas_name: str,
        output_dir: str,
        mode: str = "binary",
        **kwargs,
    ):
        super().__init__()
        self.pynutil_dir = pynutil_dir
        self.atlas_name = atlas_name
        self.output_dir = output_dir
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            self.progress.emit("Starting PyNutil quantification...")

            if self.mode == "binary":
                label_df, metadata = run_pynutil_quantification(
                    self.pynutil_dir,
                    self.atlas_name,
                    self.output_dir,
                    **self.kwargs,
                )
            else:  # intensity
                label_df, metadata = run_intensity_quantification(
                    self.pynutil_dir,
                    self.atlas_name,
                    self.output_dir,
                    **self.kwargs,
                )

            n_items = metadata.get('n_objects', metadata.get('n_pixels', 0))
            self.progress.emit(f"Quantification complete: {n_items} items analyzed")
            self.finished.emit(True, {"df": label_df, "metadata": metadata})

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(False, str(e))


class PyNutilWidget(QWidget):
    """Widget for PyNutil integration."""

    def __init__(self, viewer: Viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.worker = None
        self._parent = parent

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Info label
        info_label = QLabel(
            "PyNutil integration for brain-wide quantification.\n"
            "Export registration results and run quantification analysis."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Quality Control Section
        qc_group = QGroupBox("Quality Control")
        qc_layout = QVBoxLayout()

        self.qc_button = QPushButton("Analyze Image Quality")
        self.qc_button.clicked.connect(self.run_qc_analysis)
        qc_layout.addWidget(self.qc_button)

        self.qc_results = QTextEdit()
        self.qc_results.setReadOnly(True)
        self.qc_results.setMaximumHeight(180)
        self.qc_results.setPlaceholderText("Quality control results will appear here...")
        qc_layout.addWidget(self.qc_results)

        qc_group.setLayout(qc_layout)
        layout.addWidget(qc_group)

        # Export Section
        export_group = QGroupBox("Export for PyNutil")
        export_layout = QVBoxLayout()

        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_edit = QLineEdit()
        output_layout.addWidget(self.output_edit)
        self.output_button = QPushButton("Browse...")
        self.output_button.clicked.connect(self.browse_output_dir)
        output_layout.addWidget(self.output_button)
        export_layout.addLayout(output_layout)

        # Sample geometry
        geom_layout = QHBoxLayout()
        geom_layout.addWidget(QLabel("Sample Geometry:"))
        self.geometry_combo = QComboBox()
        self.geometry_combo.addItems([
            "full",
            "left_hemi",
            "right_hemi",
        ])
        geom_layout.addWidget(self.geometry_combo)
        export_layout.addLayout(geom_layout)

        # Damage mask checkbox
        self.damage_checkbox = QCheckBox("Include Damage Mask (if available)")
        self.damage_checkbox.setChecked(False)
        self.damage_checkbox.setToolTip(
            "If a damage mask exists from registration, include it in the export"
        )
        export_layout.addWidget(self.damage_checkbox)

        self.export_button = QPushButton("Export to PyNutil Format")
        self.export_button.clicked.connect(self.run_export)
        export_layout.addWidget(self.export_button)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        # Quantification Section
        quant_group = QGroupBox("Run Quantification")
        quant_layout = QVBoxLayout()

        # Mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Binary Segmentation", "Intensity"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        quant_layout.addLayout(mode_layout)

        # Object cutoff (for binary mode)
        cutoff_layout = QHBoxLayout()
        cutoff_layout.addWidget(QLabel("Object Cutoff:"))
        self.cutoff_spin = QSpinBox()
        self.cutoff_spin.setRange(0, 10000)
        self.cutoff_spin.setValue(0)
        self.cutoff_spin.setToolTip("Minimum object size for detection")
        cutoff_layout.addWidget(self.cutoff_spin)
        quant_layout.addLayout(cutoff_layout)

        # Intensity thresholds (for intensity mode, hidden by default)
        self.intensity_thresholds_widget = QWidget()
        intensity_thresholds_layout = QHBoxLayout()
        intensity_thresholds_layout.addWidget(QLabel("Min Intensity:"))
        self.min_intensity_spin = QSpinBox()
        self.min_intensity_spin.setRange(0, 65535)
        self.min_intensity_spin.setValue(0)
        intensity_thresholds_layout.addWidget(self.min_intensity_spin)
        intensity_thresholds_layout.addWidget(QLabel("Max Intensity:"))
        self.max_intensity_spin = QSpinBox()
        self.max_intensity_spin.setRange(0, 65535)
        self.max_intensity_spin.setValue(65535)
        intensity_thresholds_layout.addWidget(self.max_intensity_spin)
        self.intensity_thresholds_widget.setLayout(intensity_thresholds_layout)
        self.intensity_thresholds_widget.setVisible(False)
        quant_layout.addWidget(self.intensity_thresholds_widget)

        # Intensity channel
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["grayscale", "R", "G", "B"])
        channel_layout.addWidget(self.channel_combo)
        quant_layout.addLayout(channel_layout)

        self.quant_button = QPushButton("Run PyNutil Quantification")
        self.quant_button.clicked.connect(self.run_quantification)
        quant_layout.addWidget(self.quant_button)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        quant_layout.addWidget(self.progress_bar)

        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("Quantification results will appear here...")
        self.results_text.setMaximumHeight(200)
        quant_layout.addWidget(self.results_text)

        quant_group.setLayout(quant_layout)
        layout.addWidget(quant_group)

        # Open in PyNutil GUI button
        self.open_gui_button = QPushButton("Open in PyNutil GUI")
        self.open_gui_button.clicked.connect(self.open_pynutil_gui)
        self.open_gui_button.setToolTip(
            "Launch the standalone PyNutil GUI with exported data"
        )
        layout.addWidget(self.open_gui_button)

        # Spacer
        layout.addStretch()

    def _on_mode_changed(self, mode: str):
        """Show/hide intensity thresholds based on mode."""
        is_intensity = mode == "Intensity"
        self.intensity_thresholds_widget.setVisible(is_intensity)
        self.cutoff_spin.setVisible(not is_intensity)

    def browse_output_dir(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if dir_path:
            self.output_edit.setText(dir_path)

    def run_qc_analysis(self):
        """Run quality control analysis on current image."""
        # Get current moving image layer
        # Note: napari 0.7+ doesn't have LayerList.get(), use indexing instead
        moving_layer = None
        for layer in self.viewer.layers:
            if layer.name == "moving_image":
                moving_layer = layer
                break

        if moving_layer is None:
            # Try alternative layer names
            for layer in self.viewer.layers:
                if hasattr(layer, 'data') and layer.data is not None:
                    moving_layer = layer
                    break

        if moving_layer is None:
            self.qc_results.setText("No image layer found. Please load an image first.")
            return

        image = moving_layer.data
        if hasattr(image, 'compute'):
            image = image.compute()

        # Analyze
        report = analyze_image_quality(np.asarray(image))

        # Display results
        self.qc_results.setText(self._format_qc_report(report))

    def run_export(self):
        """Export registration results to PyNutil format."""
        # Get required data from parent registration widget
        if self._parent is None:
            QMessageBox.warning(
                self,
                "Export Error",
                "Cannot export: parent registration widget not found."
            )
            return

        # Get moving image layer from parent widget (has correct reference)
        moving_layer = getattr(self._parent, '_moving_image', None)
        if moving_layer is None:
            # Fallback: try to find any image layer
            for layer in self.viewer.layers:
                if hasattr(layer, 'data') and layer.data is not None:
                    moving_layer = layer
                    break
        if moving_layer is None:
            QMessageBox.warning(
                self,
                "Export Error",
                "No moving image layer found. Please load an image first."
            )
            return

        # Get registered image layer from parent widget
        registered_layer = getattr(self._parent, '_registered_image', None)
        if registered_layer is None:
            # Fallback: look for any registered image layer
            for layer in self.viewer.layers:
                if 'Registered' in layer.name or 'registered' in layer.name.lower():
                    registered_layer = layer
                    break
        if registered_layer is None:
            QMessageBox.warning(
                self,
                "Export Error",
                "No registered image layer found. Please run registration first."
            )
            return

        # Get output directory
        output_dir = self.output_edit.text()
        if not output_dir:
            QMessageBox.warning(
                self,
                "Export Error",
                "Please select an output directory first."
            )
            return

        # Get sample geometry
        sample_geometry = self.geometry_combo.currentText()

        # Get atlas name from parent
        atlas_name = getattr(self._parent, '_atlas_name', 'allen_mouse_25um')

        # Get anchoring from parent (this is the plane anchoring)
        anchoring = getattr(self._parent, '_plane_anchoring', None)
        if anchoring is None:
            # Fallback: create a default anchoring
            QMessageBox.warning(
                self,
                "Export Warning",
                "Anchoring vector not found. Using default anchoring. "
                "Results may not be accurate."
            )
            anchoring = np.array([0, 0, 0, 100, 0, 0, 0, 100, 0], dtype=np.float64)

        # Get damage mask if available and requested
        damage_mask = None
        if self.damage_checkbox.isChecked():
            damage_mask = getattr(self._parent, '_damage_mask', None)

        # Get moving image path (napari 0.7+ source is a pydantic model, not dict)
        moving_image_path = None
        if hasattr(moving_layer, 'source') and moving_layer.source:
            moving_image_path = getattr(moving_layer.source, 'path', None)
        if moving_image_path is None:
            # Save to temp file
            import tempfile
            from tifffile import imwrite
            temp_dir = tempfile.gettempdir()
            moving_image_path = os.path.join(temp_dir, "moving_image_temp.tiff")
            imwrite(moving_image_path, np.asarray(moving_layer.data))

        # Get registered image path
        registered_image_path = None
        if hasattr(registered_layer, 'source') and registered_layer.source:
            registered_image_path = getattr(registered_layer.source, 'path', None)
        if registered_image_path is None:
            import tempfile
            from tifffile import imwrite
            temp_dir = tempfile.gettempdir()
            registered_image_path = os.path.join(temp_dir, "registered_image_temp.tiff")
            imwrite(registered_image_path, np.asarray(registered_layer.data))

        try:
            pynutil_dir = export_for_pynutil(
                moving_image_path=str(moving_image_path),
                registered_image_path=str(registered_image_path),
                atlas_name=atlas_name,
                anchoring=np.asarray(anchoring),
                output_dir=output_dir,
                damage_mask=damage_mask,
                sample_geometry=sample_geometry,
            )
            self.output_edit.setText(pynutil_dir)  # Update with actual path
            self.results_text.append(f"Export successful: {pynutil_dir}")
            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported to PyNutil format:\n{pynutil_dir}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export: {str(e)}"
            )

    def run_quantification(self):
        """Run PyNutil quantification."""
        pynutil_dir = self.output_edit.text()
        if not pynutil_dir or not os.path.exists(pynutil_dir):
            self.results_text.setText(
                "Please export to PyNutil format first and ensure the directory exists."
            )
            return

        output_dir = os.path.dirname(pynutil_dir)
        atlas_name = getattr(self._parent, '_atlas_name', 'allen_mouse_25um')

        mode = "binary" if self.mode_combo.currentText() == "Binary Segmentation" else "intensity"

        kwargs = {}
        if mode == "binary":
            kwargs['object_cutoff'] = self.cutoff_spin.value()
        else:
            kwargs['intensity_channel'] = self.channel_combo.currentText()
            kwargs['min_intensity'] = self.min_intensity_spin.value()
            kwargs['max_intensity'] = self.max_intensity_spin.value()

        self.worker = PyNutilWorker(
            pynutil_dir=pynutil_dir,
            atlas_name=atlas_name,
            output_dir=output_dir,
            mode=mode,
            **kwargs,
        )

        self.worker.progress.connect(self.results_text.append)
        self.worker.finished.connect(self.quantification_finished)
        self.worker.error.connect(self.results_text.append)

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.worker.start()

    def quantification_finished(self, success, result):
        """Handle quantification completion."""
        self.progress_bar.setVisible(False)

        if success:
            df = result["df"]
            metadata = result["metadata"]

            # Determine count column based on mode (object_count for binary, pixel_count for intensity)
            count_column = 'pixel_count' if 'pixel_count' in df.columns else 'object_count'

            # Display summary
            summary = f"""
Quantification Complete!
========================
Objects/Pixels analyzed: {metadata.get('n_objects', metadata.get('n_pixels', 0))}
Atlas: {metadata['atlas_name']}
Damage mask applied: {metadata.get('damage_mask_applied', False)}

Top 10 regions:
"""
            if df is not None and len(df) > 0:
                summary += df.nlargest(10, count_column)[['name', count_column]].to_string()
            else:
                summary += "No regions found."

            self.results_text.setText(summary)
        else:
            self.results_text.setText(f"Error: {result}")

    def open_pynutil_gui(self):
        """Open PyNutil GUI with exported data."""
        pynutil_dir = self.output_edit.text()
        if not pynutil_dir or not os.path.exists(pynutil_dir):
            QMessageBox.warning(
                self,
                "Open PyNutil GUI",
                "Please export to PyNutil format first."
            )
            return

        # Launch PyNutil GUI from local repo
        try:
            # Find PyNutil GUI in local repo
            pynutil_repo = Path(__file__).parent.parent.parent.parent / "PyNutil"
            gui_script = pynutil_repo / "gui" / "PyNutilGUI.py"

            if not gui_script.exists():
                raise FileNotFoundError(
                    f"PyNutilGUI.py not found at {gui_script}\n"
                    "Make sure the PyNutil repository is in the same directory as brainglobe-registration."
                )

            # Launch GUI with settings file pre-loaded
            env = os.environ.copy()
            env['PYNUUTIL_SETTINGS'] = str(Path(pynutil_dir) / "settings.json")

            subprocess.Popen(
                [sys.executable, str(gui_script)],
                env=env,
                cwd=str(pynutil_repo)
            )
            QMessageBox.information(
                self,
                "PyNutil GUI",
                f"Opening PyNutil GUI...\n\n"
                f"Exported data location:\n{pynutil_dir}\n\n"
                f"In PyNutil GUI: File → Load Settings → Navigate to:\n"
                f"{Path(pynutil_dir) / 'settings.json'}"
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Open PyNutil GUI",
                f"Failed to open PyNutil GUI: {e}\n\n"
                f"You can manually open PyNutil GUI:\n"
                f"1. Navigate to: H:\\gsoc2026\\neuroinformatics\\brainglobe-registration\\PyNutil\n"
                f"2. Run: python gui\\PyNutilGUI.py\n"
                f"3. Load data from: {pynutil_dir}"
            )

    def _format_qc_report(self, report: QCReport) -> str:
        """Format QC report for display."""
        status_icon = lambda x: "[!]" if x else "[OK]"

        return f"""
Quality Control Report
======================

Image Statistics:
  Mean Intensity: {report.mean_intensity:.1f}
  Std Dev: {report.std_intensity:.1f}
  Range: [{report.min_intensity:.1f}, {report.max_intensity:.1f}]

Quality Flags:
  Low Signal: {status_icon(report.low_signal)}
  Saturated: {status_icon(report.saturated)}
  Potential Hemisphere: {status_icon(report.potential_hemisphere)}
  Potential Damage: {status_icon(report.potential_damage)}

Analysis:
  Asymmetry Score: {report.asymmetry_score:.2f}
  Damage Fraction: {report.damage_fraction:.2f}

Recommendations:
  Sample Geometry: {report.recommended_geometry}
  Damage Mask Needed: {"Yes" if report.requires_damage_mask else "No"}
  Overall Quality: {report.quality_score:.1f}/1.0
"""
