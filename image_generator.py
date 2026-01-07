"""
Advanced OG Image Generator with Arabic Support
Generates unique, professionally designed images with emoji decorations.
Features: Multiple design templates, professional Arabic fonts, dynamic decorations
"""

import os
import secrets
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict

from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import random

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"

# Create images directory if it doesn't exist
IMAGES_DIR.mkdir(exist_ok=True)


class ArabicFontManager:
    """Manage Arabic fonts with fallback chain"""

    _cache: dict[tuple[int, bool], ImageFont.ImageFont] = {}
    _picked_name: Optional[str] = None
    
    @staticmethod
    def _project_font_paths() -> List[Path]:
        candidates: List[Path] = []
        for font_dir in [BASE_DIR / "fonts", BASE_DIR / "assets" / "fonts"]:
            if not font_dir.exists():
                continue
            for ext in ("*.ttf", "*.otf", "*.ttc"):
                candidates.extend(font_dir.glob(ext))
        return candidates

    @staticmethod
    def get_font(size: int = 32, bold: bool = True) -> ImageFont.ImageFont:
        """
        Get best available Arabic-supporting font.
        Priority order: Project fonts > Noto Sans Arabic > Tahoma/Segoe UI > DejaVu > Arial
        """
        cache_key = (size, bold)
        if cache_key in ArabicFontManager._cache:
            return ArabicFontManager._cache[cache_key]

        project_fonts = ArabicFontManager._project_font_paths()
        preferred_project = []
        preferred_names = (
            "notosansarabic",
            "cairo",
            "amiri",
            "ibmplexsansarabic",
            "almarai",
            "tajawal",
        )
        for p in project_fonts:
            name = p.name.lower()
            if any(k in name for k in preferred_names):
                preferred_project.append(p)

        system_candidates: List[tuple[str, str]] = [
            ("C:\\Windows\\Fonts\\NotoSansArabic-Bold.ttf", "Noto Sans Arabic Bold"),
            ("C:\\Windows\\Fonts\\NotoSansArabic-Regular.ttf", "Noto Sans Arabic"),
            ("C:\\Windows\\Fonts\\tahoma.ttf", "Tahoma"),
            ("C:\\Windows\\Fonts\\segoeui.ttf", "Segoe UI"),
            ("C:\\Windows\\Fonts\\arialbd.ttf", "Arial Bold"),
            ("C:\\Windows\\Fonts\\arial.ttf", "Arial"),
            ("/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf", "Noto Sans Arabic Bold"),
            ("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf", "Noto Sans Arabic"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu Sans"),
            ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "Arial Unicode"),
        ]

        def try_font(path: Path, name: str) -> Optional[ImageFont.ImageFont]:
            try:
                font = ImageFont.truetype(str(path), size)
                if ArabicFontManager._picked_name != name:
                    ArabicFontManager._picked_name = name
                    print(f"✅ Using Arabic font: {name}")
                return font
            except Exception:
                return None

        # 1) Project fonts
        for p in preferred_project + project_fonts:
            font = try_font(p, f"Project: {p.name}")
            if font:
                ArabicFontManager._cache[cache_key] = font
                return font

        # 2) System fonts
        for font_path, font_name in system_candidates:
            p = Path(font_path)
            if not p.exists():
                continue
            # prefer bold-ish fonts when bold=True
            if bold and ("regular" in p.name.lower()):
                continue
            font = try_font(p, font_name)
            if font:
                ArabicFontManager._cache[cache_key] = font
                return font

        print("⚠️ Using default font (consider adding fonts into ./fonts)")
        font = ImageFont.load_default()
        ArabicFontManager._cache[cache_key] = font
        return font
    
    @staticmethod
    def reshape_arabic(text: str) -> str:
        """Reshape Arabic text for proper display"""
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            
            reshaped = arabic_reshaper.reshape(text)
            display = get_display(reshaped)
            return display
        except ImportError:
            return text


