import fs from "node:fs";
import RAPIER from "@dimforge/rapier3d-compat";

async function fullPhysicsSuite() {
  await RAPIER.init();

  const buf = fs.readFileSync("assets/p3/marble/run01_collider_mesh.glb");
  const chunk0Len = buf.readUInt32LE(12);
  const gltf = JSON.parse(buf.toString("utf8", 20, 20 + chunk0Len));
  const chunk1Offset = 20 + chunk0Len;
  const chunk1Len = buf.readUInt32LE(chunk1Offset);
  const binBuffer = buf.subarray(
    chunk1Offset + 8,
    chunk1Offset + 8 + chunk1Len,
  );

  const prim = gltf.meshes[0].primitives[0];
  const posAcc = gltf.accessors[prim.attributes.POSITION];
  const idxAcc = gltf.accessors[prim.indices];
  const posBv = gltf.bufferViews[posAcc.bufferView];
  const posOffset = (posBv.byteOffset || 0) + (posAcc.byteOffset || 0);
  const rawVerts = new Float32Array(
    binBuffer.buffer,
    binBuffer.byteOffset + posOffset,
    posAcc.count * 3,
  );

  const idxBv = gltf.bufferViews[idxAcc.bufferView];
  const idxOffset = (idxBv.byteOffset || 0) + (idxAcc.byteOffset || 0);
  const indices = new Uint32Array(
    binBuffer.buffer,
    binBuffer.byteOffset + idxOffset,
    idxAcc.count,
  );

  const s = 2.121173;
  const h = 1.2561374;
  const transformedVerts = new Float32Array(rawVerts.length);
  for (let i = 0; i < posAcc.count; i++) {
    transformedVerts[i * 3 + 0] = s * rawVerts[i * 3 + 0];
    transformedVerts[i * 3 + 1] = -s * rawVerts[i * 3 + 1] + h;
    transformedVerts[i * 3 + 2] = -s * rawVerts[i * 3 + 2];
  }

  const numVertices = posAcc.count;
  const numTriangles = indices.length / 3;
  console.log(
    `[T6] Static Trimesh: vertices=${numVertices}, triangles=${numTriangles}, scale=${s}, offset=${h}`,
  );

  // Dynamic Box Half Extents
  // L1: [0.4725, 0.388, 0.370]
  // R1: [0.380, 0.3785, 0.328]
  const hxL1 = 0.4725;
  const hyL1 = 0.388;
  const hzL1 = 0.37;
  const hxR1 = 0.38;
  const hyR1 = 0.3785;
  const hzR1 = 0.328;

  // Let's test resting initial poses
  const initL1 = { x: -0.943, y: 0.389, z: -1.969 };
  const initR1 = { x: 0.95, y: 0.372, z: -2.002 };

  // ==========================================
  // TASK 1: Resting Stability (1s, 60 steps)
  // ==========================================
  console.log("\n--- Task 1: Resting Stability (1s) ---");
  const world1 = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
  world1.timestep = 1.0 / 60.0;
  world1.createCollider(
    RAPIER.ColliderDesc.trimesh(transformedVerts, indices)
      .setFriction(0.6)
      .setRestitution(0.1),
    world1.createRigidBody(RAPIER.RigidBodyDesc.fixed()),
  );

  const bL1_t1 = world1.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initL1.x, initL1.y, initL1.z)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  world1.createCollider(
    RAPIER.ColliderDesc.cuboid(hxL1, hyL1, hzL1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bL1_t1,
  );

  const bR1_t1 = world1.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initR1.x, initR1.y, initR1.z)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  world1.createCollider(
    RAPIER.ColliderDesc.cuboid(hxR1, hyR1, hzR1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bR1_t1,
  );

  for (let step = 0; step < 60; step++) world1.step();

  const posL1_1s = bL1_t1.translation();
  const posR1_1s = bR1_t1.translation();
  const dispL1_1s = Math.hypot(
    posL1_1s.x - initL1.x,
    posL1_1s.y - initL1.y,
    posL1_1s.z - initL1.z,
  );
  const dispR1_1s = Math.hypot(
    posR1_1s.x - initR1.x,
    posR1_1s.y - initR1.y,
    posR1_1s.z - initR1.z,
  );

  console.log(
    `L1 1s disp: ${(dispL1_1s * 100).toFixed(3)} cm [Criteria <= 1.0 cm: ${dispL1_1s <= 0.01 ? "PASS" : "미달"}]`,
  );
  console.log(
    `R1 1s disp: ${(dispR1_1s * 100).toFixed(3)} cm [Criteria <= 1.0 cm: ${dispR1_1s <= 0.01 ? "PASS" : "미달"}]`,
  );

  // ==========================================
  // TASK 2: Scenario A (Drop +1.0m, 5s)
  // ==========================================
  console.log("\n--- Task 2: Scenario A (Drop +1.0m) ---");
  const worldA = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
  worldA.timestep = 1.0 / 60.0;
  worldA.createCollider(
    RAPIER.ColliderDesc.trimesh(transformedVerts, indices)
      .setFriction(0.6)
      .setRestitution(0.1),
    worldA.createRigidBody(RAPIER.RigidBodyDesc.fixed()),
  );

  const bL1_A = worldA.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initL1.x, initL1.y + 1.0, initL1.z)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  worldA.createCollider(
    RAPIER.ColliderDesc.cuboid(hxL1, hyL1, hzL1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bL1_A,
  );

  const bR1_A = worldA.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initR1.x, initR1.y + 1.0, initR1.z)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  worldA.createCollider(
    RAPIER.ColliderDesc.cuboid(hxR1, hyR1, hzR1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bR1_A,
  );

  let l1LandingA = null;
  let r1LandingA = null;
  const stepTimesA = [];

  for (let step = 1; step <= 300; step++) {
    const t0 = performance.now();
    worldA.step();
    stepTimesA.push(performance.now() - t0);

    const t = step / 60.0;
    const pL1 = bL1_A.translation();
    const pR1 = bR1_A.translation();
    if (!l1LandingA && pL1.y <= initL1.y + 0.02) l1LandingA = t;
    if (!r1LandingA && pR1.y <= initR1.y + 0.02) r1LandingA = t;
  }

  const finalL1_A = bL1_A.translation();
  const finalR1_A = bR1_A.translation();
  const rotL1_A = bL1_A.rotation();
  const rotR1_A = bR1_A.rotation();

  const y_mesh_floor = -0.025;
  const l1BottomY_A = finalL1_A.y - hyL1;
  const r1BottomY_A = finalR1_A.y - hyR1;
  const l1DiffY_A = l1BottomY_A - y_mesh_floor;
  const r1DiffY_A = r1BottomY_A - y_mesh_floor;
  const l1XzDrift_A = Math.hypot(
    finalL1_A.x - initL1.x,
    finalL1_A.z - initL1.z,
  );
  const r1XzDrift_A = Math.hypot(
    finalR1_A.x - initR1.x,
    finalR1_A.z - initR1.z,
  );
  const l1RotDeg_A =
    2 * Math.acos(Math.min(1, Math.abs(rotL1_A.w))) * (180 / Math.PI);
  const r1RotDeg_A =
    2 * Math.acos(Math.min(1, Math.abs(rotR1_A.w))) * (180 / Math.PI);

  console.log(
    `L1 Landing Time: ${l1LandingA.toFixed(3)}s, Bottom Y Diff: ${(l1DiffY_A * 100).toFixed(2)} cm, XZ Drift: ${(l1XzDrift_A * 100).toFixed(2)} cm, Rotation: ${l1RotDeg_A.toFixed(2)} deg`,
  );
  console.log(
    `R1 Landing Time: ${r1LandingA.toFixed(3)}s, Bottom Y Diff: ${(r1DiffY_A * 100).toFixed(2)} cm, XZ Drift: ${(r1XzDrift_A * 100).toFixed(2)} cm, Rotation: ${r1RotDeg_A.toFixed(2)} deg`,
  );

  // ==========================================
  // TASK 2: Scenario B (Throw 2.5 m/s, 5s)
  // ==========================================
  console.log("\n--- Task 2: Scenario B (Throw 2.5 m/s) ---");
  const worldB = new RAPIER.World({ x: 0, y: -9.81, z: 0 });
  worldB.timestep = 1.0 / 60.0;
  worldB.createCollider(
    RAPIER.ColliderDesc.trimesh(transformedVerts, indices)
      .setFriction(0.6)
      .setRestitution(0.1),
    worldB.createRigidBody(RAPIER.RigidBodyDesc.fixed()),
  );

  const bL1_B = worldB.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initL1.x, initL1.y, initL1.z)
      .setLinvel(2.5, 0.0, 0.0)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  worldB.createCollider(
    RAPIER.ColliderDesc.cuboid(hxL1, hyL1, hzL1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bL1_B,
  );

  const bR1_B = worldB.createRigidBody(
    RAPIER.RigidBodyDesc.dynamic()
      .setTranslation(initR1.x, initR1.y, initR1.z)
      .setLinvel(-2.5, 0.0, 0.0)
      .setLinearDamping(0.05)
      .setAngularDamping(0.05),
  );
  worldB.createCollider(
    RAPIER.ColliderDesc.cuboid(hxR1, hyR1, hzR1)
      .setMass(300.0)
      .setFriction(0.6)
      .setRestitution(0.1),
    bR1_B,
  );

  let l1StopB = null;
  let r1StopB = null;
  const stepTimesB = [];

  for (let step = 1; step <= 300; step++) {
    const t0 = performance.now();
    worldB.step();
    stepTimesB.push(performance.now() - t0);

    const t = step / 60.0;
    const vL1 = bL1_B.linvel();
    const vR1 = bR1_B.linvel();
    if (!l1StopB && Math.hypot(vL1.x, vL1.y, vL1.z) < 0.02) l1StopB = t;
    if (!r1StopB && Math.hypot(vR1.x, vR1.y, vR1.z) < 0.02) r1StopB = t;
  }

  const finalL1_B = bL1_B.translation();
  const finalR1_B = bR1_B.translation();
  const l1Travel_B = Math.hypot(finalL1_B.x - initL1.x, finalL1_B.z - initL1.z);
  const r1Travel_B = Math.hypot(finalR1_B.x - initR1.x, finalR1_B.z - initR1.z);

  console.log(
    `L1 Travel Distance: ${l1Travel_B.toFixed(3)}m [Criteria > 0.5m: ${l1Travel_B > 0.5 ? "PASS" : "미달"}], Stop Time: ${l1StopB.toFixed(3)}s`,
  );
  console.log(
    `R1 Travel Distance: ${r1Travel_B.toFixed(3)}m [Criteria > 0.5m: ${r1Travel_B > 0.5 ? "PASS" : "미달"}], Stop Time: ${r1StopB.toFixed(3)}s`,
  );

  // Step Latency
  stepTimesA.sort((a, b) => a - b);
  const p50 = stepTimesA[Math.floor(stepTimesA.length * 0.5)];
  const p95 = stepTimesA[Math.floor(stepTimesA.length * 0.95)];
  console.log(
    `Physics Step Latency (CPU): p50 = ${p50.toFixed(4)} ms, p95 = ${p95.toFixed(4)} ms`,
  );
}

fullPhysicsSuite();
