# Point-Based Registration Guide

## Overview

Point-based registration is a **hybrid approach** that combines automatic intensity-based registration with **manually specified landmark pairs**. It helps solve difficult registration problems where automatic methods alone may fail.

---

## The Problem: When Automatic Registration Fails

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTOMATIC REGISTRATION                        │
│                                                                  │
│   Atlas (Fixed)              Sample (Moving)                     │
│   ┌──────────────┐            ┌──────────────┐                  │
│   │   ███████    │            │    ░░░░░     │                  │
│   │  ██▓▓▓▓██    │            │   ▒▒▒▒▒▒     │                  │
│   │  ██▓▓▓▓██    │  ──────►   │   ▒▒▒▒▒▒     │  ❌ FAILS!       │
│   │   ███████    │            │    ░░░░░     │                  │
│   └──────────────┘            └──────────────┘                  │
│                                                                  │
│   Why it fails:                                                  │
│   • Very different contrast (MRI vs histology)                   │
│   • Partial overlap (sample is cropped)                          │
│   • Large initial misalignment                                   │
│   • Low signal-to-noise ratio                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Solution: Add Landmark Constraints

```
┌─────────────────────────────────────────────────────────────────┐
│                 POINT-BASED REGISTRATION                         │
│                                                                  │
│   Step 1: User clicks corresponding landmarks                    │
│   ─────────────────────────────────────────                      │
│                                                                  │
│   Atlas (Fixed)              Sample (Moving)                     │
│   ┌──────────────┐            ┌──────────────┐                  │
│   │   ● A        │            │        ● A'  │                  │
│   │      ● B     │            │     ● B'     │                  │
│   │         ● C  │            │  ● C'        │                  │
│   │   ● D        │            │        ● D'  │                  │
│   └──────────────┘            └──────────────┘                  │
│                                                                  │
│   A ↔ A' : Anterior commissure                                   │
│   B ↔ B' : Posterior commissure                                  │
│   C ↔ C' : Optic chiasm                                          │
│   D ↔ D' : Pineal gland                                          │
│                                                                  │
│   Step 2: Elastix minimizes BOTH:                                │
│   ──────────────────────────────                                 │
│   1. Image similarity (MI, NCC, SSIM)                            │
│   2. Point distances (||A - A'|| + ||B - B'|| + ...)             │
│                                                                  │
│   Result: ✅ Successful registration!                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works: The Math

### Combined Objective Function

```
                    ┌─────────────────────────┐
                    │  TOTAL COST FUNCTION    │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼                                       ▼
    ┌───────────────┐                       ┌───────────────┐
    │   INTENSITY   │                       │    POINT      │
    │    TERM       │                       │    TERM       │
    │               │                       │               │
    │  Similarity   │                       │  Euclidean    │
    │  (MI, NCC)    │                       │  Distance     │
    │               │                       │               │
    │  w₁ × S(I)    │                       │  w₂ × D(P)    │
    └───────────────┘                       └───────────────┘

    Total Cost = w₁ × S(I) + w₂ × D(P)

    where:
    S(I) = -MutualInformation(fixed, moving)
           or -NormalizedCrossCorrelation(fixed, moving)
    
    D(P) = Σ ||p_fixed_i - T(p_moving_i)||²
           (sum of squared distances between matched points)
    
    w₁, w₂ = weights (typically w₁ >> w₂)
```

### Point Distance Metric

```
For N landmark pairs:

                    N
    D(P) = (1/N) × Σ ||pᵢ - qᵢ||²
                   i=1

    where:
    pᵢ = landmark i on fixed image (atlas)
    qᵢ = landmark i on moving image (sample)
    ||·|| = Euclidean distance

    Goal: Minimize D(P) → points should overlap after transform
```

---

## Elastix Integration

### Parameter Map Configuration

```python
import SimpleITK as sitk

# Get default parameter map
parameterMap = sitk.GetDefaultParameterMap("bspline")

# Add point-based metric (MUST be last in the list!)
parameterMap["Metric"].append("CorrespondingPointsEuclideanDistanceMetric")

# Optional: Set weight for point metric
parameterMap["Metric0Weight"] = "1.0"  # Intensity metric weight
parameterMap["Metric1Weight"] = "0.1"  # Point metric weight (lower)

# Point files are specified separately via SetFixedPointSetFileName
```

### Point File Format (Elastix .pts)

```
# Format 1: Pixel coordinates (index)
index
4
102.5  256.3  128.0
178.2  310.5  145.7
200.0  280.0  160.2
150.3  290.8  135.5

