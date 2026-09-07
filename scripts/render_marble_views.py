#!/usr/bin/env python3
"""
scripts/render_marble_views.py

Phase 3 P3-02 Task 2 Visual Verification:
Renders 4 offline capture images of the Marble warehouse scene:
1. docs/p3/captures/marble_run01_front.png (Front / aisle view at eye level)
2. docs/p3/captures/marble_run01_45deg.png (45 degree elevated isometric view)
3. docs/p3/captures/marble_run01_top.png (Top-down view of the aisle)
4. docs/p3/captures/marble_run01_wireframe_overlay.png (Collider mesh wireframe superimposed on scene)
"""

import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BLENDER_BIN = ROOT_DIR / "tools" / "blender-4.2.0-linux-x64" / "blender"
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

BLENDER_SCRIPT = """
import bpy
import math
from mathutils import Vector, Euler

bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Setup Scene & Render Engine
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 16  # Fast offline render
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.film_transparent = False

# 2. Environment Texture (360 Panorama)
world = bpy.data.worlds.new("MarbleWorld")
scene.world = world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

node_bg = nodes.new(type='ShaderNodeBackground')
node_env = nodes.new(type='ShaderNodeTexEnvironment')
node_output = nodes.new(type='ShaderNodeOutputWorld')

pano_path = "assets/p3/marble/run01_pano.png"
if os.path.exists(pano_path):
    node_env.image = bpy.data.images.load(os.path.abspath(pano_path))
    links.new(node_env.outputs['Color'], node_bg.inputs['Color'])
    node_bg.inputs['Strength'].default_value = 1.0

links.new(node_bg.outputs['Background'], node_output.inputs['Surface'])

# 3. Import and Transform GLB Collider Mesh
bpy.ops.import_scene.gltf(filepath="assets/p3/marble/run01_collider_mesh.glb")
mesh_obj = bpy.data.objects.get("geometry_0")

s = 2.121173
h = 1.2561374

if mesh_obj:
    for v in mesh_obj.data.vertices:
        raw_x = v.co.x
        raw_y = v.co.z
        raw_z = -v.co.y
        x_three = s * raw_x
        y_three = -(s * raw_y - h)
        z_three = -s * raw_z
        # Map Three.js to Blender coordinates
        v.co.x = x_three
        v.co.y = -z_three
        v.co.z = y_three
    mesh_obj.data.update()

# 4. Create Camera
cam_data = bpy.data.cameras.new("RenderCam")
cam_data.lens = 24  # 24mm wide angle lens
cam_obj = bpy.data.objects.new("RenderCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

def look_at(cam, target, roll=0):
    loc = cam.location
    direction = target - loc
    rot_quat = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot_quat.to_euler()

# Helper to render and save
def render_view(out_path, cam_pos, target_pos, show_wireframe=False):
    cam_obj.location = Vector(cam_pos)
    look_at(cam_obj, Vector(target_pos))
    
    if mesh_obj:
        mesh_obj.hide_render = not show_wireframe
        if show_wireframe:
            # Wireframe material
            mat = bpy.data.materials.new("WireMat")
            mat.use_nodes = True
            mnodes = mat.node_tree.nodes
            mlinks = mat.node_tree.links
            mnodes.clear()
            emit = mnodes.new('ShaderNodeEmission')
            emit.inputs['Color'].default_value = (0.1, 0.9, 0.9, 1.0) # Cyan wireframe
            emit.inputs['Strength'].default_value = 2.0
            out = mnodes.new('ShaderNodeOutputMaterial')
            mlinks.new(emit.outputs['Emission'], out.inputs['Surface'])
            
            # Wireframe modifier
            wire_mod = mesh_obj.modifiers.new("Wire", 'WIREFRAME')
            wire_mod.thickness = 0.02
            wire_mod.use_replace = True
            mesh_obj.data.materials.clear()
            mesh_obj.data.materials.append(mat)
        else:
            if "Wire" in mesh_obj.modifiers:
                mesh_obj.modifiers.remove(mesh_obj.modifiers["Wire"])

    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    print(f"[+] Rendered: {out_path}")

# --- 1. Front View (Aisle view at eye level z=1.6m) ---
render_view(
    "docs/p3/captures/marble_run01_front.png",
    cam_pos=(0.0, -1.5, 1.6),
    target_pos=(0.0, 10.0, 1.6),
    show_wireframe=False
)

# --- 2. 45° View (Elevated perspective) ---
render_view(
    "docs/p3/captures/marble_run01_45deg.png",
    cam_pos=(3.0, -2.5, 3.5),
    target_pos=(0.0, 5.0, 1.5),
    show_wireframe=False
)

# --- 3. Top View (Looking straight down) ---
render_view(
    "docs/p3/captures/marble_run01_top.png",
    cam_pos=(0.0, 4.0, 10.0),
    target_pos=(0.0, 4.0, 0.0),
    show_wireframe=False
)

# --- 4. Wireframe Overlay View ---
render_view(
    "docs/p3/captures/marble_run01_wireframe_overlay.png",
    cam_pos=(3.0, -2.5, 3.5),
    target_pos=(0.0, 5.0, 1.5),
    show_wireframe=True
)

print("[SUCCESS] All 4 captures rendered successfully.")
"""

def main():
    script_path = ROOT_DIR / ".tmp_render_marble.py"
    script_path.write_text(BLENDER_SCRIPT, encoding="utf-8")
    
    cmd = [
        str(BLENDER_BIN),
        "--background",
        "--python", str(script_path)
    ]
    print(f"[*] Running Blender headless renderer...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[ERROR] Blender render failed:\n{res.stderr}", file=sys.stderr)
        print(f"Stdout:\n{res.stdout}", file=sys.stderr)
        sys.exit(1)
        
    print(res.stdout)
    if script_path.exists():
        script_path.unlink()

if __name__ == "__main__":
    main()
