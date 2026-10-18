import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('notebook/04_recommender/true_hybrid_recommender_experiment.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i in range(len(nb['cells'])):
    cell = nb['cells'][i]
    if cell['cell_type'] == 'markdown':
        print(f"Cell {i} (MD): {''.join(cell['source'])[:80].strip()}")
    else:
        print(f"Cell {i} (Code): {''.join(cell['source'])[:80].strip()}")
