#!/usr/bin/env python3
"""Astro enhancement for a night-sky photo: flatten light-pollution gradient,
denoise color, lift+stretch to reveal stars, pop point-sources, boost color."""
import numpy as np
from PIL import Image, ImageFilter

SRC = "IMG_6173.jpeg"

img = Image.open(SRC).convert("RGB")
w, h = img.size
arr = np.asarray(img, np.float32) / 255.0

def pil(a):
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8))

# --- 1. Flatten gradient (downsample->blur->upsample = smooth, no banding) ---
small = img.resize((64, 85), Image.BILINEAR).filter(ImageFilter.GaussianBlur(8))
bg = np.asarray(small.resize((w, h), Image.BICUBIC), np.float32) / 255.0
bg_mean = bg.mean(axis=(0, 1), keepdims=True)
flat = np.clip(arr - 0.92 * (bg - bg_mean), 0.0, 1.0)   # remove gradient, keep brightness

# --- 2. Chroma denoise: keep luminance sharp, blur only color ---
def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])[..., None]

lum = luma(flat)
chroma = flat - lum
chroma_s = (np.asarray(pil(chroma + 0.5).filter(ImageFilter.GaussianBlur(3.0)), np.float32) / 255.0) - 0.5
flat = np.clip(lum + chroma_s, 0.0, 1.0)

# --- 3. Light luminance denoise on the dark sky, keep stars sharp ---
lum2 = luma(flat)
lum_blur = (np.asarray(pil(np.repeat(lum2, 3, 2)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255.0)[..., :1]
detail = np.abs(lum2 - lum_blur)
keep = np.clip(detail * 18.0, 0.0, 1.0)                 # 1 where stars/detail, 0 in flat sky
flat = flat * keep + (lum_blur + (flat - lum2)) * (1 - keep)
flat = np.clip(flat, 0.0, 1.0)

# --- 4. Star-pop layer: isolate point sources and brighten them ---
lum3 = luma(flat)
local = (np.asarray(pil(np.repeat(lum3, 3, 2)).filter(ImageFilter.GaussianBlur(6.0)), np.float32) / 255.0)[..., :1]
stars = np.clip(lum3 - local, 0.0, 1.0)                 # only point sources survive
flat = np.clip(flat + stars * 1.3, 0.0, 1.0)            # gentle star lift

# --- 5. Gentle black point + asinh stretch (subtle, keep it natural) ---
black = np.percentile(flat, 30)
flat = np.clip((flat - black) / (1 - black), 0.0, 1.0)
a = 3.0
stretched = np.arcsinh(flat * a) / np.arcsinh(a)
flat = 0.4 * stretched + 0.6 * flat

# --- 6. Mild saturation for star color ---
lum4 = luma(flat)
flat = np.clip(lum4 + (flat - lum4) * 1.15, 0.0, 1.0)

out = (np.clip(flat, 0, 1) * 255).astype(np.uint8)
Image.fromarray(out).save("IMG_6173-stars.jpeg", quality=95)
print("wrote IMG_6173-stars.jpeg", img.size)
