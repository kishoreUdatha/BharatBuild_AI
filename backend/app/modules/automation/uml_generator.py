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
            except:
                self.font = ImageFont.load_default()
                self.font_bold = self.font
                self.font_small = self.font

    def get_output_dir(self, project_id: str = None) -> 'Path':
        """Get output directory - project-specific if project_id provided"""
        if project_id:
            return settings.get_project_diagrams_dir(project_id)
        return self.default_output_dir

    def generate_use_case_diagram(
        self,
        project_name: str,
        actors: List[str],
        use_cases: List[str],
        relationships: List[Dict] = None,
        project_id: str = None
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
        output_dir = self.get_output_dir(project_id)
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
        project_id: str = None
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
        output_dir = self.get_output_dir(project_id)
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
        project_id: str = None
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
        output_dir = self.get_output_dir(project_id)
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
        project_id: str = None
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
        output_dir = self.get_output_dir(project_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def generate_er_diagram(
        self,
        entities: List[Dict],
        project_id: str = None
    ) -> str:
        """
        Generate ER Diagram

        Args:
            entities: List of {name, attributes, primary_key, foreign_keys} dicts

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

        entity_width = 220
        entity_height = 160

        x_spacing = (self.WIDTH - 100) // max(cols, 1)
        y_spacing = (self.HEIGHT - 120) // max(rows, 1)

        entity_positions = {}

        for i, entity in enumerate(entities[:6]):
            col = i % cols
            row = i // cols

            x = 100 + col * x_spacing
            y = 100 + row * y_spacing

            name = entity.get('name', f'Entity{i}')
            attributes = entity.get('attributes', [])[:6]
            pk = entity.get('primary_key', 'id')

            # Entity box
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

            # Attributes
            draw.rectangle(
                [x, y + 35, x + entity_width, y + entity_height],
                fill=self.COLORS['background'],
                outline=self.COLORS['border'],
                width=2
            )

            for j, attr in enumerate(attributes):
                prefix = "PK " if attr == pk else "   "
                draw.text(
                    (x + 10, y + 45 + j * 18),
                    f"{prefix}{attr}",
                    fill=self.COLORS['text'],
                    font=self.font_small
                )

            entity_positions[name] = (x + entity_width // 2, y + entity_height // 2)

        # Draw relationships between entities
        entity_names = list(entity_positions.keys())
        for i in range(len(entity_names) - 1):
            e1 = entity_names[i]
            e2 = entity_names[i + 1]
            if e1 in entity_positions and e2 in entity_positions:
                p1 = entity_positions[e1]
                p2 = entity_positions[e2]
                draw.line([p1, p2], fill=self.COLORS['arrow'], width=2)

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            "Entity Relationship Diagram",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        filename = f"er_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def generate_dfd(
        self,
        level: int,
        processes: List[str],
        data_stores: List[str],
        external_entities: List[str],
        data_flows: List[Dict],
        project_id: str = None
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
        output_dir = self.get_output_dir(project_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def generate_system_architecture_diagram(self, project_data: Dict, project_id: str = None) -> str:
        """
        Generate System Architecture Diagram

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

        # Title
        draw.text(
            (self.WIDTH // 2, 30),
            f"{project_name} - System Architecture",
            fill=self.COLORS['primary'],
            font=self.font_bold,
            anchor="mm"
        )

        # Draw three-tier architecture
        # Presentation Layer
        draw.rounded_rectangle(
            [100, 80, 500, 180],
            radius=10,
            fill=(173, 216, 230),  # Light blue
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 100), "Presentation Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        frontend = technologies.get('frontend', ['React', 'HTML/CSS'])
        if isinstance(frontend, str):
            frontend = [frontend]
        draw.text((300, 140), ", ".join(frontend[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Client devices
        draw.rounded_rectangle([550, 80, 750, 180], radius=10, fill=(255, 228, 181), outline=self.COLORS['border'], width=2)
        draw.text((650, 110), "Client Devices", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        draw.text((650, 150), "Web Browser, Mobile", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from client to presentation
        draw.line([(550, 130), (500, 130)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(500, 130), (510, 125), (510, 135)], fill=self.COLORS['arrow'])

        # Business Logic Layer
        draw.rounded_rectangle(
            [100, 220, 500, 340],
            radius=10,
            fill=(144, 238, 144),  # Light green
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 240), "Business Logic Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        backend = technologies.get('backend', ['Node.js', 'Express'])
        if isinstance(backend, str):
            backend = [backend]
        draw.text((300, 280), ", ".join(backend[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((300, 310), "REST API / GraphQL", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from presentation to business
        draw.line([(300, 180), (300, 220)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(300, 220), (295, 210), (305, 210)], fill=self.COLORS['arrow'])

        # External Services box
        draw.rounded_rectangle([550, 220, 750, 340], radius=10, fill=(255, 218, 185), outline=self.COLORS['border'], width=2)
        draw.text((650, 250), "External Services", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        draw.text((650, 290), "Payment Gateway", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((650, 315), "Email Service", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from business to external
        draw.line([(500, 280), (550, 280)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(550, 280), (540, 275), (540, 285)], fill=self.COLORS['arrow'])

        # Data Layer
        draw.rounded_rectangle(
            [100, 380, 500, 500],
            radius=10,
            fill=(221, 160, 221),  # Light purple
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((300, 400), "Data Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        database = technologies.get('database', ['PostgreSQL', 'MongoDB'])
        if isinstance(database, str):
            database = [database]
        draw.text((300, 440), ", ".join(database[:3]), fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((300, 470), "ORM / Query Builder", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from business to data
        draw.line([(300, 340), (300, 380)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(300, 380), (295, 370), (305, 370)], fill=self.COLORS['arrow'])

        # Cache/Storage box
        draw.rounded_rectangle([550, 380, 750, 500], radius=10, fill=(255, 182, 193), outline=self.COLORS['border'], width=2)
        draw.text((650, 410), "Cache / Storage", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        draw.text((650, 450), "Redis / Memcached", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((650, 475), "File Storage (S3)", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Arrow from data to cache
        draw.line([(500, 440), (550, 440)], fill=self.COLORS['arrow'], width=2)
        draw.polygon([(550, 440), (540, 435), (540, 445)], fill=self.COLORS['arrow'])

        # Infrastructure box at bottom
        draw.rounded_rectangle(
            [100, 540, 750, 620],
            radius=10,
            fill=(211, 211, 211),  # Light gray
            outline=self.COLORS['border'],
            width=2
        )
        draw.text((425, 560), "Infrastructure Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        draw.text((425, 590), "Docker | Kubernetes | AWS/GCP | CI/CD Pipeline", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        # Security indicator
        draw.rounded_rectangle([800, 200, 1100, 400], radius=10, fill=(255, 255, 224), outline=self.COLORS['border'], width=2)
        draw.text((950, 230), "Security Layer", fill=self.COLORS['primary'], font=self.font_bold, anchor="mm")
        draw.text((950, 270), "• Authentication (JWT)", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((950, 295), "• Authorization (RBAC)", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((950, 320), "• HTTPS/TLS", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((950, 345), "• Input Validation", fill=self.COLORS['text'], font=self.font_small, anchor="mm")
        draw.text((950, 370), "• Rate Limiting", fill=self.COLORS['text'], font=self.font_small, anchor="mm")

        filename = f"system_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        output_dir = self.get_output_dir(project_id)
        filepath = output_dir / filename
        img.save(str(filepath))

        return str(filepath)

    def _generate_placeholder(self, diagram_type: str) -> str:
        """Generate placeholder image when PIL is not available"""
        # Return a path to indicate diagram should be generated
        return f"[{diagram_type} - Placeholder]"

    def generate_all_diagrams(self, project_data: Dict, project_id: str = None) -> Dict[str, str]:
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
            project_id=project_id
        )

        # 2. Class Diagram - DYNAMIC based on tables and code
        classes = self._extract_classes_from_project(project_data)
        diagrams['class'] = self.generate_class_diagram(classes, project_id=project_id)

        # 3. Sequence Diagram - DYNAMIC based on API endpoints
        participants, messages = self._extract_sequence_from_project(project_data)
        diagrams['sequence'] = self.generate_sequence_diagram(participants, messages, project_id=project_id)

        # 4. Activity Diagram - DYNAMIC based on features/workflow
        activities = self._extract_activities_from_project(project_data)
        diagrams['activity'] = self.generate_activity_diagram(activities, project_id=project_id)

        # 5. ER Diagram - DYNAMIC based on database tables
        entities = self._extract_entities_from_project(project_data)
        diagrams['er'] = self.generate_er_diagram(entities, project_id=project_id)

        # 6. DFD Level 0 - DYNAMIC based on project structure
        external_entities, data_stores, data_flows = self._extract_dfd_from_project(project_data)
        diagrams['dfd_0'] = self.generate_dfd(
            level=0,
            processes=[project_name],
            project_id=project_id,
            data_stores=data_stores,
            external_entities=external_entities,
            data_flows=data_flows
        )

        logger.info(f"[UMLGenerator] Generated {len(diagrams)} diagrams for {project_name}")

        return diagrams

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
        """Dynamically extract use cases from features"""
        features = project_data.get('features', [])

        if features:
            # Use actual features as use cases
            use_cases = []
            for feature in features[:8]:
                if isinstance(feature, str):
                    # Clean up feature name
                    uc = feature.strip()
                    if not uc.lower().startswith(('user can', 'ability to', 'the system')):
                        uc = uc.title()
                    use_cases.append(uc[:30])  # Truncate long names
            return use_cases

        # Default use cases based on project type
        project_type = project_data.get('project_type', '').lower()

        if 'ecommerce' in project_type or 'shop' in project_type:
            return ['Browse Products', 'Add to Cart', 'Checkout', 'Track Order', 'Manage Inventory', 'Process Payment']
        elif 'social' in project_type:
            return ['Create Profile', 'Post Content', 'Follow Users', 'Like/Comment', 'Send Message', 'Search Users']
        elif 'education' in project_type or 'learning' in project_type:
            return ['Enroll Course', 'Watch Lectures', 'Take Quiz', 'Submit Assignment', 'View Progress', 'Get Certificate']
        else:
            return ['User Login', 'View Dashboard', 'Manage Data', 'Generate Report', 'Update Settings', 'Logout']

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
            # Default flow
            messages = [
                {'from': 'User', 'to': participants[1], 'message': 'Submit Request'},
                {'from': participants[1], 'to': participants[2], 'message': 'API Call'},
                {'from': participants[2], 'to': participants[3], 'message': 'Query'},
                {'from': participants[3], 'to': participants[2], 'message': 'Result', 'type': 'return'},
                {'from': participants[2], 'to': participants[1], 'message': 'Response', 'type': 'return'},
                {'from': participants[1], 'to': 'User', 'message': 'Display', 'type': 'return'},
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

        # If not enough activities, add defaults
        if len(activities) < 5:
            default_activities = [
                'Load Dashboard',
                'Process Request',
                'Validate Data',
                'Update Records'
            ]
            for act in default_activities:
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
        """Extract class info from project data"""
        classes = []

        # From database tables
        tables = project_data.get('database_tables', [])
        for table in tables[:5]:
            classes.append({
                'name': table.title() if isinstance(table, str) else table.get('name', 'Entity'),
                'attributes': ['id', 'name', 'created_at', 'updated_at'],
                'methods': ['create', 'read', 'update', 'delete'],
                'relationships': []
            })

        # Default classes if none found
        if not classes:
            classes = [
                {
                    'name': 'User',
                    'attributes': ['id', 'name', 'email', 'password'],
                    'methods': ['login', 'logout', 'register'],
                    'relationships': []
                },
                {
                    'name': 'Controller',
                    'attributes': ['routes', 'middleware'],
                    'methods': ['handleRequest', 'validateInput'],
                    'relationships': [{'target': 'Service', 'type': 'association'}]
                },
                {
                    'name': 'Service',
                    'attributes': ['repository'],
                    'methods': ['processData', 'validateBusiness'],
                    'relationships': [{'target': 'Repository', 'type': 'association'}]
                },
                {
                    'name': 'Repository',
                    'attributes': ['database'],
                    'methods': ['find', 'save', 'delete'],
                    'relationships': []
                }
            ]

        return classes

    def _extract_entities_from_project(self, project_data: Dict) -> List[Dict]:
        """Extract entity info from project data"""
        entities = []

        tables = project_data.get('database_tables', [])
        for table in tables[:6]:
            name = table if isinstance(table, str) else table.get('name', 'Entity')
            entities.append({
                'name': name,
                'attributes': ['id', 'name', 'description', 'created_at', 'updated_at'],
                'primary_key': 'id'
            })

        # Default entities
        if not entities:
            entities = [
                {'name': 'User', 'attributes': ['id', 'name', 'email', 'password_hash'], 'primary_key': 'id'},
                {'name': 'Project', 'attributes': ['id', 'title', 'description', 'user_id'], 'primary_key': 'id'},
                {'name': 'Document', 'attributes': ['id', 'name', 'content', 'project_id'], 'primary_key': 'id'},
            ]

        return entities


# Singleton instance
uml_generator = UMLGenerator()
