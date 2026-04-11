# PyNutil Integration with brainglobe-registration

## Why This Integration Exists

### The Problem

Neuroscientists working with **brain section images** face a common workflow:

```
1. Take a microscope image of a brain section (e.g., hippocampus)
2. Want to know: "Which brain regions are in this image?"
3. Want to quantify: "How much signal is in each region?"
```

**Before this integration:**
```
Step 1: Open brainglobe-registration in napari
        └─→ Load atlas
        └─→ Load your brain section image
        └─→ Run registration (aligns your image to atlas)
        └─→ See colored overlay showing regions

Step 2: Export results manually (save images, note coordinates)

Step 3: Open PyNutil separately
        └─→ Load your exported images
        └─→ Configure alignment parameters
        └─→ Run quantification
        └─→ Get region-by-region counts

Step 4: Manually match results back to your registration
```

**Problems with this workflow:**
- ❌ Two separate tools with no connection
- ❌ Manual file handling (easy to make mistakes)
- ❌ Alignment parameters must be re-entered
- ❌ No quality control before export
- ❌ Time-consuming and error-prone

---

### The Solution

**brainglobe-registration + PyNutil integration:**

```
Single Workflow in napari:
┌─────────────────────────────────────────────────────────────┐
│  1. Load Atlas                                              │
│     └─→ Choose "allen_mouse_25um" (or any BrainGlobe atlas) │
│                                                             │
│  2. Load Your Image                                         │
│     └─→ Your brain section (e.g., "sample_hipp.tif")        │
│                                                             │
│  3. Register                                                │
│     └─→ Click "Register"                                    │
│     └─→ See aligned result with colored atlas overlay       │
│                                                             │
│  4. Quality Control                                         │
│     └─→ Click "Analyze Image Quality"                       │
│     └─→ Get instant feedback on image quality               │
│                                                             │
│  5. Export & Quantify                                       │
│     └─→ Click "Export to PyNutil Format"                    │
│     └─→ Click "Run PyNutil Quantification"                  │
│     └─→ Get table: Region | Count | Percentage              │
└─────────────────────────────────────────────────────────────┘
```

---

## Visual Workflow Diagram

```
                    BRAINGLOBE-REGISTRATION + PYNUUTIL WORKFLOW
                    ===========================================

    STEP 1: LOAD ATLAS
    ┌────────────────────────────────────────────┐
    │  Allen Mouse Brain Atlas (3D)              │
    │  ┌────────────────────────────────────┐    │
    │  │  [Colored 3D brain with regions]   │    │
    │  │                                    │    │
    │  │   CA1    │ Hippocampus             │    │
    │  │   DG     │ Dentate Gyrus           │    │
    │  │   CTX    │ Cortex                  │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 2: SAMPLE ATLAS PLANE
    ┌────────────────────────────────────────────┐
    │  Match your image orientation:             │
    │  ┌────────────────────────────────────┐    │
    │  │  [2D slice from 3D atlas]          │    │
    │  │    [Roll: 0°] [Yaw: 15°] [Pitch]   │    │
    │  │                                    │    │
    │  │   Adjust sliders to match view     │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 3: LOAD YOUR IMAGE
    ┌────────────────────────────────────────────┐
    │  Your brain section image:                 │
    │  ┌────────────────────────────────────┐    │
    │  │  [Grayscale brain section]         │    │
    │  │                                    │    │
    │  │  sample_hipp.tif                   │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 4: REGISTER
    ┌────────────────────────────────────────────┐
    │  Align your image to atlas:                │
    │  ┌────────────────────────────────────┐    │
    │  │  [Your image] + [Colored atlas]    │    │
    │  │       = [Overlay result]           │    │
    │  │                                    │    │
    │  │  ✓ Registration complete!          │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 5: QUALITY CONTROL
    ┌────────────────────────────────────────────┐
    │  Analyze Image Quality:                    │
    │  ┌────────────────────────────────────┐    │
    │  │  Mean Intensity: 2847.3            │    │
    │  │  Low Signal: [OK]                  │    │
    │  │  Saturated: [OK]                   │    │
    │  │  Asymmetry Score: 0.12             │    │
    │  │  Quality: 85/100 ✓                 │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 6: EXPORT TO PYNUUTIL
    ┌────────────────────────────────────────────┐
    │  Create PyNutil-compatible folder:         │
    │  ┌────────────────────────────────────┐    │
    │  │  pynutil_compatible/               │    │
    │  │  ├── segmentations/                │    │
    │  │  │   └── sample_hipp_s001.tif      │    │
    │  │  ├── registered/                   │    │
    │  │  │   └── sample_hipp_registered.tif│    │
    │  │  ├── alignment.json                │    │
    │  │  └── settings.json                 │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 7: RUN QUANTIFICATION
    ┌────────────────────────────────────────────┐
    │  PyNutil analyzes region overlap:          │
    │  ┌────────────────────────────────────┐    │
    │  │  Region Name      │ Count │ %     │    │
    │  │  ─────────────────┼───────┼────── │    │
    │  │  CA1 (hippocampus)│ 1247  │ 32.1% │    │
    │  │  DG (dentate)     │  892  │ 23.0% │    │
    │  │  Subiculum        │  534  │ 13.8% │    │
    │  │  Cortex           │  421  │ 10.9% │    │
    │  │  ...              │  ...  │  ...  │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
                      │
                      ▼
    STEP 8: EXPORT RESULTS
    ┌────────────────────────────────────────────┐
    │  Save to CSV for analysis:                 │
    │  ┌────────────────────────────────────┐    │
    │  │  quantification_results.csv        │    │
    │  │  region_id,name,count,percentage   │    │
    │  │  315,CA1,1247,32.1                 │    │
    │  │  316,DG,892,23.0                   │    │
    │  │  ...                               │    │
    │  └────────────────────────────────────┘    │
    └────────────────────────────────────────────┘
```

