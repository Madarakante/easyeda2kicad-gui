#!/usr/bin/env python3
"""Generate app.ico — a stylized IC chip for the EasyEDA2KiCad app."""
from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Rounded background with a vertical blue->teal feel (approx via two rounded rects)
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=48, fill=(30, 90, 150, 255))
d.rounded_rectangle([8, 8, SIZE - 8, (SIZE // 2)], radius=48, fill=(38, 110, 170, 255))

# IC chip body
bx0, by0, bx1, by1 = 74, 74, 182, 182
pin_len, pin_w = 18, 12
pin_color = (210, 215, 225, 255)

# pins (4 per side)
for i in range(4):
    off = 88 + i * 26
    # left / right
    d.rounded_rectangle([bx0 - pin_len, off - pin_w // 2, bx0, off + pin_w // 2], radius=3, fill=pin_color)
    d.rounded_rectangle([bx1, off - pin_w // 2, bx1 + pin_len, off + pin_w // 2], radius=3, fill=pin_color)
    # top / bottom
    d.rounded_rectangle([off - pin_w // 2, by0 - pin_len, off + pin_w // 2, by0], radius=3, fill=pin_color)
    d.rounded_rectangle([off - pin_w // 2, by1, off + pin_w // 2, by1 + pin_len], radius=3, fill=pin_color)

# chip body on top of pins
d.rounded_rectangle([bx0, by0, bx1, by1], radius=16, fill=(28, 32, 40, 255))
# pin-1 dot
d.ellipse([bx0 + 14, by0 + 14, bx0 + 30, by0 + 30], fill=(120, 200, 120, 255))
# subtle notch
d.arc([bx0 + 40, by0 - 8, bx0 + 68, by0 + 20], start=0, end=180, fill=(90, 95, 105, 255), width=4)

# small green "import" check accent bottom-right
d.ellipse([150, 150, 196, 196], fill=(60, 175, 90, 255))
d.line([161, 173, 170, 183], fill=(255, 255, 255, 255), width=6)
d.line([170, 183, 187, 160], fill=(255, 255, 255, 255), width=6)

sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("app.ico", format="ICO", sizes=sizes)
print("wrote app.ico with sizes:", sizes)
