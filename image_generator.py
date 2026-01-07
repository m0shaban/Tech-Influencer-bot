"""
Image Generator for OG Images
Generates branded images with article headlines when original images aren't available.
Strategy: Fallback chain - Original Image -> AI Generated -> OG Image
Uses custom background images with proper Arabic text support.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import textwrap
import random

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"

# Create images directory if it doesn't exist
IMAGES_DIR.mkdir(exist_ok=True)


class OGImageGenerator:
    """Generate branded OG images for articles with Arabic text support"""
    
    def __init__(self):
        self.brands_dir = IMAGES_DIR / "brand_backgrounds"
        self.generated_dir = IMAGES_DIR / "generated"
        self.brands_dir.mkdir(exist_ok=True)
        self.generated_dir.mkdir(exist_ok=True)
        
        self.backgrounds = self._load_backgrounds()
        
        if not self.backgrounds:
            print("⚠️ No background images found in images/brand_backgrounds/")
            print("📌 Please add background1.png, background2.png, background3.png")
    
    def _load_backgrounds(self) -> list:
        """Load available background images"""
        backgrounds = list(self.brands_dir.glob("*.png"))
        if backgrounds:
            print(f"✅ Loaded {len(backgrounds)} background images")
        return backgrounds
    
    def _reshape_arabic_text(self, text: str) -> str:
        """
        Reshape Arabic text for proper display.
        Fixes disconnected letters issue.
        """
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            
            # Reshape Arabic text
            reshaped_text = arabic_reshaper.reshape(text)
            # Get proper display order (RTL)
            display_text = get_display(reshaped_text)
            return display_text
        except ImportError:
            # Fallback if libraries not installed
            print("⚠️ arabic_reshaper/bidi not installed. Install with:")
            print("   pip install arabic-reshaper python-bidi")
            return text
    
    def _load_arabic_font(self, size: int = 32) -> ImageFont.FreeTypeFont:
        """
        Load a font that supports Arabic characters.
        Common options: Arial, Segoe UI, DejaVu Sans, Noto Sans Arabic
        """
        font_paths = [
            # Windows
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            # Linux/Mac
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Arial.ttf",
            # Fallback to default
            None,
        ]
        
        for font_path in font_paths:
            if font_path and Path(font_path).exists():
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    pass
        
        # Last resort: default font
        return ImageFont.load_default()
    
    def generate_og_image(self, headline: str, 
                         subtitle: Optional[str] = None) -> Path:
        """
        Generate an OG image with headline (Arabic-safe)
        
        Args:
            headline: Article headline/title
            subtitle: Optional subtitle
            
        Returns:
            Path to generated image
        """
        try:
            # Select random background
            if not self.backgrounds:
                raise Exception("No background images available in images/brand_backgrounds/")
            
            bg_path = random.choice(self.backgrounds)
            image = Image.open(bg_path).convert('RGB')
            draw = ImageDraw.Draw(image)
            
            width, height = image.size
            padding = 60
            
            # Load Arabic-compatible font
            title_font = self._load_arabic_font(int(width * 0.06))
            subtitle_font = self._load_arabic_font(int(width * 0.04))
            
            # Reshape Arabic text
            display_headline = self._reshape_arabic_text(headline)
            
            # Wrap and draw headline
            max_width = width - (padding * 2)
            wrapped_headline = self._wrap_text(
                display_headline,
                max_width,
                title_font,
                draw
            )
            
            y_pos = height // 2 - 80
            text_color = (255, 255, 255)  # White
            
            for line in wrapped_headline:
                # Draw with anchor right for RTL text
                draw.text(
                    (width - padding, y_pos),
                    line,
                    fill=text_color,
                    font=title_font,
                    anchor="rt"  # Right-top anchor for RTL
                )
                y_pos += int(width * 0.08)
            
            # Draw subtitle if provided
            if subtitle:
                y_pos += 20
                display_subtitle = self._reshape_arabic_text(subtitle)
                wrapped_subtitle = self._wrap_text(
                    display_subtitle,
                    max_width,
                    subtitle_font,
                    draw
                )
                
                subtitle_color = (200, 200, 200)  # Light gray
                for line in wrapped_subtitle:
                    draw.text(
                        (width - padding, y_pos),
                        line,
                        fill=subtitle_color,
                        font=subtitle_font,
                        anchor="rt"  # Right-top anchor for RTL
                    )
                    y_pos += int(width * 0.06)
            
            # Save generated image
            filename = f"og_image_{hash(headline) % 1000000}.png"
            output_path = self.generated_dir / filename
            image.save(output_path, quality=95)
            
            print(f"✅ Generated OG image: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ Error generating OG image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _wrap_text(self, text: str, max_width: int, font, draw) -> list:
        """Wrap text to fit in max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            
            # Estimate width
            try:
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
            except:
                text_width = len(test_line) * 10  # Fallback estimation
            
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
        
        return lines[:4]  # Max 4 lines


