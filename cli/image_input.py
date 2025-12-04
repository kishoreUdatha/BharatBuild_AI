"""
BharatBuild CLI Image Input Support

Enables image input via paste, drag-drop, or file path:
  > /image path/to/screenshot.png analyze this UI
  > (paste image from clipboard)
"""

import os
import sys
import base64
import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


class ImageSource(str, Enum):
    """Source of image input"""
    FILE = "file"
    CLIPBOARD = "clipboard"
    URL = "url"
    BASE64 = "base64"


@dataclass
class ImageData:
    """Represents an image for input"""
    source: ImageSource
    data: Union[str, bytes]  # Path, URL, or base64 data
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    size_bytes: int = 0
    filename: Optional[str] = None

    def to_base64(self) -> str:
        """Convert image data to base64 string"""
        if self.source == ImageSource.BASE64:
            return self.data if isinstance(self.data, str) else self.data.decode()

        if self.source == ImageSource.FILE:
            with open(self.data, 'rb') as f:
                return base64.b64encode(f.read()).decode()

        if isinstance(self.data, bytes):
            return base64.b64encode(self.data).decode()

        return self.data

    def to_data_url(self) -> str:
        """Convert to data URL format"""
        b64 = self.to_base64()
        return f"data:{self.mime_type};base64,{b64}"


