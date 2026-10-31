import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs('public/textures/building-pg', exist_ok=True)

width, height = 1024, 512
img = Image.new('RGB', (width, height), color='#dcd8cf')
draw = ImageDraw.Draw(img)

# Concrete base & ground floor
draw.rectangle([0, 0, width, height], fill='#dedbd2')
draw.rectangle([0, height - 80, width, height], fill='#9e9b94')

# Building stories (4 floors)
floor_h = height // 4
for f in range(4):
    y_top = f * floor_h
    # Horizontal architectural banding
    draw.line([0, y_top, width, y_top], fill='#b3afa6', width=4)
    draw.line([0, y_top + 12, width, y_top + 12], fill='#c2beb5', width=2)

    # Windows on each floor
    if f < 3: # Upper floors
        num_windows = 12
        for w in range(num_windows):
            wx = 40 + w * 78
            wy = y_top + 32
            ww = 56
            wh = 62
            # Window frame
            draw.rectangle([wx - 2, wy - 2, wx + ww + 2, wy + wh + 2], fill='#3a4248')
            # Glass
            draw.rectangle([wx, wy, wx + ww, wy + wh], fill='#365368')
            # Window mullions
            draw.line([wx + ww//2, wy, wx + ww//2, wy + wh], fill='#4a5860', width=2)
            draw.line([wx, wy + wh//3, wx + ww, wy + wh//3], fill='#4a5860', width=1)
    else: # Ground floor with entrance
        # Side windows
        for w in [0, 1, 2, 9, 10, 11]:
            wx = 40 + w * 78
            wy = y_top + 24
            ww = 56
            wh = 70
            draw.rectangle([wx - 2, wy - 2, wx + ww + 2, wy + wh + 2], fill='#3a4248')
            draw.rectangle([wx, wy, wx + ww, wy + wh], fill='#304655')
            draw.line([wx + ww//2, wy, wx + ww//2, wy + wh], fill='#4a5860', width=2)

        # Central entrance portal
        port_x1, port_x2 = 320, 704
        draw.rectangle([port_x1, y_top - 20, port_x2, height], fill='#583c2e') # Cladding
        draw.rectangle([port_x1 + 8, y_top - 12, port_x2 - 8, y_top + 30], fill='#e8e2d5') # Sign band
        draw.text((port_x1 + 45, y_top - 6), "SRM EASWARI ENGINEERING COLLEGE", fill='#1e2924')
        draw.text((port_x1 + 130, y_top + 10), "DEPARTMENT OF POST GRADUATE STUDIES", fill='#47554e')

        # Double glass entrance doors
        door_x1, door_x2 = 440, 584
        draw.rectangle([door_x1, y_top + 40, door_x2, height - 10], fill='#202930')
        draw.rectangle([door_x1 + 6, y_top + 46, door_x1 + 64, height - 14], fill='#6898b8')
        draw.rectangle([door_x1 + 76, y_top + 46, door_x2 - 6, height - 14], fill='#6898b8')

out_path = 'public/textures/building-pg/front.jpg'
img.save(out_path, quality=92)
print(f"Saved sample facade photo to {out_path}")