class ImageFetcher:
    """Fetch images from URLs with fallbacks"""
    
    @staticmethod
    def fetch_from_url(url: str, timeout: int = 5) -> Optional[bytes]:
        """Fetch image from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"⚠️ Failed to fetch image from {url}: {e}")
        return None
    
    @staticmethod
    def validate_image(image_bytes: bytes) -> bool:
        """Validate if bytes are valid image"""
        try:
            Image.open(BytesIO(image_bytes))
            return True
        except:
            return False


class ImageStrategy:
    """
    Multi-strategy image handling:
    1. Try to extract from article URL (BeautifulSoup)
    2. Try to generate with AI (Hugging Face)
    3. Generate branded OG image with custom backgrounds
    """
    
    def __init__(self):
        self.og_generator = OGImageGenerator()
        self.fetcher = ImageFetcher()
    
    def get_image(self, 
                  headline: str,
                  article_url: Optional[str] = None,
                  fallback_to_og: bool = True) -> Optional[str]:
        """
        Get image with fallback strategy
        
        Returns:
            Image URL or path to generated image
        """
        
        # Strategy 1: Try to extract from article
        if article_url:
            print(f"🖼️ Strategy 1: Extracting image from article...")
            image_data = self._extract_from_article(article_url)
            if image_data:
                print("✅ Got image from article")
                return image_data
        
        # Strategy 2: Try AI generation (optional, requires API key)
        if os.getenv("HUGGINGFACE_API_KEY"):
            print("🤖 Strategy 2: Generating image with AI...")
            image_data = self._generate_with_ai(headline)
            if image_data:
                print("✅ Generated image with AI")
                return image_data
        
        # Strategy 3: Generate branded OG image (always available)
        if fallback_to_og:
            print("🎨 Strategy 3: Generating branded OG image...")
            image_path = self.og_generator.generate_og_image(headline)
            if image_path:
                return str(image_path)
        
        return None
    
    def _extract_from_article(self, url: str) -> Optional[str]:
        """Extract image from article URL using BeautifulSoup"""
        try:
            from feed_manager import extract_image_from_url
            return extract_image_from_url(url)
        except Exception as e:
            print(f"⚠️ Failed to extract from article: {e}")
            return None
    
    def _generate_with_ai(self, headline: str) -> Optional[str]:
        """Generate image using Hugging Face API"""
        try:
            api_key = os.getenv("HUGGINGFACE_API_KEY")
            if not api_key:
                return None
            
            import requests as req
            
            # Use Hugging Face inference API
            headers = {"Authorization": f"Bearer {api_key}"}
            api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3"
            
            payload = {
                "inputs": f"Professional tech news: {headline[:100]}",
            }
            
            response = req.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Save generated image
                image_path = Path("/tmp") / f"ai_gen_{hash(headline)}.png"
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return str(image_path)
        except Exception as e:
            print(f"⚠️ AI image generation failed: {e}")
        
        return None


# Global instance
_strategy = None


def get_image_strategy() -> ImageStrategy:
    """Get or create image strategy instance"""
    global _strategy
    if _strategy is None:
        _strategy = ImageStrategy()
    return _strategy


def get_article_image(headline: str, 
                     article_url: Optional[str] = None) -> Optional[str]:
    """
    Main function to get image for article
    
    Returns:
        Image URL or path
    """
    strategy = get_image_strategy()
    return strategy.get_image(headline, article_url)


# Test function
if __name__ == "__main__":
    print("🎨 Image Generator Test\n")
    
    gen = get_image_strategy()
    
    test_headlines = [
        "جوجل عطلها الذكاء الاصطناعي في الإنتاج! 🤖",
        "OpenAI تطلق نموذج جديد يغير كل شيء",
        "Meta تستثمر مليارات في AI والحوسبة الكمومية",
    ]
    
    for headline in test_headlines:
        print(f"\n📝 Testing: {headline[:50]}...")
        image_path = gen.get_image(headline, fallback_to_og=True)
        if image_path:
            print(f"✅ Image generated: {image_path}")
        else:
            print(f"❌ Failed to generate image")

    
    def generate_og_image(self, headline: str, 
                         subtitle: Optional[str] = None) -> Path:
        """
        Generate an OG image with headline
        
        Args:
            headline: Article headline/title
            subtitle: Optional subtitle
            
        Returns:
            Path to generated image
        """
        try:
            # Select random background
            if not self.backgrounds:
                raise Exception("No background images available")
            
            bg_path = random.choice(self.backgrounds)
            image = Image.open(bg_path).convert('RGB')
            draw = ImageDraw.Draw(image)
            
            width, height = image.size
            padding = 60
            
            # Try to load fonts (fallback to default if not available)
            try:
                title_font = ImageFont.truetype(
                    "arial.ttf", 
                    int(width * 0.08)
                )
                subtitle_font = ImageFont.truetype(
                    "arial.ttf",
                    int(width * 0.05)
                )
            except:
                # Use default font if truetype not available
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
            
            # Add RoboVAI branding
            try:
                brand_font = ImageFont.truetype("arial.ttf", int(width * 0.04))
                draw.text(
                    (width - padding - 200, padding),
                    "RoboVAI",
                    fill=(59, 130, 246),
                    font=brand_font,
                    anchor="rt"
                )
            except:
                pass
            
            # Wrap and draw headline
            max_width = width - (padding * 2)
            wrapped_headline = self._wrap_text(
                headline,
                max_width,
                title_font,
                draw
            )
            
            y_pos = height // 2 - 100
            text_color = (255, 255, 255)  # White
            
            for line in wrapped_headline:
                draw.text(
                    (padding, y_pos),
                    line,
                    fill=text_color,
                    font=title_font
                )
                y_pos += int(width * 0.1)
            
            # Draw subtitle if provided
            if subtitle:
                y_pos += 20
                wrapped_subtitle = self._wrap_text(
                    subtitle,
                    max_width,
                    subtitle_font,
                    draw
                )
                
                subtitle_color = (200, 200, 200)  # Light gray
                for line in wrapped_subtitle:
                    draw.text(
                        (padding, y_pos),
                        line,
                        fill=subtitle_color,
                        font=subtitle_font
                    )
                    y_pos += int(width * 0.06)
            
            # Add shadow effect by drawing multiple times with slight offset
            # (Already done by drawing white text on dark background)
            
            # Save generated image
            filename = f"og_image_{hash(headline) % 1000000}.png"
            output_path = self.generated_dir / filename
            image.save(output_path, quality=95)
            
            return output_path
            
        except Exception as e:
            print(f"❌ Error generating OG image: {e}")
            return None
    
    def _wrap_text(self, text: str, max_width: int, font, draw) -> list:
        """Wrap text to fit in max_width"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = " ".join(current_line + [word])
            
            # Estimate width (approximate)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
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
        
        return lines[:4]  # Max 4 lines