class DesignTemplate:
    """Base class for design templates"""
    
    def __init__(self, width: int = 1200, height: int = 630, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.image = None
        self.draw = None
        self.seed = seed if seed is not None else secrets.randbelow(1_000_000_000)
        self.rng = random.Random(self.seed)
    
    def create_image(self, headline: str, bg_path: Path) -> Image.Image:
        """Create image - to be overridden by subclasses"""
        raise NotImplementedError

    def _load_background_cover(self, bg_path: Path) -> Image.Image:
        """Load and fit background to canvas (cover crop)."""
        img = Image.open(bg_path).convert("RGB")
        return ImageOps.fit(
            img,
            (self.width, self.height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    def _add_vignette(self, strength: float = 0.35):
        """Darken corners slightly to improve legibility."""
        if self.image is None:
            return
        base = self.image.convert("RGBA")
        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        steps = 30
        for i in range(steps):
            alpha = int(255 * strength * (i + 1) / steps)
            inset = int((i / steps) * min(self.width, self.height) * 0.18)
            od.rounded_rectangle(
                [(inset, inset), (self.width - inset, self.height - inset)],
                radius=48,
                outline=(0, 0, 0, alpha),
                width=6,
            )
        self.image = Image.alpha_composite(base, overlay).convert("RGB")
        self.draw = ImageDraw.Draw(self.image)
    
    def _add_gradient_overlay(self, color: Tuple[int, int, int], alpha: float = 0.3):
        """Add semi-transparent gradient overlay"""
        # Ensure image is correct size
        if self.image.size != (self.width, self.height):
            self.image = self.image.resize((self.width, self.height), Image.Resampling.LANCZOS)
        
        overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        for y in range(self.height):
            intensity = int(255 * (1 - (y / self.height)) * alpha)
            overlay_draw.line(
                [(0, y), (self.width, y)],
                fill=(*color, intensity)
            )
        
        self.image = Image.alpha_composite(
            self.image.convert('RGBA'), overlay
        ).convert('RGB')
        self.draw = ImageDraw.Draw(self.image)
    
    def _wrap_text(self, text: str, max_width: int, font) -> List[str]:
        """Wrap text to fit width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            try:
                bbox = self.draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(test_line) * 8
            
            if text_width > max_width:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines[:4]

    def _fit_text(self, text: str, max_width: int, max_height: int, start_size: int, min_size: int) -> tuple[ImageFont.ImageFont, List[str], int]:
        """Find a font size that fits inside a box."""
        display_text = ArabicFontManager.reshape_arabic(text)
        for size in range(start_size, min_size - 1, -2):
            font = ArabicFontManager.get_font(size, bold=True)
            wrapped = self._wrap_text(display_text, max_width, font)
            # estimate height
            line_heights = []
            for line in wrapped:
                try:
                    bbox = self.draw.textbbox((0, 0), line, font=font)
                    line_heights.append(bbox[3] - bbox[1])
                except Exception:
                    line_heights.append(int(size * 1.2))
            total_h = sum(line_heights) + int(size * 0.15) * max(0, len(wrapped) - 1)
            if total_h <= max_height:
                return font, wrapped, total_h
        font = ArabicFontManager.get_font(min_size, bold=True)
        wrapped = self._wrap_text(display_text, max_width, font)
        return font, wrapped, max_height


class EmojiFontManager:
    """Pick an emoji-capable font for decorations."""

    _cache: dict[int, ImageFont.ImageFont] = {}
    _picked: Optional[str] = None

    @staticmethod
    def get_font(size: int) -> ImageFont.ImageFont:
        if size in EmojiFontManager._cache:
            return EmojiFontManager._cache[size]
        candidates = [
            ("C:\\Windows\\Fonts\\seguiemj.ttf", "Segoe UI Emoji"),
            ("C:\\Windows\\Fonts\\seguisym.ttf", "Segoe UI Symbol"),
            ("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf", "Noto Color Emoji"),
        ]
        for font_path, name in candidates:
            p = Path(font_path)
            if not p.exists():
                continue
            try:
                font = ImageFont.truetype(str(p), size)
                if EmojiFontManager._picked != name:
                    EmojiFontManager._picked = name
                    print(f"✅ Using emoji font: {name}")
                EmojiFontManager._cache[size] = font
                return font
            except Exception:
                continue
        font = ImageFont.load_default()
        EmojiFontManager._cache[size] = font
        return font


class MinimalistTemplate(DesignTemplate):
    """Clean, minimal design with accent bar"""
    
    def create_image(self, headline: str, bg_path: Path) -> Image.Image:
        self.image = self._load_background_cover(bg_path)
        self.draw = ImageDraw.Draw(self.image)
        
        # Add subtle overlays for legibility
        self._add_gradient_overlay((0, 0, 0), alpha=0.28)
        self._add_vignette(0.28)
        
        # Accent bar (random placement)
        bar_color = self.rng.choice([(59, 130, 246), (168, 85, 247), (14, 165, 233)])
        if self.rng.random() < 0.5:
            bar_height = 8
            self.draw.rectangle([(0, 0), (self.width, bar_height)], fill=bar_color)
        else:
            bar_width = 10
            self.draw.rectangle([(0, 0), (bar_width, self.height)], fill=bar_color)

        # Subtle dot pattern
        for _ in range(120):
            x = self.rng.randrange(0, self.width)
            y = self.rng.randrange(0, self.height)
            r = self.rng.choice([1, 1, 2])
            a = self.rng.randrange(18, 40)
            self.draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(255, 255, 255, a))
        
        self._draw_headline(headline)
        return self.image
    
    def _draw_headline(self, headline: str):
        padding_x = 70
        box_margin_y = 80
        max_w = self.width - (padding_x * 2)
        max_h = self.height - (box_margin_y * 2)

        font, wrapped, _ = self._fit_text(headline, max_w, int(max_h * 0.72), start_size=int(self.width * 0.07), min_size=34)

        # Draw translucent text panel
        panel = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        pd = ImageDraw.Draw(panel)
        panel_w = int(max_w * 0.92)
        panel_h = int(max_h * 0.58)
        x2 = self.width - padding_x
        x1 = x2 - panel_w
        y1 = (self.height - panel_h) // 2
        y2 = y1 + panel_h
        pd.rounded_rectangle([(x1, y1), (x2, y2)], radius=28, fill=(0, 0, 0, 120))
        self.image = Image.alpha_composite(self.image.convert("RGBA"), panel).convert("RGB")
        self.draw = ImageDraw.Draw(self.image)

        y_pos = y1 + 40
        line_gap = int(font.size * 0.22)
        for line in wrapped:
            self.draw.text((self.width - padding_x, y_pos), line, fill=(255, 255, 255), font=font, anchor="rt")
            try:
                bbox = self.draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
            except Exception:
                line_h = int(font.size * 1.2)
            y_pos += line_h + line_gap


class GradientTemplate(DesignTemplate):
    """Bold design with gradient and emoji decorations"""
    
    def create_image(self, headline: str, bg_path: Path) -> Image.Image:
        self.image = self._load_background_cover(bg_path)
        self.draw = ImageDraw.Draw(self.image)
        
        # Add colorful gradient overlay (random palette)
        palette = self.rng.choice([
            (59, 130, 246),   # blue
            (168, 85, 247),   # purple
            (14, 165, 233),   # sky
            (245, 158, 11),   # amber
        ])
        self._add_gradient_overlay(palette, alpha=0.45)
        self._add_vignette(0.30)
        
        # Add emoji decorations
        self._add_emoji_decorations()

        # Add soft geometric streaks
        for _ in range(6):
            x1 = self.rng.randrange(-200, self.width)
            y1 = self.rng.randrange(0, self.height)
            x2 = x1 + self.rng.randrange(260, 520)
            y2 = y1 + self.rng.randrange(-60, 60)
            w = self.rng.randrange(2, 6)
            self.draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255, self.rng.randrange(30, 70)), width=w)
        
        self._draw_headline(headline)
        return self.image
    
    def _add_emoji_decorations(self):
        """Add emoji elements to the image"""
        emoji_font = EmojiFontManager.get_font(int(self.width * 0.085))
        
        # Tech-related emojis
        emojis = ['🤖', '💡', '⚡', '🚀', '🔧', '🎯', '💻', '🌟']
        
        # Add emoji in corners (randomized)
        positions = [
            (55, 55),
            (self.width - 120, 55),
            (55, self.height - 140),
            (self.width - 140, self.height - 160),
        ]

        picks = self.rng.sample(emojis, 3)
        for pos, emoji in zip(self.rng.sample(positions, 3), picks):
            try:
                # subtle shadow
                self.draw.text((pos[0] + 2, pos[1] + 2), emoji, font=emoji_font, fill=(0, 0, 0, 140))
                self.draw.text(pos, emoji, font=emoji_font, fill=(255, 255, 255, 235))
            except:
                pass
    
    def _draw_headline(self, headline: str):
        padding = 70
        max_w = self.width - (padding * 2)
        font, wrapped, _ = self._fit_text(headline, max_w, int(self.height * 0.55), start_size=int(self.width * 0.074), min_size=32)

        y_pos = int(self.height * 0.30)
        line_gap = int(font.size * 0.24)
        for line in wrapped:
            # stronger shadow for contrast
            self.draw.text((self.width - padding + 3, y_pos + 3), line, fill=(0, 0, 0, 190), font=font, anchor="rt")
            self.draw.text((self.width - padding, y_pos), line, fill=(255, 255, 255), font=font, anchor="rt")
            try:
                bbox = self.draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
            except Exception:
                line_h = int(font.size * 1.2)
            y_pos += line_h + line_gap


class ModernTemplate(DesignTemplate):
    """Modern design with geometric shapes"""
    
    def create_image(self, headline: str, bg_path: Path) -> Image.Image:
        self.image = self._load_background_cover(bg_path)
        self.draw = ImageDraw.Draw(self.image)
        
        # Add dark overlay
        self._add_gradient_overlay((20, 20, 40), alpha=0.36)
        self._add_vignette(0.32)
        
        # Add geometric decorations
        self._add_geometric_shapes()
        
        self._draw_headline(headline)
        return self.image
    
    def _add_geometric_shapes(self):
        """Add modern geometric shapes"""
        line_color = self.rng.choice([(59, 130, 246), (168, 85, 247), (14, 165, 233)])
        alt_color = self.rng.choice([(236, 72, 153), (34, 197, 94), (245, 158, 11)])

        # Accent bars
        self.draw.rectangle([(0, self.height // 3), (self.rng.randrange(160, 320), self.height // 3 + 5)], fill=line_color)
        self.draw.rectangle(
            [(self.width - self.rng.randrange(160, 320), self.height * 2 // 3), (self.width, self.height * 2 // 3 + 5)],
            fill=alt_color,
        )

        # Diagonal corner accent
        corner = self.rng.randrange(120, 190)
        self.draw.polygon([(self.width, 0), (self.width - corner, 0), (self.width, corner)], fill=line_color)

        # Random polygons
        for _ in range(4):
            cx = self.rng.randrange(80, self.width - 80)
            cy = self.rng.randrange(80, self.height - 80)
            s = self.rng.randrange(22, 55)
            poly = [(cx - s, cy), (cx, cy - s), (cx + s, cy), (cx, cy + s)]
            self.draw.polygon(poly, outline=(255, 255, 255, self.rng.randrange(40, 90)), width=2)
    
    def _draw_headline(self, headline: str):
        padding = 85
        max_w = self.width - (padding * 2)
        font, wrapped, _ = self._fit_text(headline, max_w, int(self.height * 0.60), start_size=int(self.width * 0.07), min_size=32)

        y_pos = int(self.height * 0.30)
        line_gap = int(font.size * 0.22)
        for line in wrapped:
            self.draw.text((self.width - padding + 3, y_pos + 3), line, fill=(0, 0, 0, 175), font=font, anchor="rt")
            self.draw.text((self.width - padding, y_pos), line, fill=(255, 255, 255), font=font, anchor="rt")
            try:
                bbox = self.draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
            except Exception:
                line_h = int(font.size * 1.2)
            y_pos += line_h + line_gap


class NeonTemplate(DesignTemplate):
    """Neon/vibrant design with bold colors"""
    
    def create_image(self, headline: str, bg_path: Path) -> Image.Image:
        self.image = self._load_background_cover(bg_path)
        self.draw = ImageDraw.Draw(self.image)
        
        # Add dark overlay
        self._add_gradient_overlay((10, 10, 30), alpha=0.45)
        self._add_vignette(0.35)
        
        # Add neon elements
        self._add_neon_elements()
        
        self._draw_headline(headline)
        return self.image
    
    def _add_neon_elements(self):
        """Add neon-style decorative elements"""
        neon_color = self.rng.choice([(255, 0, 127), (0, 255, 200), (59, 130, 246)])
        neon2 = self.rng.choice([(0, 255, 200), (168, 85, 247), (245, 158, 11)])
        
        # Neon lines
        w1 = self.rng.randrange(240, 380)
        self.draw.rectangle([(0, 0), (w1, 4)], fill=neon_color)
        w2 = self.rng.randrange(240, 380)
        self.draw.rectangle([(self.width - w2, self.height - 4), (self.width, self.height)], fill=neon2)
        
        # Corner circles
        circle_size = 40
        self.draw.ellipse(
            [(self.width - circle_size - 20, 20),
             (self.width - 20, circle_size + 20)],
            outline=neon_color,
            width=3
        )

        # Neon emoji stamp
        emoji = self.rng.choice(['🤖', '⚡', '🚀', '💻', '🎯'])
        efont = EmojiFontManager.get_font(int(self.width * 0.075))
        pos = (35, self.height - 140)
        try:
            self.draw.text((pos[0] + 3, pos[1] + 3), emoji, font=efont, fill=(0, 0, 0, 170))
            self.draw.text(pos, emoji, font=efont, fill=(255, 255, 255, 235))
        except Exception:
            pass
    
    def _draw_headline(self, headline: str):
        padding = 70
        max_w = self.width - (padding * 2)
        font, wrapped, _ = self._fit_text(headline, max_w, int(self.height * 0.58), start_size=int(self.width * 0.076), min_size=32)

        y_pos = int(self.height * 0.30)
        line_gap = int(font.size * 0.22)
        glow = self.rng.choice([(255, 0, 127), (0, 255, 200), (168, 85, 247)])
        for line in wrapped:
            self.draw.text((self.width - padding + 4, y_pos + 4), line, fill=(*glow, 210), font=font, anchor="rt")
            self.draw.text((self.width - padding + 2, y_pos + 2), line, fill=(0, 0, 0, 190), font=font, anchor="rt")
            self.draw.text((self.width - padding, y_pos), line, fill=(255, 255, 255), font=font, anchor="rt")
            try:
                bbox = self.draw.textbbox((0, 0), line, font=font)
                line_h = bbox[3] - bbox[1]
            except Exception:
                line_h = int(font.size * 1.2)
            y_pos += line_h + line_gap


class OGImageGenerator:
    """Generate branded OG images with multiple design templates"""
    
    def __init__(self):
        self.brands_dir = IMAGES_DIR / "brand_backgrounds"
        self.generated_dir = IMAGES_DIR / "generated"
        self.brands_dir.mkdir(exist_ok=True)
        self.generated_dir.mkdir(exist_ok=True)
        
        self.backgrounds = self._load_backgrounds()
        self.templates = [MinimalistTemplate, GradientTemplate, ModernTemplate, NeonTemplate]
        
        if self.backgrounds:
            print(f"✅ Loaded {len(self.backgrounds)} background images")
        else:
            print("⚠️ No background images found")
    
    def _load_backgrounds(self) -> list:
        """Load available background images"""
        return list(self.brands_dir.glob("*.png"))
    
    def generate_og_image(self, headline: str) -> Dict[str, Optional[str]]:
        """
        Generate unique OG image with random design template
        
        Args:
            headline: Article headline
            
        Returns:
            Dict with 'local_path' (for Telegram) and 'public_url' (for other platforms)
        """
        try:
            if not self.backgrounds:
                raise Exception("No background images available")
            
            # Select random background and template
            bg_path = random.choice(self.backgrounds)
            template_class = random.choice(self.templates)
            template = template_class(seed=secrets.randbelow(1_000_000_000))
            
            print(f"🎨 Design: {template_class.__name__}")
            
            # Create image
            image = template.create_image(headline, bg_path)
            
            # Save image
            stamp = int(time.time() * 1000)
            rand = secrets.token_hex(3)
            filename = f"og_{stamp}_{rand}.png"
            output_path = self.generated_dir / filename
            image.save(output_path, quality=95)
            
            # Build public URL if IMAGE_BASE_URL is set
            base_url = os.getenv("IMAGE_BASE_URL", "").rstrip("/")
            public_url = f"{base_url}/og/{filename}" if base_url else None
            
            print(f"✅ Generated: {output_path}")
            if public_url:
                print(f"🌐 Public URL: {public_url}")
            
            return {
                "local_path": str(output_path),
                "public_url": public_url
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return {"local_path": None, "public_url": None}


class ImageFetcher:
    """Fetch images from URLs"""
    
    @staticmethod
    def fetch_from_url(url: str, timeout: int = 5) -> Optional[bytes]:
        """Fetch image from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"⚠️ Failed to fetch image: {e}")
        return None


class ImageStrategy:
    """Multi-strategy image handling with fallbacks"""
    
    def __init__(self):
        self.og_generator = OGImageGenerator()
        self.fetcher = ImageFetcher()
    
    def get_image(self, 
                  headline: str,
                  article_url: Optional[str] = None,
                  fallback_to_og: bool = True) -> Optional[Dict[str, Optional[str]]]:
        """Get image with fallback strategy
        
        Returns:
            Dict with 'local_path' (for Telegram) and 'public_url' (for other platforms)
            or None if all strategies fail
        """
        
        # Strategy 1: Extract from article
        if article_url:
            print(f"🖼️ Strategy 1: Extracting image...")
            image_data = self._extract_from_article(article_url)
            if image_data:
                print("✅ Got image from article")
                # External URLs work for all platforms
                return {"local_path": image_data, "public_url": image_data}
        
        # Strategy 2: AI generation (optional)
        if os.getenv("HUGGINGFACE_API_KEY"):
            print("🤖 Strategy 2: AI generation...")
            image_data = self._generate_with_ai(headline)
            if image_data:
                print("✅ Generated with AI")
                # AI generated files need both local and public URLs
                return {"local_path": image_data, "public_url": None}
        
        # Strategy 3: OG Image (always available)
        if fallback_to_og:
            print("🎨 Strategy 3: OG Image...")
            image_result = self.og_generator.generate_og_image(headline)
            if image_result and image_result.get("local_path"):
                return image_result
        
        return None
    
    def _extract_from_article(self, url: str) -> Optional[str]:
        """Extract image from article"""
        try:
            from feed_manager import extract_image_from_url
            return extract_image_from_url(url)
        except Exception as e:
            print(f"⚠️ Failed: {e}")
            return None
    
    def _generate_with_ai(self, headline: str) -> Optional[str]:
        """Generate image with Hugging Face"""
        try:
            api_key = os.getenv("HUGGINGFACE_API_KEY")
            if not api_key:
                return None
            
            import requests as req
            headers = {"Authorization": f"Bearer {api_key}"}
            api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3"
            
            response = req.post(
                api_url,
                headers=headers,
                json={"inputs": f"Professional tech news: {headline[:100]}"},
                timeout=30
            )
            
            if response.status_code == 200:
                image_path = Path("/tmp") / f"ai_gen_{hash(headline)}.png"
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return str(image_path)
        except Exception as e:
            print(f"⚠️ AI failed: {e}")
        
        return None


# Global instance
_strategy = None


def get_image_strategy() -> ImageStrategy:
    """Get or create image strategy instance"""
    global _strategy
    if _strategy is None:
        _strategy = ImageStrategy()
    return _strategy


def get_article_image(headline: str, article_url: Optional[str] = None) -> Optional[Dict[str, Optional[str]]]:
    """Main function to get image for article
    
    Returns:
        Dict with 'local_path' (for Telegram) and 'public_url' (for other platforms)
        or None if all strategies fail
    """
    strategy = get_image_strategy()
    return strategy.get_image(headline, article_url)


# Test function
if __name__ == "__main__":
    print("🎨 Advanced Image Generator Test\n")
    
    gen = get_image_strategy()
    
    test_headlines = [
        "جوجل تطلق أداة ذكاء اصطناعي جديدة تغير كل شيء! 🚀",
        "OpenAI تعلن عن اكتشاف عظيم في المعالجة الطبيعية 💡",
        "Meta تستثمر مليارات في البحث العلمي والتطوير",
        "أمازون تطلق منصة سحابية جديدة تنافس Google و AWS ⚡",
        "مايكروسوفت تدمج الذكاء الاصطناعي في كل منتجاتها 🤖",
    ]
    
    for headline in test_headlines:
        print(f"\n📝 {headline[:50]}...")
        image_path = gen.get_image(headline, fallback_to_og=True)
        if image_path:
            print(f"✅ Generated!")
        else:
            print(f"❌ Failed")
