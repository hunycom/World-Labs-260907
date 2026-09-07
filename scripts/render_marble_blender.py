import bpy
import os
import sys
import math
from mathutils import Vector, Euler

print("Starting Blender rendering script...")
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
    print("Loading panorama:", pano_path)
    node_env.image = bpy.data.images.load(os.path.abspath(pano_path))
    links.new(node_env.outputs['Color'], node_bg.inputs['Color'])
    node_bg.inputs['Strength'].default_value = 1.0

links.new(node_bg.outputs['Background'], node_output.inputs['Surface'])

# 3. Import and Transform GLB Collider Mesh
glb_path = "assets/p3/marble/run01_collider_mesh.glb"
print("Loading GLB:", glb_path)
bpy.ops.import_scene.gltf(filepath=os.path.abspath(glb_path))
mesh_obj = bpy.data.objects.get("geometry_0")

s = 2.121173
h = 1.2561374

if mesh_obj:
    print(f"Transforming mesh vertices: {len(mesh_obj.data.vertices):,}")
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

def render_view(out_path, cam_pos, target_pos, show_wireframe=False):
    cam_obj.location = Vector(cam_pos)
    look_at(cam_obj, Vector(target_pos))
    
    if mesh_obj:
        mesh_obj.hide_render = not show_wireframe
        if show_wireframe:
            mat = bpy.data.materials.new("WireMat")
            mat.use_nodes = True
            mnodes = mat.node_tree.nodes
            mlinks = mat.node_tree.links
            mnodes.clear()
            emit = mnodes.new('ShaderNodeEmission')
            emit.inputs['Color'].default_value = (0.0, 1.0, 1.0, 1.0) # Cyan wireframe
            emit.inputs['Strength'].default_value = 2.5
            out = mnodes.new('ShaderNodeOutputMaterial')
            mlinks.new(emit.outputs['Emission'], out.inputs['Surface'])
            
            wire_mod = mesh_obj.modifiers.new("Wire", 'WIREFRAME')
            wire_mod.thickness = 0.02
            wire_mod.use_replace = True
            mesh_obj.data.materials.clear()
            mesh_obj.data.materials.append(mat)
        else:
            if "Wire" in mesh_obj.modifiers:
                mesh_obj.modifiers.remove(mesh_obj.modifiers["Wire"])

    abs_out = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(abs_out), exist_ok=True)
    scene.render.filepath = abs_out
    print(f"Rendering {out_path}...")
    bpy.ops.render.render(write_still=True)
    print(f"[+] Rendered: {out_path}")

# 1. Front View (Aisle view at eye level z=1.6m)
render_view(
    "docs/p3/captures/marble_run01_front.png",
    cam_pos=(0.0, -1.5, 1.6),
    target_pos=(0.0, 10.0, 1.6),
    show_wireframe=False
)

# 2. 45° View (Elevated perspective)
render_view(
    "docs/p3/captures/marble_run01_45deg.png",
    cam_pos=(3.0, -2.5, 3.5),
    target_pos=(0.0, 5.0, 1.5),
    show_wireframe=False
)

# 3. Top View (Top-down layout showing central aisle and racks)
def render_top_layout(out_path):
    cam_obj.location = Vector((0.0, 2.0, 14.0))
    direction = Vector((0.0, 2.0, 0.0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    # Show mesh in clay shading
    mat = bpy.data.materials.new("ClayMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.75, 0.78, 0.82, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.6
    out = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
    mesh_obj.data.materials.clear()
    mesh_obj.data.materials.append(mat)
    mesh_obj.hide_render = False
    if "Wire" in mesh_obj.modifiers:
        mesh_obj.modifiers.remove(mesh_obj.modifiers["Wire"])

    # Sunlight for clear topological shadows
    light_data = bpy.data.lights.new(name="Sun", type='SUN')
    light_data.energy = 3.0
    light_obj = bpy.data.objects.new(name="Sun", object_data=light_data)
    scene.collection.objects.link(light_obj)
    light_obj.rotation_euler = (0.5, 0.3, 0.2)

    abs_out = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(abs_out), exist_ok=True)
    scene.render.filepath = abs_out
    bpy.ops.render.render(write_still=True)
    scene.collection.objects.unlink(light_obj)
    print(f"[+] Rendered Top Layout: {out_path}")

render_top_layout("docs/p3/captures/marble_run01_top.png")

# 4. Wireframe Overlay View (Front view at origin height h=1.256 matching panorama center)
render_view(
    "docs/p3/captures/marble_run01_wireframe_overlay.png",
    cam_pos=(0.0, 0.0, 1.256),
    target_pos=(0.0, 10.0, 1.256),
    show_wireframe=True
)

print("[SUCCESS] All 4 captures rendered successfully.")
