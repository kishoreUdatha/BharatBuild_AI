import shutil
import os

# Create destination folder
dest = r"C:\Users\Lekhana\Kishore_projects\MOU"
os.makedirs(dest, exist_ok=True)

# Files to move
files = [
    r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI\docs\MOU_SmartGrow_Scient.md",
    r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI\docs\MOU_SmartGrow_Scient.docx",
    r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI\docs\MOU_SmartGrow_Scient_Updated.docx",
    r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI\docs\SmartGrow_Training_Curriculum.md",
    r"C:\Users\Lekhana\Kishore_projects\BharatBuild_AI\docs\SmartGrow_Training_Curriculum.docx",
]

for f in files:
    if os.path.exists(f):
        filename = os.path.basename(f)
        dest_path = os.path.join(dest, filename)
        shutil.move(f, dest_path)
        print(f"Moved: {filename}")
    else:
        print(f"Not found: {f}")

print(f"\nFiles moved to: {dest}")
print("\nFiles in MOU folder:")
for f in os.listdir(dest):
    print(f"  - {f}")