class ImageFetcher:
    """Fetch images from URLs with fallbacks"""
    
    @staticmethod
    def fetch_from_url(url: str, timeout: int = 5) -> Optional[bytes]:
        """Fetch image from URL"""
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"⚠️ Failed to fetch image from {url}: {e}")
        return None
    
    @staticmethod
    def validate_image(image_bytes: bytes) -> bool:
        """Validate if bytes are valid image"""
        try:
            Image.open(BytesIO(image_bytes))
            return True
        except:
            return False


class ImageStrategy:
    """
    Multi-strategy image handling:
    1. Try to extract from article URL (BeautifulSoup)
    2. Try to generate with AI (Hugging Face)
    3. Generate branded OG image
    """
    
    def __init__(self):
        self.og_generator = OGImageGenerator()
        self.fetcher = ImageFetcher()
    
    def get_image(self, 
                  headline: str,
                  article_url: Optional[str] = None,
                  fallback_to_og: bool = True) -> Optional[str]:
        """
        Get image with fallback strategy
        
        Returns:
            Image URL or path to generated image
        """
        
        # Strategy 1: Try to extract from article
        if article_url:
            print(f"🖼️ Strategy 1: Extracting image from {article_url[:50]}...")
            image_data = self._extract_from_article(article_url)
            if image_data:
                print("✅ Got image from article")
                return image_data
        
        # Strategy 2: Try AI generation (optional, requires API key)
        if os.getenv("HUGGINGFACE_API_KEY"):
            print("🤖 Strategy 2: Generating image with AI...")
            image_data = self._generate_with_ai(headline)
            if image_data:
                print("✅ Generated image with AI")
                return image_data
        
        # Strategy 3: Generate branded OG image
        if fallback_to_og:
            print("🎨 Strategy 3: Generating branded OG image...")
            image_path = self.og_generator.generate_og_image(headline)
            if image_path:
                print(f"✅ Generated OG image: {image_path}")
                return str(image_path)
        
        return None
    
    def _extract_from_article(self, url: str) -> Optional[str]:
        """Extract image from article URL using BeautifulSoup"""
        try:
            from feed_manager import extract_image_from_url
            return extract_image_from_url(url)
        except Exception as e:
            print(f"⚠️ Failed to extract from article: {e}")
            return None
    
    def _generate_with_ai(self, headline: str) -> Optional[str]:
        """Generate image using Hugging Face API"""
        try:
            api_key = os.getenv("HUGGINGFACE_API_KEY")
            if not api_key:
                return None
            
            import requests as req
            
            # Use Hugging Face inference API
            headers = {"Authorization": f"Bearer {api_key}"}
            api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-3"
            
            payload = {
                "inputs": f"Professional tech news: {headline[:100]}",
            }
            
            response = req.post(api_url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Save generated image
                image_path = Path("/tmp") / f"ai_gen_{hash(headline)}.png"
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return str(image_path)
        except Exception as e:
            print(f"⚠️ AI image generation failed: {e}")
        
        return None


# Global instance
_strategy = None


def get_image_strategy() -> ImageStrategy:
    """Get or create image strategy instance"""
    global _strategy
    if _strategy is None:
        _strategy = ImageStrategy()
    return _strategy


def get_article_image(headline: str, 
                     article_url: Optional[str] = None) -> Optional[str]:
    """
    Main function to get image for article
    
    Returns:
        Image URL or path
    """
    strategy = get_image_strategy()
    return strategy.get_image(headline, article_url)


# Test function
if __name__ == "__main__":
    print("🎨 Image Generator Test\n")
    
    gen = get_image_strategy()
    
    test_headlines = [
        "Google عطلها الذكاء الاصطناعي في الإنتاج! 🤖",
        "OpenAI تطلق نموذج جديد يغير كل شيء",
        "Meta تستثمر مليارات في AI والحوسبة الكمومية",
    ]
    
    for headline in test_headlines:
        print(f"\n📝 Testing: {headline[:50]}...")
        image_path = gen.get_image(headline, fallback_to_og=True)
        if image_path:
            print(f"✅ Image generated: {image_path}")
        else:
            print(f"❌ Failed to generate image")
