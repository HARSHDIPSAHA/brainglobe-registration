from pathlib import Path
from typing import List, Optional, Tuple

import itk
import numpy as np
import numpy.typing as npt

from brainglobe_registration.utils.atlas import (
    convert_atlas_labels,
    restore_atlas_labels,
)
from brainglobe_registration.utils.preprocess import filter_image


def run_registration(
    atlas_image: npt.NDArray,
    moving_image: npt.NDArray,
    parameter_lists: List[Tuple[str, dict]],
    output_directory: Optional[Path] = None,
    filter_images: bool = True,
) -> itk.ParameterObject:
    """
    Run the registration process on the given images.

    Parameters
    ----------
    atlas_image : npt.NDArray
        The atlas image.
    moving_image : npt.NDArray
        The moving image.
    parameter_lists : List[tuple[str, dict]]
        The list of registration parameters, one for each transform.
    output_directory : Optional[Path], optional
        The output directory for the registration results, by default None.
    filter_images : bool, optional
        Whether to filter the images before registration, by default True.

    Returns
    -------
    itk.ParameterObject
        The result transform parameters.
    """
    if filter_images:
        atlas_image = filter_image(atlas_image)
        moving_image = filter_image(moving_image)

    # convert to ITK, view only
    atlas_image = itk.GetImageViewFromArray(atlas_image)
    moving_image = itk.GetImageViewFromArray(moving_image)

    # This syntax needed for 3D images
    elastix_object = itk.ElastixRegistrationMethod.New(
        moving_image, atlas_image
    )

    parameter_object = setup_parameter_object(parameter_lists=parameter_lists)

    elastix_object.SetParameterObject(parameter_object)
    elastix_object.UpdateLargestPossibleRegion()

    # get results
    result_transform_parameters = elastix_object.GetTransformParameterObject()

    if output_directory:
        file_names = [
            f"{output_directory}/TransformParameters.{i}.txt"
            for i in range(len(parameter_lists))
        ]

        itk.ParameterObject.WriteParameterFile(
            result_transform_parameters, file_names
        )

    return result_transform_parameters


def transform_annotation_image(
    annotation_image: npt.NDArray[np.uint32],
    transform_parameters: itk.ParameterObject,
) -> npt.NDArray[np.uint32]:
    """
    Transform the annotation image using the given transform parameters.
    Sets the FinalBSplineInterpolationOrder to 0 to avoid interpolation.
    Resets the FinalBSplineInterpolationOrder to its original value after
    transforming the annotation image.

    Parameters
    ----------
    annotation_image : npt.NDArray
        The annotation image.
    transform_parameters : itk.ParameterObject
        The transform parameters.

    Returns
    -------
    npt.NDArray
        The transformed annotation image.
    """
    adjusted_annotation_image, mapping = convert_atlas_labels(annotation_image)

    if adjusted_annotation_image.ndim == 2:
        adjusted_annotation_image = adjusted_annotation_image.astype(
            np.float32
        )

    annotation_image = itk.GetImageViewFromArray(adjusted_annotation_image)

    temp_interp_order = transform_parameters.GetParameter(
        0, "FinalBSplineInterpolationOrder"
    )
    transform_parameters.SetParameter("FinalBSplineInterpolationOrder", "0")

    transformix_object = itk.TransformixFilter.New(annotation_image)
    transformix_object.SetTransformParameterObject(transform_parameters)
    transformix_object.UpdateLargestPossibleRegion()

    transformed_annotation = transformix_object.GetOutput()

    transform_parameters.SetParameter(
        "FinalBSplineInterpolationOrder", temp_interp_order
    )
    del annotation_image

    transformed_annotation_array = np.asarray(transformed_annotation).astype(
        np.uint16
    )

    transformed_annotation_array = restore_atlas_labels(
        transformed_annotation_array, mapping
    )

    return transformed_annotation_array


def transform_image(
    image: npt.NDArray,
    transform_parameters: itk.ParameterObject,
) -> npt.NDArray:
    """
    Transform the image using the given transform parameters.

    Parameters
    ----------
    image: npt.NDArray
        The image to transform.
    transform_parameters: itk.ParameterObject
        The transform parameters.

    Returns
    -------
    npt.NDArray
        The transformed image.
    """
    image = itk.GetImageViewFromArray(image)

    transformix_object = itk.TransformixFilter.New(image)
    transformix_object.SetTransformParameterObject(transform_parameters)
    transformix_object.UpdateLargestPossibleRegion()

    transformed_image = transformix_object.GetOutput()

    # Convert to a numpy array of the original type.
    transformed_image = np.asarray(transformed_image).astype(image.dtype)

    return transformed_image


def calculate_deformation_field(
    moving_image: npt.NDArray,
    transform_parameters: itk.ParameterObject,
    debug: bool = False,
) -> npt.NDArray:
    """
    Calculate the deformation field for the moving image using the given
    transform parameters.

    Parameters
    ----------
    moving_image : npt.NDArray
        The moving image.
    transform_parameters : itk.ParameterObject
        The transform parameters.
    debug : bool, optional
        Whether to save extra files for debugging, by default False

    Returns
    -------
    npt.NDArray
        The deformation field.
    """
    transformix_object = itk.TransformixFilter.New(
        itk.GetImageViewFromArray(moving_image),
        transform_parameters,
    )
    transformix_object.SetComputeDeformationField(True)

    transformix_object.UpdateLargestPossibleRegion()

    # Change from ITK to numpy axes ordering
    deformation_field = itk.GetArrayViewFromImage(
        transformix_object.GetOutputDeformationField()
    )[..., ::-1]

    if not debug:
        # Cleanup files generated by elastix
        (Path.cwd() / "deformationField.tiff").unlink(missing_ok=True)

    return deformation_field


