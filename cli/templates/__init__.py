"""
Project Templates for BharatBuild CLI

Includes:
- AI/ML Project Templates
- IEEE Standard Documentation Templates for Student Projects
- Extended IEEE Templates (60-80 pages for College Submissions)
- Word/PDF Document Generation with UML Diagrams
"""

from cli.templates.ai_templates import AI_ML_TEMPLATES, get_template, list_templates
from cli.templates.ieee_templates import (
    IEEE_TEMPLATES,
    ProjectInfo,
    generate_ieee_document,
    generate_all_ieee_documents,
    list_ieee_templates
)

# Extended IEEE Templates (60-80 pages for college submissions)
from cli.templates.ieee_templates_extended import (
    EXTENDED_IEEE_TEMPLATES,
    ExtendedProjectInfo,
    generate_extended_srs,
    generate_extended_sdd,
    generate_extended_test,
    generate_feasibility_study,
    generate_literature_survey,
    generate_all_extended_documents,
    IEEE_830_SRS_EXTENDED,
    IEEE_1016_SDD_EXTENDED,
    IEEE_829_TEST_EXTENDED,
    FEASIBILITY_STUDY_TEMPLATE,
    LITERATURE_SURVEY_TEMPLATE
)

# Document generation (Word, PDF, UML)
try:
    from cli.templates.document_generator import (
        WordDocumentGenerator,
        PDFDocumentGenerator,
        UMLGenerator,
        DocumentStyle,
        check_dependencies
    )
    from cli.templates.ieee_word_generator import (
        IEEEWordGenerator,
        generate_ieee_word_document,
        generate_all_ieee_word_documents
    )
    DOCUMENT_GENERATION_AVAILABLE = True
except ImportError:
    DOCUMENT_GENERATION_AVAILABLE = False

__all__ = [
    # AI/ML Templates
    "AI_ML_TEMPLATES",
    "get_template",
    "list_templates",
    # IEEE Templates (Markdown) - Standard
    "IEEE_TEMPLATES",
    "ProjectInfo",
    "generate_ieee_document",
    "generate_all_ieee_documents",
    "list_ieee_templates",
    # Extended IEEE Templates (60-80 pages for college)
    "EXTENDED_IEEE_TEMPLATES",
    "ExtendedProjectInfo",
    "generate_extended_srs",
    "generate_extended_sdd",
    "generate_extended_test",
    "generate_feasibility_study",
    "generate_literature_survey",
    "generate_all_extended_documents",
    "IEEE_830_SRS_EXTENDED",
    "IEEE_1016_SDD_EXTENDED",
    "IEEE_829_TEST_EXTENDED",
    "FEASIBILITY_STUDY_TEMPLATE",
    "LITERATURE_SURVEY_TEMPLATE",
    # Document Generation (Word/PDF)
    "DOCUMENT_GENERATION_AVAILABLE",
]

# Add document generation exports if available
if DOCUMENT_GENERATION_AVAILABLE:
    __all__.extend([
        "WordDocumentGenerator",
        "PDFDocumentGenerator",
        "UMLGenerator",
        "DocumentStyle",
        "check_dependencies",
        "IEEEWordGenerator",
        "generate_ieee_word_document",
        "generate_all_ieee_word_documents",
    ])
