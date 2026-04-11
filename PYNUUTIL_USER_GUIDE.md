# PyNutil Integration User Guide

This guide explains how to use the PyNutil integration in brainglobe-registration for brain-wide quantification and quality control.

## Overview

The PyNutil integration allows you to:
1. **Analyze image quality** - Detect issues like low signal, saturation, hemisphere-only samples, and damaged tissue
2. **Export registration results** - Convert brainglobe-registration outputs to PyNutil-compatible format
3. **Run quantification** - Count objects or measure intensity in atlas regions
4. **Visualize results** - View quantification results directly in napari or export for further analysis

## Prerequisites

- brainglobe-registration installed with PyNutil dependencies
- A BrainGlobe atlas downloaded (e.g., `allen_mouse_25um`)
- A 2D or 3D image to register (brain section)

## Step-by-Step Workflow

### Step 1: Load Your Image

1. Open napari and launch the brainglobe-registration plugin
2. Your image should appear in the "Moving Image" dropdown automatically
3. If not, open your image in napari first (`File > Open` or drag-and-drop)

### Step 2: Select and Prepare Atlas

1. **Select Atlas**: Choose a BrainGlobe atlas from the dropdown (e.g., `allen_mouse_25um`)
2. **Adjust Atlas Rotation** (optional):
   - Use the pitch, yaw, roll sliders in the "Prepare Images" tab
   - Or click "Automatic Slice Detection" for automated alignment
3. **Adjust Moving Image** (optional):
   - Scale the image if needed using the scale sliders
   - Rotate if needed for better alignment

### Step 3: Run Registration

1. **Select Transformations**: Choose at least one transform type (Affine, BSpline)
2. **Select Output Directory**: Click "Browse" to choose where results will be saved
3. **Click "Run"**: Wait for registration to complete

After registration completes:
- The "Registered Image" layer will be created
- The "PyNutil Quantification" tab will be enabled

### Step 4: Quality Control Analysis

Before quantification, it's recommended to check image quality:

1. Go to the **"PyNutil Quantification"** tab
2. Click **"Analyze Image Quality"**
3. Review the quality report:

```
Quality Control Report
======================

Image Statistics:
  Mean Intensity: 125.3
  Std Dev: 45.2
  Range: [10.0, 240.5]

Quality Flags:
  Low Signal: [OK]
  Saturated: [OK]
  Potential Hemisphere: [!]  <-- Warning: may be hemisphere-only
  Potential Damage: [OK]

Analysis:
  Asymmetry Score: 0.45
  Damage Fraction: 0.02

Recommendations:
  Sample Geometry: right_hemi  <-- Suggested setting
  Damage Mask Needed: No
  Overall Quality: 0.8/1.0
```

**Quality Flags Explained:**
- **Low Signal**: Image may be underexposed
- **Saturated**: Image may be overexposed (clipped highlights)
- **Potential Hemisphere**: Only one hemisphere visible (common in sectioned brains)
- **Potential Damage**: Large black regions detected (tissue damage or artifacts)

### Step 5: Export to PyNutil Format

1. **Select Output Directory**: Click "Browse" in the Export section
2. **Select Sample Geometry**:
   - `full`: Full brain (default)
   - `left_hemi`: Left hemisphere only
   - `right_hemi`: Right hemisphere only
3. **Include Damage Mask** (optional): Check if you want to exclude damaged regions
4. **Click "Export to PyNutil Format"**

This creates a directory structure like:
```
output_dir/
└── pynutil_compatible/
    ├── segmentations/      # Your original image
    ├── registered/         # Registered image
    ├── alignment.json      # Registration parameters
    ├── settings.json       # PyNutil settings
    └── damage_mask.tiff    # (if provided)
```

### Step 6: Run Quantification

1. **Select Mode**:
   - **Binary Segmentation**: For cell-counting or labeled objects
   - **Intensity**: For fluorescence intensity measurements

2. **Configure Parameters**:
   - **Object Cutoff** (binary mode): Minimum object size to count
   - **Channel** (intensity mode): Which channel to analyze (R, G, B, grayscale)
   - **Min/Max Intensity** (intensity mode): Threshold values

3. **Click "Run PyNutil Quantification"**

Results will appear in the text box below, showing:
- Total objects/pixels analyzed
- Top 10 brain regions by count/intensity
- Atlas used and damage mask status

### Step 7: Export or Further Analysis

**Option A: Use Results in napari**
- Results are automatically saved to your output directory
- CSV files can be loaded into napari or analyzed in Python

**Option B: Open in PyNutil GUI**
- Click "Open in PyNutil GUI" to launch the standalone PyNutil application
- Load the exported directory for interactive 3D visualization

## Example Workflows

### Workflow 1: Full Brain Registration + Quantification

```
1. Load full brain section image
2. Select "allen_mouse_25um" atlas
3. Run "Automatic Slice Detection"
4. Run registration (Affine + BSpline)
5. Export with geometry = "full"
6. Run binary quantification
```

### Workflow 2: Hemisphere-Only Sample

```
1. Load hemisphere section image
2. Select atlas and adjust rotation manually
3. Run QC analysis → detects "Potential Hemisphere"
4. Set geometry = "right_hemi" based on QC recommendation
5. Export and quantify
```

### Workflow 3: Damaged Tissue Analysis

```
1. Load image with visible damage
2. Run QC analysis → detects "Potential Damage"
3. Check "Include Damage Mask"
4. Export with damage mask
5. Run quantification (damaged regions excluded)
```

## Troubleshooting

### "No moving image layer found"
- Ensure your image is loaded in napari before opening the plugin
- The image layer must be named "moving_image" or be the first image layer

### "No registered image layer found"
- Run registration first before exporting to PyNutil format

### "Anchoring vector not found"
- This warning appears if registration hasn't completed properly
- Re-run registration and ensure the atlas is properly aligned

### "PyNutil is not installed"
- Install dependencies: `pip install pynutil orjson nrrd nibabel`
- Or reinstall brainglobe-registration with: `pip install -e ".[dev]"`

### Quantification returns no objects
- Check that your segmentation has non-zero values
- Adjust the "Object Cutoff" parameter
- Ensure the atlas matches your sample type (e.g., mouse atlas for mouse brain)

## Advanced: Using Results in Python

```python
import pandas as pd
from pathlib import Path

# Load quantification results
results_dir = Path("output_dir/pynutil_compatible")
label_df = pd.read_csv(results_dir / "label_counts.csv")

# Analyze top regions
top_regions = label_df.nlargest(10, 'object_count')
print(top_regions[['name', 'object_count']])

# Export for statistical analysis
label_df.to_csv("analysis_results.csv", index=False)
```

## Related Documentation

- [PyNutil Documentation](https://github.com/Neural-Systems-at-UIO/PyNutil)
- [BrainGlobe Atlas API](https://brainglobe.info/documentation/brainglobe-atlas-api/index.html)
- [brainglobe-registration README](README.md)

## Reporting Issues

If you encounter bugs or have feature requests:
1. Check existing issues on the brainglobe-registration GitHub
2. For PyNutil-specific issues, check the PyNutil GitHub
3. Include:
   - brainglobe-registration version
   - PyNutil version
   - Atlas used
   - Error messages and screenshots