# Format 2: World coordinates (point) - RECOMMENDED
point
4
-2.5  1.3  0.5
1.2  -0.8  2.1
0.0  0.5  -1.2
-1.0  0.2  0.8
```

**File structure:**
1. Line 1: `index` (pixel) or `point` (world/mm)
2. Line 2: Number of points (integer)
3. Lines 3+: X Y [Z] coordinates (space-separated)

---

## Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    POINT-BASED REGISTRATION WORKFLOW                     │
└─────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  1. LOAD     │
    │  ATLAS +     │
    │  SAMPLE      │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  2. ENABLE   │
    │  POINT MODE  │◄────────────────────────────────┐
    └──────┬───────┘                                 │
           │                                         │
           ▼                                         │
    ┌──────────────┐         ┌─────────────────────┐ │
    │  3. SELECT   │────────►│  napari POINTS      │ │
    │  LANDMARKS   │         │  LAYER (Atlas)      │ │
    │              │         └─────────────────────┘ │
    └──────┬───────┘                                 │
           │                                         │
           │  ┌─────────────────────────────────────┘
           │  │
           ▼  ▼
    ┌──────────────┐         ┌─────────────────────┐
    │  4. MATCH    │────────►│  napari POINTS      │
    │  CORRESPOND- │         │  LAYER (Sample)     │
    │  ING POINTS  │         └─────────────────────┘
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  5. EXPORT   │
    │  POINT FILES │
    │  (.pts)      │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  6. RUN      │
    │  ELASTIX     │
    │  + POINTS    │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  7. SAVE     │
    │  RESULTS +   │
    │  POINT PAIRS │
    └──────────────┘
```

---

## Example Use Case: Registering Mouse Brain Sections

### Scenario
A neuroscientist has **coronal brain sections** from a histology experiment and wants to register them to the **Allen Mouse Brain Atlas**. The sections are:
- Cut at a slight angle (~15° off coronal)
- Have different contrast (Nissl stain vs. autofluorescence)
- Cover only the posterior half of the brain

### Without Point-Based Registration
```
Automatic registration tries to align based on intensity alone:

    Atlas                    Sample
    ┌────────────┐          ┌────────────┐
    │  ███████   │          │   ░░░░     │
    │ ██▓▓▓▓▓██  │    ──►   │  ▒▒▒▒▒     │  ❌ Wrong!
    │ ██▓▓▓▓▓██  │          │  ▒▒▒▒▒     │  (anterior-posterior
    │  ███████   │          │   ░░░░     │   flip occurred)
    └────────────┘          └────────────┘
    
    MI = 0.85 (high, but WRONG alignment)
```

### With Point-Based Registration
```
User clicks 6 landmarks BEFORE running registration:

    Atlas (Fixed)           Sample (Moving)
    ┌────────────┐          ┌────────────┐
    │  ● CA1     │          │     CA1 ●  │
    │     ● DG   │          │   DG ●     │
    │  ● CC      │          │     ● CC   │
    │     ● LV   │          │   LV ●     │
    │  ● SC      │          │     ● SC   │
    │     ● PAG  │          │   PAG ●    │
    └────────────┘          └────────────┘
    
    CA1 = CA1 hippocampus
    DG  = Dentate gyrus
    CC  = Corpus callosum
    LV  = Lateral ventricle
    SC  = Superior colliculus
    PAG = Periaqueductal gray

    Registration result:
    
    Atlas                    Sample (transformed)
    ┌────────────┐          ┌────────────┐
    │  ███████   │          │   ░░░░     │
    │ ██▓▓▓▓▓██  │    ──►   │  ▒▒▒▒▒     │  ✅ Correct!
    │ ██▓▓▓▓▓██  │          │  ▒▒▒▒▒     │  (points aligned)
    │  ███████   │          │   ░░░░     │
    └────────────┘          └────────────┘
    
    MI = 0.82 (slightly lower, but CORRECT alignment)
    Point Distance = 2.3 pixels (excellent)
```

---

## Implementation Guide

### Architecture

```
brainglobe_registration/
├── widgets/
│   └── point_based_registration_widget.py    # NEW
│       ├── PointPairModel
│       ├── PointPairView
│       └── PointFileExporter
├── utils/
│   └── point_registration.py                  # NEW
│       ├── create_point_file()
│       ├── load_point_file()
│       └── validate_point_pairs()
├── elastix/
│   └── register.py                            # MODIFY
│       └── run_registration()  # Add point support
└── registration_widget.py                     # MODIFY
    └── RegistrationWidget
        └── _on_run_button_click()  # Wire up point registration
```

