import numpy as np

def convert_dragon_ply():
    # Read 3d-model/Dragon.ply
    vertices = []
    normals = []
    
    with open("3d-model/Dragon.ply", "r") as f:
        header = True
        for line in f:
            if header:
                if line.strip() == "end_header":
                    header = False
                continue
            parts = line.strip().split()
            if len(parts) == 8: # x y z nx ny nz s t
                x, y, z, nx, ny, nz, s, t = [float(p) for p in parts]
                vertices.append((x, y, z))
                normals.append((nx, ny, nz))
            elif len(parts) == 4 and parts[0] == '3': # face
                pass

    verts = np.array(vertices)
    print(f"Loaded {len(verts)} vertices from Dragon.ply")
    print(f"Min: {np.min(verts, axis=0)}, Max: {np.max(verts, axis=0)}")

    # Let's save a colored 3D point cloud PLY with dragon skin colors (emerald cyan + gold highlights)
    with open("3d-model/Dragon_colored.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(verts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        
        # Center and normalize
        center = (np.min(verts, axis=0) + np.max(verts, axis=0)) / 2.0
        scale = 2.0 / np.max(np.max(verts, axis=0) - np.min(verts, axis=0))
        
        norm_verts = (verts - center) * scale
        
        for (x, y, z), (nx, ny, nz) in zip(norm_verts, normals):
            # Calculate ambient occlusion / shading color
            # Cyan body with golden wingtips/horns
            height_factor = (y + 1.0) / 2.0
            r = int(min(255, max(40, 56 + height_factor * 160 + nx * 40)))
            g = int(min(255, max(120, 189 + height_factor * 50 + ny * 30)))
            b = int(min(255, max(180, 248 - height_factor * 40 + nz * 20)))
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {r} {g} {b}\n")

    print("Saved 3d-model/Dragon_colored.ply successfully!")

if __name__ == '__main__':
    convert_dragon_ply()
