import math
import numpy as np
from PIL import Image

def test_user_uploaded_images():
    user_imgs = [
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143844985.png",
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143845018.png",
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143844986.png",
        r"C:\Users\Sims\.gemini\antigravity\brain\aeb10d0d-ecb1-4457-85a7-35afca2c98e5\.user_uploaded\media_1788143845051.png",
    ]

    # Angles for the 4 images (Front=0, Side=90, Top/Back=180, Top/Front=270)
    angles = [0.0, math.pi / 2.0, math.pi, 3.0 * math.pi / 2.0]
    
    processed_masks = []
    processed_imgs = []

    for i, path in enumerate(user_imgs):
        im = Image.open(path).convert("RGBA")
        arr = np.array(im)
        
        # Sample background from 4 corners
        corners = [arr[0,0], arr[0,-1], arr[-1,0], arr[-1,-1]]
        bg_rgb = np.mean(corners, axis=0)[:3]
        
        # Distance from background color
        diff = np.sqrt(np.sum((arr[:,:,:3].astype(float) - bg_rgb)**2, axis=2))
        fg_mask = diff > 25.0
        
        # Find bounding box of foreground
        ys, xs = np.where(fg_mask)
        if len(ys) == 0:
            print(f"Image {i}: No foreground found!")
            continue
            
        min_y, max_y = np.min(ys), np.max(ys)
        min_x, max_x = np.min(xs), np.max(xs)
        
        # Crop and pad to square centered
        crop_h = max_y - min_y
        crop_w = max_x - min_x
        max_dim = max(crop_h, crop_w)
        
        # Create centered square canvas
        square_im = Image.new("RGBA", (max_dim, max_dim), (0, 0, 0, 0))
        crop_im = im.crop((min_x, min_y, max_x, max_y))
        square_im.paste(crop_im, ((max_dim - crop_w) // 2, (max_dim - crop_h) // 2))
        
        square_im = square_im.resize((256, 256), Image.Resampling.BILINEAR)
        s_arr = np.array(square_im)
        
        s_diff = np.sqrt(np.sum((s_arr[:,:,:3].astype(float) - bg_rgb)**2, axis=2))
        s_mask = (s_diff > 25.0) & (s_arr[:,:,3] > 50)
        
        processed_masks.append(s_mask)
        processed_imgs.append(s_arr)
        print(f"Processed view {i}: bbox {crop_w}x{crop_h} -> {np.sum(s_mask)} fg pixels")

    # Space Carving on 3D Bounding Box
    res = 90
    x_range = np.linspace(-1.0, 1.0, res)
    y_range = np.linspace(-0.6, 0.8, res)
    z_range = np.linspace(-1.0, 1.0, res)

    scale_factor = 0.85

    points = []
    colors = []

    for x in x_range:
        for y in y_range:
            for z in z_range:
                inside_count = 0
                best_view = 0
                max_cam_z = -999.0

                for k, theta in enumerate(angles):
                    xk = x * math.cos(theta) - z * math.sin(theta)
                    yk = y
                    zk = x * math.sin(theta) + z * math.cos(theta)

                    u = 0.5 + xk * scale_factor
                    v = 0.5 - yk * scale_factor

                    if 0.0 <= u < 1.0 and 0.0 <= v < 1.0:
                        px = min(255, max(0, int(u * 256)))
                        py = min(255, max(0, int(v * 256)))
                        if processed_masks[k][py, px]:
                            inside_count += 1
                            if zk > max_cam_z:
                                max_cam_z = zk
                                best_view = k

                # If inside all (or at least 3 out of 4) views
                if inside_count >= 3:
                    arr = processed_imgs[best_view]
                    xk = x * math.cos(angles[best_view]) - z * math.sin(angles[best_view])
                    u = 0.5 + xk * scale_factor
                    v = 0.5 - y * scale_factor
                    px = min(255, max(0, int(u * 256)))
                    py = min(255, max(0, int(v * 256)))
                    c = arr[py, px][:3] / 255.0

                    points.append((x, y, z))
                    colors.append(c)

    print(f"Space Carving Result from User's 4 Images: {len(points)} solid 3D points generated!")
    
    with open("test_user_carved_dragon.ply", "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("end_header\n")
        for (x, y, z), (r, g, b) in zip(points, colors):
            f.write(f"{x:.4f} {y:.4f} {z:.4f} {int(r*255)} {int(g*255)} {int(b*255)}\n")

    print("Saved test_user_carved_dragon.ply!")

if __name__ == '__main__':
    test_user_uploaded_images()
