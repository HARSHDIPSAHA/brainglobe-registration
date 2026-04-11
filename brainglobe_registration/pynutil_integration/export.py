"""
Export registration results in PyNutil-compatible format.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import numpy as np
from tifffile import imwrite, imread


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
    # PyNutil requires section numbers in filename (e.g., _s001)
    import re
    seg_dir = pynutil_dir / "segmentations"
    seg_dir.mkdir(exist_ok=True)
    moving_name = Path(moving_image_path).name
    # Add section number if not present (check for _s### or s### pattern)
    if not re.search(r"_s\d+", moving_name, re.IGNORECASE):
        # Insert _s001 before extension
        stem = Path(moving_name).stem
        suffix = Path(moving_name).suffix
        moving_name = f"{stem}_s001{suffix}"
    shutil.copy(moving_image_path, seg_dir / moving_name)

    # Copy registered image
    reg_dir = pynutil_dir / "registered"
    reg_dir.mkdir(exist_ok=True)
    reg_name = Path(registered_image_path).name
    shutil.copy(registered_image_path, reg_dir / reg_name)

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
        image_path=str(reg_dir / reg_name),
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
