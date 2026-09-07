import math
import numpy as np
from PIL import Image

def test_space_carving():
    # Load 4 dragon views
    img_files = [
        "3d-model/dragon_multiview/dragon_0_front.png",   # theta = 0 deg
        "3d-model/dragon_multiview/dragon_1_right.png",   # theta = 90 deg
        "3d-model/dragon_multiview/dragon_2_back.png",    # theta = 180 deg
        "3d-model/dragon_multiview/dragon_3_left.png"     # theta = 270 deg
    ]

    angles = [0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0]
    images = []
    masks = []

    for f in img_files:
        im = Image.open(f).convert("RGBA")
        w, h = 256, 256
        im = im.resize((w, h), Image.Resampling.BILINEAR)
        arr = np.array(im)
        images.append(arr)
        # Foreground mask: where color is brighter than background (10, 14, 22)
        r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        mask = (luma > 25) & (a > 50)
        masks.append(mask)
        print(f"Mask {f}: {np.sum(mask)} fg pixels")

    # 3D Grid Space Carving
    res = 120
    x_range = np.linspace(-1.3, 1.3, res)
    y_range = np.linspace(-0.8, 1.1, res)
    z_range = np.linspace(-1.3, 1.3, res)

    scale_factor = 0.72  # maps [-1, 1] in 3D to image canvas

    # Voxel carving
    points = []
    colors = []

    for xi, x in enumerate(x_range):
        for yi, y in enumerate(y_range):
            for zi, z in enumerate(z_range):
                inside_all = True
                best_view = 0
                max_cam_z = -999.0

                for k, theta in enumerate(angles):
                    # Rotate 3D point into camera k coordinate system
                    xk = x * math.cos(theta) - z * math.sin(theta)
                    yk = y
                    zk = x * math.sin(theta) + z * math.cos(theta)

                    # Project to UV [0, 1]
                    # In camera projection: u = 0.5 + xk * scale_factor, v = 0.5 - yk * scale_factor
                    u = 0.5 + xk * scale_factor
                    v = 0.5 - yk * scale_factor

                    if u < 0.0 or u >= 1.0 or v < 0.0 or v >= 1.0:
                        inside_all = False
                        break

                    px = int(u * 256)
                    py = int(v * 256)
                    px = min(255, max(0, px))
                    py = min(255, max(0, py))

                    if not masks[k][py, px]:
                        inside_all = False
                        break

                    if zk > max_cam_z:
                        max_cam_z = zk
                        best_view = k

                if inside_all:
                    # Get color from best viewing angle
                    arr = images[best_view]
                    xk = x * math.cos(angles[best_view]) - z * math.sin(angles[best_view])
                    u = 0.5 + xk * scale_factor
                    v = 0.5 - y * scale_factor
                    px = min(255, max(0, int(u * 256)))
                    py = min(255, max(0, int(v * 256)))
                    c = arr[py, px][:3] / 255.0

                    points.append((x, y, z))
                    colors.append(c)

    print(f"Space Carving Result: Total Solid 3D Voxel Points = {len(points)}")

    # Let's save a quick PLY to inspect
    with open("test_carved_dragon.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for (x, y, z), (r, g, b) in zip(points, colors):
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {int(r*255)} {int(g*255)} {int(b*255)}\n")

    print("Saved test_carved_dragon.ply successfully!")

if __name__ == '__main__':
    test_space_carving()