---

## What Each Tool Does

### brainglobe-registration

| Feature | Description |
|---------|-------------|
| **Atlas Loading** | Downloads any BrainGlobe atlas (Allen Mouse, Human, etc.) |
| **Plane Sampling** | Extracts a 2D slice from the 3D atlas at any angle |
| **Registration** | Aligns your image to the atlas slice using Elastix |
| **Visualization** | Shows your image + colored atlas overlay in napari |
| **Quality Control** | Analyzes image quality before export |

**Output:** Registered image with known atlas coordinates

---

### PyNutil

| Feature | Description |
|---------|-------------|
| **Segmentation** | Identifies objects/pixels in your image |
| **Coordinate Mapping** | Maps each object to atlas space |
| **Region Lookup** | Finds which brain region each object is in |
| **Quantification** | Counts objects/pixels per region |
| **Statistics** | Generates tables and summaries |

**Output:** CSV table with region-by-region quantification

---

## How They Connect

```
┌──────────────────────────────────────────────────────────────┐
│                    THE CONNECTION                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  brainglobe-registration knows:                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  • Your image shape and size                           │  │
│  │  • The atlas used (e.g., "allen_mouse_25um")           │  │
│  │  • The exact alignment (anchoring vector)              │  │
│  │  • Which regions are visible in the registered image   │  │
│  │  • Damage/excluded areas (if any)                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  PyNutil needs:                                                │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  • Your image (segmentation)                           │  │
│  │  • The atlas name                                      │  │
│  │  • Alignment parameters (anchoring)                    │  │
│  │  • Damage mask (optional)                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ✓ PERFECT MATCH! brainglobe-registration provides exactly   │
│    what PyNutil needs.                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## The "Anchoring Vector" Explained

This is the **key piece of information** that connects the two tools:

```
                    What is the Anchoring Vector?
                    ─────────────────────────────

Imagine your atlas slice as a piece of paper in 3D space:

                    Z (depth)
                      │
                      │
                      │   Y (vertical)
                      │  /
                      │ /
                      │/
                      └─────────── X (horizontal)

The anchoring vector defines:
┌─────────────────────────────────────────────────────────┐
│  [ox, oy, oz]  =  Origin point (where the slice starts) │
│  [ux, uy, uz]  =  U-axis (horizontal direction in slice)│
│  [vx, vy, vz]  =  V-axis (vertical direction in slice)  │
│  [0, 0, 0, 100, 0, 0, 0, 100, 0]                        │
│   ───────────  ───────────  ───────────                 │
│   Origin       U-vector     V-vector                    │
└─────────────────────────────────────────────────────────┘

