---
name: Feature request - Save current atlas slice during interactive exploration
about: Allow users to export the current oblique atlas slice and rotation parameters without running full registration
title: "[Feature] Save current atlas slice and rotation parameters before registration"
labels: enhancement
assignees: ''
---

# Is your feature request related to a problem? Please describe.

Currently, rotation parameters (pitch, yaw, roll, z-slice) and the sampled atlas slice are only saved **after** running the full registration process, in the `brainglobe-registration.json` file in the output directory.

This means if a user:
- Finds a useful oblique slice during interactive exploration but doesn't want to run registration yet
- Wants to share a specific atlas view with collaborators
- Needs to document a standard slicing angle for their lab protocol
- Wants to export a high-quality image of the oblique slice for a figure or presentation

...they have no built-in way to save that slice configuration without committing to the full registration pipeline.

## Describe the solution you'd like

Add a **"Save Current Slice"** button (or `Ctrl+S` shortcut) in the registration widget that exports:

1. **Sampled 2D reference image** — The current oblique atlas slice as a TIFF/PNG file
2. **Sampled 2D annotation overlay** — The corresponding annotation layer as a TIFF/PNG (optional toggle)
3. **Rotation parameters JSON** — A lightweight sidecar file containing:
   ```json
   {
     "atlas_name": "allen_mouse_25um",
     "pitch": 15.5,
     "yaw": -8.0,
     "roll": 2.5,
     "z_slice": 145,
     "interpolation_order": 1,
     "timestamp": "2026-04-09T14:32:00"
   }
   ```

### Suggested UI placement

```
┌─────────────────────────────────────┐
│  Atlas Selection                    │
│  [Dropdown]                         │
├─────────────────────────────────────┤
│  Rotation Controls                  │
│  Pitch: [━━━━●━━━━]  15.5°         │
│  Yaw:   [━━━━●━━━━]  -8.0°         │
│  Roll:  [━━━━●━━━━]   2.5°         │
├─────────────────────────────────────┤
│  [Save Current Slice]  ← NEW BUTTON │
│  [Run Registration]                 │
└─────────────────────────────────────┘
```

## Describe alternatives you've considered

1. **Screenshot the napari window** — Low quality, includes UI elements, not reproducible
2. **Note down angles manually** — Error-prone, no visual record of the slice
3. **Run full registration just to save params** — Unnecessary computation (takes minutes), creates output directory clutter

## Additional context

### Why this is useful for neuroscientists

| Use Case | Benefit |
|----------|---------|
| **Exploratory analysis** | Save interesting oblique planes through structures (e.g., hippocampal axis) without committing to registration |
| **Protocol documentation** | Labs can share standard slicing angles (e.g., "30° pitch for coronal sections") with visual confirmation |
| **Teaching/presentations** | Export high-quality oblique atlas views for lecture slides or papers |
| **Checkpointing** | Save a "good" slice configuration before experimenting with different parameters |

### Related discussion

This feature was discussed in PR #164 (plane sampling implementation). As @IgorTatarnikov noted:
> "That would be useful, but might better as a separate PR. Worth raising an issue to track it though!"

### Implementation notes

- Could leverage existing `sample_plane()` function from `plane_sampling.py`
- Would need to track current rotation state independently of registration state
- `Ctrl+S` shortcut would need to avoid conflicting with napari's native save
- Optional: Add "bookmark slots" (1-5) to save multiple configurations during a session
#