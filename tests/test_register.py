from pathlib import Path

import itk
import numpy as np
import pytest
from brainglobe_atlasapi import BrainGlobeAtlas
from tifffile import imread

from brainglobe_registration.elastix.register import (
    calculate_deformation_field,
    compute_jacobian_determinant,
    invert_transformation,
    run_registration,
    setup_parameter_object,
    transform_annotation_image,
    transform_image,
)

SLICE_NUMBER = 293


def compare_parameter_objects(param_obj1, param_obj2):
    assert (
        param_obj1.GetNumberOfParameterMaps()
        == param_obj2.GetNumberOfParameterMaps()
    )

    for index in range(param_obj1.GetNumberOfParameterMaps()):
        submap_1 = dict(param_obj1.GetParameterMap(index))
        submap_2 = dict(param_obj2.GetParameterMap(index))

        for key in submap_1.keys():
            if key in [
                "TransformParameters",
                "CenterOfRotationPoint",
                "GridOrigin",
                "GridSpacing",
            ]:
                assert np.allclose(
                    np.array(submap_1[key], dtype=np.double),
                    np.array(submap_2[key], dtype=np.double),
                    atol=0.4,
                )
            else:
                assert submap_1[key] == submap_2[key]


@pytest.fixture(scope="module")
def atlas(atlas_name="allen_mouse_25um"):
    return BrainGlobeAtlas(atlas_name)


@pytest.fixture(scope="module")
def atlas_reference(atlas, slice_number=SLICE_NUMBER):
    return atlas.reference[slice_number, :, :]


@pytest.fixture(scope="module")
def atlas_annotation(atlas, slice_number=SLICE_NUMBER):
    # Need the astype call to avoid a crash on Windows
    return atlas.annotation[slice_number, :, :].astype(np.uint32)


@pytest.fixture(scope="module")
def atlas_hemispheres(atlas, slice_number=SLICE_NUMBER):
    return atlas.hemispheres[slice_number, :, :]


@pytest.fixture(scope="module")
def load_transform_parameters():
    transform_parameters = itk.ParameterObject.New()
    transform_parameters.AddParameterFile(
        str(Path(__file__).parent / "test_images/TransformParameters.0.txt")
    )

    return transform_parameters


@pytest.fixture(scope="module")
def load_invert_parameters():
    transform_parameters = itk.ParameterObject.New()
    transform_parameters.AddParameterFile(
        str(
            Path(__file__).parent
            / "test_images/InverseTransformParameters.0.txt"
        )
    )

    return transform_parameters


@pytest.fixture(scope="module")
def sample_moving_image():
    return imread(
        Path(__file__).parent / "test_images/sample_hipp.tif"
    ).astype(np.float32)


@pytest.fixture(scope="module")
def registration_affine_only(
    atlas_reference, sample_moving_image, parameter_lists_affine_only
):
    yield run_registration(
        atlas_reference,
        sample_moving_image,
        parameter_lists_affine_only,
    )


@pytest.fixture(scope="module")
def invert_transform(
    registration_affine_only, atlas_reference, parameter_lists_affine_only
):
    transform_parameters = registration_affine_only
    invert_parameters = invert_transformation(
        atlas_reference, parameter_lists_affine_only, transform_parameters
    )

    yield invert_parameters, transform_parameters


def test_run_registration(registration_affine_only):
    transform_parameters = registration_affine_only

    expected_parameter_object = itk.ParameterObject.New()
    expected_parameter_object.AddParameterFile(
        str(Path(__file__).parent / "test_images/TransformParameters.0.txt")
    )

    compare_parameter_objects(transform_parameters, expected_parameter_object)


def test_transform_annotation_image(
    atlas_annotation, load_transform_parameters
):
    transform_parameters = load_transform_parameters

    transformed_annotation = transform_annotation_image(
        atlas_annotation, transform_parameters
    )

    expected_transformed_annotation = imread(
        Path(__file__).parent / "test_images/registered_atlas.tiff"
    )

    assert np.allclose(transformed_annotation, expected_transformed_annotation)


def test_invert_transformation(invert_transform):
    invert_parameters, original_parameters = invert_transform

    expected_parameter_object = itk.ParameterObject.New()
    expected_parameter_object.AddParameterFile(
        str(
            Path(__file__).parent
            / "test_images/InverseTransformParameters.0.txt"
        )
    )

    compare_parameter_objects(invert_parameters, expected_parameter_object)

    for i in range(original_parameters.GetNumberOfParameterMaps()):
        assert original_parameters.GetParameter(
            i, "FinalBSplineInterpolationOrder"
        ) == ("3",)


