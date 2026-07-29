import shutil
import os

# Create destination folder
dest = r"C:\Users\Lekhana\Kishore_projects\BharatBuild_Presentations"
os.makedirs(dest, exist_ok=True)

# Source directory
src = r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI"

# PowerPoint files to move
ppt_files = [
    "BharatBuild_AI_Premium_Presentation.pptx",
    "BharatBuild_AI_Presentation.pptx",
    "BharatBuild_Investor_Deck_Complete.pptx",
    "BharatBuild_Investor_Deck_v2.pptx",
    "BharatBuild_Investor_Pitch.pptx",
    "BharatBuild_Investor_Pitch_Final.pptx",
    "BharatBuild_Investor_Pitch_V2.pptx",
    "BharatBuild_Investor_Pitch_V3.pptx",
    "BharatBuild_Investor_Pitch_WithScreenshots.pptx",
    "BharatBuild_Investor_Pitch_v4.pptx",
    "BharatBuild_Investor_Pitch_v5.pptx",
    "BharatBuild_Investor_Pitch_v6.pptx",
    "BharatBuild_Presentation_Final.pptx",
]

# Also check docs folder for workshop pptx
docs_ppts = [
    "docs/BharatBuild_Workshop.pptx",
]

print(f"Moving PowerPoint files to: {dest}\n")

moved = 0
for ppt in ppt_files:
    src_path = os.path.join(src, ppt)
    if os.path.exists(src_path):
        dest_path = os.path.join(dest, ppt)
        shutil.move(src_path, dest_path)
        print(f"Moved: {ppt}")
        moved += 1
    else:
        print(f"Not found: {ppt}")

for ppt in docs_ppts:
    src_path = os.path.join(src, ppt)
    if os.path.exists(src_path):
        filename = os.path.basename(ppt)
        dest_path = os.path.join(dest, filename)
        shutil.move(src_path, dest_path)
        print(f"Moved: {filename}")
        moved += 1

print(f"\n{moved} files moved to: {dest}")
print("\nFiles in Presentations folder:")
for f in sorted(os.listdir(dest)):
    size = os.path.getsize(os.path.join(dest, f))
    print(f"  {f} ({size/1024:.1f} KB)")
