import json
import re
from pathlib import Path

import numpy as np
import scipy.ndimage as ndi
from napari.viewer import Viewer
from napari.utils.notifications import show_info, show_error


def sample_and_visualise_slice(viewer: Viewer, corners: np.ndarray, atlas_layer) -> None:
    """
    Uses scipy.ndimage.map_coordinates to extract the actual pixel data
    from the 3D atlas at the location of the 'corners'.
    """
    print("Sampling atlas slice...")
    
    # 1. Get the 3D Volume
    volume = atlas_layer.data
    
    # 2. Define resolution of the sampled slice
    # Estimate size based on physical edge length
    width_phys = np.linalg.norm(corners[1] - corners[0])
    height_phys = np.linalg.norm(corners[3] - corners[0])
    
    # We want a reasonable pixel size (e.g. 500-1000px wide)
    # This prevents lag if the physical size is huge (12000 microns)
    max_dim = 800
    scale_factor = min(1.0, max_dim / max(width_phys, height_phys))
    
    out_shape = (int(height_phys * scale_factor), int(width_phys * scale_factor))
    
    # 3. Create the Sampling Grid
    # Interpolate points between the 4 corners
    # Corner order is now [TL, TR, BR, BL] (Clockwise)
    row_linspace = np.linspace(0, 1, out_shape[0])
    col_linspace = np.linspace(0, 1, out_shape[1])
    
    # Vectors for the plane edges
    top_edge = corners[1] - corners[0]   # TL -> TR
    left_edge = corners[3] - corners[0]  # TL -> BL
    origin = corners[0]                  # TL
    
    # Create meshgrid for interpolation
    r, c = np.meshgrid(row_linspace, col_linspace, indexing='ij')
    
    # Calculate sample points in 3D PHYSICAL space
    # shape: (3, height, width)
    sample_coords = np.zeros((3, *out_shape))
    for i in range(3): # x, y, z components
        sample_coords[i] = origin[i] + (r * left_edge[i]) + (c * top_edge[i])

    # 4. Map Physical Coordinates -> Voxel Indices
    # We must divide by the layer scale to get array indices
    layer_scale = np.array(atlas_layer.scale).flatten()
    
    # Handle scale length mismatch (2D vs 3D)
    if len(layer_scale) == 2: 
        layer_scale = np.array([*layer_scale, 1.0])
    elif len(layer_scale) > 3:
        layer_scale = layer_scale[:3]
        
    # Reshape for broadcasting: (3, 1, 1)
    voxel_coords = sample_coords / layer_scale.reshape(3, 1, 1)

    # 5. Sample the volume! (Order=1 is linear interpolation, fast)
    try:
        sampled_slice = ndi.map_coordinates(volume, voxel_coords, order=1)
        
        # Add to Napari
        viewer.add_image(
            sampled_slice,
            name="Sampled Oblique Slice",
            colormap="turbo",
            opacity=1.0
        )
        show_info(f"Sampled slice created with shape {out_shape}")
        
    except Exception as e:
        print(f"Sampling failed: {e}")
        show_error("Failed to sample atlas slice (check console for details)")


def visualise_cutting_plane(viewer: Viewer, json_path: str | Path) -> None:
    """
    Main function to read registration JSON, fix geometry, and visualize.
    """
    json_path = Path(json_path)

    if not json_path.exists():
        show_error(f"JSON not found: {json_path}")
        return

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        show_error(f"Error reading JSON: {e}")
        return

    corners = data.get("atlas_slice_corners")
    if corners is None:
        show_error("JSON missing 'atlas_slice_corners'")
        return

    corners = np.array(corners, dtype=float)

    # --- FIX 1: UN-CROSS THE BOWTIE ---
    # Swap last two points to make a proper loop: [TL, TR, BR, BL]
    corners[[2, 3]] = corners[[3, 2]]

    # --- FIX 2: HANDLE SCALE MISMATCH ---
    resolution = 1.0
    atlas_layer = None
    
    # Find the atlas layer to check its resolution name
    for layer in viewer.layers:
        # We look for "allen", "reference", or "registered image"
        if any(x in layer.name.lower() for x in ["allen", "reference", "registered image"]):
            atlas_layer = layer
            
            # 2a. Detect resolution from name (e.g. "allen_mouse_25um")
            match = re.search(r"(\d+)um", layer.name)
            if match:
                resolution = float(match.group(1))
                print(f"Detected Atlas Resolution: {resolution} um/pixel")
            
            # 2b. Check current scale
            layer_scale = layer.scale[0] if hasattr(layer, 'scale') else 1.0
            
            # If layer is Unscaled (pixels) but Corners are Scaled (microns), we DOWN-SCALE corners
            if layer_scale == 1.0 and np.max(corners) > 5000:
                print(f"Downscaling corners by {resolution} to match voxel grid.")
                corners = corners / resolution
            
            break

    # --- DRAWING THE PLANE ---
    # Remove old layers
    for name in ["Registration Plane", "Viewing Angle", "Sampled Oblique Slice"]:
        if name in viewer.layers:
            viewer.layers.remove(name)

    # Add the Cyan Plane
    viewer.add_shapes(
        corners,
        shape_type="polygon",
        name="Registration Plane",
        edge_width=4,
        edge_color="cyan",
        face_color=[0, 1, 1, 0.2],
        opacity=0.8
    )

    # Add the Normal Vector (Arrow)
    center = np.mean(corners, axis=0)
    vec1 = corners[1] - corners[0]
    vec2 = corners[2] - corners[0]
    normal = np.cross(vec1, vec2)
    
    norm_len = np.linalg.norm(normal)
    if norm_len > 0:
        # Scale arrow to be reasonable size
        arrow_len = np.mean([np.linalg.norm(vec1), np.linalg.norm(vec2)]) * 0.5
        normal = (normal / norm_len) * arrow_len
        
        viewer.add_shapes(
            np.array([center, center + normal]),
            shape_type="path",
            name="Viewing Angle",
            edge_color="yellow",
            edge_width=6
        )

    # --- TRIGGER SAMPLING ---
    if atlas_layer is not None:
        sample_and_visualise_slice(viewer, corners, atlas_layer)
    else:
        show_info("Could not find Atlas layer - skipping texture sampling.")

    # Reset camera to look at the new plane
    viewer.camera.center = center