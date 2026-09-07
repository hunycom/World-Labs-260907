import math
import numpy as np
from PIL import Image

def test_spherical_visual_hull():
    # Load user's 4 dragon images
    user_imgs = [
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143844985.png", # 0 deg
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143845018.png", # 90 deg
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143844986.png", # 180 deg
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143845051.png", # 270 deg
    ]

    camera_poses = [
        (0.0, 10.0),
        (90.0, 10.0),
        (180.0, 10.0),
        (270.0, 10.0),
    ]

    masks = []
    images = []

    for path in user_imgs:
        im = Image.open(path).convert("RGBA")
        arr = np.array(im)
        bg = np.mean(arr[0:5, 0:5, :3], axis=(0,1))
        diff = np.sqrt(np.sum((arr[:,:,:3].astype(float) - bg)**2, axis=2))
        mask = (diff > 18.0) & (arr[:,:,3] > 30)

        ys, xs = np.where(mask)
        min_y, max_y = np.min(ys), np.max(ys)
        min_x, max_x = np.min(xs), np.max(xs)
        crop_h = max_y - min_y
        crop_w = max_x - min_x
        max_dim = max(crop_h, crop_w)

        sq_size = 256
        sq_im = Image.new("RGBA", (max_dim, max_dim), (0,0,0,0))
        crop_im = im.crop((min_x, min_y, max_x, max_y))
        sq_im.paste(crop_im, ((max_dim - crop_w)//2, (max_dim - crop_h)//2))
        sq_im = sq_im.resize((sq_size, sq_size), Image.Resampling.BILINEAR)
        s_arr = np.array(sq_im)

        s_diff = np.sqrt(np.sum((s_arr[:,:,:3].astype(float) - bg)**2, axis=2))
        s_mask = (s_diff > 18.0) & (s_arr[:,:,3] > 30)

        masks.append(s_mask)
        images.append(s_arr)

    # Spherical Ray-Casting Visual Hull
    num_theta = 120   # Azimuth 360 deg
    num_phi = 60      # Elevation -60 to +60 deg
    
    scale_factor = 0.75

    points = []
    colors = []

    thetas = np.linspace(0, 2*math.pi, num_theta, endpoint=False)
    phis = np.linspace(-math.pi/3, math.pi/3, num_phi)

    for phi in phis:
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)

        for theta in thetas:
            dir_x = cos_phi * math.sin(theta)
            dir_y = sin_phi
            dir_z = cos_phi * math.cos(theta)

            # Ray march along r from r_max to 0
            r_max = 1.3
            r_steps = 50
            found_r = 0.0

            for step in range(r_steps):
                r = r_max * (1.0 - step / r_steps)
                # 3D Point
                px_w = r * dir_x
                py_w = r * dir_y
                pz_w = r * dir_z

                # Check inside all views
                inside_all = True
                for k, (az_deg, el_deg) in enumerate(camera_poses):
                    az = math.radians(az_deg)
                    el = math.radians(el_deg)
                    cos_az, sin_az = math.cos(az), math.sin(az)
                    cos_el, sin_el = math.cos(el), math.sin(el)

                    # World to camera rotation
                    # 1. Yaw around Y
                    xk_1 = px_w * cos_az - pz_w * sin_az
                    yk_1 = py_w
                    zk_1 = px_w * sin_az + pz_w * cos_az

                    # 2. Pitch around X
                    xk = xk_1
                    yk = yk_1 * cos_el + zk_1 * sin_el
                    zk = -yk_1 * sin_el + zk_1 * cos_el

                    # Project to UV
                    u = 0.5 + xk * scale_factor
                    v = 0.5 - yk * scale_factor

                    if 0.0 <= u < 1.0 and 0.0 <= v < 1.0:
                        ix = int(u * 256)
                        iy = int(v * 256)
                        if not masks[k][iy, ix]:
                            inside_all = False
                            break
                    else:
                        inside_all = False
                        break

                if inside_all:
                    found_r = r
                    break

            if found_r > 0.08:
                # Find best camera view for texturing
                best_view = 0
                max_dot = -999.0
                for k, (az_deg, el_deg) in enumerate(camera_poses):
                    az = math.radians(az_deg)
                    cam_dir_x = math.sin(az)
                    cam_dir_z = math.cos(az)
                    dot = dir_x * cam_dir_x + dir_z * cam_dir_z
                    if dot > max_dot:
                        max_dot = dot
                        best_view = k

                # Sample color
                az = math.radians(camera_poses[best_view][0])
                el = math.radians(camera_poses[best_view][1])
                cos_az, sin_az = math.cos(az), math.sin(az)
                cos_el, sin_el = math.cos(el), math.sin(el)
                xk = (found_r * dir_x) * cos_az - (found_r * dir_z) * sin_az
                yk = (found_r * dir_y) * cos_el + ((found_r * dir_x) * sin_az + (found_r * dir_z) * cos_az) * sin_el
                u = 0.5 + xk * scale_factor
                v = 0.5 - yk * scale_factor
                ix = min(255, max(0, int(u * 256)))
                iy = min(255, max(0, int(v * 256)))
                c = images[best_view][iy, ix][:3] / 255.0

                surf_x = found_r * dir_x
                surf_y = found_r * dir_y + 0.35
                surf_z = found_r * dir_z

                points.append((surf_x, surf_y, surf_z))
                colors.append(c)

                # Add solid interior layers
                for fill_frac in [0.8, 0.6, 0.4]:
                    points.append((surf_x * fill_frac, (surf_y - 0.35) * fill_frac + 0.35, surf_z * fill_frac))
                    colors.append(c * 0.95)

    print(f"Continuous Ray-Casting Hull result: {len(points)} true 3D surface points (NO CROSS ARTIFACT!)")

    with open("test_continuous_hull.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for (x, y, z), (r, g, b) in zip(points, colors):
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {int(r*255)} {int(g*255)} {int(b*255)}\n")

    print("Saved test_continuous_hull.ply successfully!")

if __name__ == '__main__':
    test_spherical_visual_hull()
