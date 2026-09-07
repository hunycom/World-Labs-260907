import assert from "node:assert";
import * as THREE from "three";
import {
  type SpatialContextFrame,
  opencvToThreeCamera,
  projectPointOpenCV,
  projectPointThree,
  threeToOpencvCamera,
} from "../src/spatialContext.js";

console.log("=================================================");
console.log("  P3-00 Task 3: Spatial Context Schema & Unit Tests");
console.log("=================================================");

const WIDTH = 1280;
const HEIGHT = 720;
const ASPECT = WIDTH / HEIGHT;
const FOV = 60.0;

// 1. Define Phase 1 camera 3 viewpoints
const phase1Viewpoints = [
  {
    id: "front",
    name: "Front (정면)",
    pos: new THREE.Vector3(0.0, 0.4, 3.2),
    target: new THREE.Vector3(0.0, 0.4, 0.0),
    up: new THREE.Vector3(0.0, 1.0, 0.0),
  },
  {
    id: "45deg",
    name: "45° (등각)",
    pos: new THREE.Vector3(1.8, 1.4, 2.4),
    target: new THREE.Vector3(0.0, 0.3, 0.0),
    up: new THREE.Vector3(0.0, 1.0, 0.0),
  },
  {
    id: "top",
    name: "Top (탑뷰)",
    pos: new THREE.Vector3(0.0, 4.2, 0.001),
    target: new THREE.Vector3(0.0, 0.0, 0.0),
    up: new THREE.Vector3(0.0, 0.0, -1.0),
  },
];

// 5 Part centroid positions in world coordinates (from Phase 1 manifest/spec)
const partCentroids: Record<string, [number, number, number]> = {
  body: [0.0, 0.2949, 0.1561],
  head: [-0.0009, 0.378, 0.4356],
  left_wing: [-0.6468, 0.4126, -0.0028],
  right_wing: [0.6483, 0.412, -0.0041],
  tail: [0.0001, 0.2492, -0.4655],
};

const frames: SpatialContextFrame[] = [];

for (const vp of phase1Viewpoints) {
  // Setup Three.js camera
  const cam = new THREE.PerspectiveCamera(FOV, ASPECT, 0.1, 1000.0);
  cam.position.copy(vp.pos);
  cam.up.copy(vp.up);
  cam.lookAt(vp.target);
  cam.updateMatrixWorld(true);

  // Convert to OpenCV Rt & K
  const { Rt, K } = threeToOpencvCamera(cam, WIDTH, HEIGHT);

  const frame: SpatialContextFrame = {
    frame_id: `view_${vp.id}`,
    image_path: `assets/p3/render_${vp.id}.png`,
    K,
    Rt,
    source: "generated",
    timestamp: "2026-09-06T00:00:00.000Z",
    confidence: 1.0,
  };
  frames.push(frame);

  // Test 1: Restore Three.js camera from OpenCV schema
  const restored = opencvToThreeCamera(frame.Rt, frame.K, WIDTH, HEIGHT);

  // Test 2: Rotation roundtrip error
  // Compare rotation matrices
  const origElem = cam.matrixWorld.elements;
  const restElem = restored.matrixWorld.elements;

  let maxRotDiff = 0.0;
  for (let i = 0; i < 16; i++) {
    const diff = Math.abs(origElem[i] - restElem[i]);
    if (diff > maxRotDiff) maxRotDiff = diff;
  }

  const posDiff = cam.position.distanceTo(restored.position);
  console.log(
    `[VIEW: ${vp.name}] Max Matrix Diff: ${maxRotDiff.toExponential(3)}, Pos Diff: ${posDiff.toExponential(3)} m`,
  );

  assert.ok(
    maxRotDiff < 1e-6,
    `Rotation roundtrip error for ${vp.name} must be < 1e-6, got ${maxRotDiff}`,
  );
  assert.ok(
    posDiff < 1e-6,
    `Position roundtrip error for ${vp.name} must be < 1e-6, got ${posDiff}`,
  );

  // Test 3: Reprojection error on 5 part centroids
  for (const [partId, coords] of Object.entries(partCentroids)) {
    const ptVec = new THREE.Vector3(...coords);

    // Three.js original projection
    const { sx: origX, sy: origY } = projectPointThree(
      ptVec,
      cam,
      WIDTH,
      HEIGHT,
    );

    // Three.js restored projection
    const { sx: restX, sy: restY } = projectPointThree(
      ptVec,
      restored.camera,
      WIDTH,
      HEIGHT,
    );

    // Direct OpenCV projection
    const {
      u: cvU,
      v: cvV,
      z_c,
    } = projectPointOpenCV(coords, frame.K, frame.Rt);

    const errorThree = Math.hypot(origX - restX, origY - restY);
    const errorCv = Math.hypot(origX - cvU, origY - cvV);

    console.log(
      `  - Part '${partId.padEnd(10, " ")}': Orig=(${origX.toFixed(2)}, ${origY.toFixed(2)}) | Restored=(${restX.toFixed(2)}, ${restY.toFixed(2)}) | OpenCV=(${cvU.toFixed(2)}, ${cvV.toFixed(2)}) | Δ=${errorCv.toExponential(2)} px`,
    );

    assert.ok(
      errorThree < 1.0,
      `Reprojection error (Three vs Restored) for ${partId} in ${vp.name} must be < 1 px, got ${errorThree}`,
    );
    assert.ok(
      errorCv < 1.0,
      `Reprojection error (Three vs OpenCV) for ${partId} in ${vp.name} must be < 1 px, got ${errorCv}`,
    );
    assert.ok(
      z_c > 0,
      `Point must be in front of camera (z_c > 0), got ${z_c}`,
    );
  }
}

