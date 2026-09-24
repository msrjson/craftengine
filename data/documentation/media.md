# Image & Multimedia Manipulation

Craft Engine provides a fluent, chainable, and high-performance **Image & Video Manipulation** API powered by Pillow.

## 🖼️ Basic Image Usage

Import the `Image` facade to load, transform, optimize and save images:

```python
from craft.facades import Image

# Resize and convert to optimized WebP
Image.load("storage/photos/banner.jpg") \
    .cover(800, 600) \
    .format("webp", quality=85) \
    .optimize() \
    .save("storage/photos/banner_thumb.webp")
```

### Loading Sources

`Image.load()` accepts:
- A file path string or `pathlib.Path`
- In-memory `bytes` or `bytearray`
- `BytesIO` / file-like objects
- Starlette / FastAPI `UploadFile` directly from HTTP requests

```python
# From an HTTP file upload
avatar = request.file("avatar")
Image.load(avatar).cover(200, 200).format("webp").save("storage/avatars/user.webp")

# Create a new blank canvas
canvas = Image.new(1200, 630, color=(15, 23, 42, 255))
```

---

## ✂️ Resizing, Cropping & Fitting

```python
# Proportional resize by width (calculates height automatically)
img.resize(width=600)

# Exact resize without aspect ratio constraint
img.resize(width=400, height=400, maintain_ratio=False)

# Scale proportionally by factor (0.5 = 50%)
img.scale(0.5)

# Cover target bounds and crop excess from position
img.cover(400, 400, position="center") # or "top-left", "bottom-right", "top", etc.

# Fit/Contain within box with padded background color
img.contain(800, 800, background=(255, 255, 255, 255))

# Fast thumbnail generation
img.thumbnail(300, 300)
```

---

## 🎨 Filters, Effects & Watermarking

```python
# Rotate and flip
img.rotate(90)
img.flip(horizontal=True, vertical=False)

# Color adjustments and filters
img.greyscale()
img.blur(radius=2.0)
img.sharpen(factor=1.8)
img.brightness(1.1)
img.contrast(1.2)
img.invert()

# Watermark with positioning and alpha opacity
img.watermark("public/images/logo.png", position="bottom-right", opacity=0.7, padding=15)
```

---

## 🚀 Exporting & HTTP Streaming

```python
# Save to disk
path = img.save("storage/app/public/photo.webp")

# Export as binary bytes
raw_bytes = img.to_bytes(format="WEBP", quality=85)

# Export as base64 data URI (useful for inline HTML or JSON APIs)
data_uri = img.to_base64(format="WEBP")

# Stream directly as a Starlette HTTP Response
return img.format("webp").response(filename="image.webp")
```

---

## 🎬 Video Thumbnails & Metadata

Inspect video duration, resolution, codecs and extract frames as fluent `Image` instances:

```python
from craft.facades import Media

video = Media.video("storage/videos/intro.mp4")

# Extract metadata
meta = video.metadata()
# {'duration': 12.4, 'width': 1920, 'height': 1080, 'fps': 30.0, 'codec': 'h264', ...}

# Generate an optimized WebP thumbnail from a video timestamp
video.thumbnail(width=640, height=360, at_seconds=2.5) \
    .save("storage/videos/intro_thumb.webp")
```