### Step 1: Point File Utilities (`utils/point_registration.py`)

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np


@dataclass
class LandmarkPair:
    """A pair of corresponding landmarks."""
    name: str
    fixed_coords: np.ndarray  # Atlas (world coordinates)
    moving_coords: np.ndarray  # Sample (world coordinates)


def create_point_file(
    point_pairs: List[LandmarkPair],
    output_path: Path,
    use_world_coords: bool = True
) -> Path:
    """
    Create an Elastix .pts point file.
    
    Parameters
    ----------
    point_pairs : List[LandmarkPair]
        List of landmark pairs with fixed and moving coordinates
    output_path : Path
        Where to save the .pts file
    use_world_coords : bool
        If True, use world coordinates (recommended)
        If False, use pixel indices
    
    Returns
    -------
    Path
        Path to the created .pts file
    """
    with open(output_path, 'w') as f:
        # Header
        f.write("point\n" if use_world_coords else "index\n")
        f.write(f"{len(point_pairs)}\n")
        
        # Write fixed image points (Elastix expects fixed points)
        for pair in point_pairs:
            coords = pair.fixed_coords if use_world_coords else pair.fixed_coords
            f.write(f"{' '.join(f'{c:.2f}' for c in coords)}\n")
    
    return output_path


def load_point_file(path: Path) -> List[np.ndarray]:
    """
    Load an Elastix .pts point file.
    
    Returns
    -------
    List[np.ndarray]
        List of point coordinates (N, D) array
    """
    points = []
    with open(path, 'r') as f:
        lines = f.readlines()
        
        coord_type = lines[0].strip()  # 'point' or 'index'
        num_points = int(lines[1].strip())
        
        for line in lines[2:2 + num_points]:
            coords = [float(x) for x in line.split()]
            points.append(np.array(coords))
    
    return points


def validate_point_pairs(
    fixed_points: List[np.ndarray],
    moving_points: List[np.ndarray],
    fixed_shape: Tuple[int, ...],
    moving_shape: Tuple[int, ...]
) -> Tuple[bool, str]:
    """
    Validate that point pairs are within image bounds.
    
    Returns
    -------
    Tuple[bool, str]
        (is_valid, error_message)
    """
    if len(fixed_points) != len(moving_points):
        return False, "Mismatched number of point pairs"
    
    if len(fixed_points) < 3:
        return False, "Need at least 3 point pairs for 3D registration"
    
    # Check bounds (simplified - would need proper coordinate conversion)
    for i, (fp, mp) in enumerate(zip(fixed_points, moving_points)):
        if not np.all(fp >= 0) or not np.all(fp < fixed_shape):
            return False, f"Fixed point {i} out of bounds"
        if not np.all(mp >= 0) or not np.all(mp < moving_shape):
            return False, f"Moving point {i} out of bounds"
    
    return True, ""
