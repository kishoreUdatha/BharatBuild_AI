#!/usr/bin/env python3
"""
CLI Script to Generate Academic Documents for Any Student Project

Usage:
    python generate_academic_docs.py

This will:
1. Analyze the current project codebase
2. Generate all 8 academic documents using Claude AI
3. Save them in academic_documents/ folder
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.modules.agents.project_analyzer import ProjectAnalyzer
from app.modules.agents.docspack_agent import DocsPackAgent


async def main():
    """Main execution function"""

    print("=" * 60)
    print("🎓 ACADEMIC DOCUMENT GENERATOR")
    print("=" * 60)
    print()

    # Get project root (current directory)
    project_root = Path(__file__).parent
    print(f"📁 Project Root: {project_root}")
    print()

    # Step 1: Analyze project
    print("=" * 60)
    print("STEP 1: Analyzing Project Codebase")
    print("=" * 60)

    analyzer = ProjectAnalyzer(str(project_root))
    analysis = analyzer.analyze()

    print(f"\n✅ Analysis Complete!")
    print(f"\n📊 Project Details:")
    print(f"   • Name: {analysis['project_name']}")
    print(f"   • Purpose: {analysis['project_purpose'][:80]}...")
    print(f"   • Domain: {analysis['domain']}")
    print(f"   • Architecture: {analysis['architecture'][:60]}...")
    print(f"\n🛠️ Technology Stack:")
    if analysis['technology_stack']['backend']:
        print(f"   • Backend: {analysis['technology_stack']['backend']}")
    if analysis['technology_stack']['frontend']:
        print(f"   • Frontend: {analysis['technology_stack']['frontend']}")
    if analysis['technology_stack']['database']:
        print(f"   • Database: {analysis['technology_stack']['database']}")
    print(f"\n📦 Modules Found: {len(analysis['modules'])}")
    for module in analysis['modules'][:5]:  # Show first 5
        print(f"   • {module['name']}")
    if len(analysis['modules']) > 5:
        print(f"   ... and {len(analysis['modules']) - 5} more")
    print(f"\n⭐ Features Identified: {len(analysis['features'])}")
    for feature in analysis['features'][:5]:  # Show first 5
        print(f"   • {feature}")
    if len(analysis['features']) > 5:
        print(f"   ... and {len(analysis['features']) - 5} more")

    # Step 2: Generate documents
    print("\n" + "=" * 60)
    print("STEP 2: Generating Academic Documents with Claude AI")
    print("=" * 60)
    print("\n⚠️  This may take 2-3 minutes. Please wait...")
    print()

    agent = DocsPackAgent()

    try:
        documents = await agent.generate_documents(analysis)
        print("✅ All documents generated successfully!")
    except Exception as e:
        print(f"❌ Error generating documents: {e}")
        return

    # Step 3: Save to files
    print("\n" + "=" * 60)
    print("STEP 3: Saving Documents to Files")
    print("=" * 60)
    print()

    output_dir = project_root / "academic_documents"
    output_dir.mkdir(exist_ok=True)

    file_mapping = {
        "abstract": "01_ABSTRACT.md",
        "srs": "02_SRS_DOCUMENT.md",
        "uml": "03_UML_DIAGRAMS.md",
        "erd": "04_ER_DIAGRAM.md",
        "report": "05_PROJECT_REPORT.md",
        "ppt_slides": "06_PPT_SLIDES.md",
        "viva": "07_VIVA_QUESTIONS.md",
        "output_explanation": "08_OUTPUT_EXPLANATION.md"
    }

    for doc_type, filename in file_mapping.items():
        filepath = output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(documents[doc_type])

        # Get file size
        size_kb = filepath.stat().st_size / 1024
        print(f"   ✅ {filename} ({size_kb:.1f} KB)")

    # Summary
    print("\n" + "=" * 60)
    print("🎉 SUCCESS!")
    print("=" * 60)
    print()
    print("📦 Generated Documents:")
    print()
    print("   1. Abstract (3-4 pages)")
    print("   2. SRS Document (IEEE 830-compliant, 20+ pages)")
    print("   3. UML Diagrams (Mermaid format)")
    print("   4. ER Diagram (detailed schema)")
    print("   5. Project Report (30+ pages, 8 chapters)")
    print("   6. PPT Slides (15-18 slides)")
    print("   7. Viva Questions (25+ Q&A)")
    print("   8. Output Explanation (setup & deployment guide)")
    print()
    print(f"📁 Location: {output_dir}/")
    print()
    print("📝 Next Steps:")
    print("   1. Review all generated documents")
    print("   2. Customize with your specific details")
    print("   3. Convert Markdown to PDF using Pandoc")
    print("   4. Prepare for viva using Q&A document")
    print()
    print("=" * 60)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
