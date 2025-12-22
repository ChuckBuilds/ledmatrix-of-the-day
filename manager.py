"""
Of The Day Plugin for LEDMatrix

Display daily featured content like Word of the Day, Bible verses, or custom items.
Supports multiple categories with automatic rotation and configurable data sources.

Features:
- Multiple category support (Word of the Day, Bible verses, etc.)
- Automatic daily updates
- Rotating display of title, definition, examples
- Configurable data sources via JSON files
- Multi-line text wrapping for long content

API Version: 1.0.0
"""

import os
import json
import logging
import time
from datetime import date
from typing import Dict, Any, List, Optional
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

from src.plugin_system.base_plugin import BasePlugin

logger = logging.getLogger(__name__)


class OfTheDayPlugin(BasePlugin):
    """
    Of The Day plugin for displaying daily featured content.
    
    Supports multiple categories with rotation between title, subtitle, and content.
    
    Configuration options:
        categories (dict): Dictionary of category configurations
        category_order (list): Order to display categories
        display_rotate_interval (float): Seconds between display rotations
        subtitle_rotate_interval (float): Seconds between subtitle rotations
        update_interval (float): Seconds between checking for new day
    """
    
    def __init__(self, plugin_id: str, config: Dict[str, Any],
                 display_manager, cache_manager, plugin_manager):
        """Initialize the of-the-day plugin."""
        super().__init__(plugin_id, config, display_manager, cache_manager, plugin_manager)
        
        # Configuration
        self.update_interval = config.get('update_interval', 3600)
        self.display_rotate_interval = config.get('display_rotate_interval', 20)
        self.subtitle_rotate_interval = config.get('subtitle_rotate_interval', 10)
        
        # Categories
        self.categories = config.get('categories', {})
        self.category_order = config.get('category_order', [])
        
        # State
        self.current_day = None
        self.current_items = {}
        self.current_category_index = 0
        self.rotation_state = 0  # 0 = title, 1 = content
        self.last_update = 0
        self.last_rotation_time = time.time()
        self.last_category_rotation_time = time.time()
        
        # Data files
        self.data_files = {}
        
        # Colors
        self.title_color = (255, 255, 255)
        self.subtitle_color = (200, 200, 200)
        self.content_color = (180, 180, 180)
        self.background_color = (0, 0, 0)
        
        # Load data files
        self._load_data_files()
        
        # Load today's items
        self._load_todays_items()
        
        # Register fonts
        self._register_fonts()
        
        self.logger.info(f"Of The Day plugin initialized with {len(self.current_items)} categories")
    
    def _register_fonts(self):
        """Register fonts with the font manager."""
        try:
            if not hasattr(self.plugin_manager, 'font_manager'):
                return
            
            font_manager = self.plugin_manager.font_manager
            
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.title",
                family="press_start",
                size_px=8,
                color=self.title_color
            )
            
            font_manager.register_manager_font(
                manager_id=self.plugin_id,
                element_key=f"{self.plugin_id}.content",
                family="four_by_six",
                size_px=6,
                color=self.content_color
            )
            
            self.logger.info("Of The Day fonts registered")
        except Exception as e:
            self.logger.warning(f"Error registering fonts: {e}")
    
    def _load_data_files(self):
        """Load all data files for enabled categories."""
        for category_name, category_config in self.categories.items():
            if not category_config.get('enabled', True):
                self.logger.debug(f"Skipping disabled category: {category_name}")
                continue
            
            data_file = category_config.get('data_file')
            if not data_file:
                self.logger.warning(f"No data file specified for category: {category_name}")
                continue
            
            try:
                # Try to locate the data file
                file_path = self._find_data_file(data_file)
                if not file_path:
                    self.logger.warning(f"Could not find data file: {data_file}")
                    continue
                
                # Load and parse JSON
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.data_files[category_name] = data
                self.logger.info(f"Loaded data for category '{category_name}': {len(data)} entries")
                
            except Exception as e:
                self.logger.error(f"Error loading data file for {category_name}: {e}")
    
    def _find_data_file(self, data_file: str) -> Optional[str]:
        """Find the data file in possible locations."""
        # Get plugin directory
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Possible paths to check (prioritize plugin directory)
        possible_paths = [
            os.path.join(plugin_dir, data_file),  # In plugin directory (preferred)
            data_file,  # Direct path (if absolute)
            os.path.join(os.getcwd(), data_file),  # Relative to cwd (fallback)
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.logger.info(f"Found data file at: {path}")
                return path
        
        self.logger.warning(f"Data file not found: {data_file}")
        return None
    
    def _load_todays_items(self):
        """Load items for today's date from all enabled categories."""
        today = date.today()
        
        if self.current_day == today and self.current_items:
            return  # Already loaded for today
        
        self.current_day = today
        self.current_items = {}
        
        # Calculate day of year (1-365, or 1-366 for leap years)
        day_of_year = today.timetuple().tm_yday
        
        for category_name, data in self.data_files.items():
            try:
                # Find today's entry using day of year
                day_key = str(day_of_year)
                
                if day_key in data:
                    self.current_items[category_name] = data[day_key]
                    item_title = data[day_key].get('word', data[day_key].get('title', 'N/A'))
                    self.logger.info(f"Loaded item for {category_name} (day {day_of_year}): {item_title}")
                else:
                    self.logger.warning(f"No entry found for day {day_of_year} in category {category_name}")
            
            except Exception as e:
                self.logger.error(f"Error loading today's item for {category_name}: {e}")
    
    def update(self) -> None:
        """Update items if it's a new day."""
        current_time = time.time()
        
        # Check if we need to update
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        
        # Check if it's a new day
        today = date.today()
        if self.current_day != today:
            self.logger.info(f"New day detected, loading items for {today}")
            self._load_todays_items()
    
    def display(self, force_clear: bool = False) -> None:
        """
        Display of-the-day content.
        
        Args:
            force_clear: If True, clear display before rendering
        """
        if not self.current_items:
            self._display_no_data()
            return
        
        try:
            # Get enabled categories in order
            enabled_categories = [cat for cat in self.category_order 
                                if cat in self.current_items and 
                                self.categories.get(cat, {}).get('enabled', True)]
            
            if not enabled_categories:
                self._display_no_data()
                return
            
            # Rotate categories
            current_time = time.time()
            if current_time - self.last_category_rotation_time >= self.display_rotate_interval:
                self.current_category_index = (self.current_category_index + 1) % len(enabled_categories)
                self.last_category_rotation_time = current_time
                self.rotation_state = 0  # Reset rotation when changing categories
                self.last_rotation_time = current_time
            
            # Get current category
            category_name = enabled_categories[self.current_category_index]
            category_config = self.categories.get(category_name, {})
            item_data = self.current_items.get(category_name, {})
            
            # Rotate display content
            if current_time - self.last_rotation_time >= self.subtitle_rotate_interval:
                self.rotation_state = (self.rotation_state + 1) % 2
                self.last_rotation_time = current_time
            
            # Display based on rotation state
            if self.rotation_state == 0:
                self._display_title(category_config, item_data)
            else:
                self._display_content(category_config, item_data)
        
        except Exception as e:
            self.logger.error(f"Error displaying of-the-day: {e}")
            self._display_error()
    
    def _wrap_text(self, text: str, max_width: int, font, max_lines: int = 10) -> List[str]:
        """Wrap text to fit within max_width, similar to old manager."""
        if not text:
            return [""]
        lines = []
        current_line = []
        words = text.split()
        for word in words:
            test_line = ' '.join(current_line + [word]) if current_line else word
            try:
                text_width = self.display_manager.get_text_width(test_line, font)
            except Exception:
                # Fallback calculation
                if isinstance(font, ImageFont.ImageFont):
                    bbox = font.getbbox(test_line)
                    text_width = bbox[2] - bbox[0]
                else:
                    text_width = len(test_line) * 6
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Word is too long - truncate it
                    truncated = word
                    while len(truncated) > 0:
                        try:
                            test_width = self.display_manager.get_text_width(truncated + "...", font)
                        except Exception:
                            if isinstance(font, ImageFont.ImageFont):
                                bbox = font.getbbox(truncated + "...")
                                test_width = bbox[2] - bbox[0]
                            else:
                                test_width = len(truncated + "...") * 6
                        if test_width <= max_width:
                            lines.append(truncated + "...")
                            break
                        truncated = truncated[:-1]
                    if not truncated:
                        lines.append(word[:10] + "...")
            if len(lines) >= max_lines:
                break
        if current_line and len(lines) < max_lines:
            lines.append(' '.join(current_line))
        return lines[:max_lines]
    
    def _draw_bdf_text(self, draw, font, text: str, x: int, y: int, color: tuple = (255, 255, 255)):
        """Draw text supporting both BDF (FreeType Face) and PIL TTF fonts, similar to old manager."""
        try:
            # If we have a PIL font, use native text rendering
            if isinstance(font, ImageFont.ImageFont):
                draw.text((x, y), text, fill=color, font=font)
                return
            
            # Try to import freetype
            try:
                import freetype
            except ImportError:
                # If freetype not available, fallback to PIL
                draw.text((x, y), text, fill=color, font=ImageFont.load_default())
                return
            
            # For BDF fonts (FreeType Face)
            if isinstance(font, freetype.Face):
                # Compute baseline from font ascender so caller can pass top-left y
                try:
                    ascender_px = font.size.ascender >> 6
                except Exception:
                    ascender_px = 0
                baseline_y = y + ascender_px
                
                # Render BDF glyphs manually
                current_x = x
                for char in text:
                    font.load_char(char)
                    bitmap = font.glyph.bitmap
                    
                    # Get glyph metrics
                    glyph_left = font.glyph.bitmap_left
                    glyph_top = font.glyph.bitmap_top
                    
                    for i in range(bitmap.rows):
                        for j in range(bitmap.width):
                            try:
                                byte_index = i * bitmap.pitch + (j // 8)
                                if byte_index < len(bitmap.buffer):
                                    byte = bitmap.buffer[byte_index]
                                    if byte & (1 << (7 - (j % 8))):
                                        # Calculate actual pixel position
                                        pixel_x = current_x + glyph_left + j
                                        pixel_y = baseline_y - glyph_top + i
                                        # Only draw if within bounds
                                        if (0 <= pixel_x < self.display_manager.width and 
                                            0 <= pixel_y < self.display_manager.height):
                                            draw.point((pixel_x, pixel_y), fill=color)
                            except IndexError:
                                continue
                    current_x += font.glyph.advance.x >> 6
        except Exception as e:
            self.logger.error(f"Error in _draw_bdf_text: {e}", exc_info=True)
            # Fallback to simple text drawing
            try:
                draw.text((x, y), text, fill=color, font=ImageFont.load_default())
            except:
                pass
    
    def _display_title(self, category_config: Dict, item_data: Dict):
        """Display the title/word with subtitle, matching old manager layout."""
        # Clear display first
        self.display_manager.clear()
        
        # Use display_manager's image and draw directly
        draw = self.display_manager.draw
        
        # Load fonts - match old manager font usage
        try:
            title_font = ImageFont.truetype('assets/fonts/PressStart2P-Regular.ttf', 8)
        except:
            title_font = self.display_manager.small_font if hasattr(self.display_manager, 'small_font') else ImageFont.load_default()
        
        try:
            body_font = ImageFont.truetype('assets/fonts/4x6-font.ttf', 6)
        except:
            body_font = self.display_manager.extra_small_font if hasattr(self.display_manager, 'extra_small_font') else ImageFont.load_default()
        
        # Get font heights
        try:
            title_height = self.display_manager.get_font_height(title_font)
        except Exception:
            title_height = 8
        try:
            body_height = self.display_manager.get_font_height(body_font)
        except Exception:
            body_height = 8
        
        # Layout matching old manager: margin_top = 8
        margin_top = 8
        margin_bottom = 1
        underline_space = 1
        
        # Get title/word (JSON uses "title" not "word")
        title = item_data.get('title', item_data.get('word', 'N/A'))
        self.logger.debug(f"Displaying title: {title}")
        
        # Get subtitle (JSON uses "subtitle")
        subtitle = item_data.get('subtitle', item_data.get('pronunciation', item_data.get('type', '')))
        self.logger.debug(f"Displaying subtitle: {subtitle}")
        
        # Calculate title width for centering
        try:
            title_width = self.display_manager.get_text_width(title, title_font)
        except Exception:
            if isinstance(title_font, ImageFont.ImageFont):
                bbox = title_font.getbbox(title)
                title_width = bbox[2] - bbox[0]
            else:
                title_width = len(title) * 6
        
        # Center the title horizontally
        title_x = (self.display_manager.width - title_width) // 2
        title_y = margin_top
        
        # Draw title
        self._draw_bdf_text(draw, title_font, title, title_x, title_y, color=self.title_color)
        
        # Draw underline below title (like old manager)
        underline_y = title_y + title_height + 1
        underline_x_start = title_x
        underline_x_end = title_x + title_width
        draw.line([(underline_x_start, underline_y), (underline_x_end, underline_y)], 
                 fill=self.title_color, width=1)
        
        # Draw subtitle below underline (centered, like old manager)
        if subtitle:
            # Wrap subtitle text if needed
            available_width = self.display_manager.width - 4
            wrapped_subtitle_lines = self._wrap_text(subtitle, available_width, body_font, max_lines=3)
            actual_subtitle_lines = [line for line in wrapped_subtitle_lines if line.strip()]
            
            if actual_subtitle_lines:
                # Calculate spacing - similar to old manager's dynamic spacing
                total_subtitle_height = len(actual_subtitle_lines) * body_height
                available_space = self.display_manager.height - underline_y - margin_bottom
                space_after_underline = max(2, (available_space - total_subtitle_height) // 2)
                
                subtitle_start_y = underline_y + space_after_underline + underline_space
                current_y = subtitle_start_y
                
                for line in actual_subtitle_lines:
                    if line.strip():
                        # Center each line of subtitle
                        try:
                            line_width = self.display_manager.get_text_width(line, body_font)
                        except Exception:
                            if isinstance(body_font, ImageFont.ImageFont):
                                bbox = body_font.getbbox(line)
                                line_width = bbox[2] - bbox[0]
                            else:
                                line_width = len(line) * 6
                        line_x = (self.display_manager.width - line_width) // 2
                        
                        self._draw_bdf_text(draw, body_font, line, line_x, current_y, color=self.subtitle_color)
                        current_y += body_height + 1
        
        self.display_manager.update_display()
    
    def _display_content(self, category_config: Dict, item_data: Dict):
        """Display the definition/content, matching old manager layout."""
        # Clear display first
        self.display_manager.clear()
        
        # Use display_manager's image and draw directly
        draw = self.display_manager.draw
        
        # Load fonts - match old manager
        try:
            title_font = ImageFont.truetype('assets/fonts/PressStart2P-Regular.ttf', 8)
        except:
            title_font = self.display_manager.small_font if hasattr(self.display_manager, 'small_font') else ImageFont.load_default()
        
        try:
            body_font = ImageFont.truetype('assets/fonts/4x6-font.ttf', 6)
        except:
            body_font = self.display_manager.extra_small_font if hasattr(self.display_manager, 'extra_small_font') else ImageFont.load_default()
        
        # Get font heights
        try:
            title_height = self.display_manager.get_font_height(title_font)
        except Exception:
            title_height = 8
        try:
            body_height = self.display_manager.get_font_height(body_font)
        except Exception:
            body_height = 8
        
        # Layout matching old manager: margin_top = 8
        margin_top = 8
        margin_bottom = 1
        underline_space = 1
        
        # Get title/word (JSON uses "title")
        title = item_data.get('title', item_data.get('word', 'N/A'))
        self.logger.debug(f"Displaying content for title: {title}")
        
        # Get description (JSON uses "description")
        description = item_data.get('description', item_data.get('definition', item_data.get('content', item_data.get('text', 'No content'))))
        self.logger.debug(f"Displaying description: {description[:50]}...")
        
        # Calculate title width for centering (for underline placement)
        try:
            title_width = self.display_manager.get_text_width(title, title_font)
        except Exception:
            if isinstance(title_font, ImageFont.ImageFont):
                bbox = title_font.getbbox(title)
                title_width = bbox[2] - bbox[0]
            else:
                title_width = len(title) * 6
        
        # Center the title horizontally (same position as in _display_title)
        title_x = (self.display_manager.width - title_width) // 2
        title_y = margin_top
        
        # Draw title (same as title screen for consistency)
        self._draw_bdf_text(draw, title_font, title, title_x, title_y, color=self.title_color)
        
        # Draw underline below title (same as title screen)
        underline_y = title_y + title_height + 1
        underline_x_start = title_x
        underline_x_end = title_x + title_width
        draw.line([(underline_x_start, underline_y), (underline_x_end, underline_y)], 
                 fill=self.title_color, width=1)
        
        # Wrap description text
        available_width = self.display_manager.width - 4
        max_lines = 10
        wrapped_lines = self._wrap_text(description, available_width, body_font, max_lines=max_lines)
        actual_body_lines = [line for line in wrapped_lines if line.strip()]
        
        if actual_body_lines:
            # Calculate dynamic spacing - similar to old manager
            num_body_lines = len(actual_body_lines)
            body_content_height = num_body_lines * body_height
            available_space = self.display_manager.height - underline_y - margin_bottom
            
            if body_content_height < available_space:
                # Distribute extra space: some after underline, rest between lines
                extra_space = available_space - body_content_height
                space_after_underline = max(2, int(extra_space * 0.3))
                space_between_lines = max(1, int(extra_space * 0.7 / max(1, num_body_lines - 1))) if num_body_lines > 1 else 0
            else:
                # Tight spacing
                space_after_underline = 4
                space_between_lines = 1
            
            # Draw body text with dynamic spacing
            body_start_y = underline_y + space_after_underline + underline_space + 1  # +1 to match old manager's shift
            current_y = body_start_y
            
            for i, line in enumerate(actual_body_lines):
                if line.strip():
                    # Center each line of body text (like old manager)
                    try:
                        line_width = self.display_manager.get_text_width(line, body_font)
                    except Exception:
                        if isinstance(body_font, ImageFont.ImageFont):
                            bbox = body_font.getbbox(line)
                            line_width = bbox[2] - bbox[0]
                        else:
                            line_width = len(line) * 6
                    line_x = (self.display_manager.width - line_width) // 2
                    
                    self._draw_bdf_text(draw, body_font, line, line_x, current_y, color=self.subtitle_color)
                    
                    # Move to next line position
                    if i < len(actual_body_lines) - 1:  # Not the last line
                        current_y += body_height + space_between_lines
        
        self.display_manager.update_display()
    
    def _display_no_data(self):
        """Display message when no data is available."""
        img = Image.new('RGB', (self.display_manager.width,
                               self.display_manager.height),
                       self.background_color)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('assets/fonts/4x6-font.ttf', 8)
        except:
            font = ImageFont.load_default()
        
        draw.text((5, 12), "No Data", font=font, fill=(200, 200, 200))
        
        self.display_manager.image = img.copy()
        self.display_manager.update_display()
    
    def _display_error(self):
        """Display error message."""
        img = Image.new('RGB', (self.display_manager.width,
                               self.display_manager.height),
                       self.background_color)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('assets/fonts/4x6-font.ttf', 8)
        except:
            font = ImageFont.load_default()
        
        draw.text((5, 12), "Error", font=font, fill=(255, 0, 0))
        
        self.display_manager.image = img.copy()
        self.display_manager.update_display()
    
    def get_display_duration(self) -> float:
        """Get display duration from config."""
        return self.config.get('display_duration', 40.0)
    
    def get_info(self) -> Dict[str, Any]:
        """Return plugin info for web UI."""
        info = super().get_info()
        info.update({
            'current_day': str(self.current_day) if self.current_day else None,
            'categories_loaded': len(self.current_items),
            'enabled_categories': [cat for cat in self.category_order 
                                  if self.categories.get(cat, {}).get('enabled', True)]
        })
        return info
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.current_items = {}
        self.data_files = {}
        self.logger.info("Of The Day plugin cleaned up")