class ImageInputHandler:
    """
    Handles image input from various sources.

    Usage:
        handler = ImageInputHandler(console)

        # Load from file
        image = handler.load_from_file("screenshot.png")

        # Load from clipboard
        image = handler.load_from_clipboard()

        # Load from URL
        image = await handler.load_from_url("https://example.com/image.png")

        # Prepare for API
        api_data = handler.prepare_for_api(image)
    """

    SUPPORTED_FORMATS = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
    }

    MAX_SIZE_MB = 20  # Maximum image size

    def __init__(self, console: Console):
        self.console = console

    def load_from_file(self, path: str) -> Optional[ImageData]:
        """Load image from file path"""
        file_path = Path(path)

        if not file_path.exists():
            self.console.print(f"[red]Image not found: {path}[/red]")
            return None

        if not file_path.is_file():
            self.console.print(f"[red]Not a file: {path}[/red]")
            return None

        # Check extension
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_FORMATS:
            self.console.print(f"[red]Unsupported image format: {ext}[/red]")
            self.console.print(f"[dim]Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}[/dim]")
            return None

        # Check size
        size = file_path.stat().st_size
        if size > self.MAX_SIZE_MB * 1024 * 1024:
            self.console.print(f"[red]Image too large: {size / 1024 / 1024:.1f}MB (max {self.MAX_SIZE_MB}MB)[/red]")
            return None

        mime_type = self.SUPPORTED_FORMATS[ext]

        # Try to get dimensions
        width, height = self._get_image_dimensions(file_path)

        return ImageData(
            source=ImageSource.FILE,
            data=str(file_path.absolute()),
            mime_type=mime_type,
            width=width,
            height=height,
            size_bytes=size,
            filename=file_path.name
        )

    def load_from_clipboard(self) -> Optional[ImageData]:
        """Load image from system clipboard"""
        try:
            # Try using PIL
            from PIL import ImageGrab, Image
            import io

            img = ImageGrab.grabclipboard()

            if img is None:
                self.console.print("[yellow]No image in clipboard[/yellow]")
                return None

            if isinstance(img, list):
                # File paths copied
                if img and os.path.isfile(img[0]):
                    return self.load_from_file(img[0])
                return None

            if isinstance(img, Image.Image):
                # Convert to bytes
                buffer = io.BytesIO()
                img.save(buffer, format='PNG')
                data = buffer.getvalue()

                return ImageData(
                    source=ImageSource.CLIPBOARD,
                    data=data,
                    mime_type='image/png',
                    width=img.width,
                    height=img.height,
                    size_bytes=len(data),
                    filename="clipboard.png"
                )

        except ImportError:
            # Try pyperclip as fallback (limited support)
            try:
                import pyperclip
                content = pyperclip.paste()

                # Check if it's a file path
                if os.path.isfile(content):
                    return self.load_from_file(content)

                # Check if it's base64
                if content.startswith('data:image/'):
                    return self._parse_data_url(content)

            except ImportError:
                pass

            self.console.print("[yellow]Clipboard support requires Pillow: pip install Pillow[/yellow]")
            return None

        except Exception as e:
            self.console.print(f"[red]Error reading clipboard: {e}[/red]")
            return None

        return None

    async def load_from_url(self, url: str) -> Optional[ImageData]:
        """Load image from URL"""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')

                if not content_type.startswith('image/'):
                    self.console.print(f"[red]URL does not point to an image: {content_type}[/red]")
                    return None

                data = response.content

                if len(data) > self.MAX_SIZE_MB * 1024 * 1024:
                    self.console.print(f"[red]Image too large: {len(data) / 1024 / 1024:.1f}MB[/red]")
                    return None

                # Get dimensions
                width, height = self._get_dimensions_from_bytes(data)

                # Get filename from URL
                filename = url.split('/')[-1].split('?')[0] or "image.png"

                return ImageData(
                    source=ImageSource.URL,
                    data=data,
                    mime_type=content_type.split(';')[0],
                    width=width,
                    height=height,
                    size_bytes=len(data),
                    filename=filename
                )

        except ImportError:
            self.console.print("[yellow]URL loading requires httpx: pip install httpx[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error loading image from URL: {e}[/red]")

        return None

    def load_from_base64(self, data: str, mime_type: str = "image/png") -> Optional[ImageData]:
        """Load image from base64 string"""
        try:
            # Handle data URL format
            if data.startswith('data:'):
                return self._parse_data_url(data)

            # Decode to verify it's valid
            decoded = base64.b64decode(data)

            if len(decoded) > self.MAX_SIZE_MB * 1024 * 1024:
                self.console.print(f"[red]Image too large[/red]")
                return None

            width, height = self._get_dimensions_from_bytes(decoded)

            return ImageData(
                source=ImageSource.BASE64,
                data=data,
                mime_type=mime_type,
                width=width,
                height=height,
                size_bytes=len(decoded),
                filename="image.png"
            )

        except Exception as e:
            self.console.print(f"[red]Invalid base64 image data: {e}[/red]")
            return None

    def _parse_data_url(self, data_url: str) -> Optional[ImageData]:
        """Parse a data URL"""
        try:
            # Format: data:image/png;base64,xxxxx
            header, b64_data = data_url.split(',', 1)
            mime_type = header.split(':')[1].split(';')[0]

            decoded = base64.b64decode(b64_data)
            width, height = self._get_dimensions_from_bytes(decoded)

            return ImageData(
                source=ImageSource.BASE64,
                data=b64_data,
                mime_type=mime_type,
                width=width,
                height=height,
                size_bytes=len(decoded)
            )

        except Exception as e:
            self.console.print(f"[red]Invalid data URL: {e}[/red]")
            return None

    def _get_image_dimensions(self, path: Path) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions from file"""
        try:
            from PIL import Image
            with Image.open(path) as img:
                return img.size
        except ImportError:
            pass
        except Exception:
            pass
        return None, None

    def _get_dimensions_from_bytes(self, data: bytes) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions from bytes"""
        try:
            from PIL import Image
            import io
            with Image.open(io.BytesIO(data)) as img:
                return img.size
        except ImportError:
            pass
        except Exception:
            pass
        return None, None

    def prepare_for_api(self, image: ImageData) -> Dict[str, Any]:
        """
        Prepare image data for API submission.

        Returns format suitable for Claude API.
        """
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image.mime_type,
                "data": image.to_base64()
            }
        }

    def show_image_info(self, image: ImageData):
        """Display image information"""
        info_lines = []

        if image.filename:
            info_lines.append(f"[bold]File:[/bold] {image.filename}")

        info_lines.append(f"[bold]Source:[/bold] {image.source.value}")
        info_lines.append(f"[bold]Type:[/bold] {image.mime_type}")

        if image.width and image.height:
            info_lines.append(f"[bold]Dimensions:[/bold] {image.width}x{image.height}")

        size_kb = image.size_bytes / 1024
        if size_kb > 1024:
            info_lines.append(f"[bold]Size:[/bold] {size_kb / 1024:.1f} MB")
        else:
            info_lines.append(f"[bold]Size:[/bold] {size_kb:.1f} KB")

        content = "\n".join(info_lines)

        panel = Panel(
            Text.from_markup(content),
            title="[bold cyan]📷 Image Loaded[/bold cyan]",
            border_style="cyan"
        )

        self.console.print(panel)

    def show_preview(self, image: ImageData, max_width: int = 60):
        """Show ASCII preview of image (if supported)"""
        try:
            from PIL import Image
            import io

            # Load image
            if image.source == ImageSource.FILE:
                img = Image.open(image.data)
            else:
                data = image.data if isinstance(image.data, bytes) else base64.b64decode(image.data)
                img = Image.open(io.BytesIO(data))

            # Convert to grayscale and resize
            img = img.convert('L')

            aspect = img.height / img.width
            new_width = min(max_width, img.width)
            new_height = int(new_width * aspect * 0.5)  # Terminal chars are taller than wide

            img = img.resize((new_width, new_height))

            # Convert to ASCII
            chars = " .:-=+*#%@"
            pixels = img.getdata()

            ascii_art = ""
            for i, pixel in enumerate(pixels):
                if i > 0 and i % new_width == 0:
                    ascii_art += "\n"
                char_idx = pixel * (len(chars) - 1) // 255
                ascii_art += chars[char_idx]

            self.console.print(Panel(
                ascii_art,
                title="[dim]Image Preview[/dim]",
                border_style="dim"
            ))

        except ImportError:
            self.console.print("[dim]Preview requires Pillow: pip install Pillow[/dim]")
        except Exception as e:
            self.console.print(f"[dim]Could not generate preview: {e}[/dim]")


