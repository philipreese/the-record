import os
import re

for root, _, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith('.svelte'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Replace `{@html ` with `{`
            new_content = content.replace('{@html ', '{')
            new_content = new_content.replace('{@html\n', '{\n')
            
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated {path}")
