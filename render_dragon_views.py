import math
import os
from PIL import Image, ImageDraw

def render_dragon_multiview():
    ply_path = '3d-model/Dragon.ply'
    out_dir = '3d-model/dragon_multiview'
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs('spark_spatial_os/3d-model/dragon_multiview', exist_ok=True)

    # Read PLY
    vertices = []
    normals = []
    faces = []

    with open(ply_path, 'r', encoding='ascii', errors='ignore') as f:
        header = True
        num_v = 0
        num_f = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            if header:
                if line.startswith('element vertex'):
                    num_v = int(line.split()[-1])
                elif line.startswith('element face'):
                    num_f = int(line.split()[-1])
                elif line == 'end_header':
                    header = False
            else:
                if len(vertices) < num_v:
                    parts = [float(p) for p in line.split()]
                    vertices.append((parts[0], parts[1], parts[2]))
                    if len(parts) >= 6:
                        normals.append((parts[3], parts[4], parts[5]))
                    else:
                        normals.append((0, 1, 0))
                else:
                    parts = [int(p) for p in line.split()]
                    if parts[0] >= 3:
                        faces.append(parts[1:1+parts[0]])

    print(f"Loaded {len(vertices)} vertices and {len(faces)} faces.")

    # Normalize vertex bounding box
    min_x = min(v[0] for v in vertices)
    max_x = max(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    max_y = max(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices)
    max_z = max(v[2] for v in vertices)

    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    cz = (min_z + max_z) / 2

    span = max(max_x - min_x, max_y - min_y, max_z - min_z)
    norm_v = [((v[0] - cx) / span, (v[1] - cy) / span, (v[2] - cz) / span) for v in vertices]

    # Render 4 angles: 0 (Front), 90 (Right), 180 (Back), 270 (Left)
    angles = [
        (0, "dragon_0_front.png", "정면 0°"),
        (90, "dragon_1_right.png", "우측면 90°"),
        (180, "dragon_2_back.png", "후면 180°"),
        (270, "dragon_3_left.png", "좌측면 270°")
    ]

    img_size = 512
    margin = 40
    scale = (img_size - margin * 2) * 0.85

    # Light direction in camera coordinates
    lx, ly, lz = 0.5, 0.7, 1.0
    l_len = math.sqrt(lx*lx + ly*ly + lz*lz)
    lx, ly, lz = lx/l_len, ly/l_len, lz/l_len

    for deg, filename, label in angles:
        rad = math.radians(deg)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        # Rotate vertices
        rot_v = []
        for x, y, z in norm_v:
            rx = x * cos_a - z * sin_a
            ry = y
            rz = x * sin_a + z * cos_a
            rot_v.append((rx, ry, rz))

        # Rotate normals
        rot_n = []
        for nx, ny, nz in normals:
            rnx = nx * cos_a - nz * sin_a
            rny = ny
            rnz = nx * sin_a + nz * cos_a
            rot_n.append((rnx, rny, rnz))

        # Create image with dark obsidian background
        img = Image.new("RGB", (img_size, img_size), (10, 14, 22))
        draw = ImageDraw.Draw(img)

        # Sort faces back-to-front (Painter's Algorithm)
        face_depths = []
        for f_idx, face in enumerate(faces):
            avg_z = sum(rot_v[v_i][2] for v_i in face) / len(face)
            face_depths.append((avg_z, f_idx))
        face_depths.sort(key=lambda x: x[0])

        for _, f_idx in face_depths:
            face = faces[f_idx]
            # Screen projection (Z-up vs Y-up adjustment: in Blender Z is up, Y is depth or Y is up)
            # Center of canvas is (img_size/2, img_size/2)
            pts = []
            avg_nx = sum(rot_n[v_i][0] for v_i in face) / len(face)
            avg_ny = sum(rot_n[v_i][1] for v_i in face) / len(face)
            avg_nz = sum(rot_n[v_i][2] for v_i in face) / len(face)
            n_len = math.sqrt(avg_nx*avg_nx + avg_ny*avg_ny + avg_nz*avg_nz) or 1.0
            avg_nx, avg_ny, avg_nz = avg_nx/n_len, avg_ny/n_len, avg_nz/n_len

            # Backface culling
            if avg_nz <= -0.1:
                continue

            # Lambertian shading
            diffuse = max(0.15, avg_nx*lx + avg_ny*ly + avg_nz*lz)
            
            # Dragon skin color: Cyan/Teal metallic with warm highlights
            r = int(min(255, 30 + diffuse * 60))
            g = int(min(255, 140 + diffuse * 90))
            b = int(min(255, 210 + diffuse * 45))

            for v_i in face:
                vx, vy, _ = rot_v[v_i]
                sx = img_size / 2 + vx * scale
                sy = img_size / 2 - vy * scale  # Invert Y for screen coords
                pts.append((sx, sy))

            if len(pts) >= 3:
                draw.polygon(pts, fill=(r, g, b), outline=(r//2, g//2, b//2))

        # Save to paths
        p1 = os.path.join(out_dir, filename)
        p2 = os.path.join('spark_spatial_os/3d-model/dragon_multiview', filename)
        img.save(p1)
        img.save(p2)
        print(f"Generated {p1} ({label})")

if __name__ == '__main__':
    render_dragon_multiview()
