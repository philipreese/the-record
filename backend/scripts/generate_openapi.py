import json
import os
import sys

# Adjust path to import app package
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.append(os.path.join(PROJECT_ROOT, "backend"))

from app.main import app

def main():
    openapi_spec = app.openapi()
    output_path = os.path.join(PROJECT_ROOT, "backend", "openapi.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
    print(f"Generated OpenAPI spec at {output_path}")

if __name__ == "__main__":
    main()
