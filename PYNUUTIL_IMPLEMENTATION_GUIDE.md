# PyNutil Integration Implementation Guide
## Technical Specification for brainglobe-registration

---

## Difficulty Assessment

| Task | Difficulty (1-10) | Why |
|------|-------------------|-----|
| Plane Sampling PR (#164) | **10** | Complete architecture overhaul, 45 commits, 14 files changed, new module from scratch, automated method rewrites |
| PyNutil Integration (this guide) | **4** | Dependency addition, UI widget integration, data format conversion - no algorithm changes |

**Why PyNutil integration is EASIER:**
- PyNutil is a **dependency**, not a rewrite
- No changes to core registration algorithms
- UI widgets are modular (add new tab/widget)
- Data formats are compatible (JSON alignment files)
- Most logic is "call PyNutil function, display result"

---

## Part 1: Add PyNutil as Dependency

### 1.1 Update `pyproject.toml`

```toml
[project]
# ... existing config ...

dependencies = [
    "napari>=0.4.18, !=0.6.0",
    "bayesian-optimization",
    "brainglobe-atlasapi",
    "brainglobe-utils>=0.4.3",
    "dask",
    "dask-image",
    "fancylog",
    "itk-elastix>=0.24.0",
    "lxml_html_clean",
    "numpy",
    "pandas",
    "pytransform3d",
    "qtpy",
    "qt-niu",
    "scikit-image",
    "scipy",
    "tifffile",
    # ADD THESE:
    "pynutil>=1.0.0",           # Main PyNutil package
    "orjson",                    # For MeshView JSON export
    "nrrd",                      # For custom atlas loading
    "nibabel",                   # For NIfTI export (optional)
]
```

### 1.2 Install Dependencies

```bash
pip install -e ".[dev]"
```

---

## Part 2: Create PyNutil Integration Module

### 2.1 New File: `brainglobe_registration/pynutil_integration/__init__.py`

```python
"""
PyNutil integration for brainglobe-registration.

This module provides functionality to:
1. Export registration results in PyNutil-compatible format
2. Run PyNutil quantification on registered images
3. Display quality control and quantification results
"""

from .export import export_for_pynutil
from .quantify import run_pynutil_quantification
from .qc import QualityControlReport

__all__ = [
    "export_for_pynutil",
    "run_pynutil_quantification",
    "QualityControlReport",
]
```

### 2.2 New File: `brainglobe_registration/pynutil_integration/export.py`

```python
"""
Export registration results in PyNutil-compatible format.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np
from tifffile import imwrite


def export_for_pynutil(
    moving_image_path: str,
    registered_image_path: str,
    atlas_name: str,
    anchoring: np.ndarray,
    output_dir: str,
    damage_mask: Optional[np.ndarray] = None,
    deformation_fields: Optional[Tuple[str, str]] = None,
    sample_geometry: str = "full",
) -> str:
    """
    Export registration results in PyNutil-compatible format.
    
    Parameters
    ----------
    moving_image_path : str
        Path to the original moving image (brain section)
    registered_image_path : str
        Path to the registered image (after registration)
    atlas_name : str
        Name of the atlas used (e.g., "allen_mouse_25um")
    anchoring : np.ndarray
        9-element anchoring vector [ox,oy,oz, ux,uy,uz, vx,vy,vz]
    output_dir : str
        Output directory for PyNutil-compatible files
    damage_mask : np.ndarray, optional
        Boolean mask where True = damaged/excluded region
    deformation_fields : tuple, optional
        Paths to (deformation_field_0.tiff, deformation_field_1.tiff)
    sample_geometry : str, optional
        One of: "full", "left_hemi", "right_hemi", "quarter"
    
    Returns
    -------
    str
        Path to the created PyNutil directory
    """
    # Create output directory structure
    pynutil_dir = Path(output_dir) / "pynutil_compatible"
    pynutil_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy segmentation (moving image)
    seg_dir = pynutil_dir / "segmentations"
    seg_dir.mkdir(exist_ok=True)
    moving_name = Path(moving_image_path).name
    shutil.copy(moving_image_path, seg_dir / moving_name)
    
    # Copy registered image
    reg_dir = pynutil_dir / "registered"
    reg_dir.mkdir(exist_ok=True)
    shutil.copy(registered_image_path, reg_dir / "registered.tiff")
    
    # Copy deformation fields if available
    if deformation_fields:
        for field_path in deformation_fields:
            if os.path.exists(field_path):
                shutil.copy(field_path, reg_dir / Path(field_path).name)
    
    # Save damage mask if provided
    if damage_mask is not None:
        imwrite(pynutil_dir / "damage_mask.tiff", damage_mask.astype(np.uint8))
    
    # Build alignment.json (PyNutil format)
    alignment = build_alignment_json(
        filename=moving_name,
        anchoring=anchoring,
        image_path=registered_image_path,
        damage_mask=damage_mask,
        sample_geometry=sample_geometry,
    )
    
    with open(pynutil_dir / "alignment.json", "w") as f:
        json.dump(alignment, f, indent=2)
    
    # Build settings.json
    settings = {
        "alignment_json": str(pynutil_dir / "alignment.json"),
        "atlas_name": atlas_name,
        "segmentation_folder": str(seg_dir),
        "apply_damage_mask": damage_mask is not None,
        "segmentation_format": "binary",  # or "cellpose"
    }
    
    with open(pynutil_dir / "settings.json", "w") as f:
        json.dump(settings, f, indent=2)
    
    return str(pynutil_dir)


def build_alignment_json(
    filename: str,
    anchoring: np.ndarray,
    image_path: str,
    damage_mask: Optional[np.ndarray] = None,
    sample_geometry: str = "full",
) -> Dict[str, Any]:
    """
    Build PyNutil-compatible alignment JSON.
    
    Parameters
    ----------
    filename : str
        Name of the segmentation file
    anchoring : np.ndarray
        9-element anchoring vector
    image_path : str
        Path to the registered image
    damage_mask : np.ndarray, optional
        Damage mask array
    sample_geometry : str
        Sample geometry type
    
    Returns
    -------
    dict
        Alignment dictionary in PyNutil format
    """
    # Get image dimensions
    from tifffile import imread
    img = imread(image_path)
    height, width = img.shape[:2]
    
    slice_info = {
        "nr": 1,
        "filename": filename,
        "width": width,
        "height": height,
        "anchoring": anchoring.tolist(),
        "markers": None,  # Could add from deformation if available
    }
    
    # Add damage regions if mask provided
    if damage_mask is not None:
        damage_regions = mask_to_regions(damage_mask)
        slice_info["damage_regions"] = damage_regions
    
    # Add sample geometry metadata
    if sample_geometry != "full":
        slice_info["sample_geometry"] = sample_geometry
    
    return {"slices": [slice_info]}


def mask_to_regions(mask: np.ndarray) -> list:
    """
    Convert boolean damage mask to list of rectangular regions.
    
    Parameters
    ----------
    mask : np.ndarray
        Boolean mask where False = damaged
    
    Returns
    -------
    list
        List of dicts with x, y, width, height
    """
    from scipy.ndimage import label, find_objects
    
    # Invert: True = damaged
    damaged = ~mask
    
    # Label connected regions
    labeled, n_regions = label(damaged)
    
    regions = []
    slices = find_objects(labeled)
    
    for i, slc in enumerate(slices, 1):
        if slc is not None:
            y_slice, x_slice = slc
            regions.append({
                "x": int(x_slice.start),
                "y": int(y_slice.start),
                "width": int(x_slice.stop - x_slice.start),
                "height": int(y_slice.stop - y_slice.start),
            })
    
    return regions
```

### 2.3 New File: `brainglobe_registration/pynutil_integration/quantify.py`

```python
"""
Run PyNutil quantification on registered images.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

try:
    import PyNutil as pnt
    from PyNutil.processing.adapters.base import read_alignment
    from PyNutil.io.atlas_loader import load_atlas_data
    PYNUUTIL_AVAILABLE = True
except ImportError:
    PYNUUTIL_AVAILABLE = False
    pnt = None
    read_alignment = None
    load_atlas_data = None


def run_pynutil_quantification(
    pynutil_dir: str,
    atlas_name: str,
    output_dir: str,
    object_cutoff: int = 0,
    pixel_id: list = None,
    apply_damage_mask: bool = True,
) -> Tuple[pd.DataFrame, dict]:
    """
    Run PyNutil quantification on exported registration results.
    
    Parameters
    ----------
    pynutil_dir : str
        Path to PyNutil-compatible directory (from export_for_pynutil)
    atlas_name : str
        Name of the atlas
    output_dir : str
        Output directory for quantification results
    object_cutoff : int, optional
        Minimum object size for detection
    pixel_id : list, optional
        RGB color to match for binary segmentation
    apply_damage_mask : bool, optional
        Whether to apply damage mask in quantification
    
    Returns
    -------
    tuple
        (quantification_dataframe, metadata_dict)
    """
    if not PYNUUTIL_AVAILABLE:
        raise ImportError(
            "PyNutil is not installed. Install with: pip install pynutil"
        )
    
    # Load alignment
    alignment_path = os.path.join(pynutil_dir, "alignment.json")
    alignment = read_alignment(alignment_path)
    
    # Load atlas
    atlas = load_atlas_data(atlas_name)
    
    # Run segmentation to coordinates
    seg_dir = os.path.join(pynutil_dir, "segmentations")
    coords = pnt.seg_to_coords(
        folder=seg_dir,
        registration=alignment,
        atlas=atlas,
        pixel_id=pixel_id or [0, 0, 0],
        object_cutoff=object_cutoff,
        apply_damage_mask=apply_damage_mask,
    )
    
    # Quantify
    label_df = pnt.quantify_coords(coords, atlas, apply_damage_mask=apply_damage_mask)
    
    # Save results
    pnt.save_analysis(
        output_dir,
        coords,
        atlas,
        label_df=label_df,
    )
    
    metadata = {
        "n_objects": len(coords.objects.points) if coords.objects else 0,
        "n_pixels": len(coords.points.points),
        "atlas_name": atlas_name,
        "damage_mask_applied": apply_damage_mask,
    }
    
    return label_df, metadata


def run_intensity_quantification(
    pynutil_dir: str,
    atlas_name: str,
    output_dir: str,
    intensity_channel: str = "grayscale",
    min_intensity: Optional[int] = None,
    max_intensity: Optional[int] = None,
    apply_damage_mask: bool = True,
) -> Tuple[pd.DataFrame, dict]:
    """
    Run PyNutil intensity quantification (for fluorescence images).
    
    Parameters
    ----------
    pynutil_dir : str
        Path to PyNutil-compatible directory
    atlas_name : str
        Name of the atlas
    output_dir : str
        Output directory for results
    intensity_channel : str, optional
        Channel to use: "R", "G", "B", or "grayscale"
    min_intensity : int, optional
        Minimum intensity threshold
    max_intensity : int, optional
        Maximum intensity threshold
    apply_damage_mask : bool, optional
        Whether to apply damage mask
    
    Returns
    -------
    tuple
        (quantification_dataframe, metadata_dict)
    """
    if not PYNUUTIL_AVAILABLE:
        raise ImportError("PyNutil is not installed")
    
    # Load alignment
    alignment_path = os.path.join(pynutil_dir, "alignment.json")
    alignment = read_alignment(alignment_path)
    
    # Load atlas
    atlas = load_atlas_data(atlas_name)
    
    # Run image to coordinates (intensity mode)
    image_dir = os.path.join(pynutil_dir, "segmentations")
    coords = pnt.image_to_coords(
        folder=image_dir,
        registration=alignment,
        atlas=atlas,
        intensity_channel=intensity_channel,
        min_intensity=min_intensity,
        max_intensity=max_intensity,
        apply_damage_mask=apply_damage_mask,
    )
    
    # Quantify
    label_df = pnt.quantify_coords(coords, atlas, apply_damage_mask=apply_damage_mask)
    
    # Save results
    pnt.save_analysis(
        output_dir,
        coords,
        atlas,
        label_df=label_df,
    )
    
    metadata = {
        "n_pixels": len(coords.points.points),
        "atlas_name": atlas_name,
        "intensity_channel": intensity_channel,
        "damage_mask_applied": apply_damage_mask,
    }
    
    return label_df, metadata
```

### 2.4 New File: `brainglobe_registration/pynutil_integration/qc.py`

```python
"""
Quality control report for PyNutil integration.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import numpy as np


@dataclass
class QCReport:
    """Quality control report for a brain section image."""
    
    # Image statistics
    mean_intensity: float = 0.0
    std_intensity: float = 0.0
    min_intensity: float = 0.0
    max_intensity: float = 0.0
    
    # Quality flags
    low_signal: bool = False
    saturated: bool = False
    potential_hemisphere: bool = False
    potential_damage: bool = False
    has_artifacts: bool = False
    
    # Detailed analysis
    asymmetry_score: float = 0.0  # Left-right intensity difference
    damage_fraction: float = 0.0  # Fraction of image that is damaged
    artifact_regions: List[Dict] = field(default_factory=list)
    
    # Recommendations
    recommended_geometry: str = "full"
    requires_damage_mask: bool = False
    quality_score: float = 1.0  # 0-1, higher is better
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "statistics": {
                "mean": self.mean_intensity,
                "std": self.std_intensity,
                "min": self.min_intensity,
                "max": self.max_intensity,
            },
            "flags": {
                "low_signal": self.low_signal,
                "saturated": self.saturated,
                "potential_hemisphere": self.potential_hemisphere,
                "potential_damage": self.potential_damage,
                "has_artifacts": self.has_artifacts,
            },
            "analysis": {
                "asymmetry_score": self.asymmetry_score,
                "damage_fraction": self.damage_fraction,
            },
            "recommendations": {
                "geometry": self.recommended_geometry,
                "damage_mask": self.requires_damage_mask,
                "quality_score": self.quality_score,
            },
        }


def analyze_image_quality(
    image: np.ndarray,
    threshold_low: float = 50,
    threshold_high: float = 250,
    saturation_fraction: float = 0.20,
    asymmetry_threshold: float = 0.3,
) -> QCReport:
    """
    Analyze image quality and detect potential issues.
    
    Parameters
    ----------
    image : np.ndarray
        Input image (2D or 3D)
    threshold_low : float
        Intensity threshold for low signal detection
    threshold_high : float
        Intensity threshold for saturation detection
    saturation_fraction : float
        Fraction of pixels that must be saturated to flag
    asymmetry_threshold : float
        Threshold for left-right asymmetry detection
    
    Returns
    -------
    QCReport
        Quality control report
    """
    # Handle 3D images (take max projection or middle slice)
    if image.ndim == 3:
        image = image.max(axis=0) if image.shape[0] > 1 else image[0]
    
    # Convert to float for analysis
    img = image.astype(np.float64)
    
    report = QCReport()
    
    # Basic statistics
    report.mean_intensity = float(np.mean(img))
    report.std_intensity = float(np.std(img))
    report.min_intensity = float(np.min(img))
    report.max_intensity = float(np.max(img))
    
    # Check 1: Low signal
    report.low_signal = report.mean_intensity < threshold_low
    
    # Check 2: Saturation
    if img.max() > 0:
        saturated_fraction = np.sum(img >= img.max() * 0.99) / img.size
        report.saturated = saturated_fraction > saturation_fraction
    
    # Check 3: Left-right asymmetry (hemisphere detection)
    h, w = img.shape[:2]
    left_half = img[:, :w//2]
    right_half = img[:, w//2:]
    
    left_mean = np.mean(left_half)
    right_mean = np.mean(right_half)
    overall_mean = (left_mean + right_mean) / 2
    
    if overall_mean > 0:
        report.asymmetry_score = abs(left_mean - right_mean) / overall_mean
        report.potential_hemisphere = report.asymmetry_score > asymmetry_threshold
    
    # Check 4: Large black regions (damage detection)
    from scipy.ndimage import label
    
    # Threshold for "black" (adjust based on image type)
    black_threshold = img.max() * 0.05
    black_mask = img < black_threshold
    
    labeled, n_regions = label(black_mask)
    
    # Find large black regions
    total_pixels = img.size
    large_black_pixels = 0
    
    for i in range(1, n_regions + 1):
        region_size = np.sum(labeled == i)
        if region_size > (total_pixels * 0.05):  # >5% of image
            large_black_pixels += region_size
            report.artifact_regions.append({
                "size": int(region_size),
                "type": "black_region",
            })
    
    report.damage_fraction = large_black_pixels / total_pixels
    report.potential_damage = report.damage_fraction > 0.10
    
    # Generate recommendations
    if report.potential_hemisphere:
        # Determine which hemisphere based on which side is brighter
        if left_mean > right_mean:
            report.recommended_geometry = "left_hemi"
        else:
            report.recommended_geometry = "right_hemi"
    
    if report.potential_damage:
        report.requires_damage_mask = True
    
    # Calculate overall quality score
    quality_deductions = 0.0
    if report.low_signal:
        quality_deductions += 0.3
    if report.saturated:
        quality_deductions += 0.2
    if report.potential_damage:
        quality_deductions += 0.2
    if report.has_artifacts:
        quality_deductions += 0.1
    
    report.quality_score = max(0.0, 1.0 - quality_deductions)
    
    return report
```

---

## Part 3: UI Integration

### 3.1 New File: `brainglobe_registration/widgets/pynutil_widget.py`

```python
"""
PyNutil integration widget for brainglobe-registration.
"""

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
)
from qtpy.QtCore import Qt, Signal, QThread
from napari.viewer import Viewer

from ..pynutil_integration import (
    export_for_pynutil,
    run_pynutil_quantification,
    QualityControlReport,
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
            
            self.progress.emit(f"Quantification complete: {metadata['n_objects']} objects")
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
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Quality Control Section
        qc_group = QGroupBox("Quality Control")
        qc_layout = QVBoxLayout()
        
        self.qc_button = QPushButton("Analyze Image Quality")
        self.qc_button.clicked.connect(self.run_qc_analysis)
        qc_layout.addWidget(self.qc_button)
        
        self.qc_results = QTextEdit()
        self.qc_results.setReadOnly(True)
        self.qc_results.setMaximumHeight(150)
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
            "Full Brain",
            "Left Hemisphere",
            "Right Hemisphere",
            "Quarter (Anterior)",
            "Quarter (Posterior)",
        ])
        geom_layout.addWidget(self.geometry_combo)
        export_layout.addLayout(geom_layout)
        
        # Damage mask checkbox
        self.damage_checkbox = QCheckBox("Include Damage Mask")
        self.damage_checkbox.setChecked(False)
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
        mode_layout.addWidget(self.mode_combo)
        quant_layout.addLayout(mode_layout)
        
        # Object cutoff (for binary mode)
        cutoff_layout = QHBoxLayout()
        cutoff_layout.addWidget(QLabel("Object Cutoff:"))
        self.cutoff_spin = QSpinBox()
        self.cutoff_spin.setRange(0, 10000)
        self.cutoff_spin.setValue(0)
        cutoff_layout.addWidget(self.cutoff_spin)
        quant_layout.addLayout(cutoff_layout)
        
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
        quant_layout.addWidget(self.results_text)
        
        quant_group.setLayout(quant_layout)
        layout.addWidget(quant_group)
        
        # Open in PyNutil GUI button
        self.open_gui_button = QPushButton("Open in PyNutil GUI")
        self.open_gui_button.clicked.connect(self.open_pynutil_gui)
        layout.addWidget(self.open_gui_button)
    
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
        moving_layer = self.viewer.layers.get("moving_image", None)
        if moving_layer is None:
            self.qc_results.setText("No moving image layer found.")
            return
        
        image = moving_layer.data
        if hasattr(image, 'compute'):
            image = image.compute()
        
        # Analyze
        report = analyze_image_quality(np.asarray(image))
        
        # Display results
        self.qc_results.setText(format_qc_report(report))
    
    def run_export(self):
        """Export registration results to PyNutil format."""
        # Get required data from registration widget
        # (This would be passed from the parent widget)
        pass
    
    def run_quantification(self):
        """Run PyNutil quantification."""
        pynutil_dir = self.output_edit.text()
        if not pynutil_dir:
            self.results_text.setText("Please export to PyNutil format first.")
            return
        
        output_dir = self.output_edit.text()
        atlas_name = "allen_mouse_25um"  # Get from registration widget
        
        mode = "binary" if self.mode_combo.currentText() == "Binary Segmentation" else "intensity"
        
        self.worker = PyNutilWorker(
            pynutil_dir=pynutil_dir,
            atlas_name=atlas_name,
            output_dir=output_dir,
            mode=mode,
            object_cutoff=self.cutoff_spin.value(),
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
            
            # Display summary
            summary = f"""
Quantification Complete!
========================
Objects detected: {metadata['n_objects']}
Pixels analyzed: {metadata['n_pixels']}
Atlas: {metadata['atlas_name']}

Top 10 regions by count:
{df.nlargest(10, 'object_count')[['name', 'object_count']].to_string()}
"""
            self.results_text.setText(summary)
        else:
            self.results_text.setText(f"Error: {result}")
    
    def open_pynutil_gui(self):
        """Open PyNutil GUI with exported data."""
        import subprocess
        import sys
        
        pynutil_dir = self.output_edit.text()
        if not pynutil_dir:
            return
        
        # Launch PyNutil GUI
        try:
            subprocess.Popen([sys.executable, "-m", "PyNutil.gui.PyNutilGUI"])
        except Exception as e:
            self.results_text.append(f"Failed to open PyNutil GUI: {e}")


def format_qc_report(report: QCReport) -> str:
    """Format QC report for display."""
    status_icon = lambda x: "⚠️" if x else "✅"
    
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
```

---

## Part 4: Update Registration Widget

### 4.1 Modify `registration_widget.py`

Add PyNutil widget to the tabs:

```python
# In RegistrationWidget.__init__(), after creating other widgets:

# Add PyNutil integration tab
self._pynutil_widget = PyNutilWidget(self._viewer, self)
self._tab_widget.addTab(self._pynutil_widget, "PyNutil Quantification")
```

---

## Part 5: Testing

### 5.1 New File: `tests/test_pynutil_integration.py`

```python
"""Tests for PyNutil integration."""

import pytest
import numpy as np
from pathlib import Path

from brainglobe_registration.pynutil_integration import (
    export_for_pynutil,
    analyze_image_quality,
)


def test_export_for_pynutil(tmp_path):
    """Test PyNutil export creates correct structure."""
    # Create test image
    test_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    image_path = tmp_path / "test_image.tiff"
    
    from tifffile import imwrite
    imwrite(image_path, test_image)
    
    # Test export
    anchoring = np.array([10, 20, 30, 100, 0, 0, 0, 100, 0])
    output_dir = tmp_path / "output"
    
    pynutil_dir = export_for_pynutil(
        moving_image_path=str(image_path),
        registered_image_path=str(image_path),
        atlas_name="allen_mouse_25um",
        anchoring=anchoring,
        output_dir=str(output_dir),
    )
    
    # Verify structure
    pynutil_path = Path(pynutil_dir)
    assert (pynutil_path / "segmentations").exists()
    assert (pynutil_path / "alignment.json").exists()
    assert (pynutil_path / "settings.json").exists()


def test_analyze_image_quality():
    """Test image quality analysis."""
    # Test normal image
    normal_img = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    report = analyze_image_quality(normal_img)
    assert report.quality_score > 0.5
    assert not report.potential_hemisphere
    
    # Test hemisphere image (asymmetric)
    hemi_img = np.zeros((100, 100), dtype=np.uint8)
    hemi_img[:, :50] = np.random.randint(100, 200, (100, 50), dtype=np.uint8)
    report = analyze_image_quality(hemi_img)
    assert report.potential_hemisphere
    assert report.recommended_geometry in ["left_hemi", "right_hemi"]
    
    # Test damaged image
    damaged_img = np.random.randint(100, 200, (100, 100), dtype=np.uint8)
    damaged_img[:50, :50] = 0  # Large black region
    report = analyze_image_quality(damaged_img)
    assert report.potential_damage
```

---

## Part 6: Documentation

### 6.1 Update README.md

Add section:

```markdown
## PyNutil Integration

brainglobe-registration now includes integration with [PyNutil](https://github.com/Neural-Systems-at-UIO/PyNutil) for downstream quantification.

### Quick Start

1. Register your image using brainglobe-registration
2. Go to the "PyNutil Quantification" tab
3. Click "Analyze Image Quality" to check for issues
4. Click "Export to PyNutil Format"
5. Click "Run PyNutil Quantification"

### Features

- **Quality Control**: Automatic detection of hemisphere-only samples and damaged tissue
- **Damage-Aware Quantification**: Exclude damaged regions from analysis
- **One-Click Export**: Seamless handoff to PyNutil
```

---

## Summary

### Files to Create

```
brainglobe_registration/
├── pynutil_integration/
│   ├── __init__.py
│   ├── export.py
│   ├── quantify.py
│   └── qc.py
└── widgets/
    └── pynutil_widget.py

tests/
└── test_pynutil_integration.py
```

### Files to Modify

```
pyproject.toml          # Add dependencies
registration_widget.py  # Add PyNutil tab
README.md               # Add documentation
```

### Total Effort

| Component | Lines of Code | Time Estimate |
|-----------|---------------|---------------|
| Export module | ~150 | 2 hours |
| Quantify module | ~100 | 1 hour |
| QC module | ~150 | 2 hours |
| UI widget | ~250 | 3 hours |
| Integration | ~50 | 1 hour |
| Tests | ~100 | 2 hours |
| **Total** | **~800** | **~11 hours** |

---

## Comparison: Plane Sampling PR vs PyNutil Integration

| Aspect | Plane Sampling (#164) | PyNutil Integration |
|--------|----------------------|---------------------|
| Lines changed | 1,476 additions | ~800 additions |
| Files changed | 14 | ~8 |
| Core algorithm changes | Yes (complete rewrite) | No (wrapper around existing) |
| New dependencies | No | Yes (PyNutil) |
| Breaking changes | Yes | No |
| Tests needed | Comprehensive | Integration-focused |
| **Difficulty** | **10/10** | **4/10** |

The PyNutil integration is **significantly easier** because:
1. PyNutil already exists and works
2. We're just calling its functions, not rewriting algorithms
3. Data formats are already compatible
4. UI is modular (just add a new tab)
5. No changes to core registration logic
