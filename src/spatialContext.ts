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
 * Coordinate Sign Flip Matrix between OpenCV and Three.js camera space:
 * S = diag(1, -1, -1)
 * X_cv = X_three, Y_cv = -Y_three, Z_cv = -Z_three
 */
const S_MAT = [
  [1, 0, 0],
  [0, -1, 0],
  [0, 0, -1],
];

/**
 * Multiply 3x3 matrix by 3x3 matrix.
 */
function mat3Mul(A: number[][], B: number[][]): number[][] {
  const C: number[][] = [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];
  for (let i = 0; i < 3; i++) {
    for (let j = 0; j < 3; j++) {
      for (let k = 0; k < 3; k++) {
        C[i][j] += A[i][k] * B[k][j];
      }
    }
  }
  return C;
}

/**
 * Transpose of a 3x3 matrix.
 */
function mat3Transpose(M: number[][]): number[][] {
  return [
    [M[0][0], M[1][0], M[2][0]],
    [M[0][1], M[1][1], M[2][1]],
    [M[0][2], M[1][2], M[2][2]],
  ];
}

/**
 * Multiply 3x3 matrix by 3x1 vector.
 */
function mat3Vec3Mul(M: number[][], v: number[]): number[] {
  return [
    M[0][0] * v[0] + M[0][1] * v[1] + M[0][2] * v[2],
    M[1][0] * v[0] + M[1][1] * v[1] + M[1][2] * v[2],
    M[2][0] * v[0] + M[2][1] * v[1] + M[2][2] * v[2],
  ];
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
export function opencvToThreeCamera(
  Rt: number[][],
  K: number[][],
  width?: number,
  height?: number,
): {
  camera: THREE.PerspectiveCamera;
  position: THREE.Vector3;
  quaternion: THREE.Quaternion;
  matrixWorld: THREE.Matrix4;
  matrixWorldInverse: THREE.Matrix4;
  fovYDeg: number;
  aspect: number;
} {
  // 1. Extract R_cv (3x3) and t_cv (3x1)
  const R_cv: number[][] = [
    [Rt[0][0], Rt[0][1], Rt[0][2]],
    [Rt[1][0], Rt[1][1], Rt[1][2]],
    [Rt[2][0], Rt[2][1], Rt[2][2]],
  ];
  const t_cv: number[] = [Rt[0][3], Rt[1][3], Rt[2][3]];

  // 2. Camera position in world: C = - R_cv^T * t_cv
  const R_cv_T = mat3Transpose(R_cv);
  const neg_t_cv = [-t_cv[0], -t_cv[1], -t_cv[2]];
  const posWorldArr = mat3Vec3Mul(R_cv_T, neg_t_cv);
  const position = new THREE.Vector3(
    posWorldArr[0],
    posWorldArr[1],
    posWorldArr[2],
  );

  // 3. Three.js world rotation: R_three = R_cv^T * S
  const R_three = mat3Mul(R_cv_T, S_MAT);

  // 4. Construct Three.js matrixWorld
  const matrixWorld = new THREE.Matrix4();
  matrixWorld.set(
    R_three[0][0],
    R_three[0][1],
    R_three[0][2],
    position.x,
    R_three[1][0],
    R_three[1][1],
    R_three[1][2],
    position.y,
    R_three[2][0],
    R_three[2][1],
    R_three[2][2],
    position.z,
    0,
    0,
    0,
    1,
  );

  const matrixWorldInverse = matrixWorld.clone().invert();
  const quaternion = new THREE.Quaternion().setFromRotationMatrix(matrixWorld);

  // 5. Compute PerspectiveCamera parameters from K
  const fx = K[0][0];
  const fy = K[1][1];
  const cx = K[0][2];
  const cy = K[1][2];

  const w = width ?? cx * 2;
  const h = height ?? cy * 2;
  const aspect = w / h;
  const fovYRad = 2.0 * Math.atan(h / 2.0 / fy);
  const fovYDeg = (fovYRad * 180.0) / Math.PI;

  const camera = new THREE.PerspectiveCamera(fovYDeg, aspect, 0.01, 1000.0);
  camera.position.copy(position);
  camera.quaternion.copy(quaternion);
  camera.updateMatrixWorld(true);

  return {
    camera,
    position,
    quaternion,
    matrixWorld,
    matrixWorldInverse,
    fovYDeg,
    aspect,
  };
}

/**
 * Converts a Three.js PerspectiveCamera into an OpenCV 4x4 extrinsic matrix [R|t]
 * and 3x3 intrinsic matrix K.
 *
 * @param camera THREE.PerspectiveCamera
 * @param width Viewport width in pixels
 * @param height Viewport height in pixels
 * @returns { Rt: number[][], K: number[][] }
 */
export function threeToOpencvCamera(
  camera: THREE.PerspectiveCamera,
  width: number,
  height: number,
): {
  Rt: number[][];
  K: number[][];
} {
  camera.updateMatrixWorld(true);

  // Extract camera world rotation (R_three) and position (C)
  const e = camera.matrixWorld.elements;
  // Three.js elements are column-major: e[0..15]
  const R_three: number[][] = [
    [e[0], e[4], e[8]],
    [e[1], e[5], e[9]],
    [e[2], e[6], e[10]],
  ];
  const C = [e[12], e[13], e[14]];

  // R_cv = S * R_three^T
  const R_three_T = mat3Transpose(R_three);
  const R_cv = mat3Mul(S_MAT, R_three_T);

  // t_cv = - R_cv * C
  const t_cv = mat3Vec3Mul(R_cv, [-C[0], -C[1], -C[2]]);

  const Rt: number[][] = [
    [R_cv[0][0], R_cv[0][1], R_cv[0][2], t_cv[0]],
    [R_cv[1][0], R_cv[1][1], R_cv[1][2], t_cv[1]],
    [R_cv[2][0], R_cv[2][1], R_cv[2][2], t_cv[2]],
    [0, 0, 0, 1],
  ];

  // Intrinsic K from fov and dimensions
  const fovYRad = (camera.fov * Math.PI) / 180.0;
  const fy = height / 2.0 / Math.tan(fovYRad / 2.0);
  const fx = fy; // standard square pixels
  const cx = width / 2.0;
  const cy = height / 2.0;

  const K: number[][] = [
    [fx, 0, cx],
    [0, fy, cy],
    [0, 0, 1],
  ];

  return { Rt, K };
}

/**
 * Projects a 3D world coordinate point into 2D pixel coordinates using OpenCV projection formula.
 * x_c = R_cv * X_w + t_cv
 * u = fx * (x_c / z_c) + cx
 * v = fy * (y_c / z_c) + cy
 */
export function projectPointOpenCV(
  pointWorld: [number, number, number],
  K: number[][],
  Rt: number[][],
): { u: number; v: number; z_c: number } {
  const R_cv = [
    [Rt[0][0], Rt[0][1], Rt[0][2]],
    [Rt[1][0], Rt[1][1], Rt[1][2]],
    [Rt[2][0], Rt[2][1], Rt[2][2]],
  ];
  const t_cv = [Rt[0][3], Rt[1][3], Rt[2][3]];

  const p_c = mat3Vec3Mul(R_cv, pointWorld);
  const x_c = p_c[0] + t_cv[0];
  const y_c = p_c[1] + t_cv[1];
  const z_c = p_c[2] + t_cv[2];

  const fx = K[0][0];
  const fy = K[1][1];
  const cx = K[0][2];
  const cy = K[1][2];

  const u = fx * (x_c / z_c) + cx;
  const v = fy * (y_c / z_c) + cy;

  return { u, v, z_c };
}

/**
 * Projects a 3D point using standard Three.js project() method into pixel coordinates.
 */
export function projectPointThree(
  pointWorld: THREE.Vector3,
  camera: THREE.PerspectiveCamera,
  width: number,
  height: number,
): { sx: number; sy: number } {
  camera.updateMatrixWorld(true);
  const proj = pointWorld.clone().project(camera);
  const sx = (proj.x + 1.0) * 0.5 * width;
  const sy = (-proj.y + 1.0) * 0.5 * height;
  return { sx, sy };
}
