import numpy as np

def create_ultra_fine_dragon():
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
                vertices.append((x, z, -y))
                normals.append((nx, nz, -ny))
            elif len(parts) == 4 and parts[0] == '3':
                faces.append((int(parts[1]), int(parts[2]), int(parts[3])))

    verts = np.array(vertices)
    norms = np.array(normals)

    min_b = np.min(verts, axis=0)
    max_b = np.max(verts, axis=0)
    center = (min_b + max_b) / 2.0
    size = max_b - min_b
    scale = 2.4 / np.max(size)

    norm_verts = (verts - center) * scale
    norm_verts[:, 1] += 0.35

    splat_points = []
    splat_colors = []

    # 1. Base vertex points
    for i, (x, y, z) in enumerate(norm_verts):
        nx, ny, nz = norms[i]
        h = (y + 1.2) / 2.4
        r = int(np.clip(35 + h * 175 + nx * 45, 15, 255))
        g = int(np.clip(145 + h * 75 + ny * 35, 40, 255))
        b = int(np.clip(225 - h * 95 + nz * 25, 40, 255))
        splat_points.append((x, y, z))
        splat_colors.append((r, g, b))

    # 2. High-density barycentric triangle subdivision (7 points per face -> ~280,000 points!)
    # Barycentric coordinates for 7 sub-points per triangle
    bary_samples = [
        (0.333, 0.333, 0.334),
        (0.6, 0.2, 0.2),
        (0.2, 0.6, 0.2),
        (0.2, 0.2, 0.6),
        (0.45, 0.45, 0.1),
        (0.45, 0.1, 0.45),
        (0.1, 0.45, 0.45),
    ]

    for f1, f2, f3 in faces:
        v1, v2, v3 = norm_verts[f1], norm_verts[f2], norm_verts[f3]
        n1, n2, n3 = norms[f1], norms[f2], norms[f3]

        for w1, w2, w3 in bary_samples:
            p = w1 * v1 + w2 * v2 + w3 * v3
            n = w1 * n1 + w2 * n2 + w3 * n3
            
            # Subtle micro-jitter to prevent aliasing grid lines
            j = (np.random.rand(3) - 0.5) * 0.0018
            px, py, pz = p[0] + j[0], p[1] + j[1], p[2] + j[2]

            h = (py + 1.2) / 2.4
            r = int(np.clip(35 + h * 175 + n[0] * 45, 15, 255))
            g = int(np.clip(145 + h * 75 + n[1] * 35, 40, 255))
            b = int(np.clip(225 - h * 95 + n[2] * 25, 40, 255))
            splat_points.append((px, py, pz))
            splat_colors.append((r, g, b))

    print(f"Generated {len(splat_points)} ultra-fine micro-splats for Dragon!")

    # Write to Dragon_dense_splats.ply
    out_files = [
        "3d-model/Dragon_dense_splats.ply",
        "spark_spatial_os/3d-model/Dragon_dense_splats.ply",
        "sample/3d-model/Dragon_dense_splats.ply"
    ]

    for path in out_files:
        with open(path, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(splat_points)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("end_header\n")
            for (x, y, z), (r, g, b) in zip(splat_points, splat_colors):
                f.write(f"{x:.4f} {y:.4f} {z:.4f} {r} {g} {b}\n")
        print(f"Saved {path} successfully!")

if __name__ == '__main__':
    create_ultra_fine_dragon()
