"""
Quality control report for PyNutil integration.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import numpy as np


@dataclass
class QCReport:
    """Quality control report for a brain section image."""

    # Image statistics
    mean_intensity: float = 0.0
    std_intensity: float = 0.0
    min_intensity: float = 0.0
    max_intensity: float = 0.0

    # Quality flags
    low_signal: bool = False
    saturated: bool = False
    potential_hemisphere: bool = False
    potential_damage: bool = False
    has_artifacts: bool = False

    # Detailed analysis
    asymmetry_score: float = 0.0  # Left-right intensity difference
    damage_fraction: float = 0.0  # Fraction of image that is damaged
    artifact_regions: List[Dict] = field(default_factory=list)

    # Recommendations
    recommended_geometry: str = "full"
    requires_damage_mask: bool = False
    quality_score: float = 1.0  # 0-1, higher is better

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "statistics": {
                "mean": self.mean_intensity,
                "std": self.std_intensity,
                "min": self.min_intensity,
                "max": self.max_intensity,
            },
            "flags": {
                "low_signal": self.low_signal,
                "saturated": self.saturated,
                "potential_hemisphere": self.potential_hemisphere,
                "potential_damage": self.potential_damage,
                "has_artifacts": self.has_artifacts,
            },
            "analysis": {
                "asymmetry_score": self.asymmetry_score,
                "damage_fraction": self.damage_fraction,
            },
            "recommendations": {
                "geometry": self.recommended_geometry,
                "damage_mask": self.requires_damage_mask,
                "quality_score": self.quality_score,
            },
        }


def analyze_image_quality(
    image: np.ndarray,
    threshold_low: float = 50,
    threshold_high: float = 250,
    saturation_fraction: float = 0.20,
    asymmetry_threshold: float = 0.3,
) -> QCReport:
    """
    Analyze image quality and detect potential issues.

    Parameters
    ----------
    image : np.ndarray
        Input image (2D or 3D)
    threshold_low : float
        Intensity threshold for low signal detection
    threshold_high : float
        Intensity threshold for saturation detection
    saturation_fraction : float
        Fraction of pixels that must be saturated to flag
    asymmetry_threshold : float
        Threshold for left-right asymmetry detection

    Returns
    -------
    QCReport
        Quality control report
    """
    # Handle 3D images (take max projection or middle slice)
    if image.ndim == 3:
        image = image.max(axis=0) if image.shape[0] > 1 else image[0]

    # Convert to float for analysis
    img = image.astype(np.float64)

    report = QCReport()

    # Basic statistics
    report.mean_intensity = float(np.mean(img))
    report.std_intensity = float(np.std(img))
    report.min_intensity = float(np.min(img))
    report.max_intensity = float(np.max(img))

    # Check 1: Low signal
    report.low_signal = report.mean_intensity < threshold_low

    # Check 2: Saturation
    if img.max() > 0:
        saturated_fraction = np.sum(img >= img.max() * 0.99) / img.size
        report.saturated = saturated_fraction > saturation_fraction

    # Check 3: Left-right asymmetry (hemisphere detection)
    h, w = img.shape[:2]
    left_half = img[:, :w//2]
    right_half = img[:, w//2:]

    left_mean = np.mean(left_half)
    right_mean = np.mean(right_half)
    overall_mean = (left_mean + right_mean) / 2

    if overall_mean > 0:
        report.asymmetry_score = abs(left_mean - right_mean) / overall_mean
        report.potential_hemisphere = report.asymmetry_score > asymmetry_threshold

    # Check 4: Large black regions (damage detection)
    from scipy.ndimage import label

    # Threshold for "black" (adjust based on image type)
    black_threshold = img.max() * 0.05
    black_mask = img < black_threshold

    labeled, n_regions = label(black_mask)

    # Find large black regions
    total_pixels = img.size
    large_black_pixels = 0

    for i in range(1, n_regions + 1):
        region_size = np.sum(labeled == i)
        if region_size > (total_pixels * 0.05):  # >5% of image
            large_black_pixels += region_size
            report.artifact_regions.append({
                "size": int(region_size),
                "type": "black_region",
            })

    report.damage_fraction = large_black_pixels / total_pixels
    report.potential_damage = report.damage_fraction > 0.10

    # Generate recommendations
    if report.potential_hemisphere:
        # Determine which hemisphere based on which side is brighter
        if left_mean > right_mean:
            report.recommended_geometry = "left_hemi"
        else:
            report.recommended_geometry = "right_hemi"

    if report.potential_damage:
        report.requires_damage_mask = True

    # Calculate overall quality score
    quality_deductions = 0.0
    if report.low_signal:
        quality_deductions += 0.3
    if report.saturated:
        quality_deductions += 0.2
    if report.potential_damage:
        quality_deductions += 0.2
    if report.has_artifacts:
        quality_deductions += 0.1

    report.quality_score = max(0.0, 1.0 - quality_deductions)

    return report
