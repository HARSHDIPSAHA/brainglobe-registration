# BrainGlobe Registration - Comprehensive Repository Analysis

## Table of Contents
1. [Project Overview](#project-overview)
2. [Repository Structure](#repository-structure)
3. [Core Components](#core-components)
4. [Pipeline Flow](#pipeline-flow)
5. [File-by-File Analysis](#file-by-file-analysis)
6. [Folder-by-Folder Analysis](#folder-by-folder-analysis)
7. [Dependencies and Integration](#dependencies-and-integration)
8. [Testing Infrastructure](#testing-infrastructure)

---

## Project Overview

**BrainGlobe Registration** is a napari plugin for registering biological brain images to standardized BrainGlobe atlases using the Elastix registration framework. The tool enables neuroscientists to align experimental brain images (2D slices or 3D volumes) with reference atlases, facilitating spatial analysis, annotation transfer, and quantitative measurements.

### Key Features
- **Interactive GUI**: Napari-based interface for visual registration workflow
- **Multiple Transform Types**: Supports affine and B-spline transformations
- **Automated Slice Detection**: Bayesian optimization for automatic atlas slice selection
- **Flexible Parameter Configuration**: Customizable Elastix registration parameters
- **Atlas Integration**: Seamless integration with BrainGlobe atlas ecosystem
- **2D and 3D Support**: Handles both 2D brain slices and 3D volumes

---

## Repository Structure

```
brainglobe-registration/
├── brainglobe_registration/          # Main package
│   ├── __init__.py                   # Package initialization
│   ├── registration_widget.py       # Main widget orchestrator
│   ├── automated_target_selection.py # Bayesian optimization
│   ├── similarity_metrics.py        # Image similarity calculations
│   ├── sample_data.py               # Sample data loading
│   ├── napari.yaml                  # Napari plugin manifest
│   ├── elastix/                     # Elastix registration module
│   ├── utils/                       # Utility functions
│   │   ├── __init__.py
│   │   ├── atlas.py                 # Atlas-specific operations
│   │   ├── file.py                  # File I/O operations
│   │   ├── preprocess.py            # Image preprocessing
│   │   ├── transforms.py            # Geometric transformations
│   │   ├── napari.py                # Napari integration utilities
│   │   ├── logging.py               # Logging configuration
│   │   └── visuals.py               # Visualization utilities (checkerboard)
│   ├── widgets/                     # UI component widgets
│   │   ├── __init__.py
│   │   ├── select_images_view.py    # Atlas and image selection
│   │   ├── transform_select_view.py # Transform type selection
│   │   ├── adjust_moving_image_view.py # Manual adjustments
│   │   ├── parameter_list_view.py   # Elastix parameter editor
│   │   ├── target_selection_widget.py # Automated slice dialog
│   │   └── qc_widget.py             # Quality control widget
│   ├── parameters/                  # Elastix parameter files
│   └── resources/                   # Sample images
├── tests/                           # Test suite
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_visuals.py              # Checkerboard tests
│   └── ...
├── imgs/                            # Documentation images
├── pyproject.toml                   # Project configuration
├── README.md                        # User documentation
└── LICENSE                          # BSD-3-Clause license
```

---

## Core Components

### 1. Registration Pipeline
The registration process follows these stages:
1. **Image Selection**: User selects moving image and target atlas
2. **Preprocessing**: Image filtering, scaling, and normalization
3. **Initial Alignment**: Manual or automated slice/rotation selection
4. **Registration**: Elastix-based transformation computation
5. **Post-processing**: Transform application, annotation transfer, result visualization
6. **Quality Control**: Checkerboard visualization and QC metrics for validation

### 2. Quality Control (QC) Feature
The QC feature provides visual tools for assessing registration quality:

**Checkerboard Visualization**:
- Alternates between moving and registered images in a checkerboard pattern
- Misalignments appear as discontinuities in the pattern
- Configurable square size (4-512 pixels, adaptive default based on image dimensions)
- Real-time updates when square size changes (debounced)
- Supports both 2D and 3D images
- Uses background threading to keep UI responsive during computation

**Implementation Details**:
- `QCWidget` provides UI controls (checkbox, square size spinbox, Plot/Clear buttons)
- `generate_checkerboard()` in `visuals.py` creates the pattern using NumPy broadcasting
- Normalization option matches intensity ranges between images for fair comparison
- Layer update optimization: modifies existing layer data instead of remove/re-add

**Future QC Features** (planned):
- Intensity difference maps
- Jacobian determinant analysis
- Deformation field visualization

### 2. Architecture Layers
- **UI Layer**: Napari widgets and Qt-based components
- **Business Logic**: Registration orchestration and parameter management
- **Registration Engine**: Elastix integration via ITK
- **Utilities**: Image processing, transforms, file I/O, atlas operations
- **Quality Control**: Checkerboard visualization, QC metrics (future: intensity maps, Jacobian analysis)

---

## Pipeline Flow

### Complete Registration Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE (Napari)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Select Images│  │ Adjust Image │  │ Transform    │      │
│  │    View      │→ │     View     │→ │   Select     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              RegistrationWidget (Orchestrator)              │
│  • Manages widget lifecycle                                 │
│  • Coordinates user interactions                            │
│  • Handles atlas loading and layer management               │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    PREPROCESSING STAGE                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Image Filter │  │ Image Scale  │  │ Normalize    │     │
│  │ (preprocess) │→ │ (transforms) │→ │ (similarity) │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              INITIAL ALIGNMENT (Optional)                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Automated Slice Detection (Bayesian Optimization) │    │
│  │  • Optimize pitch, yaw, roll, z-slice              │    │
│  │  • Compute similarity metrics                      │    │
│  │  • Return optimal alignment parameters              │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                  REGISTRATION STAGE                         │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Elastix Registration (elastix/register.py)          │    │
│  │  1. Setup parameter objects                        │    │
│  │  2. Run ElastixRegistrationMethod                  │    │
│  │  3. Extract transform parameters                    │    │
│  │  4. Apply transforms to images/annotations           │    │
│  └────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    POST-PROCESSING                          │
│  • Transform moving image                                   │
│  • Transform atlas annotations                              │
│  • Calculate deformation fields                             │
│  • Compute region sizes                                     │
│  • Display results in Napari                                │
└─────────────────────────────────────────────────────────────┘
```

---

## File-by-File Analysis

### Root Level Files

#### `pyproject.toml`
**Purpose**: Project configuration and dependency management
**Key Contents**:
- Package metadata (name, version, description)
- Python version requirements (>=3.11)
- Core dependencies: napari, itk-elastix, brainglobe-atlasapi, dask, scikit-image
- Development dependencies: pytest, black, mypy, ruff
- Build system configuration (setuptools)
- Tool configurations (black, ruff, pytest)

**Role in Pipeline**: Defines the project structure and ensures all required libraries are available for the registration workflow.

#### `README.md`
**Purpose**: User-facing documentation
**Contents**: Installation instructions, usage guide, atlas installation, citation information

**Role in Pipeline**: Provides user guidance for setting up and using the registration tool.

#### `LICENSE`
**Purpose**: BSD-3-Clause license file
**Role**: Legal framework for open-source distribution

#### `MANIFEST.in`
**Purpose**: Specifies additional files to include in package distribution
**Role**: Ensures parameter files and resources are packaged correctly

---

### Main Package: `brainglobe_registration/`

#### `__init__.py`
**Purpose**: Package initialization
**Contents**: Version import and module exports
**Role**: Makes the package importable and exposes version information

#### `napari.yaml`
**Purpose**: Napari plugin manifest
**Key Contents**:
- Plugin name and display name
- Command definitions for widget creation
- Sample data definitions (2D and 3D examples)
- Widget registration

**Role in Pipeline**: Registers the plugin with Napari, making it discoverable and accessible through the Napari interface. Defines entry points for the registration widget and sample data loading.

#### `registration_widget.py` (1083 lines)
**Purpose**: Main widget orchestrator - the central controller for the registration workflow
**Key Responsibilities**:
1. **Widget Lifecycle Management**: Initializes and manages all sub-widgets
2. **Atlas Management**: Loads and displays BrainGlobe atlases
3. **Image Layer Management**: Handles Napari layer creation and updates
4. **Registration Orchestration**: Coordinates the entire registration process
5. **User Interaction Handling**: Connects UI signals to business logic
6. **Transform Application**: Applies manual adjustments to images
7. **Result Visualization**: Displays registered images and annotations
8. **Quality Control Visualizations**: Checkerboard pattern generation and QC tools

**Key Methods**:
- `__init__()`: Sets up UI components, connects signals, initializes state
- `_on_atlas_selection()`: Loads selected atlas and creates Napari layers
- `_on_run_registration()`: Executes the full registration pipeline
- `_apply_manual_adjustments()`: Applies user-specified translations/rotations
- `_scale_moving_image()`: Rescales moving image to match atlas resolution
- `_rotate_atlas()`: Applies 3D rotations to atlas volume
- `_run_automated_slice_detection()`: Triggers Bayesian optimization
- `_on_plot_qc_clicked()`: Generates selected QC visualizations
- `_show_checkerboard()`: Creates checkerboard pattern using background threading
- `_generate_checkerboard_thread()`: Background computation of checkerboard pattern
- `_update_checkerboard_layer()`: Updates Napari layer with checkerboard data
- `_on_square_size_value_changed()`: Debounced handler for square size changes
- `_on_clear_qc_images()`: Removes all QC visualization layers

**Key State Variables**:
- `_checkerboard_layer`: Reference to checkerboard Napari layer
- `_cached_moving_data`: Cached moving image data for QC
- `_cached_registered_data`: Cached registered image data for QC

**Role in Pipeline**: Central hub that coordinates all components. Receives user input from widgets, manages data flow, calls registration functions, and updates the Napari viewer with results. Also provides QC visualization tools for registration validation.

#### `automated_target_selection.py`
**Purpose**: Automated slice detection using Bayesian optimization
**Key Functions**:

1. **`registration_objective()`**:
   - Objective function for Bayesian optimization
   - Rotates 3D atlas volume by pitch/yaw
   - Extracts z-slice from rotated volume
   - Runs affine registration between slice and sample
   - Computes similarity metric (MI, NCC, SSIM, or combined)
   - Returns similarity score

2. **`similarity_only_objective()`**:
   - Optimizes roll angle independently
   - Rotates 2D slice and computes similarity
   - Used for fine-tuning after coarse optimization

3. **`run_bayesian_generator()`**:
   - Main optimization function
   - Two-stage optimization:
     - **Coarse stage**: Optimizes pitch, yaw, z-slice
     - **Fine stage**: Optimizes roll angle
   - Uses BayesianOptimization with Gaussian Process
   - Yields intermediate results for progress tracking
   - Returns optimal alignment parameters

**Role in Pipeline**: Automates the initial alignment step, reducing manual effort. Finds the best matching atlas slice and rotation angles by exploring parameter space intelligently.

#### `similarity_metrics.py`
**Purpose**: Image similarity computation for registration quality assessment
**Key Functions**:

1. **`compute_similarity_metric()`**:
   - Computes similarity between two images
   - Supports multiple metrics:
     - **MI (Mutual Information)**: Information-theoretic measure
     - **NCC (Normalized Cross-Correlation)**: Statistical correlation
     - **SSIM (Structural Similarity Index)**: Perceptual similarity
     - **Combined**: Weighted combination of all three

2. **`prepare_images()`**:
   - Pads images to matching shapes
   - Normalizes images to [0, 1] range
   - Prepares images for comparison

3. **`pad_to_match_shape()`**:
   - Symmetrically pads two images to largest dimensions
   - Ensures fair comparison regardless of size differences

**Role in Pipeline**: Provides quantitative measures of registration quality. Used by automated slice detection to evaluate alignment and by users to assess registration results.

#### `sample_data.py`
**Purpose**: Provides sample data for testing and demonstration
**Functions**:
- `load_sample_data_2d()`: Loads 2D coronal mouse brain section
- `load_sample_data_3d()`: Loads 3D mouse brain volume

**Role in Pipeline**: Enables users to test the plugin without their own data. Registered as Napari sample data for easy access.

---

### Elastix Module: `brainglobe_registration/elastix/`

#### `__init__.py`
**Purpose**: Module initialization
**Role**: Makes elastix submodule importable

#### `register.py`
**Purpose**: Core registration engine - interface to ITK-Elastix
**Key Functions**:

1. **`run_registration()`**:
   - Main registration function
   - Filters images (optional)
   - Converts NumPy arrays to ITK image views
   - Creates ElastixRegistrationMethod object
   - Sets up parameter objects from parameter lists
   - Executes registration
   - Saves transform parameters (optional)
   - Returns transform parameter object

2. **`transform_image()`**:
   - Applies computed transform to an image
   - Uses TransformixFilter
   - Preserves original data type

3. **`transform_annotation_image()`**:
   - Transforms annotation/label images
   - Uses nearest-neighbor interpolation (order=0)
   - Handles label remapping for uint16 compatibility
   - Preserves label integrity

4. **`calculate_deformation_field()`**:
   - Computes deformation field visualization
   - Shows pixel displacement vectors
   - Useful for understanding transformation

5. **`invert_transformation()`**:
   - Computes inverse transform
   - Enables reverse mapping (atlas → sample space)

6. **`setup_parameter_object()`**:
   - Creates ITK ParameterObject from parameter dictionaries
   - Handles multiple transform stages
   - Configures Elastix parameter maps

**Role in Pipeline**: Direct interface to Elastix registration engine. Converts between NumPy (Python) and ITK (C++) formats, executes registration algorithms, and applies computed transforms. This is the computational core of the registration process.

---

### Utilities Module: `brainglobe_registration/utils/`

#### `__init__.py`
**Purpose**: Utility module initialization
**Role**: Exposes utility functions to the package

#### `atlas.py`
**Purpose**: Atlas-specific operations and utilities
**Key Functions**:

1. **`calculate_region_size()`**:
   - Computes area/volume of brain regions
   - Separates left/right hemisphere measurements
   - Converts pixel counts to physical units (mm²/mm³)
   - Outputs CSV with structure names and sizes

2. **`convert_atlas_labels()`**:
   - Remaps annotation labels to fit uint16 range
   - Some atlases have labels > 65535
   - Creates mapping dictionary for restoration

3. **`restore_atlas_labels()`**:
   - Restores original label values after transformation
   - Uses mapping from convert_atlas_labels()

4. **`generate_mask_from_atlas_annotations()`**:
   - Creates binary mask from annotation array
   - Identifies brain vs. background regions

5. **`mask_atlas()`** / **`mask_atlas_with_annotations()`**:
   - Applies masks to atlas reference images
   - Useful for focused registration

**Role in Pipeline**: Handles atlas-specific data operations, label management, and quantitative analysis. Ensures compatibility between different atlas formats and enables region-based measurements.

#### `file.py`
**Purpose**: File I/O operations
**Key Functions**:

1. **`open_parameter_file()`**:
   - Parses Elastix parameter files
   - Extracts key-value pairs from text format
   - Returns parameter dictionary
   - Handles Elastix parameter file syntax: `(Key value1 value2 ...)`

2. **`serialize_registration_widget()`**:
   - Custom serializer for widget state
   - Handles Napari layers, viewers, Path objects, atlases
   - Used for debugging/logging widget state

**Role in Pipeline**: Enables loading of pre-configured Elastix parameters from text files. Supports multiple parameter sets (elastix_default, brainglobe_registration, ara_tools, brainregister_IBL).

#### `preprocess.py`
**Purpose**: Image preprocessing for registration
**Key Functions**:

1. **`filter_image()`**:
   - Applies filtering to 2D or 3D images
   - Processes plane-by-plane for 3D
   - Scales and converts to 16-bit

2. **`filter_plane()`**:
   - Applies despeckle and pseudo-flatfield filters
   - Reduces noise and illumination artifacts

3. **`despeckle_by_opening()`**:
   - Morphological opening operation
   - Removes small bright artifacts
   - Uses disk-shaped kernel

4. **`pseudo_flatfield()`**:
   - Corrects uneven illumination
   - Divides image by heavily blurred version
   - Normalizes intensity variations

**Role in Pipeline**: Prepares images for registration by reducing noise and artifacts that could interfere with alignment. Applied before registration to improve robustness.

#### `transforms.py`
**Purpose**: Geometric transformation utilities
**Key Functions**:

1. **`create_rotation_matrix()`**:
   - Creates 4×4 affine transformation matrix
   - Combines roll, yaw, pitch rotations
   - Centers rotation about image center
   - Computes bounding box for rotated volume
   - Returns transform matrix and output shape

2. **`rotate_volume()`**:
   - Applies 3D affine transformation to volume
   - Uses dask for efficient computation
   - Supports spline interpolation
   - Handles large volumes with chunking

3. **`scale_moving_image()`**:
   - Rescales moving image to match atlas resolution
   - Handles 2D and 3D images
   - Preserves physical dimensions
   - Uses skimage.rescale with anti-aliasing

4. **`calculate_rotated_bounding_box()`**:
   - Computes minimum bounding box for rotated volume
   - Transforms corner points
   - Finds min/max extents

**Role in Pipeline**: Provides geometric transformations for initial alignment. Enables manual and automated rotation/scaling of images before registration. Critical for handling orientation differences between sample and atlas.

#### `napari.py`
**Purpose**: Napari-specific utilities
**Key Functions**:

1. **`adjust_napari_image_layer()`**:
   - Applies translation and rotation to Napari layer
   - Updates layer affine transform
   - Rotates around image center

2. **`get_data_from_napari_layer()`**:
   - Extracts NumPy array from Napari layer
   - Handles dask arrays (computes on demand)
   - Supports slicing

3. **`find_layer_index()`**:
   - Locates layer by name in viewer
   - Returns layer index

4. **`get_image_layer_names()`**:
   - Lists all image layer names in viewer

5. **`check_atlas_installed()`**:
   - Verifies atlases are available
   - Shows error dialog if none found

**Role in Pipeline**: Bridges between Napari viewer and registration logic. Handles layer management, data extraction, and user notifications. Essential for GUI integration.

#### `logging.py`
**Purpose**: Logging configuration and utilities
**Key Components**:

1. **`FancyBayesLogger`**:
   - Custom logger for Bayesian optimization
   - Redirects output to fancylog
   - Formats optimization step information

2. **`StripANSIColorFilter`**:
   - Removes ANSI color codes from log messages
   - Ensures clean log files

3. **`get_auto_slice_logging_args()`**:
   - Formats automated slice detection parameters
   - Creates named tuple for structured logging

**Role in Pipeline**: Provides structured logging for debugging and monitoring. Especially important for tracking Bayesian optimization progress.

#### `visuals.py`
**Purpose**: Visualization utilities for registration quality assessment
**Key Functions**:

1. **`generate_checkerboard()`**:
   - Creates checkerboard pattern by alternating between two images
   - Supports 2D and 3D images (applies pattern to last two dimensions)
   - Optional normalization to match intensity ranges between images
   - Handles shape mismatches by cropping to overlapping region
   - Configurable square size (default 32 pixels)
   - Uses `np.ogrid` for memory-efficient sparse grid creation
   - Broadcasting automatically handles 2D vs 3D images

2. **`_normalize_images_for_comparison()`**:
   - Normalizes two images to match intensity ranges
   - Scales to uint16 max (65535) for integer types
   - Scales to [0, 1] for float types
   - Handles constant images (sets to mid-range value)

3. **`_generate_checkerboard()`**:
   - Core implementation for 2D/3D checkerboard generation
   - Creates mask using integer division: `(y // size + x // size) % 2`
   - Uses `np.where()` for efficient single-pass assignment

**Role in Pipeline**: Provides visual quality assessment tools. The checkerboard visualization helps users assess registration accuracy by highlighting misalignments between the moving and registered images as discontinuities in the checkerboard pattern.

---

### Widgets Module: `brainglobe_registration/widgets/`

#### `__init__.py`
**Purpose**: Widget module initialization
**Role**: Makes widgets importable

#### `select_images_view.py`
**Purpose**: UI component for selecting atlas and moving image
**Key Components**:

- **`SelectImagesView`**: Main widget class
  - Two dropdown menus (atlas selection, sample image selection)
  - Emits signals when selections change
  - Updates dynamically as layers are added/removed

- **`SampleImageComboBox`**: Custom combobox
  - Emits signal before popup shows
  - Enables dynamic layer list updates

**Signals**:
- `atlas_index_change`: Emitted when atlas selection changes
- `moving_image_index_change`: Emitted when sample selection changes
- `sample_image_popup_about_to_show`: Emitted before dropdown opens

**Role in Pipeline**: First step in registration workflow. User selects which images to register. Widget communicates selections to RegistrationWidget.

#### `transform_select_view.py`
**Purpose**: UI for selecting transform types and parameter sets
**Key Components**:

- **`TransformSelectView`**: Table widget for transform configuration
  - Rows for each transform stage (affine, bspline, etc.)
  - Dropdowns for transform type and parameter file
  - Dynamically adds/removes rows
  - Supports multiple transform stages

**Transform Types**: `""` (empty), `"affine"`, `"bspline"`
**Parameter Sets**: `"elastix_default"`, `"brainglobe_registration"`, `"ara_tools"`, `"brainregister_IBL"`

**Signals**:
- `transform_type_added_signal`: New transform type selected
- `transform_type_removed_signal`: Transform type cleared
- `file_option_changed_signal`: Parameter file changed

**Role in Pipeline**: Allows users to configure the registration pipeline. Users can specify multiple transform stages (e.g., affine then bspline) and choose parameter sets. This configuration drives the registration process.

#### `adjust_moving_image_view.py`
**Purpose**: UI for manual image adjustments and automated slice detection
**Key Components**:

- **`AdjustMovingImageView`**: Form widget with multiple controls
  - Pixel size inputs (X, Y, Z) for scaling
  - Data orientation field
  - Atlas rotation controls (pitch, yaw, roll)
  - Scale and rotation buttons
  - Reset button
  - Automatic slice detection button
  - Progress bar for optimization

**Features**:
- Shows/hides 3D-specific controls based on image dimensionality
- Connects to automated slice detection callback
- Displays optimization progress

**Signals**:
- `scale_image_signal`: Emitted when scaling requested
- `atlas_rotation_signal`: Emitted when rotation requested
- `reset_atlas_signal`: Emitted when reset requested

**Role in Pipeline**: Enables manual refinement of initial alignment. Users can adjust image scale and atlas orientation before registration. Also provides access to automated slice detection feature.

#### `parameter_list_view.py`
**Purpose**: UI for viewing and editing Elastix parameters
**Key Components**:

- **`RegistrationParameterListView`**: Editable table widget
  - Two columns: Parameter name, Parameter values
  - Allows direct editing of parameter values
  - Dynamically adds/removes rows
  - Tracks parameter name changes

**Features**:
- Real-time parameter dictionary updates
- Supports multi-value parameters (comma-separated)
- Handles parameter renaming and deletion
- Auto-adds empty row for new parameters

**Role in Pipeline**: Provides advanced users with fine-grained control over registration parameters. Users can modify Elastix settings (e.g., optimization iterations, grid spacing, similarity metrics) to tune registration behavior.

#### `target_selection_widget.py`
**Purpose**: Dialog for automated slice detection configuration
**Key Components**:

- **`AutoSliceDialog`**: Configuration dialog
  - Z-range selection (min/max slice indices)
  - Rotation bounds (pitch, yaw, roll in degrees)
  - Bayesian optimization parameters (init_points, n_iter)
  - Similarity metric selection
  - Combined metric weight configuration

**Features**:
- Validates input ranges
- Shows/hides weight controls based on metric selection
- Maps UI selections to internal parameter format

**Signals**:
- `parameters_confirmed`: Emitted with configuration dictionary

**Role in Pipeline**: Configures automated slice detection. Users specify search bounds and optimization parameters. Dialog collects settings and passes them to Bayesian optimization function.

#### `qc_widget.py`
**Purpose**: Quality Control (QC) widget for registration validation
**Key Components**:

- **`QCWidget`**: QWidget subclass for QC visualizations
  - **Checkerboard checkbox**: Toggle checkerboard visualization on/off
  - **Square size spinbox**: Configure checkerboard square size (4-512 pixels, default 32)
  - **Plot QC button**: Generate all selected QC visualizations
  - **Clear QC Images button**: Remove all QC visualization layers

**Features**:
- All controls disabled until registration completes
- Square size adapts to image dimensions (1/16th of smallest dimension)
- Real-time updates when square size changes (debounced)
- Tooltips explain each control's purpose

**Methods**:
- `set_enabled(enabled: bool)`: Enable/disable all QC controls

**Role in Pipeline**: Provides visual quality assessment tools for users to validate registration accuracy. The checkerboard pattern alternates between moving and registered images to highlight misalignments.

---

### Parameters Directory: `brainglobe_registration/parameters/`

**Purpose**: Stores pre-configured Elastix parameter files

**Structure**:
```
parameters/
├── ara_tools/              # ARA Tools parameter set
│   ├── affine.txt
│   └── bspline.txt
├── brainglobe_registration/  # Default BrainGlobe parameters
│   ├── affine.txt
│   ├── automated_reg_affine.txt  # For automated slice detection
│   └── bspline.txt
├── brainregister_IBL/      # IBL BrainRegister parameters
│   ├── affine.txt
│   └── bspline.txt
└── elastix_default/        # Default Elastix parameters
    ├── affine.txt
    └── bspline.txt
```

**Parameter File Format**:
- Text files with Elastix parameter syntax
- Format: `(ParameterName value1 value2 ...)`
- Contains optimization settings, transform parameters, interpolation options

**Role in Pipeline**: Provides ready-to-use parameter configurations for different use cases. Users can select parameter sets based on their needs (e.g., ARA Tools for Allen Reference Atlas, IBL for International Brain Laboratory workflows).

---

### Resources Directory: `brainglobe_registration/resources/`

**Purpose**: Stores sample images for testing and demonstration

**Files**:
- `sample_hipp.tif`: 2D coronal mouse brain section (hippocampus)
- `sample_3d.tif`: 3D mouse brain volume

**Role in Pipeline**: Provides example data for users to test the plugin. Loaded via `sample_data.py` functions and registered as Napari sample data.

---

## Folder-by-Folder Analysis

### `brainglobe_registration/` (Main Package)
**Purpose**: Core package containing all registration functionality
**Contents**:
- Main widget and orchestration logic
- Registration engine (Elastix integration)
- Utility functions (atlas, file I/O, transforms, preprocessing)
- UI widgets (Qt-based components)
- Parameter files (Elastix configurations)
- Sample resources (test images)

**Role**: Central package that provides all registration capabilities. Imported by Napari to create the plugin.

### `brainglobe_registration/elastix/`
**Purpose**: Elastix registration engine wrapper
**Contents**: `register.py` - ITK-Elastix interface functions
**Role**: Provides Python interface to C++ Elastix library via ITK. Handles all low-level registration operations.

### `brainglobe_registration/utils/`
**Purpose**: Reusable utility functions
**Contents**:
- `atlas.py`: Atlas-specific operations (region size calculation, label remapping, masking)
- `file.py`: File I/O (parameter file parsing, widget serialization)
- `preprocess.py`: Image filtering (despeckle, pseudo-flatfield correction)
- `transforms.py`: Geometric transformations (rotation matrices, volume scaling)
- `napari.py`: Napari integration (layer management, data extraction)
- `logging.py`: Logging utilities (Bayesian optimization logging)
- `visuals.py`: Visualization utilities (checkerboard pattern generation for QC)

**Role**: Provides shared functionality used across the package. Modular design enables code reuse and maintainability.

### `brainglobe_registration/widgets/`
**Purpose**: UI component library
**Contents**:
- `select_images_view.py`: Atlas and moving image selection dropdowns
- `transform_select_view.py`: Transform type and parameter set selection table
- `adjust_moving_image_view.py`: Manual adjustment controls (sliders for pitch/yaw/roll, interpolation dropdown)
- `parameter_list_view.py`: Editable Elastix parameter table
- `target_selection_widget.py`: Automated slice detection configuration dialog
- `qc_widget.py`: Quality control widget (checkerboard visualization, square size control)

**Role**: Modular UI components that can be composed into the main registration widget. Each widget handles a specific aspect of user interaction.

### `brainglobe_registration/parameters/`
**Purpose**: Elastix parameter file storage
**Contents**: Multiple subdirectories with parameter sets for different workflows
**Role**: Provides pre-configured registration parameters. Users can select appropriate sets or use as templates for customization.

### `tests/`
**Purpose**: Comprehensive test suite
**Contents**:
- `conftest.py`: Pytest fixtures and configuration
- Test files for each major component
- `test_images/`: Test data and expected results
- `test_utils/`: Utility function tests

**Key Test Files**:
- `test_registration_widget.py`: Main widget tests (including checkerboard QC integration)
- `test_register.py`: Elastix registration tests
- `test_automated_target_selection.py`: Bayesian optimization tests
- `test_similarity_metrics.py`: Similarity metric tests
- `test_visuals.py`: Checkerboard visualization tests (2D/3D, normalization, edge cases)
- Component-specific tests for each widget and utility

**Role**: Ensures code quality and correctness. Provides regression testing and validates functionality across different scenarios.

### `imgs/`
**Purpose**: Documentation images
**Contents**: Screenshots of the plugin interface
**Role**: Visual documentation for README and user guides. Shows plugin appearance and workflow.

### `brainglobe_registration.egg-info/`
**Purpose**: Package metadata (generated during installation)
**Contents**: Package information, dependencies, entry points
**Role**: Used by package managers (pip) to install and manage the package.

---

## Dependencies and Integration

### Core Dependencies

1. **napari** (>=0.4.18): Visualization framework
   - Provides viewer, layers, and plugin infrastructure
   - Enables interactive image display and manipulation

2. **itk-elastix**: Elastix registration library
   - Python bindings for Elastix
   - Provides registration algorithms and transform application

3. **brainglobe-atlasapi**: Atlas management
   - Loads and manages BrainGlobe atlases
   - Provides atlas metadata and annotation data

4. **dask / dask-image**: Lazy array computation
   - Enables efficient processing of large 3D volumes
   - Chunked array operations for memory efficiency

5. **scikit-image**: Image processing
   - Image transformations, filtering, metrics
   - Used for preprocessing and similarity computation

6. **bayesian-optimization**: Automated parameter search
   - Gaussian Process-based optimization
   - Finds optimal alignment parameters

7. **numpy / scipy**: Numerical computing
   - Array operations, mathematical functions
   - Core data structures and algorithms

### Integration Points

1. **Napari Plugin System**: Registers as Napari plugin via `napari.yaml`
2. **BrainGlobe Ecosystem**: Integrates with BrainGlobe atlas infrastructure
3. **Elastix Framework**: Uses Elastix for registration algorithms
4. **Qt/PyQt**: UI framework for widget creation

---

## Testing Infrastructure

### Test Organization

Tests are organized to mirror the package structure:
- Component tests for each module
- Integration tests for workflows
- Fixtures for common test data

### Key Test Fixtures (`conftest.py`)

1. **`make_napari_viewer_with_images`**: Creates Napari viewer with test images
2. **`parameter_lists`**: Loads registration parameters for testing
3. **`mock_brainglobe_user_folders`**: Mocks user data directories
4. **`setup_preexisting_local_atlases`**: Sets up test atlases

### Test Coverage

Tests cover:
- Widget initialization and interaction
- Registration execution
- Transform application
- Image preprocessing
- Similarity metric computation
- Automated slice detection
- Utility functions
- Error handling

---

## Data Flow Summary

### Registration Request Flow

1. **User Action** → Widget Signal
2. **Widget Signal** → RegistrationWidget Handler
3. **Handler** → Extract Data from Napari Layers
4. **Data Extraction** → Preprocessing (filter, scale, normalize)
5. **Preprocessing** → Elastix Registration
6. **Registration** → Transform Parameters
7. **Transform Parameters** → Apply to Images/Annotations
8. **Transformed Data** → Create Napari Layers
9. **Napari Layers** → Display in Viewer

### Automated Slice Detection Flow

1. **User Triggers** → AutoSliceDialog
2. **Dialog** → Configuration Parameters
3. **Parameters** → Bayesian Optimization
4. **Optimization** → Registration Objective Function
5. **Objective** → Rotate Atlas, Extract Slice, Register, Compute Similarity
6. **Similarity Scores** → Optimization Updates
7. **Optimal Parameters** → Update Atlas Display
8. **User Confirms** → Proceed to Registration

### Quality Control (Checkerboard) Flow

1. **Registration Complete** → QC widget enabled, square size adapted to image
2. **User Checks "Checkerboard"** → `_on_plot_qc_clicked()` triggered
3. **Data Validation** → Verify moving and registered images have matching dimensions
4. **Background Worker** → `_generate_checkerboard_thread()` computes pattern
5. **Thread Completion** → `_update_checkerboard_layer()` updates Napari layer
6. **User Adjusts Square Size** → Debounced timer triggers regeneration
7. **User Clears QC** → All QC layers removed, checkboxes unchecked

---

## Key Design Patterns

1. **Widget Composition**: Main widget composes smaller specialized widgets
2. **Signal-Slot Architecture**: Qt signals connect UI to business logic
3. **Separation of Concerns**: UI, business logic, and registration engine are separate
4. **Modular Utilities**: Reusable functions organized by domain
5. **Configuration Files**: External parameter files for flexibility
6. **Lazy Evaluation**: Dask arrays for efficient large-volume processing

---

## Extension Points

The architecture supports extension in several areas:

1. **New Transform Types**: Add to `transform_select_view.py` options
2. **Custom Parameters**: Add parameter files to `parameters/` directory
3. **New Similarity Metrics**: Extend `similarity_metrics.py`
4. **Additional Preprocessing**: Add functions to `preprocess.py`
5. **New Widgets**: Create widgets following existing patterns
6. **Atlas Formats**: Extend `atlas.py` for new atlas types

---

## Conclusion

The BrainGlobe Registration repository is a well-structured, modular napari plugin that provides comprehensive image registration capabilities. The architecture separates concerns effectively, with clear boundaries between UI, business logic, and registration engine. The use of established frameworks (Napari, Elastix, Qt) ensures reliability and maintainability, while the modular design enables extensibility for future enhancements.

The pipeline supports both manual and automated workflows, providing flexibility for different use cases. Comprehensive testing ensures code quality, and the parameter file system allows users to customize registration behavior without code changes.
