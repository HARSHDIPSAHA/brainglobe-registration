"""Tests for PyNutil integration."""

import pytest
import numpy as np
from pathlib import Path

from brainglobe_registration.pynutil_integration import (
    export_for_pynutil,
    analyze_image_quality,
    QCReport,
)


def test_export_for_pynutil(tmp_path):
    """Test PyNutil export creates correct structure."""
    # Create test image
    test_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    image_path = tmp_path / "test_image.tiff"

    from tifffile import imwrite
    imwrite(image_path, test_image)

    # Test export
    anchoring = np.array([10, 20, 30, 100, 0, 0, 0, 100, 0], dtype=np.float64)
    output_dir = tmp_path / "output"

    pynutil_dir = export_for_pynutil(
        moving_image_path=str(image_path),
        registered_image_path=str(image_path),
        atlas_name="allen_mouse_25um",
        anchoring=anchoring,
        output_dir=str(output_dir),
    )

    # Verify structure
    pynutil_path = Path(pynutil_dir)
    assert (pynutil_path / "segmentations").exists()
    assert (pynutil_path / "alignment.json").exists()
    assert (pynutil_path / "settings.json").exists()


def test_export_for_pynutil_with_damage_mask(tmp_path):
    """Test PyNutil export with damage mask."""
    # Create test image and damage mask
    test_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    image_path = tmp_path / "test_image.tiff"
    damage_mask = np.ones((100, 100), dtype=bool)
    damage_mask[:20, :20] = False  # Mark corner as damaged

    from tifffile import imwrite
    imwrite(image_path, test_image)

    # Test export with damage mask
    anchoring = np.array([10, 20, 30, 100, 0, 0, 0, 100, 0], dtype=np.float64)
    output_dir = tmp_path / "output"

    pynutil_dir = export_for_pynutil(
        moving_image_path=str(image_path),
        registered_image_path=str(image_path),
        atlas_name="allen_mouse_25um",
        anchoring=anchoring,
        output_dir=str(output_dir),
        damage_mask=damage_mask,
    )

    # Verify damage mask was saved
    pynutil_path = Path(pynutil_dir)
    assert (pynutil_path / "damage_mask.tiff").exists()


def test_analyze_image_quality_normal():
    """Test image quality analysis with normal image."""
    # Test normal image
    normal_img = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    report = analyze_image_quality(normal_img)

    assert report.quality_score > 0.5
    assert not report.potential_hemisphere
    assert not report.potential_damage


def test_analyze_image_quality_hemisphere():
    """Test image quality analysis with hemisphere image."""
    # Test hemisphere image (asymmetric)
    hemi_img = np.zeros((100, 100), dtype=np.uint8)
    hemi_img[:, :50] = np.random.randint(100, 200, (100, 50), dtype=np.uint8)
    report = analyze_image_quality(hemi_img)

    assert report.potential_hemisphere
    assert report.recommended_geometry in ["left_hemi", "right_hemi"]


def test_analyze_image_quality_damaged():
    """Test image quality analysis with damaged image."""
    # Test damaged image
    damaged_img = np.random.randint(100, 200, (100, 100), dtype=np.uint8)
    damaged_img[:50, :50] = 0  # Large black region
    report = analyze_image_quality(damaged_img)

    assert report.potential_damage
    assert report.requires_damage_mask


def test_analyze_image_quality_low_signal():
    """Test image quality analysis with low signal image."""
    # Test low signal image
    low_signal_img = np.random.randint(0, 30, (100, 100), dtype=np.uint8)
    report = analyze_image_quality(low_signal_img, threshold_low=50)

    assert report.low_signal
    assert report.quality_score < 0.8


def test_analyze_image_quality_saturated():
    """Test image quality analysis with saturated image."""
    # Test saturated image (many pixels at max value)
    saturated_img = np.random.randint(0, 200, (100, 100), dtype=np.uint8)
    saturated_img[:30, :] = 255  # 30% saturated
    report = analyze_image_quality(saturated_img)

    assert report.saturated


def test_analyze_image_quality_3d():
    """Test image quality analysis with 3D image."""
    # Test 3D image (should take max projection)
    img_3d = np.random.randint(50, 200, (10, 100, 100), dtype=np.uint8)
    report = analyze_image_quality(img_3d)

    assert isinstance(report, QCReport)
    assert report.quality_score > 0


def test_qc_report_to_dict():
    """Test QCReport serialization to dictionary."""
    report = QCReport(
        mean_intensity=100.0,
        std_intensity=25.0,
        low_signal=False,
        saturated=False,
        potential_hemisphere=True,
        potential_damage=False,
        asymmetry_score=0.45,
        damage_fraction=0.02,
        recommended_geometry="right_hemi",
        requires_damage_mask=False,
        quality_score=0.8,
    )

    result_dict = report.to_dict()

    assert "statistics" in result_dict
    assert "flags" in result_dict
    assert "analysis" in result_dict
    assert "recommendations" in result_dict
    assert result_dict["flags"]["potential_hemisphere"] is True
    assert result_dict["recommendations"]["quality_score"] == 0.8