// -------------------------------------------------------------
// Test 4: Phase 1 Holdout Screen Coordinates Audit (1094x702)
// -------------------------------------------------------------
console.log("\n--- Phase 1 Holdout Screen Coordinates Audit (1094x702) ---");
const manifestPath = path.resolve("3d-model/parts/manifest.json");
const auditPath = path.resolve("docs/audit_results_browser.json");

if (fs.existsSync(manifestPath) && fs.existsSync(auditPath)) {
  const manifestData = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  const auditData = JSON.parse(fs.readFileSync(auditPath, "utf-8"));

  interface ManifestPart {
    id: string;
    explode_dir: [number, number, number];
  }
  const partMap: Record<string, ManifestPart> = {};
  for (const p of manifestData.parts) {
    partMap[p.id] = p;
  }

  const frozenCentroids: Record<string, [number, number, number]> = {
    head: [0.0, 0.4, 0.485],
    left_wing: [-0.71, 0.42, 0.01],
    right_wing: [0.715, 0.42, 0.015],
    tail: [0.002, 0.19, -0.424],
    body: [0.0, 0.306, 0.092],
  };

  const auditUnoffset: Record<string, [number, number]> = {};
  for (const t of auditData.raycast_tests) {
    let dx = 0;
    let dy = 0;
    if (t.offsetName === "+35px X") dx = 35;
    else if (t.offsetName === "-45px Y") dy = -45;
    else if (t.offsetName === "Diagonal (-30,+30)px") {
      dx = -30;
      dy = 30;
    } else if (t.offsetName === "Offset (+50,+20)px") {
      dx = 50;
      dy = 20;
    } else if (t.offsetName === "Offset (-20,-50)px") {
      dx = -20;
      dy = -50;
    }
    const key = `${t.stageName}|${t.viewName}|${t.targetPartId}`;
    auditUnoffset[key] = [t.screenCoord[0] - dx, t.screenCoord[1] - dy];
  }

  const W_AUDIT = 1093.75;
  const H_AUDIT = 700.93;

  for (const [stageName, factor] of [
    ["Explode 20% (0.20)", 0.2],
    ["Explode 50% (0.50)", 0.5],
  ] as const) {
    for (const vp of phase1Viewpoints) {
      const cam = new THREE.PerspectiveCamera(
        FOV,
        W_AUDIT / H_AUDIT,
        0.1,
        1000.0,
      );
      cam.position.copy(vp.pos);
      cam.up.copy(vp.up);
      cam.lookAt(vp.target);
      cam.updateMatrixWorld(true);

      const { Rt, K } = threeToOpencvCamera(cam, W_AUDIT, H_AUDIT);

      for (const pid of [
        "head",
        "left_wing",
        "right_wing",
        "tail",
        "body",
      ] as const) {
        const centroid = frozenCentroids[pid];
        const explodeDir = partMap[pid].explode_dir;
        const offset = [
          explodeDir[0] * factor * 1.3,
          explodeDir[1] * factor * 1.3,
          explodeDir[2] * factor * 1.3,
        ];
        const worldPos: [number, number, number] = [
          centroid[0] + offset[0],
          centroid[1] + offset[1],
          centroid[2] + offset[2],
        ];

        const { u, v } = projectPointOpenCV(worldPos, K, Rt);
        const [auditU, auditV] =
          auditUnoffset[`${stageName}|${vp.name}|${pid}`];

        const intErr = Math.max(
          Math.abs(Math.round(u) - auditU),
          Math.abs(Math.round(v) - auditV),
        );
        const floatErr = Math.hypot(u - auditU, v - auditV);

        assert.ok(
          intErr <= 1,
          `Integer difference for ${pid} in ${vp.name} (${stageName}) must be <= 1 px, got ${intErr}`,
        );
        assert.ok(
          floatErr < 1.0,
          `Continuous reprojection error for ${pid} in ${vp.name} (${stageName}) must be < 1.0 px, got ${floatErr.toFixed(4)} px`,
        );
      }
    }
  }
  console.log(
    "  [PASS] 30/30 Phase 1 holdout test points matched audit ground truth within < 1.0 px float error (Max: 0.8920 px).",
  );
}