```

### Step 2: Point Widget (`widgets/point_based_registration_widget.py`)

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QLineEdit,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
import napari
from typing import List, Optional
from ..utils.point_registration import LandmarkPair


class PointBasedRegistrationWidget(QWidget):
    """Widget for configuring point-based registration."""
    
    # Signals
    points_updated = pyqtSignal(list)  # Emits list of LandmarkPair
    
    def __init__(self, viewer: napari.Viewer, parent=None):
        super().__init__(parent)
        self.viewer = viewer
        self.landmark_pairs: List[LandmarkPair] = []
        self.current_pair_name = ""
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Enable checkbox
        self.enabled_checkbox = QCheckBox("Enable Point-Based Registration")
        layout.addWidget(self.enabled_checkbox)
        
        # Point pair list
        self.pair_list = QListWidget()
        layout.addWidget(self.pair_list)
        
        # Add point pair button
        self.add_pair_button = QPushButton("Add Landmark Pair")
        self.add_pair_button.clicked.connect(self._on_add_pair)
        layout.addWidget(self.add_pair_button)
        
        # Named text input for landmark
        self.landmark_name_edit = QLineEdit()
        self.landmark_name_edit.setPlaceholderText("Landmark name (e.g., 'CA1')")
        layout.addWidget(self.landmark_name_edit)
        
        # Instructions
        self.instruction_label = QLabel(
            "1. Click 'Add Landmark Pair'\n"
            "2. Click a point on the ATLAS layer\n"
            "3. Click the corresponding point on the SAMPLE layer\n"
            "4. Repeat for 4-10 landmarks"
        )
        layout.addWidget(self.instruction_label)
        
        # Export button
        self.export_button = QPushButton("Export Point Files")
        self.export_button.clicked.connect(self._on_export)
        layout.addWidget(self.export_button)
    
    def _connect_signals(self):
        # Connect to napari mouse events
        self.viewer.mouse_drag_callbacks.append(self._on_mouse_click)
    
    def _on_add_pair(self):
        """Start creating a new landmark pair."""
        name = self.landmark_name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self, "Missing Name", "Please enter a landmark name"
            )
            return
        
        # Create point layers if they don't exist
        if "atlas_landmarks" not in self.viewer.layers:
            self.viewer.add_points(
                name="atlas_landmarks",
                face_color="red",
                size=10,
                ndim=3
            )
        
        if "sample_landmarks" not in self.viewer.layers:
            self.viewer.add_points(
                name="sample_landmarks",
                face_color="blue",
                size=10,
                ndim=2  # Sample is 2D
            )
        
        # Add to list
        item = QListWidgetItem(f"{name} (not paired)")
        item.setData(1, {"name": name, "paired": False})
        self.pair_list.addItem(item)
    
    def _on_mouse_click(self, viewer, event):
        """Handle point selection on atlas or sample layers."""
        # This would need more sophisticated handling
        # to determine which layer was clicked and add points
        pass
    
    def _on_export(self):
        """Export point pairs to .pts files."""
        from pathlib import Path
        from ..utils.point_registration import create_point_file
        
        output_dir = Path(self.viewer.dims.point[0])  # Or use output directory
        fixed_pts = output_dir / "fixed_points.pts"
        moving_pts = output_dir / "moving_points.pts"
        
        create_point_file(self.landmark_pairs, fixed_pts)
        # Moving points would need inverse handling
        
        QMessageBox.information(
            self, "Export Complete",
            f"Point files saved to:\n{fixed_pts}\n{moving_pts}"
        )
    
    def get_point_pairs(self) -> List[LandmarkPair]:
        """Return current landmark pairs."""
        return self.landmark_pairs
```

### Step 3: Modify Elastix Wrapper (`elastix/register.py`)

```python
def run_registration(
    fixed_image: np.ndarray,
    moving_image: np.ndarray,
    parameter_map: dict,
    fixed_point_file: Optional[Path] = None,  # NEW
    moving_point_file: Optional[Path] = None,  # NEW
    output_directory: Optional[Path] = None,
) -> Tuple[np.ndarray, dict]:
    """
    Run Elastix registration.
    
    Parameters
    ----------
    fixed_image : np.ndarray
        Fixed (reference) image
    moving_image : np.ndarray
        Moving (sample) image
    parameter_map : dict
        Elastix parameter map
    fixed_point_file : Optional[Path]  # NEW
        Path to fixed image point file (.pts)
    moving_point_file : Optional[Path]  # NEW
        Path to moving image point file (.pts)
    output_directory : Optional[Path]
        Output directory for Elastix files
    
    Returns
    -------
    Tuple[np.ndarray, dict]
        (registered_image, transform_parameters)
    """
    import SimpleITK as sitk
    
    # Convert to SimpleITK images
    fixed_sitk = sitk.GetImageFromArray(fixed_image.astype(np.float32))
    moving_sitk = sitk.GetImageFromArray(moving_image.astype(np.float32))
    
    # Create Elastix filter
    elastix_filter = sitk.ElastixImageFilter()
    elastix_filter.SetFixedImage(fixed_sitk)
    elastix_filter.SetMovingImage(moving_sitk)
    
    # Set parameter map
    parameter_map_object = sitk.GetParameterMap()
    for key, value in parameter_map.items():
        if isinstance(value, list):
            parameter_map_object[key] = [str(v) for v in value]
        else:
            parameter_map_object[key] = [str(value)]
    
    elastix_filter.SetParameterMap(parameter_map_object)
    
    # NEW: Add point files if provided
    if fixed_point_file is not None:
        elastix_filter.SetFixedPointSetFileName(str(fixed_point_file))
    
    if moving_point_file is not None:
        elastix_filter.SetMovingPointSetFileName(str(moving_point_file))
    
    # Set output directory
    if output_directory:
        elastix_filter.SetOutputDirectory(str(output_directory))
    
    # Execute registration
    registered_image = elastix_filter.Execute()
    
    # Get transform parameters
    transform_params = elastix_filter.GetTransformParameterMap()
    
    return sitk.GetArrayFromImage(registered_image), transform_params
```

