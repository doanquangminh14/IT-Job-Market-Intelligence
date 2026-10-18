import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('notebook/03_nlp_embeddings/nlp_pipeline_deepdive.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print("Cell 2 source:")
print("".join(nb['cells'][2]['source']))
