# Integrating PyNutil with brainglobe-registration
## Creating a Full-Fledged Validation & Registration Tool

---

## Executive Summary

This document outlines a comprehensive plan to integrate **PyNutil** (quantification and spatial analysis) with **brainglobe-registration** (2D-to-3D registration). The integration will transform brainglobe-registration from a pure registration tool into a **complete validation pipeline** that:

1. Detects poor-quality images

2. Identifies damaged/hemisphere-only samples
3. Provides quality control feedback before registration
4. Enables downstream quantification with damage-aware analysis

---

## Current State Analysis

### brainglobe-registration (Current)
- **Purpose**: Register 2D brain section images to 3D atlases
- **Input**: Single 2D image + atlas selection
- **Output**: Transformation matrix, registered image, deformation fields
- **Limitation**: Assumes whole-brain input; no quality validation

### PyNutil (Current)
- **Purpose**: Quantify features in registered serial sections
- **Input**: Multiple registered sections + alignment JSON + atlas
- **Output**: Region counts, intensity measurements, 3D point clouds
- **Strength**: Damage-aware quantification via QCAlign integration
- **Limitation**: Requires registration to be done externally (QuickNII/VisuAlign)

### The Gap
Users working with **hemisphere-only** or **damaged tissue** have no integrated solution:
1. brainglobe-registration fails on partial brains (tries to match full atlas)
2. PyNutil requires manual registration first
3. No automated quality control exists in either tool

---

## Proposed Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INTEGRATED WORKFLOW                                   │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  1. IMAGE LOAD   │────▶│  2. QC CHECK     │────▶│  3. GEOMETRY     │
│                  │     │  (PyNutil)       │     │  SELECTION       │
│  - Load image    │     │                  │     │                  │
│  - Preview       │     │  - Detect        │     │  - Full Brain    │
│                  │     │    - Damaged     │     │  - Left Hemi     │
│                  │     │    - Hemi-only   │     │  - Right Hemi    │
│                  │     │    - Artifacts   │     │  - Quarter       │
└──────────────────┘     └──────────────────┘     └──────────────────┘
         ▲                                              │
         │                                              ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  6. VALIDATION   │◀────│  5. POST-REG     │◀────│  4. REGISTRATION │
│  REPORT          │     │  QC CHECK        │     │  (ATLAS CROPPED) │
│                  │     │                  │     │                  │
│  - Quality score │     │  - Verify        │     │  - Mask unused   │
│  - Damage mask   │     │    alignment     │     │    atlas regions │
│  - Export to     │     │  - Flag issues   │     │  - Run elastix   │
│    PyNutil       │     │                  │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘
```

---

## Detailed Integration Points

### 1. Quality Control Widget (Pre-Registration)

**Location**: New widget in brainglobe-registration UI

**Functionality**:
- Load image and display histogram statistics
- Detect potential issues:
  - **Low signal**: Mean intensity below threshold
  - **Saturated regions**: >20% pixels at max value
  - **Asymmetry**: Left-right intensity difference (suggests hemisphere)
  - **Missing tissue**: Large black regions (damaged areas)
  - **Artifacts**: High-frequency noise patterns

**Implementation**:
```python
# brainglobe_registration/widgets/quality_control_widget.py

