# FIGMENT PWA Icons

Place the following image files in this directory:

## Required Icons
- `icon-192x192.png` - App icon for homescreen (192x192 pixels)
- `icon-192x192-maskable.png` - Maskable version for modern Android (192x192 pixels)
- `icon-512x512.png` - Splash screen icon (512x512 pixels)
- `icon-512x512-maskable.png` - Maskable splash screen (512x512 pixels)
- `badge-192x192.png` - Notification badge icon (192x192 pixels)
- `disney-96.png` - Disney shortcut icon (96x96 pixels)
- `spotify-96.png` - Spotify shortcut icon (96x96 pixels)

## How to Generate Icons

### Quick Option - Use online tools:
- https://www.favicon-generator.org/
- https://icon.kitchen/

### Using Python Pillow:
```python
from PIL import Image, ImageDraw

# Generate a simple icon
img = Image.new('RGB', (512, 512), color='#1F1F1F')
draw = ImageDraw.Draw(img)
# Add design here
img.save('icon-512x512.png')
```

### Maskable Icons:
Maskable icons should have content in the center 80% of the square, with padding for Android's dynamic icon masking.

## Design Recommendations for Pixel Dark Mode
- Background: Dark theme (#1F1F1F or #121212)
- Accent colors: Bright cyan, magenta, or neon green
- Text: White or light colors
- Style: Modern, minimal, rounded corners

## Testing
After adding icons, verify by:
1. Opening the app on Pixel 9XL
2. Checking browser console for manifest warnings
3. Selecting "Install app" and checking homescreen appearance
