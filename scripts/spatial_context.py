"""
Spatial Context Module for Python Pipeline (Phase 3).
Connects Generation Layer (MISO) and Runtime Layer (MIMO).
Conforms to docs/p3/spatial_context_schema.json.
"""

from typing import Dict, Any, Tuple, List, Optional
import numpy as np

# S matrix for coordinate convention flip between OpenCV and Three.js camera frames
# X_cv = X_three, Y_cv = -Y_three, Z_cv = -Z_three
S_MAT = np.diag([1.0, -1.0, -1.0])


def opencv_to_three_camera(
    Rt: np.ndarray,
    K: np.ndarray,
    width: Optional[float] = None,
    height: Optional[float] = None
) -> Tuple[np.ndarray, np.ndarray, float, float]:
    """
    Converts OpenCV 4x4 extrinsic [R|t] and 3x3 intrinsic K to Three.js camera pose.

    Returns:
        position (3,): Three.js camera world position
        R_three (3,3): Three.js camera world rotation matrix (columns: right, up, back)
        fov_y_deg: Vertical field of view in degrees
        aspect: Aspect ratio (width / height)
    """
    Rt = np.asarray(Rt, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)

    R_cv = Rt[:3, :3]
    t_cv = Rt[:3, 3]

    # Camera center in world coordinates: C = - R_cv^T * t_cv
    position = -R_cv.T @ t_cv

    # Three.js camera world rotation: R_three = R_cv^T * S
    R_three = R_cv.T @ S_MAT

    fx = K[0, 0]
    fy = K[1, 1]
    cx = K[0, 2]
    cy = K[1, 2]

    w = width if width is not None else cx * 2.0
    h = height if height is not None else cy * 2.0
    aspect = w / h
    fov_y_rad = 2.0 * np.arctan((h / 2.0) / fy)
    fov_y_deg = float(np.degrees(fov_y_rad))

    return position, R_three, fov_y_deg, aspect


def three_to_opencv_camera(
    position: np.ndarray,
    R_three: np.ndarray,
    fov_y_deg: float,
    width: float,
    height: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Converts Three.js camera pose to OpenCV 4x4 extrinsic [R|t] and 3x3 intrinsic K.

    Returns:
        Rt (4,4): OpenCV extrinsic matrix
        K (3,3): OpenCV intrinsic matrix
    """
    position = np.asarray(position, dtype=np.float64)
    R_three = np.asarray(R_three, dtype=np.float64)

    # R_cv = S * R_three^T
    R_cv = S_MAT @ R_three.T
    # t_cv = - R_cv * C
    t_cv = -R_cv @ position

    Rt = np.eye(4, dtype=np.float64)
    Rt[:3, :3] = R_cv
    Rt[:3, 3] = t_cv

    fov_y_rad = np.radians(fov_y_deg)
    fy = (height / 2.0) / np.tan(fov_y_rad / 2.0)
    fx = fy
    cx = width / 2.0
    cy = height / 2.0

    K = np.array([
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
    ], dtype=np.float64)

    return Rt, K


def project_point_opencv(
    point_world: np.ndarray,
    K: np.ndarray,
    Rt: np.ndarray
) -> Tuple[float, float, float]:
    """
    Projects 3D world point into pixel coordinates using OpenCV projection.
    Returns: (u, v, z_c)
    """
    pt = np.asarray(point_world, dtype=np.float64)
    R_cv = Rt[:3, :3]
    t_cv = Rt[:3, 3]
    p_c = R_cv @ pt + t_cv
    x_c, y_c, z_c = p_c

    fx = K[0, 0]
    fy = K[1, 1]
    cx = K[0, 2]
    cy = K[1, 2]

    u = fx * (x_c / z_c) + cx
    v = fy * (y_c / z_c) + cy
    return float(u), float(v), float(z_c)