def compute_jacobian_determinant(
    deformation_field: npt.NDArray,
) -> npt.NDArray:
    """
    Compute the determinant of the spatial Jacobian from a displacement field.

    The spatial Jacobian is J = I + d(disp)/d(x). Values: |J|=1 no change,
    |J|>1 expansion, |J|<1 contraction, |J|<=0 folding (invalid).

    Parameters
    ----------
    deformation_field : npt.NDArray
        Displacement field, shape (..., ndim) with ndim in (2, 3).
        Last axis is (y, x) or (z, y, x) in numpy order.

    Returns
    -------
    npt.NDArray
        Scalar field of det(J) per voxel, same shape as
        deformation_field[..., 0]. Dtype float32.
    """
    ndim = deformation_field.shape[-1]
    if ndim not in (2, 3):
        raise ValueError(
            f"Deformation field must have last dim 2 or 3, got {ndim}."
        )
    # Gradients of each displacement component along each axis
    # disp_i is deformation_field[..., i]; d(disp_i)/d(x_j) uses axis j
    # numpy default: axis 0 is first, so for (D,H,W,3) axis 0,1,2 are z,y,x
    shape = deformation_field.shape[:-1]
    grad_disp = np.empty((ndim, ndim) + shape, dtype=np.float64)
    for i in range(ndim):
        disp_i = np.asarray(deformation_field[..., i], dtype=np.float64)
        grads = np.gradient(disp_i)
        for j in range(ndim):
            grad_disp[i, j] = grads[j]
    # J = I + grad(disp); J_ij = delta_ij + d(disp_i)/d(x_j)
    # Build (ndim, ndim, *shape) then move to (..., ndim, ndim) for det
    identity = np.eye(ndim, dtype=np.float64)
    for _ in range(len(shape)):
        identity = identity[..., np.newaxis]
    J = np.broadcast_to(identity, (ndim, ndim) + shape).copy()
    J += grad_disp
    J_mat = np.moveaxis(J, (0, 1), (-2, -1))
    det_j = np.linalg.det(J_mat).astype(np.float32)
    return det_j


def invert_transformation(
    fixed_image: npt.NDArray,
    parameter_list: List[Tuple[str, dict]],
    transform_parameters: itk.ParameterObject,
    output_directory: Optional[Path] = None,
    filter_images: bool = True,
) -> itk.ParameterObject:
    """
    Invert the transformation of the fixed image using the given transform
    parameters.

    Inverts the transformation by applying the forward transformation to the
    fixed image and registering it to itself.

    Parameters
    ----------
    fixed_image : npt.NDArray
        The reference image.
    parameter_list : List[Tuple[str, dict]]
        The list of registration parameters, one for each transform.
    transform_parameters : itk.ParameterObject
        The transform parameters to inverse.
    output_directory : Optional[Path], optional
        The output directory for the registration results, by default None.
    filter_images : bool, optional
        Whether to filter the images before registration, by default True.

    Returns
    -------
    itk.ParameterObject
        The inverse transform parameters.
    """
    if filter_images:
        fixed_image = filter_image(fixed_image)

    fixed_image = itk.GetImageViewFromArray(fixed_image)

    elastix_object = itk.ElastixRegistrationMethod.New(
        fixed_image, fixed_image
    )

    parameter_object_inverse = setup_parameter_object(parameter_list)
    elastix_object.SetInitialTransformParameterObject(transform_parameters)
    elastix_object.SetParameterObject(parameter_object_inverse)

    elastix_object.UpdateLargestPossibleRegion()

    num_initial_transforms = transform_parameters.GetNumberOfParameterMaps()

    out_parameters = elastix_object.GetTransformParameterObject()
    result_transform_parameters = itk.ParameterObject.New()

    for i in range(
        num_initial_transforms, out_parameters.GetNumberOfParameterMaps()
    ):
        result_transform_parameters.AddParameterMap(
            out_parameters.GetParameterMap(i)
        )

    result_transform_parameters.SetParameter(
        0, "InitialTransformParameterFileName", "NoInitialTransform"
    )

    if output_directory:
        file_names = [
            f"{output_directory}/InverseTransformParameters.{i}.txt"
            for i in range(len(parameter_list))
        ]

        itk.ParameterObject.WriteParameterFiles(
            result_transform_parameters, file_names
        )

    return result_transform_parameters


def setup_parameter_object(parameter_lists: List[tuple[str, dict]]):
    """
    Set up the parameter object for the registration process.

    Parameters
    ----------
    parameter_lists : List[tuple[str, dict]], optional
        The list of parameter lists, by default None

    Returns
    -------
    itk.ParameterObject
        The parameter object.#
    """
    parameter_object = itk.ParameterObject.New()

    for transform_type, parameter_dict in parameter_lists:
        parameter_map = parameter_object.GetDefaultParameterMap(transform_type)
        parameter_map.clear()

        for k, v in parameter_dict.items():
            parameter_map[k] = v

        parameter_object.AddParameterMap(parameter_map)

    return parameter_object
