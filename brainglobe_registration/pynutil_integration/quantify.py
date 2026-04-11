"""
Run PyNutil quantification on registered images.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

try:
    import PyNutil as pnt
    from PyNutil import read_alignment, load_atlas_data
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