class QualityControlWidget(QWidget):
    """Pre-registration image quality assessment."""
    
    def analyze_image(self, image: np.ndarray) -> QCReport:
        """Analyze image and return quality report."""
        report = QCReport()
        
        # Check 1: Overall intensity
        report.mean_intensity = np.mean(image)
        report.low_signal = report.mean_intensity < self.threshold_low
        
        # Check 2: Saturation
        saturated = np.sum(image >= self.max_value) / image.size
        report.saturated = saturated > 0.20
        
        # Check 3: Left-right asymmetry (hemisphere detection)
        h, w = image.shape[:2]
        left_half = image[:, :w//2]
        right_half = image[:, w//2:]
        asymmetry = abs(np.mean(left_half) - np.mean(right_half))
        report.potential_hemisphere = asymmetry > self.asymmetry_threshold
        
        # Check 4: Large black regions (damage detection)
        black_regions = label(image < 10)
        large_black = [r for r in regionprops(black_regions) 
                       if r.area > (h * w * 0.1)]
        report.potential_damage = len(large_black) > 0
        
        return report
```

---

### 2. Sample Geometry Selection

**Location**: Enhanced UI dropdown (already in PR #161)

**Options**:
- **Full Brain** (default) - Use entire atlas
- **Left Hemisphere** - Mask right hemisphere of atlas
- **Right Hemisphere** - Mask left hemisphere of atlas
- **Quarter (Anterior)** - Mask posterior + opposite side
- **Quarter (Posterior)** - Mask anterior + opposite side
- **Custom ROI** - User draws region to keep

**Backend Logic**:
```python
# brainglobe_registration/utils/atlas_cropping.py

def crop_atlas_to_geometry(
    atlas_volume: np.ndarray,
    hemi_map: np.ndarray,
    geometry: str
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Mask atlas based on sample geometry.
    
    Parameters
    ----------
    atlas_volume : np.ndarray
        3D atlas annotation volume
    hemi_map : np.ndarray
        3D hemisphere mask (1=left, 2=right)
    geometry : str
        One of: 'full', 'left_hemi', 'right_hemi', 
                'quarter_anterior', 'quarter_posterior'
    
    Returns
    -------
    masked_atlas : np.ndarray
        Atlas with unused regions set to 0
    mask : np.ndarray
        Boolean mask of valid regions
    """
    mask = np.ones_like(atlas_volume, dtype=bool)
    
    if geometry == 'left_hemi':
        mask = hemi_map == 1
    elif geometry == 'right_hemi':
        mask = hemi_map == 2
    elif geometry == 'quarter_anterior':
        # Assuming AP is axis 0
        mid_ap = atlas_volume.shape[0] // 2
        mask[:mid_ap] &= (hemi_map[:mid_ap] == 1)
    elif geometry == 'quarter_posterior':
        mid_ap = atlas_volume.shape[0] // 2
        mask[mid_ap:] &= (hemi_map[mid_ap:] == 1)
    
    masked_atlas = atlas_volume.copy()
    masked_atlas[~mask] = 0
    return masked_atlas, mask
```

---

### 3. Damage Mask Integration (PyNutil-Compatible)

**Location**: Post-registration widget

**Functionality**:
- User can paint/annotate damaged regions on the registered image
- Damage mask saved in QCAlign-compatible JSON format
- Export includes damage information for PyNutil quantification

**Output Format** (compatible with PyNutil's damage handling):
```json
{
  "slices": [
    {
      "nr": 1,
      "filename": "section_001.png",
      "anchoring": [ox, oy, oz, ux, uy, uz, vx, vy, vz],
      "damage_regions": [
        {"x": 100, "y": 200, "width": 50, "height": 50},
        {"x": 300, "y": 150, "width": 80, "height": 60}
      ]
    }
  ]
}
```

**Implementation**:
```python
# brainglobe_registration/widgets/damage_annotation_widget.py

class DamageAnnotationWidget(QWidget):
    """Interactive damage region annotation."""
    
    def __init__(self, viewer: napari.Viewer):
        super().__init__()
        self.viewer = viewer
        self.damage_layer = None
        
    def create_damage_layer(self, image_shape: Tuple[int, int]):
        """Create shapes layer for damage annotation."""
        self.damage_layer = self.viewer.add_shapes(
            name="damage_regions",
            shape_type="rectangle",
            edge_color="red",
            face_color="red",
            opacity=0.3,
        )
        
    def export_damage_mask(self, image_shape: Tuple[int, int]) -> np.ndarray:
        """Convert annotated regions to boolean damage mask."""
        mask = np.ones(image_shape, dtype=bool)  # True = undamaged
        
        if self.damage_layer is not None:
            for rectangle in self.damage_layer.data:
                # rectangle is [y1, x1; y1, x2; y2, x2; y2, x1]
                y_min, y_max = int(rectangle[:, 0].min()), int(rectangle[:, 0].max())
                x_min, x_max = int(rectangle[:, 1].min()), int(rectangle[:, 1].max())
                mask[y_min:y_max, x_min:x_max] = False  # Mark as damaged
        
        return mask
```

---

### 4. Unified Export for PyNutil

**Location**: Enhanced export functionality

**Output Structure**:
```
output_folder/
├── registration.json          # brainglobe-registration output
├── damage_mask.png            # Optional damage annotation
├── registered_image.tiff      # Registered image
├── deformation_field_0.tiff   # For PyNutil non-linear support
├── deformation_field_1.tiff
└── pynutil_compatible/
    ├── alignment.json         # PyNutil-compatible alignment
    ├── segmentations/         # Copy of input images
    └── settings.json          # Analysis settings
```

**Export Function**:
```python
# brainglobe_registration/io/pynutil_export.py

def export_for_pynutil(
    registration_result: RegistrationResult,
    damage_mask: Optional[np.ndarray],
    output_dir: str,
    atlas_name: str,
) -> str:
    """
    Export registration results in PyNutil-compatible format.
    
    Creates alignment.json and organizes files for direct PyNutil import.
    """
    pynutil_dir = os.path.join(output_dir, "pynutil_compatible")
    os.makedirs(pynutil_dir, exist_ok=True)
    
    # Copy segmentations
    seg_dir = os.path.join(pynutil_dir, "segmentations")
    os.makedirs(seg_dir)
    shutil.copy(registration_result.moving_image_path, seg_dir)
    
    # Build alignment.json
    alignment = {
        "slices": [{
            "nr": 1,
            "filename": os.path.basename(registration_result.moving_image_path),
            "width": registration_result.width,
            "height": registration_result.height,
            "anchoring": registration_result.anchoring.tolist(),
            "markers": None,  # Could add from deformation
        }]
    }
    
    if damage_mask is not None:
        # Add damage regions in QCAlign format
        damage_regions = mask_to_regions(damage_mask)
        alignment["slices"][0]["damage_regions"] = damage_regions
    
    # Save alignment
    with open(os.path.join(pynutil_dir, "alignment.json"), "w") as f:
        json.dump(alignment, f, indent=2)
    
    # Save settings
    settings = {
        "alignment_json": os.path.join(pynutil_dir, "alignment.json"),
        "atlas_name": atlas_name,
        "segmentation_folder": seg_dir,
        "apply_damage_mask": damage_mask is not None,
    }
    with open(os.path.join(pynutil_dir, "settings.json"), "w") as f:
        json.dump(settings, f, indent=2)
    
    return pynutil_dir
```

---

## Example User Workflows

### Workflow 1: Hemisphere-Only Sample

**Scenario**: Researcher has left hemisphere brain sections only.

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Image                                              │
│ - User opens brainglobe-registration                            │
│ - Loads "hemisphere_section_001.png"                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: QC Widget Auto-Detects Hemisphere                       │
│ - Warning: "Image appears asymmetric - possible hemisphere"     │
│ - Suggestion: "Select 'Left Hemisphere' in Sample Geometry"     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: User Selects "Left Hemisphere"                          │
│ - Atlas is masked (right hemisphere excluded from registration) │
│ - Registration runs successfully                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Export for PyNutil                                      │
│ - Click "Export for Quantification"                             │
│ - Alignment.json created with hemisphere metadata               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: PyNutil Quantification                                  │
│ - Open PyNutil GUI                                              │
│ - Load alignment.json (automatically detects hemisphere)        │
│ - Run quantification - results only count left hemisphere       │
│ - Output: counts.csv with per-region data                       │
└─────────────────────────────────────────────────────────────────┘
```

---

### Workflow 2: Damaged Tissue Sample

**Scenario**: User has full brain section but with tissue damage on right side.

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Load Image + Register                                   │
│ - Standard registration workflow                                │
│ - Image registers successfully to full atlas                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Damage Annotation                                       │
│ - User opens "Annotate Damage" widget                           │
│ - Draws rectangles over damaged regions                         │
│ - Damage mask saved (red overlay visible)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Export with Damage Info                                 │
│ - Export includes damage_mask.png                               │
│ - alignment.json contains damage_regions array                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: PyNutil Damage-Aware Quantification                     │
│ - PyNutil loads alignment.json with damage info                 │
│ - apply_damage_mask=True (default)                              │
│ - Output CSV includes:                                          │
│   - undamaged_pixel_count                                       │
│   - damaged_pixel_count                                         │
│   - undamaged_area_fraction                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

### Workflow 3: Batch Processing with QC

**Scenario**: Lab has 100 sections, wants to identify problematic ones before quantification.

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Batch Load Images                                       │
│ - User selects folder with 100 section images                   │
│ - brainglobe-registration loads all                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Automated QC Report                                     │
│ - QC widget analyzes all 100 images                             │
│ - Generates summary table:                                      │
│   ┌─────────┬────────────┬──────────────┬──────────────┐       │
│   │ Image   │ Mean Int.  │ Asymmetric?  │ Damaged?     │       │
│   ├─────────┼────────────┼──────────────┼──────────────┤       │
│   │ sec_001 │ 1250       │ No           │ No           │       │
│   │ sec_002 │ 45         │ No           │ YES (low)    │       │
│   │ sec_003 │ 1180       │ YES (left)   │ No           │       │
│   │ sec_004 │ 1300       │ No           │ YES (tear)   │       │
│   └─────────┴────────────┴──────────────┴──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: User Review                                             │
│ - User reviews flagged images                                   │
│ - Sets geometry for asymmetric ones (sec_003 → Left Hemi)       │
│ - Annotates damage for damaged ones (sec_004)                   │
│ - Excludes truly bad ones (sec_002 - too dark)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Batch Register + Export                                 │
│ - Register all valid images                                     │
│ - Export PyNutil-compatible folder structure                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: PyNutil Batch Quantification                            │
│ - PyNutil processes all sections                                │
│ - Damage-aware quantification                                   │
│ - Generates whole-series report                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Benefits of Integration

### For Users
| Benefit | Description |
|---------|-------------|
| **Single workflow** | No need to manually register then quantify |
| **Early problem detection** | QC before registration saves time |
| **Damage-aware results** | Accurate quantification even with damaged tissue |
| **Hemisphere support** | Proper handling of partial brain samples |

### For Developers
| Benefit | Description |
|---------|-------------|
| **Shared code** | Atlas cropping logic reusable in brainreg |
| **Consistent formats** | PyNutil-native export reduces support burden |
| **Modular design** | QC widget can be standalone package |

### For Science
| Benefit | Description |
|---------|-------------|
| **Reproducibility** | Documented QC steps in pipeline |
| **Data quality** | Automated flagging of problematic samples |
| **Inclusivity** | Supports non-standard samples (hemi, quarter) |

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- [ ] Add `crop_atlas_to_geometry()` function
- [ ] Add Sample Geometry dropdown to UI
- [ ] Test hemisphere registration with synthetic data

### Phase 2: Quality Control (Weeks 3-4)
- [ ] Implement `QualityControlWidget`
- [ ] Add auto-detection of hemisphere/damage
- [ ] Create QC report visualization

### Phase 3: Damage Annotation (Weeks 5-6)
- [ ] Implement `DamageAnnotationWidget`
- [ ] Add damage mask export
- [ ] QCAlign-compatible JSON format

### Phase 4: PyNutil Export (Weeks 7-8)
- [ ] Implement `export_for_pynutil()`
- [ ] Create PyNutil-compatible folder structure
- [ ] End-to-end testing with PyNutil

### Phase 5: Polish & Documentation (Weeks 9-10)
- [ ] Write user documentation
- [ ] Create tutorial videos
- [ ] Address community feedback

---

## Issues to Raise in PyNutil Repository

To establish yourself as a genuine contributor and understand the codebase better, consider raising these issues:

### Issue 1: Documentation Gap - Hemisphere Support
```
Title: Document hemisphere handling in quantification

## Description
When using PyNutil with hemisphere-only samples, users need to:
1. Ensure alignment.json reflects the hemisphere
2. Understand how hemi_map is used in region counting

## Proposed Addition
Add a "Partial Brain Samples" section to README.md covering:
- How to prepare hemisphere-only data
- Expected format for hemisphere-aware alignment files
- How per-hemisphere columns are populated

## Why This Matters
Many users work with hemisphere sections but may not know PyNutil 
can handle them correctly with proper setup.
```

### Issue 2: Feature Request - Damage Mask Visualization
```
Title: Add damage mask preview in GUI

## Description
Currently, damage masks from QCAlign are processed silently. Users 
cannot visually verify which regions are excluded.

## Proposed Feature
In PyNutilGUI:
- Add "Show Damage Mask" toggle
- Overlay damage regions on section preview
- Red semi-transparent overlay for damaged areas

## Use Case
Users can verify damage annotations before running full quantification,
catching errors early (e.g., wrong section matched to damage mask).

## Technical Notes
Damage masks are loaded in section_processor.py via slice_info.damage_mask
Could display using napari if integrating with viewer, or PyQt overlay.
```

### Issue 3: Bug Report - Flat File Label Path Handling
```
Title: flat_label_path validation could be clearer

## Description
When using flat files with indexed labels, the error message for 
missing flat_label_path is technical:

"Flat map uses indexed labels beyond atlas_labels rows"

## Suggested Improvement
Add more context:
- Link to documentation on flat file format
- Example of correct .label file format
- Common causes (e.g., using Allen atlas flat files without lookup)

## Why This Matters
New users may not understand what a "flat file" is or why they need
a separate label lookup file.
```

### Issue 4: Feature Request - Batch QC Report
```
Title: Pre-analysis batch summary for large datasets

## Description
When processing 50+ sections, users have no way to preview data 
quality before committing to full quantification.

## Proposed Feature
Add "Analyze Batch" button in GUI that:
1. Loads all section images
2. Computes basic stats (mean intensity, size, etc.)
3. Flags outliers (too dark, too small, etc.)
4. Exports summary CSV for review

## Benefit
Users can identify problematic sections BEFORE running hours of 
quantification, saving time and compute resources.

## Similar Tools
- FastQC for sequencing data
- CellProfiler's quality control module
```

### Issue 5: Documentation - Coordinate System Confusion
```
Title: Clarify orientation handling in coordinate outputs

## Description
The `orientation` parameter in ExtractionResult uses BrainGlobe 
codes (e.g., "asr", "lpi"), but documentation doesn't explain:
- What the internal "lpi" orientation means
- How to convert to other coordinate systems
- When reorientation happens in the pipeline

## Proposed Addition
Add "Coordinate Systems" section to docs:
- Diagram showing LPI vs ASR axes
- When reorientation occurs (after extraction, before saving)
- How to change output orientation for compatibility with other tools

## Context
Users comparing PyNutil coordinates with other tools (e.g., 
brainreg, Allen SDK) need to understand coordinate transformations.
```

### Issue 6: Feature Request - Integration Guide
```
Title: Document integration with brainglobe-registration

## Description
Users may want to use brainglobe-registration for registration, 
then PyNutil for quantification. Currently no guide exists.

## Proposed Documentation
Add "Integration with Other Tools" page covering:
1. Exporting from brainglobe-registration
2. Required file structure for PyNutil
3. How to add damage masks if needed
4. Example workflow script

## Why Now
With brainglobe-registration adding hemisphere/damage support,
integration documentation will become increasingly relevant.
```

---

## Code Examples for Integration Testing

### Test Hemisphere Registration
```python
# tests/test_hemisphere_registration.py

import numpy as np
from brainglobe_registration.utils.atlas_cropping import crop_atlas_to_geometry

def test_left_hemisphere_crop():
    """Test that right hemisphere is properly masked."""
    # Create mock atlas and hemisphere map
    atlas = np.ones((100, 100, 100), dtype=np.uint8)
    hemi_map = np.zeros((100, 100, 100), dtype=np.uint8)
    hemi_map[:, :, :50] = 1  # Left hemisphere
    hemi_map[:, :, 50:] = 2  # Right hemisphere
    
    masked, mask = crop_atlas_to_geometry(atlas, hemi_map, 'left_hemi')
    
    # Verify right hemisphere is zeroed
    assert np.all(masked[:, :, 50:] == 0)
    # Verify left hemisphere is preserved
    assert np.all(masked[:, :, :50] == 1)
```

### Test Damage Mask Export
```python
# tests/test_damage_export.py

import numpy as np
from brainglobe_registration.io.pynutil_export import mask_to_regions

def test_damage_mask_to_regions():
    """Test damage mask conversion to QCAlign format."""
    mask = np.ones((100, 100), dtype=bool)
    mask[20:40, 30:50] = False  # Damaged rectangle
    
    regions = mask_to_regions(mask)
    
    assert len(regions) == 1
    assert regions[0]['x'] == 30
    assert regions[0]['y'] == 20
    assert regions[0]['width'] == 20
    assert regions[0]['height'] == 20
```

---

## Conclusion

Integrating PyNutil with brainglobe-registration creates a **complete validation and quantification pipeline** that:

1. **Detects problems early** - QC before registration
2. **Handles real-world samples** - Hemisphere, quarter, damaged tissue
3. **Preserves data quality** - Damage-aware quantification
4. **Streamlines workflows** - One-click export between tools

This integration positions brainglobe-registration as more than just a registration tool - it becomes a **comprehensive quality control and validation platform** for neuroscience image analysis.

---

## References

1. PyNutil Repository: https://github.com/Neural-Systems-at-UIO/PyNutil
2. brainglobe-registration: https://github.com/brainglobe/brainglobe-registration
3. brainreg hemisphere handling: https://github.com/brainglobe/brainreg/blob/main/brainreg/core/backend/niftyreg/run.py#L58-L70
4. QCAlign: https://www.nitrc.org/projects/qcalign
5. QUINT Workflow: https://quint-workflow.readthedocs.io/

 ---
  The Connection                                                                                                                                                           
   
  ┌─────────────────────────────────────────────────────────────────┐                                                                                                      
  │                    CURRENT PROBLEM                              │ 
  │                                                                 │
  │  User's brain section:     Atlas (full brain):                  │
  │  ┌─────────────────┐       ┌─────────────────┐                 │
  │  │  ████████████   │       │  ┌───────────┐  │                 │
  │  │  ████████████   │  vs   │  │ Olfactory │  │                 │
  │  │  ████████████   │       │  │   Bulbs   │  │ ← Missing in    │
  │  │  ████████████   │       │  └───────────┘  │    sample!       │
  │  └─────────────────┘       └─────────────────┘                 │
  │       ↑                                                                │
  │  (olfactory bulbs                                                 │
  │   fell off)                                                       │
  │                                                                 │
  │  Registration tries to match EVERY part → FAILS or BAD RESULT  │
  └─────────────────────────────────────────────────────────────────┘

  ---
  Simple Explanation

  ▎ "Sometimes when preparing brain slides, delicate parts like olfactory bulbs fall off. Currently brainglobe-registration tries to match the ENTIRE atlas to the image -
  ▎ including parts that don't exist. This causes registration failures. We need to tell the algorithm: 'Ignore these missing regions when matching.'"

  ---
  How It Relates to PyNutil

  ┌───────────┬──────────────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
  │  Aspect   │            brainglobe-registration (#168)            │                        PyNutil                         │
  ├───────────┼──────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ Problem   │ Damaged/missing tissue causes registration failure   │ Damaged tissue causes wrong quantification             │
  ├───────────┼──────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ Solution  │ Mask atlas regions TO BE IGNORED during registration │ Mask sample regions TO BE IGNORED during counting      │
  ├───────────┼──────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ Direction │ Atlas → Image (find where atlas regions go)          │ Image → Atlas (which atlas region contains each pixel) │
  ├───────────┼──────────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ Output    │ Registration that ignores missing bulbs              │ Quantification that excludes damaged areas             │
  └───────────┴──────────────────────────────────────────────────────┴────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────┐
  │                    TWO-WAY PROTECTION                            │
  │                                                                 │
  │  brainglobe-registration:          PyNutil:                     │
  │  "Atlas has parts sample doesn't"  "Sample has parts atlas      │
  │                                   doesn't"                      │
  │                                                                 │
  │  Mask atlas regions              Mask sample regions            │
  │  (olfactory bulbs)               (tears, folds, artifacts)      │
  │                                                                 │
  │  ↓ Registration succeeds         ↓ Quantification accurate      │
  └─────────────────────────────────────────────────────────────────┘

  ---
  Why This Matters for Your Proposal

  This issue (#168) is exactly the use case you described in your proposal:

  ▎ "Adding PyNutil support to brainglobe-registration to detect bad images captured or half brain damaged etc - overall making this tool a full fledged validation tool"

  Your Integration Vision

  ┌─────────────────────────────────────────────────────────────────┐
  │  COMPLETE WORKFLOW (Your GSoC Goal)                             │
  │                                                                 │
  │  1. User loads image with missing olfactory bulbs              │
  │     ↓                                                           │
  │  2. QC widget detects: "Large black region anteriorly"         │
  │     ↓                                                           │
  │  3. User selects: "Mask olfactory bulbs" (this issue #168)     │
  │     ↓                                                           │
  │  4. Registration ignores missing parts → SUCCESS               │
  │     ↓                                                           │
  │  5. Damage mask exported to PyNutil format                     │
  │     ↓                                                           │
  │  6. PyNutil quantification excludes damaged areas              │
  │     ↓                                                           │
  │  7. Accurate, damage-aware results                             │
  └─────────────────────────────────────────────────────────────────┘

  ---
  How to Comment on the Issue (Show You Understand)

  You could comment on #168 with something like:

  This is directly related to damage-aware quantification in PyNutil.

  **Connection to PyNutil:**
  PyNutil already supports damage masks for quantification (via QCAlign
  integration). Users can mark damaged regions, and PyNutil excludes them
  from counts, producing columns like:
  - `undamaged_pixel_count`
  - `damaged_pixel_count`
  - `undamaged_area_fraction`

  **Proposed Integration:**
  If brainglobe-registration adds atlas masking for registration (this issue),
  the same mask could be:
  1. Used during registration (ignore missing olfactory bulbs)
  2. Exported to PyNutil format (exclude from quantification)

  This would create an end-to-end pipeline:
    damaged sample → masked registration → damage-aware quantification

  **Question for @PolarBean:**
  Should the mask be:
  - User-drawn (like QCAlign)?
  - Auto-detected from large black regions?
  - Selected from preset templates (e.g., "olfactory bulbs", "hippocampus")?

  ---
  Summary Table

  ┌────────────────────────────────┬──────────────────────────────────────────────────┬────────────────────────────────────────────────────────┐
  │             Issue              │                  What It Solves                  │                  How PyNutil Connects                  │
  ├────────────────────────────────┼──────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ #168 (brainglobe-registration) │ Registration fails when sample has missing parts │ PyNutil needs damage masks for accurate quantification │
  ├────────────────────────────────┼──────────────────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ Your GSoC work                 │ Bridge the two tools                             │ Same mask → both registration AND quantification       │
  └────────────────────────────────┴──────────────────────────────────────────────────┴────────────────────────────────────────────────────────┘

  Key insight: The mask that helps registration (ignoring missing bulbs) is the SAME mask PyNutil needs for accurate counting. Your integration makes one mask serve both
  purposes!