This tells PyNutil: "This 2D image corresponds to THIS exact
plane in the 3D atlas."

Without this: PyNutil can't know where your image is in the brain
With this: PyNutil can map every pixel to its exact brain region
```

---

## Real-World Use Case Example

### Scenario: Counting Neurons in Hippocampus

**Your experiment:**
- You have a fluorescent image of a mouse hippocampus
- You want to count neurons in CA1, CA3, and Dentate Gyrus
- You need to know: "How many neurons in each subregion?"

**Old workflow (before integration):**
```
1. Open ImageJ → manually trace regions → count cells
   OR
2. Use PyNutil standalone → manually enter alignment → hope it's correct
```

**New workflow (with integration):**
```
1. Open napari with brainglobe-registration plugin
2. Load "allen_mouse_25um" atlas
3. Load your hippocampus image
4. Adjust atlas plane to match your view
5. Click "Register" → wait 30 seconds
6. Click "Analyze Image Quality" → confirms good quality
7. Click "Export to PyNutil" → creates folder
8. Click "Run Quantification" → gets results table
9. Export CSV → done!
```

**Result:**
```
Region              | Neuron Count | Percentage
────────────────────┼──────────────┼───────────
CA1 (field CA1)     | 1,247        | 32.1%
CA3 (field CA3)     | 892          | 23.0%
Dentate Gyrus       | 534          | 13.8%
Subiculum           | 421          | 10.9%
Other regions       | 784          | 20.2%
────────────────────┴──────────────┴───────────
Total: 3,878 neurons
```

---

## Benefits of This Integration

| Benefit | What It Means |
|---------|---------------|
| **One-click export** | No manual file handling or parameter copying |
| **Automatic alignment** | Anchoring vector transferred automatically |
| **Quality control built-in** | Know if your image is good before quantifying |
| **Damage mask support** | Exclude damaged areas from quantification |
| **Reproducible** | All parameters saved in JSON files |
| **Fast** | Go from registration to results in < 2 minutes |

---

## What You Get After Quantification

### Files Created

```
pynutil_compatible/
├── segmentations/
│   └── sample_hipp_s001.tif      # Your original image
├── registered/
│   └── sample_hipp_registered.tif # Registered result
├── alignment.json                 # Alignment parameters
├── settings.json                  # Analysis settings
└── quantification_results/
    ├── coords.csv                 # Object coordinates
    └── labels.csv                 # Region assignments
```

### Results Table

| Column | Description |
|--------|-------------|
| `label_id` | Atlas region ID (e.g., 315 for CA1) |
| `name` | Region name (e.g., "CA1") |
| `object_count` | Number of objects in this region |
| `pixel_count` | Total pixels in this region |
| `percentage` | % of total objects |

---

## Troubleshooting

### "No moving image layer found"
**Cause:** Image wasn't loaded properly  
**Fix:** Make sure you loaded your image BEFORE clicking Export

### "PyNutil is not installed"
**Cause:** PyNutil package missing  
**Fix:** Run `pip install pynutil`

### "No section number found in filename"
**Cause:** PyNutil needs `_s001` in filename  
**Fix:** This is now automatic - just export again!

### Quantification takes too long
**Cause:** Large image or high object count  
**Fix:** Increase "Object Cutoff" to ignore small debris

---

## Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    KEY TAKEAWAYS                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. brainglobe-registration = Aligns your image to atlas    │
│  2. PyNutil = Counts objects in each brain region           │
│  3. Integration = Automatic handoff between the two         │
│                                                             │
│  The integration solves:                                    │
│  ✓ No more manual file handling                             │
│  ✓ No more re-entering alignment parameters                 │
│  ✓ Quality control before quantification                    │
│  ✓ Reproducible, documented workflow                        │
│                                                             │
│  What you need to run:                                      │
│  • napari with brainglobe-registration plugin               │
│  • PyNutil package (pip install pynutil)                    │
│  • Your brain section image                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Future Possibilities

```
┌─────────────────────────────────────────────────────────────┐
│              What Could Come Next?                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • 3D support (brainreg integration)                        │
│  • Direct CSV export from napari                            │
│  • Visualization of quantification results in napari        │
│  • Batch processing (multiple images at once)               │
│  • Cell-type classification integration                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
