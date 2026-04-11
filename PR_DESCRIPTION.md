# PR Description: Arbitrary Plane Sampling for Atlas Registration

**Branch:** `slider2d`  
**Author:** Harshdip Saha  
**References:** #151

---

## What is this PR?

- [x] Bug fix
- [x] Addition of a new feature
- [ ] Other

---

## Why is this PR needed?

This PR is needed for the following reasons:

1. **Improved user experience** - Users can now analyze brain structures at arbitrary angles with consistent Z-slider behavior, enabling exploration of oblique planes through the atlas.

2. **Consistent Z-slider** - The Z-slider range remains constant and no longer dynamically changes depending on rotation parameters. Previously, rotating the volume would expand the bounding box and change the slider range, confusing users.

3. **Significant performance improvements in automated methods** - For Bayesian optimization-based automated target selection:
   - **~4.2× faster** execution time (tested and verified)
   - **~97% memory savings** - No longer loads entire rotated volume into memory
   - Enables practical real-time automated slice detection

4. **Fixes clipping at extreme rotation angles** - The previous volume rotation approach suffered from data clipping at angles like 90° pitch. The new plane sampling approach correctly handles all rotation angles.

---

## What does this PR do? (Feature Checklist)

### Core Feature: Plane Sampling Instead of Volume Rotation

- [x] **New `plane_sampling.py` module** - Implements efficient 2D plane extraction from static 3D volumes at arbitrary rotations
  - `build_rotation_matrix()` - Creates rotation matrix from Euler angles
  - `compute_rotation_offset()` - Computes inverse rotation, offset, and bounding box with Z-axis anchoring for Napari compatibility
  - `sample_plane()` - Samples single 2D plane using `scipy.ndimage.map_coordinates`
  - `sample_annotation_plane()` - Wrapper for label volumes with nearest-neighbor interpolation

- [x] **Replaced volume rotation with plane sampling** throughout the codebase
  - Registration widget now samples 2D planes instead of rotating entire 3D volumes
  - Automated target selection uses plane sampling for faster iteration
  - Annotation layers use nearest-neighbor sampling to preserve label integrity

### UI Improvements: Rotation Controls

- [x] **Slider + Spinbox pairs for rotation controls** (Pitch, Yaw, Roll)
  - Horizontal sliders for quick adjustment with visual tick marks every 90°
  - Numeric spinboxes for precise input (0.1° resolution, ±360° range)
  - Bidirectional sync: slider updates spinbox and vice versa

- [x] **Throttled live updates during slider drag**
  - `ThrottledTimer` class ensures smooth updates at 5ms intervals
  - Prevents UI lag during rapid slider movement
  - Fires immediately on first change, then throttles subsequent calls

- [x] **Dedicated signal handlers** for each rotation axis
  - `_on_pitch_slider_changed()`, `_on_yaw_slider_changed()`, `_on_roll_slider_changed()`
  - Proper signal blocking to prevent feedback loops

- [x] **Programmatic rotation setting**
  - `set_rotation_values()` method for updating UI from code
  - Used by automated target selection to display results

### UI Improvements: Interpolation Control

- [x] **Interpolation order dropdown** (0=Nearest, 1=Linear)
  - User-selectable interpolation for plane sampling
  - Default: Linear (order=1) for smoother visual output
  - Nearest (order=0) available for label/annotation preservation
  - Signal emitted on change to trigger re-sampling

### Automated Target Selection Improvements

- [x] **Updated registration parameters** (`automated_reg_affine.txt`)
  - Transform changed from `AffineTransform` → `EulerTransform`
    - Biologically correct (rigid transformation only, no scaling/shearing)
    - Faster convergence (6 DOF vs 12 DOF)
  - Iterations optimized: `500` → `400 200 50` (per resolution level)
    - 57% fewer total iterations (1500 → 650)
    - Coarse level gets most iterations, fine level gets fewest

- [x] **Interpolation order support** in automated detection
  - Dialog includes interpolation dropdown
  - Parameters passed through Bayesian optimization pipeline

- [x] **Roll angle optimization** now included in pipeline
  - Two-stage process: coarse (pitch/yaw/z) then fine (roll)
  - Uses `EulerTransform` for consistent rigid registration

### Napari Viewer Integration

- [x] **Dynamic layer management**
  - Original 3D atlas layers hidden during plane sampling
  - New 2D sampled plane layers created and updated in real-time
  - Annotation layer toggleable for region identification

- [x] **Z-slider event handling**
  - Slider changes trigger debounced plane re-sampling (30ms)
  - Prevents unnecessary computation during rapid slider movement
  - Tracks last sampled Z to avoid redundant updates

