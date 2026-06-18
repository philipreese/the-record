import json
import re

with open('backend/data/narrative_templates.json', 'r') as f:
    data = json.load(f)

def process_node(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'text' and isinstance(v, str):
                # Replace <span class="...">...</span> with *...*
                new_text = re.sub(r'<span[^>]*>(.*?)</span>', r'*\1*', v)
                node[k] = new_text
            else:
                process_node(v)
    elif isinstance(node, list):
        for item in node:
            process_node(item)

process_node(data)

with open('backend/data/narrative_templates.json', 'w') as f:
    json.dump(data, f, indent=2)
