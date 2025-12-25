"""
UML Diagram Generator
Creates UML diagrams (Use Case, Class, Sequence, Activity, ER) as images for PDF embedding
"""

from typing import Dict, List, Optional
import os
import tempfile
from io import BytesIO

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle
    from matplotlib.lines import Line2D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from app.core.logging_config import logger


class UMLDiagramGenerator:
    """
    Generate UML diagrams as images

    Supports:
    - Use Case Diagrams
    - Class Diagrams
    - Sequence Diagrams
    - Activity Diagrams
    - ER Diagrams
    - Component Diagrams
    """

    def __init__(self):
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Matplotlib not available, UML diagrams will be text-based")

    def generate_use_case_diagram(
        self,
        actors: List[str],
        use_cases: List[str],
        relationships: List[Dict],
        output_path: str
    ) -> bool:
        """
        Generate Use Case Diagram

        Args:
            actors: List of actor names
            use_cases: List of use case names
            relationships: List of {actor, use_case} connections
            output_path: Path to save PNG image

        Returns:
            bool: Success status
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_text_placeholder(output_path, "Use Case Diagram")

        try:
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.set_xlim(0, 10)
            ax.set_ylim(0, 10)
            ax.axis('off')

            # Draw system boundary
            system_box = FancyBboxPatch(
                (2, 1), 6, 8,
                boxstyle="round,pad=0.1",
                edgecolor='black',
                facecolor='white',
                linewidth=2
            )
            ax.add_patch(system_box)
            ax.text(5, 9.3, 'System', ha='center', fontsize=14, fontweight='bold')

            # Draw actors (stick figures on left and right)
            actor_positions = {}
            left_actors = actors[:len(actors)//2 + len(actors)%2]
            right_actors = actors[len(actors)//2 + len(actors)%2:]

            y_step = 7 / max(len(left_actors), 1)
            for i, actor in enumerate(left_actors):
                y = 7.5 - i * y_step
                actor_positions[actor] = (1, y)
                self._draw_stick_figure(ax, 1, y)
                ax.text(1, y - 0.5, actor, ha='center', fontsize=10)

            y_step = 7 / max(len(right_actors), 1)
            for i, actor in enumerate(right_actors):
                y = 7.5 - i * y_step
                actor_positions[actor] = (9, y)
                self._draw_stick_figure(ax, 9, y)
                ax.text(9, y - 0.5, actor, ha='center', fontsize=10)

            # Draw use cases (ovals in center)
            use_case_positions = {}
            y_step = 7 / max(len(use_cases), 1)
            for i, uc in enumerate(use_cases):
                y = 7.5 - i * y_step
                use_case_positions[uc] = (5, y)

                ellipse = patches.Ellipse(
                    (5, y), 2.5, 0.8,
                    edgecolor='black',
                    facecolor='lightyellow',
                    linewidth=1.5
                )
                ax.add_patch(ellipse)
                ax.text(5, y, uc, ha='center', va='center', fontsize=9, wrap=True)

            # Draw relationships
            for rel in relationships:
                actor = rel.get('actor')
                use_case = rel.get('use_case')
                if actor in actor_positions and use_case in use_case_positions:
                    x1, y1 = actor_positions[actor]
                    x2, y2 = use_case_positions[use_case]
                    arrow = FancyArrowPatch(
                        (x1, y1), (x2, y2),
                        arrowstyle='-',
                        color='black',
                        linewidth=1,
                        linestyle='--'
                    )
                    ax.add_patch(arrow)

            plt.title('Use Case Diagram', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            logger.info(f"Generated Use Case Diagram: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating use case diagram: {e}", exc_info=True)
            return False

    def generate_class_diagram(
        self,
        classes: List[Dict],
        relationships: List[Dict],
        output_path: str
    ) -> bool:
        """
        Generate Class Diagram

        Args:
            classes: List of {name, attributes, methods}
            relationships: List of {from, to, type} (inheritance, association, etc.)
            output_path: Path to save PNG

        Returns:
            bool: Success
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_text_placeholder(output_path, "Class Diagram")

        try:
            fig, ax = plt.subplots(figsize=(14, 10))
            ax.set_xlim(0, 14)
            ax.set_ylim(0, 10)
            ax.axis('off')

            # Position classes in grid
            class_positions = {}
            cols = min(3, len(classes))
            rows = (len(classes) + cols - 1) // cols

            x_step = 12 / cols
            y_step = 8 / rows

            for i, cls in enumerate(classes):
                col = i % cols
                row = i // cols
                x = 1 + col * x_step + x_step / 2
                y = 8 - row * y_step

                class_positions[cls['name']] = (x, y)

                # Draw class box
                box_width = 3.5
                box_height = 1.2 + len(cls.get('attributes', [])) * 0.15 + len(cls.get('methods', [])) * 0.15

                # Class name section
                name_box = FancyBboxPatch(
                    (x - box_width/2, y), box_width, 0.4,
                    boxstyle="square",
                    edgecolor='black',
                    facecolor='lightblue',
                    linewidth=1.5
                )
                ax.add_patch(name_box)
                ax.text(x, y + 0.2, cls['name'], ha='center', va='center',
                       fontsize=11, fontweight='bold')

                # Attributes section
                attr_height = len(cls.get('attributes', [])) * 0.15 + 0.2
                attr_box = FancyBboxPatch(
                    (x - box_width/2, y - attr_height), box_width, attr_height,
                    boxstyle="square",
                    edgecolor='black',
                    facecolor='white',
                    linewidth=1.5
                )
                ax.add_patch(attr_box)

                y_attr = y - 0.1
                for attr in cls.get('attributes', []):
                    ax.text(x - box_width/2 + 0.1, y_attr, f"- {attr}",
                           ha='left', va='top', fontsize=8)
                    y_attr -= 0.15

                # Methods section
                method_height = len(cls.get('methods', [])) * 0.15 + 0.2
                method_box = FancyBboxPatch(
                    (x - box_width/2, y - attr_height - method_height),
                    box_width, method_height,
                    boxstyle="square",
                    edgecolor='black',
                    facecolor='white',
                    linewidth=1.5
                )
                ax.add_patch(method_box)

                y_method = y - attr_height - 0.1
                for method in cls.get('methods', []):
                    ax.text(x - box_width/2 + 0.1, y_method, f"+ {method}()",
                           ha='left', va='top', fontsize=8)
                    y_method -= 0.15

            # Draw relationships
            for rel in relationships:
                from_cls = rel.get('from')
                to_cls = rel.get('to')
                rel_type = rel.get('type', 'association')

                if from_cls in class_positions and to_cls in class_positions:
                    x1, y1 = class_positions[from_cls]
                    x2, y2 = class_positions[to_cls]

                    if rel_type == 'inheritance':
                        arrowstyle = '-|>'
                    elif rel_type == 'composition':
                        arrowstyle = '-D'
                    else:
                        arrowstyle = '->'

                    arrow = FancyArrowPatch(
                        (x1, y1 - 0.5), (x2, y2 + 0.2),
                        arrowstyle=arrowstyle,
                        color='black',
                        linewidth=1.5
                    )
                    ax.add_patch(arrow)

            plt.title('Class Diagram', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            logger.info(f"Generated Class Diagram: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating class diagram: {e}", exc_info=True)
            return False

    def generate_sequence_diagram(
        self,
        actors: List[str],
        messages: List[Dict],
        output_path: str
    ) -> bool:
        """Generate Sequence Diagram"""
        if not MATPLOTLIB_AVAILABLE:
            return self._create_text_placeholder(output_path, "Sequence Diagram")

        try:
            fig, ax = plt.subplots(figsize=(12, 10))
            ax.set_xlim(0, len(actors) + 1)
            ax.set_ylim(0, len(messages) + 2)
            ax.axis('off')

            # Draw actors at top
            actor_x = {}
            for i, actor in enumerate(actors):
                x = i + 1
                actor_x[actor] = x

                # Actor box
                box = FancyBboxPatch(
                    (x - 0.3, len(messages) + 1.5), 0.6, 0.4,
                    boxstyle="round,pad=0.05",
                    edgecolor='black',
                    facecolor='lightblue',
                    linewidth=1.5
                )
                ax.add_patch(box)
                ax.text(x, len(messages) + 1.7, actor, ha='center', va='center',
                       fontsize=10, fontweight='bold')

                # Lifeline
                ax.plot([x, x], [len(messages) + 1.5, 0.5],
                       'k--', linewidth=1)

            # Draw messages
            for i, msg in enumerate(messages):
                y = len(messages) - i

                from_actor = msg.get('from')
                to_actor = msg.get('to')
                message = msg.get('message', '')

                if from_actor in actor_x and to_actor in actor_x:
                    x1 = actor_x[from_actor]
                    x2 = actor_x[to_actor]

                    # Arrow
                    arrow = FancyArrowPatch(
                        (x1, y), (x2, y),
                        arrowstyle='->',
                        color='black',
                        linewidth=1.5
                    )
                    ax.add_patch(arrow)

                    # Message label
                    ax.text((x1 + x2) / 2, y + 0.1, message,
                           ha='center', va='bottom', fontsize=9)

            plt.title('Sequence Diagram', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            logger.info(f"Generated Sequence Diagram: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating sequence diagram: {e}", exc_info=True)
            return False

    def generate_er_diagram(
        self,
        entities: List[Dict],
        relationships: List[Dict],
        output_path: str
    ) -> bool:
        """Generate ER Diagram"""
        if not MATPLOTLIB_AVAILABLE:
            return self._create_text_placeholder(output_path, "ER Diagram")

        try:
            fig, ax = plt.subplots(figsize=(14, 10))
            ax.set_xlim(0, 14)
            ax.set_ylim(0, 10)
            ax.axis('off')

            # Position entities
            entity_positions = {}
            cols = min(3, len(entities))
            rows = (len(entities) + cols - 1) // cols

            x_step = 12 / cols
            y_step = 8 / rows

            for i, entity in enumerate(entities):
                col = i % cols
                row = i // cols
                x = 1 + col * x_step + x_step / 2
                y = 8 - row * y_step

                entity_positions[entity['name']] = (x, y)

                # Draw entity rectangle
                box_width = 3
                box_height = 0.8 + len(entity.get('attributes', [])) * 0.15

                # Entity name
                name_box = FancyBboxPatch(
                    (x - box_width/2, y), box_width, 0.4,
                    boxstyle="square",
                    edgecolor='black',
                    facecolor='lightgreen',
                    linewidth=2
                )
                ax.add_patch(name_box)
                ax.text(x, y + 0.2, entity['name'], ha='center', va='center',
                       fontsize=11, fontweight='bold')

                # Attributes
                attr_box = FancyBboxPatch(
                    (x - box_width/2, y - box_height + 0.4), box_width, box_height - 0.4,
                    boxstyle="square",
                    edgecolor='black',
                    facecolor='white',
                    linewidth=2
                )
                ax.add_patch(attr_box)

                y_attr = y - 0.1
                for attr in entity.get('attributes', []):
                    ax.text(x - box_width/2 + 0.1, y_attr, attr,
                           ha='left', va='top', fontsize=8)
                    y_attr -= 0.15

            # Draw relationships
            for rel in relationships:
                from_entity = rel.get('from')
                to_entity = rel.get('to')
                rel_type = rel.get('type', '1:N')

                if from_entity in entity_positions and to_entity in entity_positions:
                    x1, y1 = entity_positions[from_entity]
                    x2, y2 = entity_positions[to_entity]

                    # Draw line
                    ax.plot([x1, x2], [y1 - 0.3, y2 + 0.2], 'k-', linewidth=2)

                    # Relationship label
                    mid_x = (x1 + x2) / 2
                    mid_y = (y1 + y2) / 2
                    ax.text(mid_x, mid_y, rel_type, ha='center', va='center',
                           fontsize=9, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

            plt.title('ER Diagram', fontsize=16, fontweight='bold', pad=20)
            plt.tight_layout()
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            logger.info(f"Generated ER Diagram: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error generating ER diagram: {e}", exc_info=True)
            return False

    def _draw_stick_figure(self, ax, x, y, size=0.3):
        """Draw a simple stick figure for actors"""
        # Head
        circle = Circle((x, y), size/3, edgecolor='black', facecolor='white', linewidth=1.5)
        ax.add_patch(circle)

        # Body
        ax.plot([x, x], [y - size/3, y - size], 'k-', linewidth=1.5)

        # Arms
        ax.plot([x - size/2, x + size/2], [y - size/2, y - size/2], 'k-', linewidth=1.5)

        # Legs
        ax.plot([x, x - size/3], [y - size, y - size - size/2], 'k-', linewidth=1.5)
        ax.plot([x, x + size/3], [y - size, y - size - size/2], 'k-', linewidth=1.5)

    def _create_text_placeholder(self, output_path: str, diagram_type: str) -> bool:
        """Create a text-based placeholder when matplotlib not available"""
        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f"{diagram_type}\n(Diagram visualization requires matplotlib)",
                   ha='center', va='center', fontsize=14)
            ax.axis('off')
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close()
            return True
        except Exception as e:
            logger.warning(f"Could not generate diagram: {e}")
            return False


# Singleton instance
diagram_generator = UMLDiagramGenerator()
