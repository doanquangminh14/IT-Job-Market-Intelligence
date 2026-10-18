import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

files = [
    'notebook/03_nlp_embeddings/nlp_pipeline_deepdive.ipynb',
    'notebook/03_nlp_embeddings/semantic_embedding_experiment.ipynb',
    'notebook/04_recommender/collaborative_filtering_experiment.ipynb',
    'notebook/04_recommender/true_hybrid_recommender_experiment.ipynb'
]

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        nb = json.load(fp)
    print(f"\n==================== {f} ({len(nb['cells'])} cells) ====================")
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] == 'markdown':
            src = "".join(c.get('source', []))
            lines = [l.strip() for l in src.split('\n') if l.strip().startswith('#')]
            if lines:
                print(f"  [{i:2d}] MD: {lines[0]}")
        else:
            first_code = "".join(c.get('source', []))[:60].replace('\n', ' ')
            if any(k in first_code for k in ['Khai phá', 'Phân tích', 'Đánh giá', 'Thực nghiệm', 'Ma trận', 'Bản Đồ', 'Top 25', 'Đo lường']):
                print(f"  [{i:2d}] Code: {first_code}")
