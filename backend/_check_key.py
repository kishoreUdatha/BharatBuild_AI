import sys, os
os.chdir('D:/Smartgrow Projects/BharatBuild_AI/backend')
sys.path.insert(0, 'D:/Smartgrow Projects/BharatBuild_AI/backend')

# Force dotenv to load from correct location
from dotenv import load_dotenv
load_dotenv('D:/Smartgrow Projects/BharatBuild_AI/backend/.env', override=True)

from app.core.config import settings

key = settings.ANTHROPIC_API_KEY
print(f"Key length: {len(key)}")
print(f"Starts with: {key[:20]}")
print(f"Ends with: {key[-15:]}")
print(f"Has leading/trailing spaces: {key != key.strip()}")
print(f"Has newline: {chr(10) in key or chr(13) in key}")
print(f"USE_MOCK_CLAUDE: {settings.USE_MOCK_CLAUDE}")

# Also check if key looks valid format
if key.startswith("sk-ant-api03-"):
    print("Format: VALID (sk-ant-api03-...)")
else:
    print(f"Format: UNEXPECTED (starts with '{key[:13]}')")