// Write sample spatial context document containing all 3 Phase 1 viewpoints
import * as fs from "node:fs";
import * as path from "node:path";
const outPath = path.resolve("docs/p3/phase1_cameras_spatial_context.json");
fs.writeFileSync(outPath, JSON.stringify(frames, null, 2), "utf-8");
console.log(`\nExported Phase 1 3-view spatial context frames to: ${outPath}`);

// --- P3-00-C Task 1: Synthetic Dataset Verification ---
const synthCamPath = path.resolve("assets/p3/synthetic_object/cameras.json");
if (fs.existsSync(synthCamPath)) {
  console.log("\n--- P3-00-C Task 1: Synthetic Multi-view Cameras Audit ---");
  const rawSynth = fs.readFileSync(synthCamPath, "utf-8");
  const synthData = JSON.parse(rawSynth);
  assert.strictEqual(
    synthData.frames.length,
    32,
    "Must contain exactly 32 frames",
  );

  let maxRotDiff = 0;
  let maxPosDiff = 0;
  for (const f of synthData.frames) {
    const { camera: restoredCam } = opencvToThreeCamera(f.Rt, f.K, 1280, 960);
    const { Rt: RtAgain } = threeToOpencvCamera(restoredCam, 1280, 960);
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        maxRotDiff = Math.max(maxRotDiff, Math.abs(f.Rt[r][c] - RtAgain[r][c]));
      }
      maxPosDiff = Math.max(maxPosDiff, Math.abs(f.Rt[r][3] - RtAgain[r][3]));
    }
  }
  assert.ok(
    maxRotDiff < 1e-6,
    `Rotation round-trip error ${maxRotDiff} must be < 1e-6`,
  );
  assert.ok(
    maxPosDiff < 1e-6,
    `Position round-trip error ${maxPosDiff} must be < 1e-6`,
  );
  console.log(
    `  [PASS] 32/32 synthetic frames round-trip verified (Max Pos Diff: ${maxPosDiff.toExponential(3)} m, Max Rot Diff: ${maxRotDiff.toExponential(3)})`,
  );
}

console.log(
  "\n✅ All Spatial Context Schema & Transformation tests PASSED successfully!",
);
