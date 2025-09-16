#!/usr/bin/env python3

import math
import numpy as np
from typing import Tuple
from beartype import beartype


@beartype
def create_rotation_matrix(axis: np.ndarray, angle: float) -> np.ndarray:
    """
    Create a 4x4 rotation matrix around an arbitrary axis.

    Args:
        axis: 3D axis vector (will be normalized)
        angle: Rotation angle in radians

    Returns:
        4x4 rotation matrix
    """
    # Normalize axis
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    one_minus_cos = 1.0 - cos_a

    # Rodrigues' rotation formula in matrix form
    rotation = np.array(
        [
            [
                cos_a + x * x * one_minus_cos,
                x * y * one_minus_cos - z * sin_a,
                x * z * one_minus_cos + y * sin_a,
                0.0,
            ],
            [
                y * x * one_minus_cos + z * sin_a,
                cos_a + y * y * one_minus_cos,
                y * z * one_minus_cos - x * sin_a,
                0.0,
            ],
            [
                z * x * one_minus_cos - y * sin_a,
                z * y * one_minus_cos + x * sin_a,
                cos_a + z * z * one_minus_cos,
                0.0,
            ],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )

    return rotation


@beartype
def create_translation_matrix(translation: np.ndarray) -> np.ndarray:
    """
    Create a 4x4 translation matrix.

    Args:
        translation: 3D translation vector

    Returns:
        4x4 translation matrix
    """
    matrix = np.eye(4, dtype=np.float32)
    matrix[:3, 3] = translation
    return matrix


@beartype
def create_scale_matrix(scale: float | np.ndarray) -> np.ndarray:
    """
    Create a 4x4 scale matrix.

    Args:
        scale: Uniform scale factor or 3D scale vector

    Returns:
        4x4 scale matrix
    """
    matrix = np.eye(4, dtype=np.float32)

    if isinstance(scale, (int, float)):
        matrix[0, 0] = scale
        matrix[1, 1] = scale
        matrix[2, 2] = scale
    else:
        matrix[0, 0] = scale[0]
        matrix[1, 1] = scale[1]
        matrix[2, 2] = scale[2]

    return matrix


@beartype
def look_at_matrix(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """
    Create a look-at view matrix.

    Args:
        eye: Camera position
        target: Point to look at
        up: Up vector

    Returns:
        4x4 view matrix
    """
    # Calculate camera coordinate system
    forward = target - eye
    forward = forward / np.linalg.norm(forward)

    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)

    camera_up = np.cross(right, forward)

    # Create view matrix
    view = np.eye(4, dtype=np.float32)
    view[0, :3] = right
    view[1, :3] = camera_up
    view[2, :3] = -forward
    view[:3, 3] = [-np.dot(right, eye), -np.dot(camera_up, eye), np.dot(forward, eye)]

    return view


@beartype
def perspective_matrix(
    fovy: float, aspect: float, near: float, far: float
) -> np.ndarray:
    """
    Create a perspective projection matrix.

    Args:
        fovy: Field of view in degrees
        aspect: Aspect ratio (width/height)
        near: Near clipping plane
        far: Far clipping plane

    Returns:
        4x4 projection matrix
    """
    f = 1.0 / math.tan(math.radians(fovy) / 2.0)

    proj = np.zeros((4, 4), dtype=np.float32)
    proj[0, 0] = f / aspect
    proj[1, 1] = f
    proj[2, 2] = (far + near) / (near - far)
    proj[2, 3] = (2.0 * far * near) / (near - far)
    proj[3, 2] = -1.0

    return proj


@beartype
def orthographic_matrix(
    left: float, right: float, bottom: float, top: float, near: float, far: float
) -> np.ndarray:
    """
    Create an orthographic projection matrix.

    Args:
        left, right: Left and right clipping planes
        bottom, top: Bottom and top clipping planes
        near, far: Near and far clipping planes

    Returns:
        4x4 orthographic projection matrix
    """
    ortho = np.zeros((4, 4), dtype=np.float32)
    ortho[0, 0] = 2.0 / (right - left)
    ortho[1, 1] = 2.0 / (top - bottom)
    ortho[2, 2] = -2.0 / (far - near)
    ortho[0, 3] = -(right + left) / (right - left)
    ortho[1, 3] = -(top + bottom) / (top - bottom)
    ortho[2, 3] = -(far + near) / (far - near)
    ortho[3, 3] = 1.0

    return ortho


@beartype
def align_to_direction(direction: np.ndarray, up: np.ndarray = None) -> np.ndarray:
    """
    Create a rotation matrix that aligns the Z-axis with the given direction.

    Args:
        direction: Target direction vector (will be normalized)
        up: Up vector hint (default: world Y-axis)

    Returns:
        4x4 rotation matrix
    """
    if up is None:
        up = np.array([0.0, 1.0, 0.0])

    # Normalize direction
    forward = direction / np.linalg.norm(direction)

    # Create orthonormal basis
    right = np.cross(up, forward)
    if np.linalg.norm(right) < 1e-6:  # Direction is parallel to up
        # Choose a different up vector
        up = (
            np.array([1.0, 0.0, 0.0])
            if abs(forward[0]) < 0.9
            else np.array([0.0, 0.0, 1.0])
        )
        right = np.cross(up, forward)

    right = right / np.linalg.norm(right)
    up = np.cross(forward, right)

    # Create rotation matrix
    rotation = np.eye(4, dtype=np.float32)
    rotation[:3, 0] = right
    rotation[:3, 1] = up
    rotation[:3, 2] = forward

    return rotation


@beartype
def spherical_to_cartesian(radius: float, theta: float, phi: float) -> np.ndarray:
    """
    Convert spherical coordinates to Cartesian coordinates.

    Args:
        radius: Distance from origin
        theta: Azimuthal angle in radians (around Y-axis)
        phi: Polar angle in radians (from Y-axis)

    Returns:
        3D Cartesian coordinates
    """
    x = radius * math.sin(phi) * math.cos(theta)
    y = radius * math.cos(phi)
    z = radius * math.sin(phi) * math.sin(theta)

    return np.array([x, y, z], dtype=np.float32)


@beartype
def cartesian_to_spherical(position: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert Cartesian coordinates to spherical coordinates.

    Args:
        position: 3D Cartesian coordinates

    Returns:
        Tuple of (radius, theta, phi)
    """
    x, y, z = position

    radius = math.sqrt(x * x + y * y + z * z)
    theta = math.atan2(z, x)
    phi = math.acos(y / radius) if radius > 0 else 0.0

    return radius, theta, phi


@beartype
def smooth_damp(
    current: float, target: float, velocity: float, smooth_time: float, dt: float
) -> Tuple[float, float]:
    """
    Smoothly damp a value towards a target (similar to Unity's SmoothDamp).

    Args:
        current: Current value
        target: Target value
        velocity: Current velocity (modified in-place)
        smooth_time: Approximate time to reach target
        dt: Delta time

    Returns:
        Tuple of (new_value, new_velocity)
    """
    smooth_time = max(0.0001, smooth_time)
    omega = 2.0 / smooth_time
    x = omega * dt
    exp = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x)

    change = current - target
    original_to = target

    # Clamp maximum speed
    max_change = float("inf")  # No max speed limit by default
    change = max(-max_change, min(change, max_change))
    target = current - change

    temp = (velocity + omega * change) * dt
    velocity = (velocity - omega * temp) * exp
    output = target + (change + temp) * exp

    # Prevent overshooting
    if (original_to - current > 0.0) == (output > original_to):
        output = original_to
        velocity = (output - original_to) / dt

    return output, velocity


@beartype
def lerp_angle(a: float, b: float, t: float) -> float:
    """
    Linearly interpolate between two angles, taking the shortest path.

    Args:
        a: Start angle in radians
        b: End angle in radians
        t: Interpolation factor (0.0 to 1.0)

    Returns:
        Interpolated angle in radians
    """
    # Normalize angles to [-π, π]
    a = ((a + math.pi) % (2 * math.pi)) - math.pi
    b = ((b + math.pi) % (2 * math.pi)) - math.pi

    # Calculate shortest angular distance
    diff = b - a
    if diff > math.pi:
        diff -= 2 * math.pi
    elif diff < -math.pi:
        diff += 2 * math.pi

    return a + diff * t
