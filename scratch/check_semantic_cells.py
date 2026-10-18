import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('notebook/03_nlp_embeddings/semantic_embedding_experiment.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print(f"Total cells in semantic_embedding_experiment: {len(nb['cells'])}")
for i, c in enumerate(nb['cells']):
    first_line = "".join(c.get('source', []))[:80].replace('\n', ' ')
    print(f"[{i:2d}] {c['cell_type']:8s}: {first_line}")