class ImageInputParser:
    """
    Parses image references from user input.

    Detects:
    - File paths: /path/to/image.png
    - URLs: https://example.com/image.png
    - Commands: /image path/to/file
    """

    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}

    def __init__(self):
        pass

    def parse_input(self, text: str) -> Tuple[str, List[str]]:
        """
        Parse input text for image references.

        Returns (clean_text, list_of_image_paths_or_urls)
        """
        images = []
        clean_parts = []

        words = text.split()
        i = 0

        while i < len(words):
            word = words[i]

            # Check for /image command
            if word.lower() == '/image' and i + 1 < len(words):
                images.append(words[i + 1])
                i += 2
                continue

            # Check for image URL
            if word.startswith('http') and self._looks_like_image_url(word):
                images.append(word)
                i += 1
                continue

            # Check for image file path
            if self._looks_like_image_path(word):
                images.append(word)
                i += 1
                continue

            clean_parts.append(word)
            i += 1

        clean_text = ' '.join(clean_parts)
        return clean_text, images

    def _looks_like_image_url(self, url: str) -> bool:
        """Check if URL looks like an image"""
        url_lower = url.lower()
        for ext in self.IMAGE_EXTENSIONS:
            if ext in url_lower:
                return True
        return False

    def _looks_like_image_path(self, path: str) -> bool:
        """Check if path looks like an image file"""
        path_lower = path.lower()
        for ext in self.IMAGE_EXTENSIONS:
            if path_lower.endswith(ext):
                return True
        return False


class ImageManager:
    """
    High-level manager for image input in the CLI.

    Usage:
        manager = ImageManager(console)

        # Process user input
        text, images = await manager.process_input("analyze this /image screenshot.png")

        # Prepare for API
        content = manager.build_message_content(text, images)
    """

    def __init__(self, console: Console):
        self.console = console
        self.handler = ImageInputHandler(console)
        self.parser = ImageInputParser()

    async def process_input(self, text: str) -> Tuple[str, List[ImageData]]:
        """
        Process user input and load any referenced images.

        Returns (clean_text, list_of_loaded_images)
        """
        clean_text, image_refs = self.parser.parse_input(text)

        loaded_images = []

        for ref in image_refs:
            image = None

            if ref.startswith('http://') or ref.startswith('https://'):
                image = await self.handler.load_from_url(ref)
            elif ref == 'clipboard' or ref == '@clipboard':
                image = self.handler.load_from_clipboard()
            else:
                image = self.handler.load_from_file(ref)

            if image:
                self.handler.show_image_info(image)
                loaded_images.append(image)

        return clean_text, loaded_images

    def build_message_content(
        self,
        text: str,
        images: List[ImageData]
    ) -> List[Dict[str, Any]]:
        """
        Build message content array for API.

        Returns list of content blocks (text and images).
        """
        content = []

        # Add images first
        for image in images:
            content.append(self.handler.prepare_for_api(image))

        # Add text
        if text.strip():
            content.append({
                "type": "text",
                "text": text
            })

        return content

    def show_help(self):
        """Show help for image input"""
        help_text = """
[bold cyan]Image Input[/bold cyan]

Add images to your prompts using:

[green]/image path/to/file.png[/green]  Load image from file
[green]/image clipboard[/green]         Load image from clipboard
[green]https://url/to/image.png[/green] Load image from URL

[bold]Examples:[/bold]
  /image screenshot.png analyze this UI
  /image clipboard what's in this image?
  https://example.com/diagram.png explain this

[bold]Supported formats:[/bold] PNG, JPG, JPEG, GIF, WEBP, BMP
[bold]Max size:[/bold] 20MB

[dim]Tip: You can include multiple images in one prompt[/dim]
"""
        panel = Panel(
            Text.from_markup(help_text),
            title="[bold]Image Input Help[/bold]",
            border_style="cyan"
        )
        self.console.print(panel)