- [x] **State management**
  - `_plane_sampling_active` flag differentiates first-time setup from updates
  - Cached transform state (`_plane_inv_rotation`, `_plane_offset`, `_plane_output_shape`)
  - Proper cleanup on atlas reset/deletion

### Bug Fixes

- [x] **Fixed clipping at extreme rotation angles** - Previous volume rotation clipped data at angles like 90° pitch; new approach correctly computes bounding box

- [x] **Fixed ITK parameter file writing** - Changed `WriteParameterFile` → `WriteParameterFiles` for newer ITK version compatibility

- [x] **Fixed unsigned integer wraparound** - Added clipping to prevent negative values wrapping when casting transformed images to unsigned types

- [x] **Fixed mutual information metric** - Changed from `sklearn.mutual_info_regression` to `skimage.metrics.normalized_mutual_information` for proper MI computation

### Testing

- [x] **New test suite for plane sampling** (`test_plane_sampling.py`)
  - Tests for rotation matrix construction
  - Tests for bounding box computation
  - Tests for plane sampling correctness
  - Tests for annotation plane sampling

- [x] **New tests for rotation controls** (`test_adjust_moving_image_view.py`)
  - Slider + spinbox synchronization
  - Signal emission verification
  - Throttling behavior

- [x] **Updated automated target selection tests** (`test_automated_target_selection.py`)
  - Tests for plane sampling integration
  - Bayesian optimization workflow tests

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `utils/plane_sampling.py` | **NEW** | Core plane sampling implementation |
| `utils/transforms.py` | Modified | Added deprecation warning for `rotate_volume()` |
| `widgets/adjust_moving_image_view.py` | Modified | New rotation controls, throttling, interpolation dropdown |
| `widgets/target_selection_widget.py` | Modified | Added interpolation order to dialog |
| `registration_widget.py` | Modified | Main integration of plane sampling, layer management |
| `automated_target_selection.py` | Modified | Uses plane sampling, added roll optimization |
| `parameters/brainglobe_registration/automated_reg_affine.txt` | Modified | EulerTransform, optimized iterations |
| `elastix/register.py` | Modified | ITK compatibility fix, unsigned int clipping |
| `similarity_metrics.py` | Modified | Fixed MI metric implementation |
| `tests/test_plane_sampling.py` | **NEW** | Tests for plane sampling module |
| `tests/test_adjust_moving_image_view.py` | Modified | Tests for new rotation controls |
| `tests/test_automated_target_selection.py` | Modified | Tests for plane sampling integration |
| `tests/test_registration_widget.py` | Modified | Updated tests for new behavior |

---

## How has this PR been tested?

- [x] All existing tests pass
- [x] New unit tests added for plane sampling functions
- [x] New unit tests for rotation control widgets
- [x] Integration tests for automated target selection
- [x] Manual testing in Napari UI for:
  - Smooth slider interaction
  - Plane sampling at various rotation angles
  - Z-slider plane updates
  - Interpolation order changes
  - Automated slice detection workflow

---

## Is this a breaking change?

**Yes**, this is a breaking change since it changes the default behavior:

- **Before:** Relied on Napari's orthogonal slicing + full 3D volume rotation
- **After:** Uses resampling for arbitrary plane sampling from static volumes

Users with custom workflows depending on the rotated 3D volume layers will need to update to use the new sampled 2D plane layers.

---

## Does this PR require an update to the documentation?

**Yes**, documentation updates needed for:

1. User guide: Explain new rotation controls and interpolation options
2. API documentation: Document new `plane_sampling` module
3. Deprecation notice: `rotate_volume()` is deprecated
4. Tutorial updates: Show new automated detection workflow

---

## Performance Benchmarks

| Metric | Before (Volume Rotation) | After (Plane Sampling) | Improvement |
|--------|-------------------------|------------------------|-------------|
| Time per iteration (Bayesian opt) | ~2.5s | ~0.6s | **4.2× faster** |
| Memory per iteration | ~500 MB | ~15 MB | **97% savings** |
| UI responsiveness during slider drag | Laggy | Smooth | Subjective improvement |
| Z-slider range stability | Changes with rotation | Constant | Fixed bug |

---

## Checklist

- [x] The code has been tested locally
- [x] Tests have been added to cover all new functionality (unit & integration)
- [ ] The documentation has been updated to reflect any changes *(pending)*
- [x] The code has been formatted with `pre-commit`
- [x] Ruff linting passes
- [x] All new and existing tests pass
