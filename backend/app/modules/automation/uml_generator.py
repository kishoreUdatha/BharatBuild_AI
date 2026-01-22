"""
UML DIAGRAM GENERATOR
=====================
Generates UML diagrams for academic documentation.

Supported Diagrams:
1. Use Case Diagram
2. Class Diagram
3. Sequence Diagram
4. Activity Diagram
5. ER Diagram
6. Component Diagram
7. Deployment Diagram
8. State Diagram
9. Data Flow Diagram (DFD)

Output: PNG images for Word/PPT embedding
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os
import tempfile
from io import BytesIO

from app.core.logging_config import logger
from app.core.config import settings

# Try to import diagram libraries
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available for diagram generation")


class UMLGenerator:
    """
    UML Diagram Generator using PIL/Pillow

    Creates professional UML diagrams as PNG images
    """

    # Colors
    COLORS = {
        'primary': (0, 51, 102),      # Dark blue
        'secondary': (0, 102, 153),   # Teal
        'accent': (255, 153, 0),      # Orange
        'background': (255, 255, 255), # White
        'border': (100, 100, 100),    # Gray
        'text': (51, 51, 51),         # Dark gray
        'actor': (0, 102, 153),       # Teal for actors
        'usecase': (240, 248, 255),   # Light blue for use cases
        'class_header': (0, 51, 102), # Dark blue for class headers
        'arrow': (80, 80, 80),        # Dark gray for arrows
        'lifeline': (150, 150, 150),  # Light gray for lifelines
    }

    # Standard dimensions
    WIDTH = 1200
    HEIGHT = 800
    PADDING = 50

    def __init__(self):
        self.default_output_dir = settings.DIAGRAMS_DIR
        self.default_output_dir.mkdir(parents=True, exist_ok=True)

        # Try to load font
        self.font = None
        self.font_bold = None
        self.font_small = None

        if PIL_AVAILABLE:
            try:
                self.font = ImageFont.truetype("arial.ttf", 14)
                self.font_bold = ImageFont.truetype("arialbd.ttf", 16)
                self.font_small = ImageFont.truetype("arial.ttf", 12)
            except (IOError, OSError) as e:
                logger.debug(f"Could not load custom fonts, using default: {e}")
                self.font = ImageFont.load_default()
                self.font_bold = self.font
                self.font_small = self.font

    def get_output_dir(self, project_id: str = None, user_id: str = None) -> 'Path':
        """Get output directory - user and project-specific for proper isolation"""
        if project_id:
            return settings.get_project_diagrams_dir(project_id, user_id)
        return self.default_output_dir

    def generate_use_case_diagram(
        self,
        project_name: str,
        actors: List[str],
        use_cases: List[str],
        relationships: List[Dict] = None,
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate Use Case Diagram

        Args:
            project_name: Name of the system
            actors: List of actor names
            use_cases: List of use case names
            relationships: List of {actor, use_case, type} relationships

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("Use Case Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        # Draw system boundary (rectangle)
        system_x = 300
        system_y = 80
        system_width = 600
        system_height = 620

        draw.rectangle(
            [system_x, system_y, system_x + system_width, system_y + system_height],
            outline=self.COLORS['border'],
            width=2
        )

        # System name
        draw.text(
            (system_x + system_width // 2, system_y + 20),
            project_name,
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        # Draw actors on the left
        actor_spacing = min(150, (system_height - 100) // max(len(actors), 1))
        actor_positions = {}

        for i, actor in enumerate(actors[:5]):  # Max 5 actors
            y = system_y + 80 + i * actor_spacing
            self._draw_actor(draw, 120, y, actor)
            actor_positions[actor] = (120, y)

        # Draw use cases inside system
        usecase_spacing = min(100, (system_height - 120) // max(len(use_cases), 1))
        usecase_positions = {}

        for i, uc in enumerate(use_cases[:8]):  # Max 8 use cases
            x = system_x + system_width // 2
            y = system_y + 100 + i * usecase_spacing
            self._draw_use_case(draw, x, y, uc)
            usecase_positions[uc] = (x, y)

        # Draw relationships (lines from actors to use cases)
        if relationships:
            for rel in relationships:
                actor = rel.get('actor')
                uc = rel.get('use_case')
                if actor in actor_positions and uc in usecase_positions:
                    ax, ay = actor_positions[actor]
                    ux, uy = usecase_positions[uc]
                    draw.line([(ax + 40, ay), (ux - 80, uy)], fill=self.COLORS['arrow'], width=1)
        else:
            # Default: connect all actors to all use cases
            for actor, (ax, ay) in actor_positions.items():
                for uc, (ux, uy) in usecase_positions.items():
                    draw.line([(ax + 40, ay), (ux - 80, uy)], fill=self.COLORS['arrow'], width=1)

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            "Use Case Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        # Save
        filename = f"use_case_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _draw_actor(self, draw, x, y, name):
        """Draw stick figure actor"""
        # Head
        draw.ellipse([x - 10, y - 40, x + 10, y - 20], outline=self.COLORS['actor'], width=2)
        # Body
        draw.line([(x, y - 20), (x, y + 10)], fill=self.COLORS['actor'], width=2)
        # Arms
        draw.line([(x - 20, y - 10), (x + 20, y - 10)], fill=self.COLORS['actor'], width=2)
        # Legs
        draw.line([(x, y + 10), (x - 15, y + 35)], fill=self.COLORS['actor'], width=2)
        draw.line([(x, y + 10), (x + 15, y + 35)], fill=self.COLORS['actor'], width=2)
        # Name
        draw.text((x, y + 50), name, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

    def _draw_use_case(self, draw, x, y, name):
        """Draw use case ellipse"""
        # Truncate long names
        display_name = name[:25] + "..." if len(name) > 25 else name

        # Ellipse
        draw.ellipse(
            [x - 80, y - 25, x + 80, y + 25],
            fill=self.COLORS['usecase'],
            outline=self.COLORS['border'],
            width=2
        )
        # Text
        draw.text((x, y), display_name, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

    def generate_class_diagram(
        self,
        classes: List[Dict],
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate Class Diagram

        Args:
            classes: List of {name, attributes, methods, relationships} dicts

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("Class Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        # Calculate positions
        num_classes = len(classes)
        cols = min(3, num_classes)
        rows = (num_classes + cols - 1) // cols

        class_width = 250
        class_height = 180

        x_spacing = (self.WIDTH - 100) // cols
        y_spacing = (self.HEIGHT - 100) // max(rows, 1)

        class_positions = {}

        for i, cls in enumerate(classes[:9]):  # Max 9 classes
            col = i % cols
            row = i // cols

            x = 80 + col * x_spacing
            y = 80 + row * y_spacing

            self._draw_class_box(draw, x, y, class_width, class_height, cls)
            class_positions[cls.get('name', f'Class{i}')] = (x + class_width // 2, y + class_height // 2)

        # Draw relationships
        for cls in classes:
            cls_name = cls.get('name', '')
            relations = cls.get('relationships', [])

            if cls_name in class_positions:
                for rel in relations:
                    target = rel.get('target', '')
                    rel_type = rel.get('type', 'association')

                    if target in class_positions:
                        self._draw_relationship(
                            draw,
                            class_positions[cls_name],
                            class_positions[target],
                            rel_type
                        )

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            "Class Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"class_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _draw_class_box(self, draw, x, y, width, height, cls_data):
        """Draw a class box with name, attributes, methods"""
        name = cls_data.get('name', 'ClassName')
        attributes = cls_data.get('attributes', [])[:5]
        methods = cls_data.get('methods', [])[:5]

        header_height = 30
        attr_height = (height - header_height) // 2

        # Class name section (header)
        draw.rectangle(
            [x, y, x + width, y + header_height],
            fill=self.COLORS['class_header'],
            outline=self.COLORS['border'],
            width=2
        )
        draw.text(
            (x + width // 2, y + header_height // 2),
            name,
            fill=(255, 255, 255),
            font=self.font_bold,
            anchor="mm"
        )

        # Attributes section
        draw.rectangle(
            [x, y + header_height, x + width, y + header_height + attr_height],
            fill=self.COLORS['background'],
            outline=self.COLORS['border'],
            width=2
        )

        for i, attr in enumerate(attributes):
            attr_text = f"- {attr}" if not attr.startswith(('+', '-', '#')) else attr
            draw.text(
                (x + 10, y + header_height + 8 + i * 18),
                attr_text[:30],
                fill=self.COLORS['text'],
                font=self.font_small
            )

        # Methods section
        draw.rectangle(
            [x, y + header_height + attr_height, x + width, y + height],
            fill=self.COLORS['background'],
            outline=self.COLORS['border'],
            width=2
        )

        for i, method in enumerate(methods):
            method_text = f"+ {method}()" if not method.startswith(('+', '-', '#')) else method
            draw.text(
                (x + 10, y + header_height + attr_height + 8 + i * 18),
                method_text[:30],
                fill=self.COLORS['text'],
                font=self.font_small
            )

    def _draw_relationship(self, draw, start, end, rel_type):
        """Draw relationship line between classes"""
        draw.line([start, end], fill=self.COLORS['arrow'], width=2)

        # Add arrow head or diamond based on type
        if rel_type == 'inheritance':
            # Triangle arrow
            pass
        elif rel_type == 'composition':
            # Filled diamond
            pass
        elif rel_type == 'aggregation':
            # Empty diamond
            pass

    def generate_sequence_diagram(
        self,
        participants: List[str],
        messages: List[Dict],
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate Sequence Diagram

        Args:
            participants: List of participant names
            messages: List of {from, to, message, type} dicts

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("Sequence Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        # Draw participants at top
        num_participants = min(len(participants), 6)
        spacing = (self.WIDTH - 100) // max(num_participants, 1)

        participant_x = {}

        for i, p in enumerate(participants[:6]):
            x = 80 + i * spacing

            # Participant box
            draw.rectangle(
                [x - 50, 60, x + 50, 90],
                fill=self.COLORS['secondary'],
                outline=self.COLORS['border'],
                width=2
            )
            draw.text((x, 75), p[:12], fill=(255, 255, 255), font=self.font_small, anchor="mm")

            # Lifeline
            draw.line([(x, 90), (x, self.HEIGHT - 50)], fill=self.COLORS['lifeline'], width=1)

            participant_x[p] = x

        # Draw messages
        y_offset = 120
        message_spacing = 50

        for i, msg in enumerate(messages[:12]):  # Max 12 messages
            from_p = msg.get('from', participants[0] if participants else '')
            to_p = msg.get('to', participants[-1] if participants else '')
            message = msg.get('message', 'message')
            msg_type = msg.get('type', 'sync')

            if from_p in participant_x and to_p in participant_x:
                from_x = participant_x[from_p]
                to_x = participant_x[to_p]
                y = y_offset + i * message_spacing

                # Arrow line
                if msg_type == 'return':
                    # Dashed line
                    self._draw_dashed_line(draw, from_x, y, to_x, y)
                else:
                    draw.line([(from_x, y), (to_x, y)], fill=self.COLORS['arrow'], width=2)

                # Arrow head
                if to_x > from_x:
                    draw.polygon([(to_x, y), (to_x - 10, y - 5), (to_x - 10, y + 5)], fill=self.COLORS['arrow'])
                else:
                    draw.polygon([(to_x, y), (to_x + 10, y - 5), (to_x + 10, y + 5)], fill=self.COLORS['arrow'])

                # Message text
                mid_x = (from_x + to_x) // 2
                draw.text((mid_x, y - 12), message[:30], fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Title
        draw.text(
            (self.WIDTH // 2, 25),
            "Sequence Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"sequence_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _draw_dashed_line(self, draw, x1, y1, x2, y2, dash_length=10):
        """Draw a dashed line"""
        total_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        dashes = int(total_length / (dash_length * 2))

        for i in range(dashes):
            start_ratio = (i * 2 * dash_length) / total_length
            end_ratio = ((i * 2 + 1) * dash_length) / total_length

            start_x = x1 + (x2 - x1) * start_ratio
            start_y = y1 + (y2 - y1) * start_ratio
            end_x = x1 + (x2 - x1) * end_ratio
            end_y = y1 + (y2 - y1) * end_ratio

            draw.line([(start_x, start_y), (end_x, end_y)], fill=self.COLORS['arrow'], width=1)

    def generate_activity_diagram(
        self,
        activities: List[str],
        decisions: List[Dict] = None,
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate Activity Diagram

        Args:
            activities: List of activity names in order
            decisions: List of {condition, yes_branch, no_branch} dicts

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("Activity Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        # Start node
        start_y = 80
        center_x = self.WIDTH // 2

        draw.ellipse(
            [center_x - 15, start_y - 15, center_x + 15, start_y + 15],
            fill=self.COLORS['primary']
        )

        # Draw activities
        y = start_y + 60
        spacing = 80

        for i, activity in enumerate(activities[:8]):
            # Activity box (rounded rectangle)
            box_width = 200
            box_height = 40

            draw.rounded_rectangle(
                [center_x - box_width // 2, y, center_x + box_width // 2, y + box_height],
                radius=10,
                fill=self.COLORS['usecase'],
                outline=self.COLORS['border'],
                width=2
            )
            draw.text(
                (center_x, y + box_height // 2),
                activity[:25],
                fill=self.COLORS['text'],
                font=self.font_small,
                anchor="mm"
            )

            # Arrow to next
            if i < len(activities) - 1:
                arrow_y = y + box_height + 10
                draw.line([(center_x, arrow_y), (center_x, arrow_y + 30)], fill=self.COLORS['arrow'], width=2)
                draw.polygon(
                    [(center_x, arrow_y + 30), (center_x - 5, arrow_y + 20), (center_x + 5, arrow_y + 20)],
                    fill=self.COLORS['arrow']
                )

            y += spacing

        # End node
        end_y = y + 20
        draw.ellipse(
            [center_x - 15, end_y - 15, center_x + 15, end_y + 15],
            outline=self.COLORS['primary'],
            width=3
        )
        draw.ellipse(
            [center_x - 10, end_y - 10, center_x + 10, end_y + 10],
            fill=self.COLORS['primary']
        )

        # Title
        draw.text(
            (self.WIDTH // 2, 25),
            "Activity Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"activity_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def generate_er_diagram(
        self,
        entities: List[Dict],
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate ER Diagram with columns, types, and relationships

        Args:
            entities: List of dicts with:
                - name: Table name
                - columns: List of {name, type} dicts
                - attributes: List of column names (fallback)
                - primary_key: Primary key column name
                - relationships: List of {column, references, type} dicts

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("ER Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        # Calculate positions in grid
        num_entities = min(len(entities), 6)
        cols = min(3, num_entities)
        rows = (num_entities + cols - 1) // cols

        entity_width = 250
        entity_height = 180

        x_spacing = (self.WIDTH - 100) // max(cols, 1)
        y_spacing = (self.HEIGHT - 120) // max(rows, 1)

        entity_positions = {}
        entity_fks = {}  # Track foreign keys for relationship drawing

        for i, entity in enumerate(entities[:6]):
            col = i % cols
            row = i // cols

            x = 80 + col * x_spacing
            y = 80 + row * y_spacing

            name = entity.get('name', f'Entity{i}')
            # Use columns if available, fall back to attributes
            columns = entity.get('columns', [])
            if not columns:
                # Convert attributes list to column dicts
                attrs = entity.get('attributes', [])[:6]
                columns = [{'name': a, 'type': 'String'} for a in attrs]
            columns = columns[:7]  # Limit to 7 columns

            pk = entity.get('primary_key', 'id')
            relationships = entity.get('relationships', [])

            # Store FK info for relationship drawing
            for rel in relationships:
                ref_table = rel.get('references', '')
                if ref_table:
                    if name not in entity_fks:
                        entity_fks[name] = []
                    entity_fks[name].append(ref_table)

            # Calculate dynamic height based on columns
            attr_height = max(len(columns) * 18 + 20, 80)
            entity_height = 35 + attr_height

            # Entity header box
            draw.rectangle(
                [x, y, x + entity_width, y + 35],
                fill=self.COLORS['class_header'],
                outline=self.COLORS['border'],
                width=2
            )
            draw.text(
                (x + entity_width // 2, y + 17),
                name.upper(),
                fill=(255, 255, 255),
                font=self.font_bold,
                anchor="mm"
            )

            # Attributes box
            draw.rectangle(
                [x, y + 35, x + entity_width, y + entity_height],
                fill=self.COLORS['background'],
                outline=self.COLORS['border'],
                width=2
            )

            # Draw columns with types
            for j, col in enumerate(columns):
                col_name = col.get('name', col) if isinstance(col, dict) else str(col)
                col_type = col.get('type', '') if isinstance(col, dict) else ''

                # Check if this is a PK or FK
                is_pk = col_name.lower() == pk.lower() or col_name.lower() == 'id'
                is_fk = col_name.lower().endswith('_id') and col_name.lower() != 'id'

                if is_pk:
                    prefix = "PK "
                    color = (0, 100, 0)  # Dark green for PK
                elif is_fk:
                    prefix = "FK "
                    color = (0, 0, 139)  # Dark blue for FK
                else:
                    prefix = "   "
                    color = self.COLORS['text']

                # Format: column_name : type
                type_str = f" : {col_type[:12]}" if col_type else ""
                draw.text(
                    (x + 10, y + 45 + j * 18),
                    f"{prefix}{col_name[:15]}{type_str}",
                    fill=color,
                    font=self.font_small
                )

            entity_positions[name] = {
                'center': (x + entity_width // 2, y + entity_height // 2),
                'left': (x, y + entity_height // 2),
                'right': (x + entity_width, y + entity_height // 2),
                'top': (x + entity_width // 2, y),
                'bottom': (x + entity_width // 2, y + entity_height)
            }

        # Draw actual relationships based on foreign keys
        drawn_rels = set()
        for entity_name, fk_targets in entity_fks.items():
            if entity_name not in entity_positions:
                continue
            for target in fk_targets:
                # Find matching target entity (case-insensitive)
                target_key = None
                for ent_name in entity_positions.keys():
                    if ent_name.lower() == target.lower():
                        target_key = ent_name
                        break

                if target_key and (entity_name, target_key) not in drawn_rels:
                    p1 = entity_positions[entity_name]['right']
                    p2 = entity_positions[target_key]['left']

                    # Draw relationship line
                    draw.line([p1, p2], fill=self.COLORS['arrow'], width=2)

                    # Draw crow's foot (many) on FK side
                    self._draw_crow_foot(draw, p1, 'left')

                    # Draw single line (one) on PK side
                    self._draw_one_marker(draw, p2, 'right')

                    drawn_rels.add((entity_name, target_key))
                    drawn_rels.add((target_key, entity_name))

        # If no explicit relationships, draw based on naming conventions
        if not entity_fks:
            entity_names = list(entity_positions.keys())
            for i, e1 in enumerate(entity_names):
                for e2 in entity_names[i+1:]:
                    # Check if e1 might reference e2 (e.g., user_id in Order -> User)
                    if e2.lower() + '_id' in str(entities[i].get('columns', [])).lower():
                        p1 = entity_positions[e1]['center']
                        p2 = entity_positions[e2]['center']
                        draw.line([p1, p2], fill=self.COLORS['arrow'], width=2)

        # Title
        draw.text(
            (self.WIDTH // 2, 25),
            "Entity Relationship Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"er_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _draw_crow_foot(self, draw, point, direction='left'):
        """Draw crow's foot notation (many) for ER relationships"""
        x, y = point
        size = 10

        if direction == 'left':
            # Draw three lines from point spreading left
            draw.line([(x, y), (x - size, y - size)], fill=self.COLORS['arrow'], width=2)
            draw.line([(x, y), (x - size, y)], fill=self.COLORS['arrow'], width=2)
            draw.line([(x, y), (x - size, y + size)], fill=self.COLORS['arrow'], width=2)
        else:
            # Draw three lines from point spreading right
            draw.line([(x, y), (x + size, y - size)], fill=self.COLORS['arrow'], width=2)
            draw.line([(x, y), (x + size, y)], fill=self.COLORS['arrow'], width=2)
            draw.line([(x, y), (x + size, y + size)], fill=self.COLORS['arrow'], width=2)

    def _draw_one_marker(self, draw, point, direction='right'):
        """Draw one-side marker (single line) for ER relationships"""
        x, y = point
        size = 10

        if direction == 'right':
            draw.line([(x, y - size), (x, y + size)], fill=self.COLORS['arrow'], width=2)
        else:
            draw.line([(x, y - size), (x, y + size)], fill=self.COLORS['arrow'], width=2)

    def generate_dfd(
        self,
        level: int,
        processes: List[str],
        data_stores: List[str],
        external_entities: List[str],
        data_flows: List[Dict],
        project_id: str = None,
        user_id: str = None
    ) -> str:
        """
        Generate Data Flow Diagram

        Args:
            level: DFD level (0, 1, 2)
            processes: List of process names
            data_stores: List of data store names
            external_entities: List of external entity names
            data_flows: List of {from, to, data} dicts

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder(f"DFD Level {level}")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        positions = {}

        # Draw external entities (rectangles) on left and right
        for i, entity in enumerate(external_entities[:4]):
            if i < 2:
                x, y = 80, 150 + i * 200
            else:
                x, y = self.WIDTH - 180, 150 + (i - 2) * 200

            draw.rectangle(
                [x, y, x + 100, y + 50],
                fill=self.COLORS['usecase'],
                outline=self.COLORS['border'],
                width=2
            )
            draw.text((x + 50, y + 25), entity[:12], fill=self.COLORS['text'], font=self.font_small, anchor="mm")
            positions[entity] = (x + 50, y + 25)

        # Draw processes (circles) in center
        center_x = self.WIDTH // 2
        for i, process in enumerate(processes[:4]):
            y = 120 + i * 150

            draw.ellipse(
                [center_x - 50, y, center_x + 50, y + 80],
                fill=self.COLORS['secondary'],
                outline=self.COLORS['border'],
                width=2
            )
            draw.text((center_x, y + 40), process[:15], fill=(255, 255, 255), font=self.font_small, anchor="mm")
            positions[process] = (center_x, y + 40)

        # Draw data stores (open rectangles) at bottom
        for i, store in enumerate(data_stores[:3]):
            x = 200 + i * 300
            y = self.HEIGHT - 100

            # Open rectangle (two parallel lines)
            draw.line([(x, y), (x + 150, y)], fill=self.COLORS['border'], width=2)
            draw.line([(x, y + 40), (x + 150, y + 40)], fill=self.COLORS['border'], width=2)
            draw.text((x + 75, y + 20), store[:15], fill=self.COLORS['text'], font=self.font_small, anchor="mm")
            positions[store] = (x + 75, y + 20)

        # Draw data flows
        for flow in data_flows[:10]:
            from_elem = flow.get('from', '')
            to_elem = flow.get('to', '')
            data = flow.get('data', '')

            if from_elem in positions and to_elem in positions:
                p1 = positions[from_elem]
                p2 = positions[to_elem]

                # Draw arrow
                draw.line([p1, p2], fill=self.COLORS['arrow'], width=2)

                # Arrow head
                mid_x = (p1[0] + p2[0]) // 2
                mid_y = (p1[1] + p2[1]) // 2
                draw.text((mid_x, mid_y - 10), data[:15], fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            f"Data Flow Diagram - Level {level}",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"dfd_level{level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def generate_system_architecture_diagram(self, project_data: Dict, project_id: str = None, user_id: str = None) -> str:
        """
        Generate System Architecture Diagram - FULLY DYNAMIC

        Args:
            project_data: Project data with technologies and components

        Returns:
            Path to generated PNG
        """
        if not PIL_AVAILABLE:
            return self._generate_placeholder("System Architecture Diagram")

        img = Image.new('RGB', (self.WIDTH, self.HEIGHT), self.COLORS['background'])
        draw = ImageDraw.Draw(img)

        project_name = project_data.get('project_name', 'System')
        technologies = project_data.get('technologies', {})
        features = project_data.get('features', [])
        features_str = ' '.join(str(f).lower() for f in features)

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            f"{project_name} - System Architecture",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        # ===== PRESENTATION LAYER (DYNAMIC) =====
        draw.rounded_rectangle(
            [100, 80, 500, 180],
            radius=10,
            fill=(173, 216, 230),  # Light blue
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 100), "Presentation Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        frontend = technologies.get('frontend', [])
        if isinstance(frontend, str):
            frontend = [frontend]
        if not frontend:
            # Infer from project type
            frontend = self._infer_frontend_tech(project_data)
        draw.text((300, 140), ", ".join(frontend[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # ===== CLIENT DEVICES (DYNAMIC) =====
        draw.rounded_rectangle([550, 80, 750, 180], radius=10, fill=(255, 228, 181), outline=self.COLORS['border'], width=2)
        draw.text((650, 110), "Client Devices", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        client_devices = self._detect_client_devices(project_data)
        draw.text((650, 150), client_devices, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from client to presentation
        draw.line([(550, 130), (500, 130)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(500, 130), (510, 125), (510, 135)], fill=self.COLORS['arrow'])

        # ===== BUSINESS LOGIC LAYER (DYNAMIC) =====
        draw.rounded_rectangle(
            [100, 220, 500, 340],
            radius=10,
            fill=(144, 238, 144),  # Light green
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 240), "Business Logic Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        backend = technologies.get('backend', [])
        if isinstance(backend, str):
            backend = [backend]
        if not backend:
            backend = self._infer_backend_tech(project_data)
        draw.text((300, 280), ", ".join(backend[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Detect API type dynamically
        api_type = self._detect_api_type(project_data)
        draw.text((300, 310), api_type, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from presentation to business
        draw.line([(300, 180), (300, 220)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(300, 220), (295, 210), (305, 210)], fill=self.COLORS['arrow'])

        # ===== EXTERNAL SERVICES (DYNAMIC) =====
        draw.rounded_rectangle([550, 220, 750, 340], radius=10, fill=(255, 218, 185), outline=self.COLORS['border'], width=2)
        draw.text((650, 250), "External Services", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        external_services = self._detect_external_services(project_data)
        for i, service in enumerate(external_services[:3]):
            draw.text((650, 280 + i * 20), f"• {service}", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from business to external
        draw.line([(500, 280), (550, 280)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(550, 280), (540, 275), (540, 285)], fill=self.COLORS['arrow'])

        # ===== DATA LAYER (DYNAMIC) =====
        draw.rounded_rectangle(
            [100, 380, 500, 500],
            radius=10,
            fill=(221, 160, 221),  # Light purple
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 400), "Data Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        database = technologies.get('database', [])
        if isinstance(database, str):
            database = [database]
        if not database:
            database = self._infer_database_tech(project_data)
        draw.text((300, 440), ", ".join(database[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Detect ORM dynamically
        orm = self._detect_orm(project_data)
        draw.text((300, 470), orm, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from business to data
        draw.line([(300, 340), (300, 380)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(300, 380), (295, 370), (305, 370)], fill=self.COLORS['arrow'])

        # ===== CACHE/STORAGE (DYNAMIC) =====
        draw.rounded_rectangle([550, 380, 750, 500], radius=10, fill=(255, 182, 193), outline=self.COLORS['border'], width=2)
        draw.text((650, 410), "Cache / Storage", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        cache_storage = self._detect_cache_storage(project_data)
        for i, item in enumerate(cache_storage[:2]):
            draw.text((650, 445 + i * 25), item, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from data to cache
        draw.line([(500, 440), (550, 440)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(550, 440), (540, 435), (540, 445)], fill=self.COLORS['arrow'])

        # ===== INFRASTRUCTURE LAYER (DYNAMIC) =====
        draw.rounded_rectangle(
            [100, 540, 750, 620],
            radius=10,
            fill=(211, 211, 211),  # Light gray
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((425, 560), "Infrastructure Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        infrastructure = self._detect_infrastructure(project_data)
        draw.text((425, 590), infrastructure, fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # ===== SECURITY LAYER (DYNAMIC) =====
        draw.rounded_rectangle([800, 200, 1100, 400], radius=10, fill=(255, 255, 224), outline=self.COLORS['border'], width=2)
        draw.text((950, 230), "Security Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        security_features = self._detect_security_features(project_data)
        for i, feature in enumerate(security_features[:5]):
            draw.text((950, 265 + i * 25), f"• {feature}", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        filename = f"system_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id, user_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _infer_frontend_tech(self, project_data: Dict) -> List[str]:
        """Infer frontend technologies from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))
        project_name = project_data.get('project_name', '').lower()

        frontend = []

        # Check for specific frameworks in features or name
        if 'react' in features_str or 'react' in project_name:
            frontend.append('React')
        if 'vue' in features_str or 'vue' in project_name:
            frontend.append('Vue.js')
        if 'angular' in features_str or 'angular' in project_name:
            frontend.append('Angular')
        if 'next' in features_str or 'next' in project_name:
            frontend.append('Next.js')
        if 'svelte' in features_str:
            frontend.append('Svelte')

        # Check for mobile
        if 'mobile' in features_str or 'app' in features_str:
            if 'react native' in features_str:
                frontend.append('React Native')
            elif 'flutter' in features_str:
                frontend.append('Flutter')

        # Default based on project type
        if not frontend:
            if 'api' in features_str and 'web' not in features_str:
                frontend = ['API Only']
            else:
                frontend = ['Web UI', 'HTML/CSS']

        return frontend[:3]

    def _infer_backend_tech(self, project_data: Dict) -> List[str]:
        """Infer backend technologies from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))
        project_name = project_data.get('project_name', '').lower()

        backend = []

        if 'python' in features_str or 'django' in features_str or 'flask' in features_str or 'fastapi' in features_str:
            if 'fastapi' in features_str:
                backend.append('FastAPI')
            elif 'django' in features_str:
                backend.append('Django')
            elif 'flask' in features_str:
                backend.append('Flask')
            else:
                backend.append('Python')

        if 'node' in features_str or 'express' in features_str or 'nest' in features_str:
            if 'nest' in features_str:
                backend.append('NestJS')
            else:
                backend.append('Node.js')

        if 'java' in features_str or 'spring' in features_str:
            backend.append('Spring Boot')

        if 'go' in features_str or 'golang' in features_str:
            backend.append('Go')

        if 'rust' in features_str:
            backend.append('Rust')

        if not backend:
            backend = ['Backend Server']

        return backend[:3]

    def _infer_database_tech(self, project_data: Dict) -> List[str]:
        """Infer database technologies from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        database = []

        if 'postgres' in features_str or 'postgresql' in features_str:
            database.append('PostgreSQL')
        if 'mysql' in features_str or 'mariadb' in features_str:
            database.append('MySQL')
        if 'mongo' in features_str:
            database.append('MongoDB')
        if 'sqlite' in features_str:
            database.append('SQLite')
        if 'redis' in features_str:
            database.append('Redis')
        if 'dynamodb' in features_str:
            database.append('DynamoDB')

        if not database:
            database = ['Database']

        return database[:3]

    def _detect_client_devices(self, project_data: Dict) -> str:
        """Detect client devices from project features."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        devices = []

        if 'web' in features_str or 'browser' in features_str or not ('mobile' in features_str or 'app' in features_str):
            devices.append('Web Browser')
        if 'mobile' in features_str or 'ios' in features_str or 'android' in features_str:
            devices.append('Mobile App')
        if 'desktop' in features_str or 'electron' in features_str:
            devices.append('Desktop')
        if 'api' in features_str and len(devices) == 0:
            devices.append('API Clients')

        if not devices:
            devices = ['Web Browser']

        return ', '.join(devices[:2])

    def _detect_api_type(self, project_data: Dict) -> str:
        """Detect API type from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))
        technologies = project_data.get('technologies', {})

        api_types = []

        if 'graphql' in features_str or 'graphql' in str(technologies).lower():
            api_types.append('GraphQL')
        if 'grpc' in features_str:
            api_types.append('gRPC')
        if 'websocket' in features_str or 'realtime' in features_str or 'real-time' in features_str:
            api_types.append('WebSocket')

        # REST is default for most APIs
        if 'rest' in features_str or 'api' in features_str or not api_types:
            api_types.insert(0, 'REST API')

        return ' / '.join(api_types[:2])

    def _detect_external_services(self, project_data: Dict) -> List[str]:
        """Detect external services from project features."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        services = []

        # Payment
        if any(kw in features_str for kw in ['payment', 'checkout', 'stripe', 'paypal', 'razorpay', 'billing']):
            services.append('Payment Gateway')

        # Email
        if any(kw in features_str for kw in ['email', 'notification', 'sendgrid', 'mailgun', 'smtp']):
            services.append('Email Service')

        # SMS
        if any(kw in features_str for kw in ['sms', 'twilio', 'otp', 'phone verification']):
            services.append('SMS Service')

        # Auth providers
        if any(kw in features_str for kw in ['oauth', 'google login', 'facebook login', 'social login', 'sso']):
            services.append('OAuth Provider')

        # Maps
        if any(kw in features_str for kw in ['map', 'location', 'gps', 'geocoding']):
            services.append('Maps API')

        # AI/ML
        if any(kw in features_str for kw in ['ai', 'ml', 'openai', 'chatgpt', 'llm']):
            services.append('AI/ML API')

        # Analytics
        if any(kw in features_str for kw in ['analytics', 'tracking', 'google analytics']):
            services.append('Analytics')

        # Cloud storage
        if any(kw in features_str for kw in ['upload', 'file', 's3', 'cloudinary', 'storage']):
            services.append('Cloud Storage')

        if not services:
            services = ['Third-party APIs']

        return services[:3]

    def _detect_orm(self, project_data: Dict) -> str:
        """Detect ORM/database library from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))
        technologies = project_data.get('technologies', {})
        backend = technologies.get('backend', [])
        if isinstance(backend, str):
            backend = [backend]
        backend_str = ' '.join(str(b).lower() for b in backend)

        # Python ORMs
        if any(kw in features_str or kw in backend_str for kw in ['sqlalchemy', 'fastapi', 'flask']):
            return 'SQLAlchemy ORM'
        if 'django' in features_str or 'django' in backend_str:
            return 'Django ORM'

        # Node.js ORMs
        if 'prisma' in features_str:
            return 'Prisma ORM'
        if 'typeorm' in features_str:
            return 'TypeORM'
        if 'sequelize' in features_str:
            return 'Sequelize'
        if 'mongoose' in features_str or 'mongo' in features_str:
            return 'Mongoose ODM'

        # Java
        if 'hibernate' in features_str or 'jpa' in features_str or 'spring' in backend_str:
            return 'JPA/Hibernate'

        # Default
        if 'node' in backend_str or 'express' in backend_str:
            return 'Query Builder'

        return 'Data Access Layer'

    def _detect_cache_storage(self, project_data: Dict) -> List[str]:
        """Detect cache and storage solutions from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        cache_storage = []

        # Cache
        if 'redis' in features_str:
            cache_storage.append('Redis Cache')
        elif 'memcached' in features_str:
            cache_storage.append('Memcached')
        elif any(kw in features_str for kw in ['cache', 'session', 'realtime']):
            cache_storage.append('In-Memory Cache')

        # File storage
        if 's3' in features_str or 'aws' in features_str:
            cache_storage.append('AWS S3 Storage')
        elif 'gcs' in features_str or 'google cloud' in features_str:
            cache_storage.append('Google Cloud Storage')
        elif 'azure' in features_str:
            cache_storage.append('Azure Blob Storage')
        elif 'cloudinary' in features_str:
            cache_storage.append('Cloudinary')
        elif any(kw in features_str for kw in ['upload', 'file', 'image', 'media']):
            cache_storage.append('File Storage')

        if not cache_storage:
            cache_storage = ['Local Storage', 'Session Storage']

        return cache_storage[:2]

    def _detect_infrastructure(self, project_data: Dict) -> str:
        """Detect infrastructure from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        infra = []

        # Containerization
        if 'docker' in features_str:
            infra.append('Docker')
        if 'kubernetes' in features_str or 'k8s' in features_str:
            infra.append('Kubernetes')

        # Cloud providers
        if 'aws' in features_str or 's3' in features_str or 'ec2' in features_str:
            infra.append('AWS')
        elif 'gcp' in features_str or 'google cloud' in features_str:
            infra.append('GCP')
        elif 'azure' in features_str:
            infra.append('Azure')
        elif 'vercel' in features_str:
            infra.append('Vercel')
        elif 'heroku' in features_str:
            infra.append('Heroku')

        # CI/CD
        if any(kw in features_str for kw in ['ci/cd', 'github actions', 'jenkins', 'gitlab ci']):
            infra.append('CI/CD Pipeline')

        if not infra:
            infra = ['Cloud Hosting', 'CI/CD']

        return ' | '.join(infra[:4])

    def _detect_security_features(self, project_data: Dict) -> List[str]:
        """Detect security features from project data."""
        features_str = ' '.join(str(f).lower() for f in project_data.get('features', []))

        security = []

        # Authentication
        if any(kw in features_str for kw in ['jwt', 'token', 'auth']):
            security.append('JWT Authentication')
        elif any(kw in features_str for kw in ['session', 'cookie']):
            security.append('Session Auth')
        elif any(kw in features_str for kw in ['login', 'register', 'user']):
            security.append('User Authentication')

        # Authorization
        if any(kw in features_str for kw in ['rbac', 'role', 'permission', 'admin']):
            security.append('Role-Based Access')

        # OAuth
        if any(kw in features_str for kw in ['oauth', 'google login', 'social']):
            security.append('OAuth 2.0')

        # API Security
        if any(kw in features_str for kw in ['api key', 'rate limit', 'throttle']):
            security.append('API Rate Limiting')

        # Encryption
        if any(kw in features_str for kw in ['encrypt', 'https', 'ssl', 'tls']):
            security.append('HTTPS/TLS')

        # Validation
        if any(kw in features_str for kw in ['validation', 'sanitize', 'xss', 'sql injection']):
            security.append('Input Validation')

        # If no specific security detected but has auth-related features
        if not security and any(kw in features_str for kw in ['login', 'user', 'account']):
            security = ['Authentication', 'Authorization', 'Data Encryption']

        if not security:
            security = ['Basic Security']

        return security[:5]

    def _generate_placeholder(self, diagram_type: str) -> str:
        """Generate placeholder image when PIL is not available"""
        # Return a path to indicate diagram should be generated
        return f"[{diagram_type} - Placeholder]"

    def generate_all_diagrams(self, project_data: Dict, project_id: str = None, user_id: str = None) -> Dict[str, str]:
        """
        Generate all UML diagrams for a project - FULLY DYNAMIC

        Args:
            project_data: Project data with features, classes, etc.

        Returns:
            Dict mapping diagram type to file path
        """
        diagrams = {}

        project_name = project_data.get('project_name', 'System')
        features = project_data.get('features', [])
        technologies = project_data.get('technologies', {})
        api_endpoints = project_data.get('api_endpoints', [])
        database_tables = project_data.get('database_tables', [])

        # 1. Use Case Diagram - DYNAMIC based on features
        actors = self._extract_actors_from_project(project_data)
        use_cases = self._extract_use_cases_from_project(project_data)

        diagrams['use_case'] = self.generate_use_case_diagram(
            project_name=project_name,
            actors=actors,
            use_cases=use_cases,
            project_id=project_id,
            user_id=user_id
        )

        # 2. Class Diagram - DYNAMIC based on tables and code
        classes = self._extract_classes_from_project(project_data)
        diagrams['class'] = self.generate_class_diagram(classes, project_id=project_id, user_id=user_id)

        # 3. Sequence Diagram - DYNAMIC based on API endpoints
        participants, messages = self._extract_sequence_from_project(project_data)
        diagrams['sequence'] = self.generate_sequence_diagram(participants, messages, project_id=project_id, user_id=user_id)

        # 4. Activity Diagram - DYNAMIC based on features/workflow
        activities = self._extract_activities_from_project(project_data)
        diagrams['activity'] = self.generate_activity_diagram(activities, project_id=project_id, user_id=user_id)

        # 5. ER Diagram - DYNAMIC based on database tables
        entities = self._extract_entities_from_project(project_data)
        diagrams['er'] = self.generate_er_diagram(entities, project_id=project_id, user_id=user_id)

        # 6. DFD Level 0 - DYNAMIC based on project structure
        external_entities, data_stores, data_flows = self._extract_dfd_from_project(project_data)
        diagrams['dfd_0'] = self.generate_dfd(
            level=0,
            processes=[project_name],
            project_id=project_id,
            user_id=user_id,
            data_stores=data_stores,
            external_entities=external_entities,
            data_flows=data_flows
        )

        # 7. System Architecture Diagram - Shows three-tier architecture with tech stack
        diagrams['architecture'] = self.generate_system_architecture_diagram(
            project_data=project_data,
            project_id=project_id,
            user_id=user_id
        )

        logger.info(f"[UMLGenerator] Generated {len(diagrams)} diagrams for {project_name}")

        return diagrams

    async def generate_all_diagrams_and_save(
        self,
        project_data: Dict,
        project_id: str,
        user_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate all UML diagrams and save them to S3 + PostgreSQL.

        Args:
            project_data: Project data with features, classes, etc.
            project_id: Project UUID (required for storage)
            user_id: User UUID (required for storage)

        Returns:
            Dict mapping diagram type to storage result:
            {
                'use_case': {
                    'local_path': '/path/to/file.png',
                    's3_key': 'documents/user/project/diagrams/...',
                    'file_url': 'https://...',
                    'document_id': 'uuid'
                },
                ...
            }
        """
        from app.services.document_storage_service import document_storage

        if not project_id or not user_id:
            logger.error("[UMLGenerator] project_id and user_id are required for saving diagrams")
            # Fall back to local-only generation
            local_diagrams = self.generate_all_diagrams(project_data, project_id, user_id)
            return {k: {'local_path': v, 's3_key': None, 'file_url': None} for k, v in local_diagrams.items()}

        project_name = project_data.get('project_name', 'System')
        logger.info(f"[UMLGenerator] Generating and saving diagrams for {project_name} to S3+DB")

        # Generate diagrams locally first
        local_diagrams = self.generate_all_diagrams(project_data, project_id, user_id)

        # Save each diagram to S3 and DB
        results = {}
        for diagram_type, local_path in local_diagrams.items():
            if not local_path or local_path.startswith('['):
                # Skip placeholders
                results[diagram_type] = {'local_path': local_path, 'error': 'Placeholder or failed'}
                continue

            try:
                save_result = await document_storage.save_diagram(
                    user_id=user_id,
                    project_id=project_id,
                    local_file_path=local_path,
                    diagram_type=diagram_type,
                    extra_metadata={
                        'project_name': project_name,
                        'generated_at': datetime.now().isoformat()
                    }
                )

                if save_result:
                    results[diagram_type] = {
                        'local_path': local_path,
                        's3_key': save_result.get('s3_key'),
                        'file_url': save_result.get('file_url'),
                        'document_id': save_result.get('document_id'),
                        'saved_to_cloud': True
                    }
                    logger.info(f"[UMLGenerator] Saved {diagram_type} diagram to S3+DB")
                else:
                    results[diagram_type] = {
                        'local_path': local_path,
                        'saved_to_cloud': False,
                        'error': 'Failed to save to cloud'
                    }

            except Exception as e:
                logger.error(f"[UMLGenerator] Error saving {diagram_type}: {e}")
                results[diagram_type] = {
                    'local_path': local_path,
                    'saved_to_cloud': False,
                    'error': str(e)
                }

        saved_count = sum(1 for r in results.values() if r.get('saved_to_cloud'))
        logger.info(f"[UMLGenerator] Saved {saved_count}/{len(results)} diagrams to S3+DB")

        return results

    def _extract_actors_from_project(self, project_data: Dict) -> List[str]:
        """Dynamically extract actors from project data"""
        actors = set()
        features = project_data.get('features', [])
        features_str = ' '.join(str(f).lower() for f in features)

        # Always include User
        actors.add('User')

        # Check for admin features
        admin_keywords = ['admin', 'manage', 'dashboard', 'settings', 'configuration', 'moderate']
        if any(kw in features_str for kw in admin_keywords):
            actors.add('Admin')

        # Check for guest/public features
        guest_keywords = ['guest', 'public', 'visitor', 'anonymous', 'browse']
        if any(kw in features_str for kw in guest_keywords):
            actors.add('Guest')

        # Check for API/system integration
        api_keywords = ['api', 'integration', 'external', 'webhook', 'third-party']
        if any(kw in features_str for kw in api_keywords):
            actors.add('External System')

        # Check for specific roles
        if 'seller' in features_str or 'vendor' in features_str:
            actors.add('Seller')
        if 'buyer' in features_str or 'customer' in features_str:
            actors.add('Customer')
        if 'teacher' in features_str or 'instructor' in features_str:
            actors.add('Teacher')
        if 'student' in features_str or 'learner' in features_str:
            actors.add('Student')

        return list(actors)[:5]  # Max 5 actors

    def _extract_use_cases_from_project(self, project_data: Dict) -> List[str]:
        """Dynamically extract use cases from features - NO HARDCODED DEFAULTS"""
        features = project_data.get('features', [])
        project_name = project_data.get('project_name', '').lower()
        project_type = project_data.get('project_type', '').lower()

        use_cases = []

        # Use actual features as use cases
        if features:
            for feature in features[:8]:
                if isinstance(feature, str):
                    # Clean up feature name
                    uc = feature.strip()
                    # Remove common prefixes
                    for prefix in ['user can ', 'ability to ', 'the system ', 'users can ', 'allow ']:
                        if uc.lower().startswith(prefix):
                            uc = uc[len(prefix):]
                    uc = uc.strip().title()
                    if len(uc) > 3:  # Skip very short strings
                        use_cases.append(uc[:30])

        # If no features, infer from project name and type
        if not use_cases:
            # Parse project name for clues
            name_words = project_name.replace('-', ' ').replace('_', ' ').split()

            # Infer based on keywords in name or type
            all_text = f"{project_name} {project_type}".lower()

            # E-commerce patterns
            if any(kw in all_text for kw in ['shop', 'store', 'ecommerce', 'cart', 'product']):
                use_cases = [f'Browse {project_name.title()} Products', 'Add to Cart', 'Checkout', 'Track Order']
            # Social patterns
            elif any(kw in all_text for kw in ['social', 'community', 'forum', 'chat']):
                use_cases = [f'Join {project_name.title()}', 'Create Post', 'Connect Users', 'Send Message']
            # Education patterns
            elif any(kw in all_text for kw in ['learn', 'course', 'education', 'school', 'student']):
                use_cases = ['Enroll in Course', 'Access Content', 'Track Progress', 'Get Certified']
            # Healthcare patterns
            elif any(kw in all_text for kw in ['health', 'hospital', 'medical', 'patient', 'doctor']):
                use_cases = ['Book Appointment', 'View Medical Records', 'Consult Doctor', 'Manage Prescriptions']
            # Finance patterns
            elif any(kw in all_text for kw in ['finance', 'bank', 'payment', 'money', 'wallet']):
                use_cases = ['View Balance', 'Transfer Funds', 'Pay Bills', 'Transaction History']
            # Management patterns
            elif any(kw in all_text for kw in ['manage', 'admin', 'dashboard', 'crm', 'erp']):
                use_cases = [f'Manage {name_words[0].title() if name_words else "Data"}', 'View Reports', 'Configure Settings', 'Export Data']
            else:
                # Generic based on project name
                main_noun = name_words[0].title() if name_words else 'Data'
                use_cases = [f'Create {main_noun}', f'View {main_noun}', f'Update {main_noun}', f'Delete {main_noun}']

        return use_cases[:8]

    def _extract_sequence_from_project(self, project_data: Dict) -> tuple:
        """Dynamically extract sequence diagram data from API endpoints"""
        api_endpoints = project_data.get('api_endpoints', [])
        technologies = project_data.get('technologies', {})

        # Determine participants based on tech stack
        frontend = technologies.get('frontend', 'Frontend')
        if isinstance(frontend, list):
            frontend = frontend[0] if frontend else 'Frontend'

        backend = technologies.get('backend', 'API')
        if isinstance(backend, list):
            backend = backend[0] if backend else 'API'

        database = technologies.get('database', 'Database')
        if isinstance(database, list):
            database = database[0] if database else 'Database'

        participants = ['User', str(frontend)[:12], str(backend)[:12], str(database)[:12]]

        # Generate messages from API endpoints
        messages = []
        if api_endpoints:
            for endpoint in api_endpoints[:4]:
                if isinstance(endpoint, dict):
                    method = endpoint.get('method', 'GET')
                    path = endpoint.get('path', '/api')
                    desc = endpoint.get('description', path)[:20]
                else:
                    desc = str(endpoint)[:20]

                messages.extend([
                    {'from': 'User', 'to': participants[1], 'message': f'Request {desc}'},
                    {'from': participants[1], 'to': participants[2], 'message': f'API: {desc}'},
                    {'from': participants[2], 'to': participants[3], 'message': 'Query'},
                    {'from': participants[3], 'to': participants[2], 'message': 'Data', 'type': 'return'},
                ])
                break  # Just one flow for clarity

        if not messages:
            # Build flow based on project context - not hardcoded
            project_name = project_data.get('project_name', 'System')
            features = project_data.get('features', [])
            features_str = ' '.join(str(f).lower() for f in features)

            # Determine the main action based on features
            if any(kw in features_str for kw in ['login', 'auth', 'register']):
                action = 'Authenticate'
            elif any(kw in features_str for kw in ['create', 'add', 'new']):
                action = 'Create Data'
            elif any(kw in features_str for kw in ['search', 'find', 'browse']):
                action = 'Search'
            elif any(kw in features_str for kw in ['update', 'edit', 'modify']):
                action = 'Update Data'
            elif any(kw in features_str for kw in ['delete', 'remove']):
                action = 'Delete Data'
            elif any(kw in features_str for kw in ['view', 'list', 'get']):
                action = 'Fetch Data'
            else:
                action = f'Use {project_name[:15]}'

            messages = [
                {'from': 'User', 'to': participants[1], 'message': f'{action} Request'},
                {'from': participants[1], 'to': participants[2], 'message': f'Process {action}'},
                {'from': participants[2], 'to': participants[3], 'message': 'Data Query'},
                {'from': participants[3], 'to': participants[2], 'message': 'Data Result', 'type': 'return'},
                {'from': participants[2], 'to': participants[1], 'message': f'{action} Response', 'type': 'return'},
                {'from': participants[1], 'to': 'User', 'message': 'Show Result', 'type': 'return'},
            ]

        return participants, messages

    def _extract_activities_from_project(self, project_data: Dict) -> List[str]:
        """Dynamically extract activity flow from project"""
        features = project_data.get('features', [])
        project_type = project_data.get('project_type', '').lower()

        # Try to build workflow from features
        activities = ['Start Application']

        # Check for auth
        features_str = ' '.join(str(f).lower() for f in features)
        if any(kw in features_str for kw in ['login', 'auth', 'register', 'sign']):
            activities.append('User Authentication')

        # Add main feature activities
        for feature in features[:4]:
            if isinstance(feature, str):
                activity = feature.strip()
                if len(activity) > 5 and activity.lower() not in ['login', 'logout', 'register']:
                    activities.append(activity[:25])

        # Add standard ending activities
        if 'database' in features_str or 'save' in features_str or 'store' in features_str:
            activities.append('Save to Database')

        activities.append('Return Response')

        # If not enough activities, infer from project context
        if len(activities) < 5:
            project_name = project_data.get('project_name', 'System')
            project_type = project_data.get('project_type', '').lower()

            # Build context-aware activities
            if any(kw in features_str or kw in project_type for kw in ['shop', 'ecommerce', 'store']):
                extra = ['Browse Catalog', 'Select Items', 'Process Order', 'Confirm Purchase']
            elif any(kw in features_str or kw in project_type for kw in ['social', 'community']):
                extra = ['Load Feed', 'Create Content', 'Interact with Posts', 'Update Profile']
            elif any(kw in features_str or kw in project_type for kw in ['education', 'course', 'learning']):
                extra = ['Load Course', 'View Content', 'Complete Exercise', 'Track Progress']
            elif any(kw in features_str or kw in project_type for kw in ['health', 'hospital', 'medical']):
                extra = ['Check Availability', 'Book Slot', 'Confirm Appointment', 'Send Notification']
            else:
                # Generic based on project name
                main_noun = project_name.split()[0] if project_name else 'Data'
                extra = [f'Load {main_noun}', f'Process {main_noun}', f'Validate {main_noun}', f'Save {main_noun}']

            for act in extra:
                if act not in activities and len(activities) < 6:
                    activities.append(act)

        return activities[:8]  # Max 8 activities

    def _extract_dfd_from_project(self, project_data: Dict) -> tuple:
        """Dynamically extract DFD components from project"""
        features = project_data.get('features', [])
        database_tables = project_data.get('database_tables', [])
        project_name = project_data.get('project_name', 'System')

        # Extract external entities (actors who interact with system)
        external_entities = self._extract_actors_from_project(project_data)[:4]

        # Extract data stores from database tables
        data_stores = []
        if database_tables:
            for table in database_tables[:3]:
                name = table if isinstance(table, str) else table.get('name', 'Data')
                data_stores.append(f"{name} Store")
        else:
            data_stores = ['User Database', 'Application Data']

        # Build data flows based on entities and stores
        data_flows = []
        for entity in external_entities[:2]:
            data_flows.append({'from': entity, 'to': project_name, 'data': f'{entity} Request'})
            data_flows.append({'from': project_name, 'to': entity, 'data': 'Response'})

        for store in data_stores[:2]:
            data_flows.append({'from': project_name, 'to': store, 'data': 'Write Data'})
            data_flows.append({'from': store, 'to': project_name, 'data': 'Read Data'})

        return external_entities, data_stores, data_flows[:10]

    def _extract_classes_from_project(self, project_data: Dict) -> List[Dict]:
        """
        Extract class info from project data for Class Diagram.
        Uses ACTUAL columns and methods from parsed model files.
        """
        classes = []

        # First, try to get from database_schema (from ProjectAnalyzer with AST parsing)
        db_schema = project_data.get('database_schema', {})
        tables_from_schema = db_schema.get('tables', [])

        if tables_from_schema:
            for table in tables_from_schema[:9]:  # Max 9 classes
                if isinstance(table, dict):
                    name = table.get('name', 'Entity')
                    columns = table.get('columns', [])
                    methods = table.get('methods', [])
                    relationships = table.get('relationships', [])

                    # Convert columns to attributes with proper formatting
                    attributes = []
                    for col in columns[:8]:  # Limit to 8 attributes
                        if isinstance(col, dict):
                            col_name = col.get('name', '')
                            col_type = col.get('type', 'Any')
                            # Format: - name: Type or + name: Type (public by default)
                            prefix = '-' if col.get('primary_key') else '+'
                            attributes.append(f"{prefix} {col_name}: {col_type}")
                        else:
                            attributes.append(f"+ {col}")

                    # If no methods found, generate CRUD based on class name
                    if not methods:
                        methods = [f'create{name}', f'get{name}ById', f'update{name}', f'delete{name}']

                    # Format methods
                    formatted_methods = [f"+ {m}()" if not m.endswith(')') else f"+ {m}" for m in methods[:6]]

                    # Build class relationships
                    class_rels = []
                    for rel in relationships:
                        if isinstance(rel, dict):
                            target = rel.get('references', rel.get('target', ''))
                            rel_type = rel.get('type', 'association')
                            if target:
                                class_rels.append({'target': target, 'type': rel_type})

                    classes.append({
                        'name': name,
                        'attributes': attributes if attributes else ['+ id: UUID', '+ createdAt: DateTime'],
                        'methods': formatted_methods,
                        'relationships': class_rels
                    })

        # Fallback: Try database_tables (older format or from code file extraction)
        if not classes:
            tables = project_data.get('database_tables', [])
            for table in tables[:9]:
                if isinstance(table, dict):
                    name = table.get('name', 'Entity')
                    columns = table.get('columns', [])

                    attributes = []
                    for col in columns[:8]:
                        if isinstance(col, dict):
                            col_name = col.get('name', '')
                            col_type = col.get('type', 'Any')
                            attributes.append(f"+ {col_name}: {col_type}")
                        else:
                            attributes.append(f"+ {col}")

                    classes.append({
                        'name': name,
                        'attributes': attributes if attributes else ['+ id: UUID'],
                        'methods': [f'+ create{name}()', f'+ get{name}()', f'+ update{name}()', f'+ delete{name}()'],
                        'relationships': []
                    })
                elif isinstance(table, str):
                    name = table.title().replace('_', '')
                    classes.append({
                        'name': name,
                        'attributes': ['+ id: UUID', '+ createdAt: DateTime', '+ updatedAt: DateTime'],
                        'methods': [f'+ create()', f'+ findById()', f'+ update()', f'+ delete()'],
                        'relationships': []
                    })

        # Last resort: Use features to infer classes
        if not classes:
            features = project_data.get('features', [])
            project_name = project_data.get('project_name', '').lower()

            # Infer entities from features
            feature_str = ' '.join(str(f).lower() for f in features)

            # Common entity patterns
            entity_keywords = {
                'user': ['user', 'login', 'auth', 'account', 'profile'],
                'product': ['product', 'item', 'catalog', 'inventory'],
                'order': ['order', 'purchase', 'checkout', 'cart'],
                'payment': ['payment', 'billing', 'transaction'],
                'course': ['course', 'lesson', 'module', 'learning'],
                'student': ['student', 'enrollment', 'learner'],
                'post': ['post', 'article', 'blog', 'content'],
                'comment': ['comment', 'review', 'feedback'],
            }

            for entity_name, keywords in entity_keywords.items():
                if any(kw in feature_str or kw in project_name for kw in keywords):
                    classes.append({
                        'name': entity_name.title(),
                        'attributes': ['+ id: UUID', f'+ {entity_name}Name: String', '+ createdAt: DateTime'],
                        'methods': [f'+ create{entity_name.title()}()', f'+ get{entity_name.title()}()'],
                        'relationships': []
                    })

        # Context-aware fallback based on project
        if not classes:
            project_name = project_data.get('project_name', 'System')
            project_type = project_data.get('project_type', '').lower()
            features = project_data.get('features', [])
            features_str = ' '.join(str(f).lower() for f in features)
            all_text = f"{project_name} {features_str}".lower()

            # Always include a User class if auth-related
            if any(kw in all_text for kw in ['user', 'login', 'auth', 'account']):
                classes.append({
                    'name': 'User',
                    'attributes': ['+ id: UUID', '+ email: String', '+ passwordHash: String', '+ role: Enum'],
                    'methods': ['+ login()', '+ logout()', '+ register()'],
                    'relationships': []
                })

            # Add project-specific main entity
            main_noun = project_name.split()[0].title() if project_name else 'Entity'
            if main_noun.lower() not in ['user', 'the', 'a', 'my']:
                classes.append({
                    'name': main_noun,
                    'attributes': ['+ id: UUID', f'+ {main_noun.lower()}Name: String', '+ status: String', '+ createdAt: DateTime'],
                    'methods': [f'+ create{main_noun}()', f'+ get{main_noun}()', f'+ update{main_noun}()', f'+ delete{main_noun}()'],
                    'relationships': [{'target': 'User', 'type': 'association'}] if 'User' in [c['name'] for c in classes] else []
                })

            # If still empty, create generic based on project name
            if not classes:
                classes = [{
                    'name': project_name.replace(' ', '')[:15] or 'MainEntity',
                    'attributes': ['+ id: UUID', '+ name: String', '+ createdAt: DateTime'],
                    'methods': ['+ create()', '+ read()', '+ update()', '+ delete()'],
                    'relationships': []
                }]

        return classes

    def _extract_entities_from_project(self, project_data: Dict) -> List[Dict]:
        """
        Extract entity info from project data for ER Diagram.
        Uses ACTUAL columns, types, PKs, FKs from parsed model files.
        """
        entities = []

        # First, try database_schema (from ProjectAnalyzer with full AST parsing)
        db_schema = project_data.get('database_schema', {})
        tables_from_schema = db_schema.get('tables', [])

        if tables_from_schema:
            for table in tables_from_schema[:6]:  # Max 6 entities
                if isinstance(table, dict):
                    name = table.get('name', 'Entity')
                    columns = table.get('columns', [])
                    pk = table.get('primary_key', 'id')
                    relationships = table.get('relationships', [])

                    # Use actual columns if available
                    if columns:
                        entities.append({
                            'name': name,
                            'columns': columns[:10],  # Limit to 10 columns
                            'primary_key': pk,
                            'relationships': relationships
                        })
                    else:
                        # Table name only, use minimal defaults
                        entities.append({
                            'name': name,
                            'columns': [
                                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                                {'name': 'created_at', 'type': 'DateTime'},
                            ],
                            'primary_key': 'id',
                            'relationships': relationships
                        })

        # Fallback: Try database_tables (from code file extraction)
        if not entities:
            tables = project_data.get('database_tables', [])
            for table in tables[:6]:
                if isinstance(table, dict):
                    name = table.get('name', 'Entity')
                    columns = table.get('columns', [])
                    relationships = table.get('relationships', [])

                    if columns:
                        entities.append({
                            'name': name,
                            'columns': columns[:10],
                            'primary_key': table.get('primary_key', 'id'),
                            'relationships': relationships
                        })
                    else:
                        # No columns, infer from name
                        inferred_cols = self._infer_columns_from_entity_name(name)
                        entities.append({
                            'name': name,
                            'columns': inferred_cols,
                            'primary_key': 'id',
                            'relationships': relationships
                        })
                elif isinstance(table, str):
                    # Just table name string
                    name = table.title().replace('_', '')
                    inferred_cols = self._infer_columns_from_entity_name(name)
                    entities.append({
                        'name': name,
                        'columns': inferred_cols,
                        'primary_key': 'id',
                        'relationships': []
                    })

        # Try to infer from features/project type
        if not entities:
            entities = self._infer_entities_from_features(project_data)

        return entities

    def _infer_columns_from_entity_name(self, entity_name: str) -> List[Dict]:
        """Infer likely columns based on entity name."""
        name_lower = entity_name.lower()
        columns = [{'name': 'id', 'type': 'UUID', 'primary_key': True}]

        # Common columns based on entity type
        entity_columns = {
            'user': [
                {'name': 'email', 'type': 'String'},
                {'name': 'password_hash', 'type': 'String'},
                {'name': 'name', 'type': 'String'},
                {'name': 'role', 'type': 'Enum'},
                {'name': 'is_active', 'type': 'Boolean'},
            ],
            'product': [
                {'name': 'name', 'type': 'String'},
                {'name': 'description', 'type': 'Text'},
                {'name': 'price', 'type': 'Decimal'},
                {'name': 'stock', 'type': 'Integer'},
                {'name': 'category_id', 'type': 'UUID', 'foreign_key': 'categories'},
            ],
            'order': [
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'total', 'type': 'Decimal'},
                {'name': 'status', 'type': 'Enum'},
                {'name': 'shipping_address', 'type': 'Text'},
            ],
            'payment': [
                {'name': 'order_id', 'type': 'UUID', 'foreign_key': 'orders'},
                {'name': 'amount', 'type': 'Decimal'},
                {'name': 'method', 'type': 'String'},
                {'name': 'status', 'type': 'Enum'},
            ],
            'course': [
                {'name': 'title', 'type': 'String'},
                {'name': 'description', 'type': 'Text'},
                {'name': 'instructor_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'price', 'type': 'Decimal'},
                {'name': 'duration', 'type': 'Integer'},
            ],
            'post': [
                {'name': 'title', 'type': 'String'},
                {'name': 'content', 'type': 'Text'},
                {'name': 'author_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'published_at', 'type': 'DateTime'},
            ],
            'comment': [
                {'name': 'content', 'type': 'Text'},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'post_id', 'type': 'UUID', 'foreign_key': 'posts'},
            ],
        }

        # Check if entity name matches known patterns
        for pattern, cols in entity_columns.items():
            if pattern in name_lower:
                columns.extend(cols)
                break
        else:
            # Generic columns
            columns.extend([
                {'name': 'name', 'type': 'String'},
                {'name': 'description', 'type': 'Text'},
            ])

        # Always add timestamps
        columns.extend([
            {'name': 'created_at', 'type': 'DateTime'},
            {'name': 'updated_at', 'type': 'DateTime'},
        ])

        return columns

    def _infer_entities_from_features(self, project_data: Dict) -> List[Dict]:
        """Infer entities from project features and name - FULLY DYNAMIC."""
        entities = []
        features = project_data.get('features', [])
        project_name = project_data.get('project_name', '').lower()
        project_type = project_data.get('project_type', '').lower()
        features_str = ' '.join(str(f).lower() for f in features)
        all_text = f"{project_name} {project_type} {features_str}"

        # Detect which entities are needed based on keywords
        detected_entities = set()

        # User/Auth detection
        if any(kw in all_text for kw in ['user', 'login', 'auth', 'account', 'profile', 'member']):
            detected_entities.add('user')

        # E-commerce detection
        if any(kw in all_text for kw in ['product', 'item', 'catalog', 'inventory']):
            detected_entities.add('product')
        if any(kw in all_text for kw in ['order', 'purchase', 'buy', 'checkout']):
            detected_entities.add('order')
        if any(kw in all_text for kw in ['cart', 'basket']):
            detected_entities.add('cart')
        if any(kw in all_text for kw in ['category', 'categories']):
            detected_entities.add('category')

        # Education detection
        if any(kw in all_text for kw in ['course', 'class', 'lesson', 'module']):
            detected_entities.add('course')
        if any(kw in all_text for kw in ['student', 'learner', 'enrollment']):
            detected_entities.add('enrollment')

        # Content/Blog detection
        if any(kw in all_text for kw in ['post', 'article', 'blog', 'content']):
            detected_entities.add('post')
        if any(kw in all_text for kw in ['comment', 'reply', 'feedback']):
            detected_entities.add('comment')

        # Healthcare detection
        if any(kw in all_text for kw in ['patient', 'medical']):
            detected_entities.add('patient')
        if any(kw in all_text for kw in ['doctor', 'physician']):
            detected_entities.add('doctor')
        if any(kw in all_text for kw in ['appointment', 'booking', 'schedule']):
            detected_entities.add('appointment')

        # Finance detection
        if any(kw in all_text for kw in ['transaction', 'payment', 'transfer']):
            detected_entities.add('transaction')
        if any(kw in all_text for kw in ['wallet', 'balance', 'account']):
            detected_entities.add('wallet')

        # Social detection
        if any(kw in all_text for kw in ['message', 'chat', 'conversation']):
            detected_entities.add('message')
        if any(kw in all_text for kw in ['follow', 'friend', 'connection']):
            detected_entities.add('follow')

        # Build entities based on detection
        entity_builders = {
            'user': lambda: {'name': 'User', 'columns': self._infer_columns_from_entity_name('user'), 'primary_key': 'id', 'relationships': []},
            'product': lambda: {'name': 'Product', 'columns': self._infer_columns_from_entity_name('product'), 'primary_key': 'id',
                               'relationships': [{'column': 'category_id', 'references': 'Category', 'type': 'many_to_one'}] if 'category' in detected_entities else []},
            'order': lambda: {'name': 'Order', 'columns': self._infer_columns_from_entity_name('order'), 'primary_key': 'id',
                             'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'many_to_one'}] if 'user' in detected_entities else []},
            'cart': lambda: {'name': 'Cart', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'total', 'type': 'Decimal'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'many_to_one'}] if 'user' in detected_entities else []},
            'category': lambda: {'name': 'Category', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'name', 'type': 'String'},
                {'name': 'parent_id', 'type': 'UUID'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': []},
            'course': lambda: {'name': 'Course', 'columns': self._infer_columns_from_entity_name('course'), 'primary_key': 'id',
                              'relationships': [{'column': 'instructor_id', 'references': 'User', 'type': 'many_to_one'}] if 'user' in detected_entities else []},
            'enrollment': lambda: {'name': 'Enrollment', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'course_id', 'type': 'UUID', 'foreign_key': 'courses'},
                {'name': 'enrolled_at', 'type': 'DateTime'},
                {'name': 'progress', 'type': 'Integer'},
            ], 'primary_key': 'id', 'relationships': [
                {'column': 'user_id', 'references': 'User', 'type': 'many_to_one'},
                {'column': 'course_id', 'references': 'Course', 'type': 'many_to_one'},
            ]},
            'post': lambda: {'name': 'Post', 'columns': self._infer_columns_from_entity_name('post'), 'primary_key': 'id',
                            'relationships': [{'column': 'author_id', 'references': 'User', 'type': 'many_to_one'}] if 'user' in detected_entities else []},
            'comment': lambda: {'name': 'Comment', 'columns': self._infer_columns_from_entity_name('comment'), 'primary_key': 'id',
                               'relationships': [
                                   {'column': 'user_id', 'references': 'User', 'type': 'many_to_one'},
                                   {'column': 'post_id', 'references': 'Post', 'type': 'many_to_one'},
                               ] if 'user' in detected_entities and 'post' in detected_entities else []},
            'patient': lambda: {'name': 'Patient', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'medical_history', 'type': 'Text'},
                {'name': 'blood_type', 'type': 'String'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'one_to_one'}] if 'user' in detected_entities else []},
            'doctor': lambda: {'name': 'Doctor', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'specialization', 'type': 'String'},
                {'name': 'license_number', 'type': 'String'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'one_to_one'}] if 'user' in detected_entities else []},
            'appointment': lambda: {'name': 'Appointment', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'patient_id', 'type': 'UUID', 'foreign_key': 'patients'},
                {'name': 'doctor_id', 'type': 'UUID', 'foreign_key': 'doctors'},
                {'name': 'scheduled_at', 'type': 'DateTime'},
                {'name': 'status', 'type': 'Enum'},
            ], 'primary_key': 'id', 'relationships': [
                {'column': 'patient_id', 'references': 'Patient', 'type': 'many_to_one'},
                {'column': 'doctor_id', 'references': 'Doctor', 'type': 'many_to_one'},
            ]},
            'transaction': lambda: {'name': 'Transaction', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'amount', 'type': 'Decimal'},
                {'name': 'type', 'type': 'Enum'},
                {'name': 'status', 'type': 'Enum'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'many_to_one'}] if 'user' in detected_entities else []},
            'wallet': lambda: {'name': 'Wallet', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'balance', 'type': 'Decimal'},
                {'name': 'currency', 'type': 'String'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [{'column': 'user_id', 'references': 'User', 'type': 'one_to_one'}] if 'user' in detected_entities else []},
            'message': lambda: {'name': 'Message', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'sender_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'receiver_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'content', 'type': 'Text'},
                {'name': 'sent_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [
                {'column': 'sender_id', 'references': 'User', 'type': 'many_to_one'},
                {'column': 'receiver_id', 'references': 'User', 'type': 'many_to_one'},
            ] if 'user' in detected_entities else []},
            'follow': lambda: {'name': 'Follow', 'columns': [
                {'name': 'id', 'type': 'UUID', 'primary_key': True},
                {'name': 'follower_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'following_id', 'type': 'UUID', 'foreign_key': 'users'},
                {'name': 'created_at', 'type': 'DateTime'},
            ], 'primary_key': 'id', 'relationships': [
                {'column': 'follower_id', 'references': 'User', 'type': 'many_to_one'},
                {'column': 'following_id', 'references': 'User', 'type': 'many_to_one'},
            ] if 'user' in detected_entities else []},
        }

        # Build entities in logical order
        for entity_key in ['user', 'category', 'product', 'cart', 'order', 'course', 'enrollment',
                          'post', 'comment', 'patient', 'doctor', 'appointment', 'transaction',
                          'wallet', 'message', 'follow']:
            if entity_key in detected_entities:
                entities.append(entity_builders[entity_key]())

        # If nothing detected, create project-specific entity
        if not entities:
            main_noun = project_name.split()[0].title() if project_name.split() else 'Entity'
            if main_noun.lower() in ['the', 'a', 'my', 'our']:
                main_noun = project_name.split()[1].title() if len(project_name.split()) > 1 else 'Entity'

            entities = [
                {'name': 'User', 'columns': [
                    {'name': 'id', 'type': 'UUID', 'primary_key': True},
                    {'name': 'email', 'type': 'String'},
                    {'name': 'password_hash', 'type': 'String'},
                    {'name': 'name', 'type': 'String'},
                    {'name': 'created_at', 'type': 'DateTime'},
                ], 'primary_key': 'id', 'relationships': []},
                {'name': main_noun, 'columns': [
                    {'name': 'id', 'type': 'UUID', 'primary_key': True},
                    {'name': 'name', 'type': 'String'},
                    {'name': 'description', 'type': 'Text'},
                    {'name': 'user_id', 'type': 'UUID', 'foreign_key': 'users'},
                    {'name': 'created_at', 'type': 'DateTime'},
                ], 'primary_key': 'id', 'relationships': [
                    {'column': 'user_id', 'references': 'User', 'type': 'many_to_one'}
                ]},
            ]

        return entities[:6]  # Max 6 entities for readability


# Singleton instance
uml_generator = UMLGenerator()
