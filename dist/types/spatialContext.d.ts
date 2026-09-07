import * as THREE from "three";
/**
 * Spatial Context Frame schema representing a single calibrated frame.
 * Complies with docs/p3/spatial_context_schema.json.
 */
export interface SpatialContextFrame {
    frame_id: string;
    image_path: string;
    /** 3x3 Camera intrinsic matrix: [[fx, 0, cx], [0, fy, cy], [0, 0, 1]] */
    K: number[][];
    /** 4x4 Camera extrinsic matrix [R|t] in OpenCV convention (maps world points to camera coordinates) */
    Rt: number[][];
    depth_path?: string;
    timestamp?: string;
    source: "capture" | "generated";
    confidence?: number;
    metadata?: Record<string, unknown>;
}
/**
 * Converts OpenCV extrinsic matrix (4x4) and intrinsic matrix (3x3)
 * into a Three.js PerspectiveCamera configuration.
 *
 * @param Rt 4x4 OpenCV extrinsic matrix [R|t]
 * @param K 3x3 OpenCV intrinsic matrix
 * @param width Image width in pixels (defaults to 2 * cx)
 * @param height Image height in pixels (defaults to 2 * cy)
 * @returns Configured THREE.PerspectiveCamera and decomposed spatial components
 */
export declare function opencvToThreeCamera(Rt: number[][], K: number[][], width?: number, height?: number): {
    camera: THREE.PerspectiveCamera;
    position: THREE.Vector3;
    quaternion: THREE.Quaternion;
    matrixWorld: THREE.Matrix4;
    matrixWorldInverse: THREE.Matrix4;
    fovYDeg: number;
    aspect: number;
};
/**
 * Converts a Three.js PerspectiveCamera into an OpenCV 4x4 extrinsic matrix [R|t]
 * and 3x3 intrinsic matrix K.
 *
 * @param camera THREE.PerspectiveCamera
 * @param width Viewport width in pixels
 * @param height Viewport height in pixels
 * @returns { Rt: number[][], K: number[][] }
 */
export declare function threeToOpencvCamera(camera: THREE.PerspectiveCamera, width: number, height: number): {
    Rt: number[][];
    K: number[][];
};
/**
 * Projects a 3D world coordinate point into 2D pixel coordinates using OpenCV projection formula.
 * x_c = R_cv * X_w + t_cv
 * u = fx * (x_c / z_c) + cx
 * v = fy * (y_c / z_c) + cy
 */
export declare function projectPointOpenCV(pointWorld: [number, number, number], K: number[][], Rt: number[][]): {
    u: number;
    v: number;
    z_c: number;
};
/**
 * Projects a 3D point using standard Three.js project() method into pixel coordinates.
 */
export declare function projectPointThree(pointWorld: THREE.Vector3, camera: THREE.PerspectiveCamera, width: number, height: number): {
    sx: number;
    sy: number;
};
