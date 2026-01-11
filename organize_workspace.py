import os
import shutil
from pathlib import Path

# Config
BASE_DIR = Path(__file__).parent
FOLDERS = {
    "docs": [".md", ".png"],
    "scripts": ["get_", "find_", "debug_", "generate_", "test_image"],
    "tests": ["test_", "health_check"],
    "legacy": ["_legacy", "old_", "copy"],
    "config": ["_config", ".json"],
    "services": ["_publisher", "_manager", "_processor"],
    "core": ["launcher", "worker", "master", "registry", "auto"]
}

# Specific moves to avoid breaking imports (Only moving safe non-code files for now)
# Moving code requires refactoring imports. We will focus on Docs, Scripts, Tests.

MOVES = {
    "docs": ["*.md", "ARCHITECTURE.md", "DEPLOYMENT.md", "README.md", "MAINTENANCE.md"],
    "scripts": ["get_blogger_oauth.py", "get_blogger_tokens.py", "get_facebook_token_guide.py", "get_linkedin_token.py", "find_linkedin_id.py", "debug_facebook_token.py"],
    "tests": ["test_full_system.py", "test_linkedin.py", "test_linkedin_publish.py", "test_image_generator.py"],
    "legacy": ["main_legacy.py"],
    "images/brand_backgrounds": ["background1.png", "background2.png", "background3.png"]
}

def organize():
    print("🧹 Organizing Workspace...")

    # Create directories
    for folder in MOVES.keys():
        target_dir = BASE_DIR / folder
        target_dir.mkdir(parents=True, exist_ok=True)

    # Move files
    for folder, patterns in MOVES.items():
        target_dir = BASE_DIR / folder
        for pattern in patterns:
            for file_path in BASE_DIR.glob(pattern):
                if file_path.is_file() and file_path.name != "organize_workspace.py":
                    dest = target_dir / file_path.name
                    try:
                        shutil.move(str(file_path), str(dest))
                        print(f"Moved: {file_path.name} -> {folder}/")
                    except Exception as e:
                        print(f"Error moving {file_path.name}: {e}")

    print("✅ Organization Complete!")
    print("NOTE: Verify 'image_generator.py' can find backgrounds in images/brand_backgrounds/")

if __name__ == "__main__":
    organize()
