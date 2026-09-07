import numpy as np

def create_perfect_dragon():
    vertices = []
    normals = []
    faces = []

    with open("3d-model/Dragon.ply", "r") as f:
        header = True
        for line in f:
            line_str = line.strip()
            if header:
                if line_str == "end_header":
                    header = False
                continue
            parts = line_str.split()
            if len(parts) == 8:  # x y z nx ny nz s t
                x, y, z, nx, ny, nz, s, t = [float(p) for p in parts]
                # Blender (Z-up) to Three.js (Y-up):
                # X_three = x, Y_three = z, Z_three = -y
                # Normal: nx_three = nx, ny_three = nz, nz_three = -ny
                vertices.append((x, z, -y))
                normals.append((nx, nz, -ny))
            elif len(parts) == 4 and parts[0] == '3':
                faces.append((int(parts[1]), int(parts[2]), int(parts[3])))

    verts = np.array(vertices)
    norms = np.array(normals)
    print(f"Loaded {len(verts)} vertices, {len(faces)} faces.")

    # Center and scale to 2.0 unit box
    min_b = np.min(verts, axis=0)
    max_b = np.max(verts, axis=0)
    center = (min_b + max_b) / 2.0
    size = max_b - min_b
    max_dim = np.max(size)
    scale = 2.4 / max_dim

    norm_verts = (verts - center) * scale
    norm_verts[:, 1] += 0.3  # Lift up slightly above ground

    print(f"Centered Bounds: Min={np.min(norm_verts, axis=0)}, Max={np.max(norm_verts, axis=0)}")

    # 1. Write Clean Standalone PLY Mesh
    with open("3d-model/Dragon_clean.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(norm_verts)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property float nx\nproperty float ny\nproperty float nz\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(faces)}\n")
        f.write("property list uchar uint vertex_indices\n")
        f.write("end_header\n")

        for (x, y, z), (nx, ny, nz) in zip(norm_verts, norms):
            # Realistic dragon coloring: Emerald green body, golden wings, fiery red spine
            h = (y + 1.2) / 2.4
            r = int(np.clip(30 + h * 180 + nx * 50, 20, 255))
            g = int(np.clip(140 + h * 80 + ny * 40, 50, 255))
            b = int(np.clip(220 - h * 100 + nz * 30, 40, 255))
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {nx:.4f} {ny:.4f} {nz:.4f} {r} {g} {b}\n")

        for f1, f2, f3 in faces:
            f.write(f"3 {f1} {f2} {f3}\n")

    print("Saved 3d-model/Dragon_clean.ply successfully!")

    # 2. Dense Surface Gaussian Splat Cloud (Sample triangles to 100,000 points!)
    splat_points = []
    splat_colors = []

    # Add vertex points
    for i, (x, y, z) in enumerate(norm_verts):
        nx, ny, nz = norms[i]
        h = (y + 1.2) / 2.4
        r = (30 + h * 180 + nx * 50) / 255.0
        g = (140 + h * 80 + ny * 40) / 255.0
        b = (220 - h * 100 + nz * 30) / 255.0
        splat_points.append((x, y, z))
        splat_colors.append((r, g, b))

    # Subdivide faces to create 80,000 dense surface splats
    for f1, f2, f3 in faces:
        v1, v2, v3 = norm_verts[f1], norm_verts[f2], norm_verts[f3]
        n1, n2, n3 = norms[f1], norms[f2], norms[f3]
        
        # Sample 2 points per face
        for _ in range(2):
            r1, r2 = np.random.rand(), np.random.rand()
            if r1 + r2 > 1.0:
                r1 = 1.0 - r1
                r2 = 1.0 - r2
            r3 = 1.0 - r1 - r2
            p = r1 * v1 + r2 * v2 + r3 * v3
            n = r1 * n1 + r2 * n2 + r3 * n3
            
            h = (p[1] + 1.2) / 2.4
            r_c = np.clip((30 + h * 180 + n[0] * 50) / 255.0, 0, 1)
            g_c = np.clip((140 + h * 80 + n[1] * 40) / 255.0, 0, 1)
            b_c = np.clip((220 - h * 100 + n[2] * 30) / 255.0, 0, 1)
            splat_points.append((p[0], p[1], p[2]))
            splat_colors.append((r_c, g_c, b_c))

    print(f"Generated {len(splat_points)} dense surface splats for Dragon!")

    with open("3d-model/Dragon_dense_splats.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(splat_points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for (x, y, z), (r, g, b) in zip(splat_points, splat_colors):
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {int(r*255)} {int(g*255)} {int(b*255)}\n")

    print("Saved 3d-model/Dragon_dense_splats.ply successfully!")

if __name__ == '__main__':
    create_perfect_dragon()