def test_transform_image(load_invert_parameters, sample_moving_image):
    invert_parameters = load_invert_parameters

    transformed_image = transform_image(sample_moving_image, invert_parameters)

    expected_image = imread(
        Path(__file__).parent / "test_images/registered_sample.tiff"
    )

    assert np.allclose(transformed_image, expected_image, atol=0.1)


def test_calculate_deformation_field(
    sample_moving_image, load_transform_parameters
):
    transform_parameters = load_transform_parameters

    deformation_field = calculate_deformation_field(
        sample_moving_image, transform_parameters
    )

    deformation_field_0 = imread(
        Path(__file__).parent / "test_images/deformation_field_0.tiff"
    )
    deformation_field_1 = imread(
        Path(__file__).parent / "test_images/deformation_field_1.tiff"
    )
    expected_deformation_field = np.stack(
        (deformation_field_0, deformation_field_1), axis=-1
    )

    assert np.allclose(deformation_field, expected_deformation_field, atol=0.5)


def test_compute_jacobian_determinant_identity_2d():
    """Zero displacement field gives det(J) ≈ 1 everywhere."""
    h, w = 8, 10
    disp = np.zeros((h, w, 2), dtype=np.float32)
    det_j = compute_jacobian_determinant(disp)
    assert det_j.shape == (h, w)
    assert det_j.dtype == np.float32
    np.testing.assert_allclose(det_j, 1.0, atol=1e-5)


def test_compute_jacobian_determinant_identity_3d():
    """Zero displacement field in 3D gives det(J) ≈ 1 everywhere."""
    d, h, w = 4, 6, 8
    disp = np.zeros((d, h, w, 3), dtype=np.float32)
    det_j = compute_jacobian_determinant(disp)
    assert det_j.shape == (d, h, w)
    assert det_j.dtype == np.float32
    np.testing.assert_allclose(det_j, 1.0, atol=1e-5)


def test_compute_jacobian_determinant_wrong_ndim_raises():
    """Last dimension must be 2 or 3."""
    bad = np.zeros((5, 5, 4), dtype=np.float32)  # 4 components
    with pytest.raises(ValueError, match="last dim 2 or 3, got 4"):
        compute_jacobian_determinant(bad)


def test_compute_jacobian_determinant_wrong_ndim_one_raises():
    """Last dimension 1 is invalid."""
    bad = np.zeros((5, 5, 1), dtype=np.float32)
    with pytest.raises(ValueError, match="last dim 2 or 3, got 1"):
        compute_jacobian_determinant(bad)


def test_setup_parameter_object_empty_list():
    parameter_list = []

    param_obj = setup_parameter_object(parameter_list)

    assert param_obj.GetNumberOfParameterMaps() == 0


@pytest.mark.parametrize(
    "parameter_list, expected",
    [
        (
            [("rigid", {"Transform": ["EulerTransform"]})],
            [("EulerTransform",)],
        ),
        (
            [("affine", {"Transform": ["AffineTransform"]})],
            [("AffineTransform",)],
        ),
        (
            [("bspline", {"Transform": ["BSplineTransform"]})],
            [("BSplineTransform",)],
        ),
        (
            [
                ("rigid", {"Transform": ["EulerTransform"]}),
                ("affine", {"Transform": ["AffineTransform"]}),
                ("bspline", {"Transform": ["BSplineTransform"]}),
            ],
            [("EulerTransform",), ("AffineTransform",), ("BSplineTransform",)],
        ),
        (
            [
                ("rigid", {"Transform": ["EulerTransform"]}),
                ("rigid", {"Transform": ["EulerTransform"]}),
                ("rigid", {"Transform": ["EulerTransform"]}),
            ],
            [("EulerTransform",), ("EulerTransform",), ("EulerTransform",)],
        ),
    ],
)
def test_setup_parameter_object_one_transform(parameter_list, expected):
    param_obj = setup_parameter_object(parameter_list)

    assert param_obj.GetNumberOfParameterMaps() == len(expected)

    for index, transform_type in enumerate(expected):
        assert param_obj.GetParameterMap(index)["Transform"] == transform_type
