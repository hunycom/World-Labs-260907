import math
import numpy as np
from PIL import Image

def test_woobles_reconstruction():
    img_paths = [
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144080255.png", # Front
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144087933.png", # Right
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144054208.png", # Back
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788144080253.png", # Top
    ]

    # Camera poses: (azimuth_deg, elevation_deg)
    camera_poses = [
        (0.0, 15.0),      # Front view
        (90.0, 15.0),     # Right view
        (180.0, 20.0),    # Back view
        (270.0, 65.0),    # Top view (looking down at 65 deg)
    ]

    processed_views = []

    for i, (path, (az_deg, el_deg)) in enumerate(zip(img_paths, camera_poses)):
        im = Image.open(path).convert("RGBA")
        arr = np.array(im)
        
        # Sample background from top-left, top-right
        bg_color = np.mean(arr[0:5, 0:5, :3], axis=(0,1))
        
        # Color distance to background
        diff = np.sqrt(np.sum((arr[:,:,:3].astype(float) - bg_color)**2, axis=2))
        fg_mask = (diff > 18.0) & (arr[:,:,3] > 30)
        
        ys, xs = np.where(fg_mask)
        if len(ys) == 0:
            continue
            
        min_y, max_y = np.min(ys), np.max(ys)
        min_x, max_x = np.min(xs), np.max(xs)
        
        crop_h = max_y - min_y
        crop_w = max_x - min_x
        max_dim = max(crop_h, crop_w)
        
        # Square normalized canvas
        sq_size = 256
        sq_im = Image.new("RGBA", (max_dim, max_dim), (0,0,0,0))
        crop_im = im.crop((min_x, min_y, max_x, max_y))
        sq_im.paste(crop_im, ((max_dim - crop_w)//2, (max_dim - crop_h)//2))
        sq_im = sq_im.resize((sq_size, sq_size), Image.Resampling.BILINEAR)
        
        s_arr = np.array(sq_im)
        s_diff = np.sqrt(np.sum((s_arr[:,:,:3].astype(float) - bg_color)**2, axis=2))
        s_mask = (s_diff > 18.0) & (s_arr[:,:,3] > 30)
        
        # Estimate surface depth relief for this view (shape-from-silhouette + distance transform)
        from scipy.ndimage import distance_transform_edt
        dist_map = distance_transform_edt(s_mask)
        if np.max(dist_map) > 0:
            depth_relief = dist_map / np.max(dist_map)
        else:
            depth_relief = np.zeros_like(dist_map)
            
        processed_views.append({
            "image": s_arr,
            "mask": s_mask,
            "depth_relief": depth_relief,
            "azimuth": math.radians(az_deg),
            "elevation": math.radians(el_deg),
        })
        print(f"View {i} ({az_deg} deg, el {el_deg} deg): {np.sum(s_mask)} fg pixels")

    # Generate 3D Gaussian Surface Splats from all multi-view relief projections
    all_points = []
    all_colors = []

    for v_idx, v in enumerate(processed_views):
        az = v["azimuth"]
        el = v["elevation"]
        img = v["image"]
        mask = v["mask"]
        relief = v["depth_relief"]
        
        # Camera rotation matrix: R = R_az * R_el
        # Camera forwards is towards origin
        cos_az, sin_az = math.cos(az), math.sin(az)
        cos_el, sin_el = math.cos(el), math.sin(el)
        
        # Sample active foreground pixels with stride
        stride = 2
        for py in range(0, 256, stride):
            for px in range(0, 256, stride):
                if not mask[py, px]:
                    continue
                    
                u = (px / 256.0 - 0.5) * 1.5
                v_coord = -(py / 256.0 - 0.5) * 1.5  # Y up
                d = relief[py, px] * 0.45  # surface depth bulge
                
                # Point in camera coordinate (X_cam, Y_cam, Z_cam)
                # X_cam = right, Y_cam = up, Z_cam = towards camera
                x_cam = u
                y_cam = v_coord
                z_cam = d
                
                # Transform camera to world coordinates
                # Elevation rotation around X_cam:
                # y_w_intermediate = y_cam * cos_el - z_cam * sin_el
                # z_w_intermediate = y_cam * sin_el + z_cam * cos_el
                y_inter = y_cam * cos_el - z_cam * sin_el
                z_inter = y_cam * sin_el + z_cam * cos_el
                
                # Azimuth rotation around Y_world:
                x_world = x_cam * cos_az + z_inter * sin_az
                y_world = y_inter
                z_world = -x_cam * sin_az + z_inter * cos_az
                
                # Color
                rgb = img[py, px, :3] / 255.0
                
                # Add surface splat
                all_points.append((x_world, y_world + 0.35, z_world))
                all_colors.append(rgb)
                
                # Add interior volumetric fill for solid body if deep
                if d > 0.15:
                    d_sub = d * 0.5
                    y_in = y_cam * cos_el - d_sub * sin_el
                    z_in = y_cam * sin_el + d_sub * cos_el
                    xw_in = x_cam * cos_az + z_in * sin_az
                    yw_in = y_in
                    zw_in = -x_cam * sin_az + z_in * cos_az
                    all_points.append((xw_in, yw_in + 0.35, zw_in))
                    all_colors.append(rgb * 0.9)

    print(f"Generated {len(all_points)} solid 3D Gaussian Splats from all {len(processed_views)} multi-view images!")

    # Save to PLY
    with open("test_woobles_solid.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(all_points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for (x, y, z), (r, g, b) in zip(all_points, all_colors):
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {int(r*255)} {int(g*255)} {int(b*255)}\n")

    print("Saved test_woobles_solid.ply!")

if __name__ == '__main__':
    test_woobles_reconstruction()
