import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('notebook/03_nlp_embeddings/semantic_embedding_experiment.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i in range(len(nb['cells'])):
    cell = nb['cells'][i]
    print(f"Cell {i} ({cell['cell_type']}):")
    print("".join(cell['source'])[:300])
    print("-" * 40)