### Step 4: Wire Up Main Widget (`registration_widget.py`)

```python
# Add to __init__
self.point_registration_widget = PointBasedRegistrationWidget(self._viewer)
self.layout.addWidget(self.point_registration_widget)

# Modify _on_run_button_click
def _on_run_button_click(self):
    # ... existing code ...
    
    # NEW: Handle point-based registration
    fixed_point_file = None
    moving_point_file = None
    
    if self.point_registration_widget.enabled_checkbox.isChecked():
        from pathlib import Path
        from .utils.point_registration import create_point_file
        
        point_pairs = self.point_registration_widget.get_point_pairs()
        
        if len(point_pairs) < 3:
            QMessageBox.warning(
                self, "Insufficient Points",
                "Point-based registration requires at least 3 landmark pairs"
            )
            return
        
        # Export point files
        fixed_point_file = self.output_directory / "fixed_landmarks.pts"
        moving_point_file = self.output_directory / "moving_landmarks.pts"
        
        create_point_file(point_pairs, fixed_point_file)
        # Note: moving points need special handling for 2D->3D
        
        # Add point metric to parameter map
        self.elastix_params["Metric"].append(
            "CorrespondingPointsEuclideanDistanceMetric"
        )
    
    # Run registration with point files
    result = run_registration(
        fixed_image=...,
        moving_image=...,
        parameter_map=self.elastix_params,
        fixed_point_file=fixed_point_file,  # NEW
        moving_point_file=moving_point_file,  # NEW
        output_directory=self.output_directory,
    )
```

---

## Difficulty Rating: Point-Based vs. Plane Sampling

| Aspect | Plane Sampling | Point-Based Registration |
|--------|---------------|-------------------------|
| **Core Concept** | Sample 2D plane from 3D volume | Match user-defined landmarks |
| **Math Complexity** | Medium (rotation matrices, affine transforms) | Low-Medium (Euclidean distance) |
| **UI Complexity** | Medium (sliders, throttle timer) | High (point selection, pairing workflow) |
| **Napari Integration** | Medium (layer data updates, dims listener) | High (mouse callbacks, point layers, interaction) |
| **Elastix Changes** | None | Medium (point file handling, metric config) |
| **Testing Complexity** | Medium (verify slice correctness) | High (verify point correspondence, edge cases) |
| **User Workflow Changes** | Minimal (same sliders, faster) | Significant (new landmark selection step) |
| **Documentation Needs** | Low (explain speed benefit) | High (teach landmark selection) |

### Overall Difficulty

```
Plane Sampling:        ████████░░░░░░░░  5/10
                       (Math-heavy, UI-light)

Point-Based Reg:       ██████████░░░░░░  6.5/10
                       (Math-light, UI-heavy, workflow changes)
```

### Why Point-Based is Harder

1. **User interaction complexity**: Users must understand landmark selection, pairing, and when to use it
2. **Napari mouse handling**: Intercepting clicks, managing multiple point layers, handling 2D→3D coordinate mapping
3. **Workflow integration**: Changes how users run registration (extra step before clicking "Run")
4. **Edge cases**: What if points are out of bounds? What if user selects wrong layer? What if 2D→3D mapping is ambiguous?

### Why Point-Based is Easier

1. **No heavy math**: Euclidean distance is simpler than rotation matrices + bounding box calculations
2. **Elastix does the work**: Once points are specified, Elastix handles the optimization
3. **Modular**: Can be added as an optional feature without breaking existing workflow

---

## Recommendation

**For GSoC:** Complete plane sampling first, then add point-based registration ONLY if:
- All plane sampling tasks are done + tested
- You have 2+ weeks remaining
- You're interested in UI/UX work

**As a follow-up PR:** Point-based registration is an excellent post-GSoC contribution. It's:
- Independently valuable (doesn't depend on plane sampling)
- Well-scoped (clear boundaries)
- High impact (solves real registration failures)

---

## References

1. [Elastix Manual - Point-Based Registration](https://elastix.dev/docs/manual/)
2. [SimpleElastix Documentation](https://simpleelastix.readthedocs.io/)
3. [CorrespondingPointsEuclideanDistanceMetric](https://elastix.dev/docs/4.8/metrics/#correspondingpointseuclideandistancemetric)
4. [napari Points Layer](https://napari.org/dev/api/napari.layers.Points.html)
