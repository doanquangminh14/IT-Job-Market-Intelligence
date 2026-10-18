import json
import os
import sys

def create_code_cell(source_code):
    lines = [line + "\n" for line in source_code.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines
    }

def create_markdown_cell(source_md):
    lines = [line + "\n" for line in source_md.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines
    }

def update_semantic_embedding_notebook():
    nb_path = "notebook/03_nlp_embeddings/semantic_embedding_experiment.ipynb"
    print(f"Updating {nb_path}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Check if section 7 already exists
    has_part_7 = any("PHẦN 7" in "".join(c.get("source", [])) for c in nb["cells"])
    if has_part_7:
        print("Section 7 already exists in semantic_embedding_experiment.ipynb, replacing or skipping.")
        # Filter out existing part 7 cells if re-running
        new_cells = []
        for c in nb["cells"]:
            if "PHẦN 7" in "".join(c.get("source", [])):
                break
            new_cells.append(c)
        nb["cells"] = new_cells

    cells = []

    # Markdown Header for Section 7
    cells.append(create_markdown_cell("""---
### PHẦN 7: KHAI PHÁ & PHÂN TÍCH PHÂN BỐ TOÀN BỘ KHÔNG GIAN VECTOR THỰC TẾ (3,249 TIN VIỆC LÀM)

Sau khi thử nghiệm trên tập mẫu nhỏ, chúng ta tiến hành **phân tích chuyên sâu trên toàn bộ 3,249 vector đặc trưng (384 chiều)** được tạo ra từ pipeline sản xuất của dự án (`data/embeddings/jobs_embeddings.npy` và `data/embeddings/jobs_metadata.json`).

Mục tiêu phân tích:
1. **Kiểm tra chuẩn hóa L2 và phân bố độ dài văn bản** giữa các nguồn crawl (TopCV, VietnamWorks, TopDev).
2. **Khảo sát phân bố độ tương đồng Cosine (Pairwise Cosine Similarity Distribution)** trong toàn bộ không gian tuyển dụng IT.
3. **Phân tích ma trận tương đồng ngữ nghĩa giữa các Domain / Career Track (Cross-Track Semantic Distance)** với Centroid Vector.
4. **Chiếu giảm chiều PCA (2D Projection)** để trực quan hóa bản đồ phân cụm việc làm thị trường IT.
5. **Khai phá các cặp công việc đặc biệt (Extreme Pairs Analysis)**: Cặp tin trùng lặp cao nhất và cặp tin xa nhau nhất."""))

    # Code Cell 1: Load production embeddings and check length distribution
    cells.append(create_code_cell("""# 1. Nạp toàn bộ 3,249 vector embeddings & metadata từ dữ liệu sản xuất
import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Thiết lập đường dẫn tới data/embeddings
PROJECT_ROOT = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
if not os.path.exists(os.path.join(PROJECT_ROOT, 'data')):
    # Fallback nếu đang chạy từ root
    PROJECT_ROOT = os.path.abspath(os.getcwd())

EMB_PATH = os.path.join(PROJECT_ROOT, "data", "embeddings", "jobs_embeddings.npy")
META_PATH = os.path.join(PROJECT_ROOT, "data", "embeddings", "jobs_metadata.json")

embeddings = np.load(EMB_PATH)
with open(META_PATH, "r", encoding="utf-8") as f:
    metadata = json.load(f)

print(f" Đã nạp thành công ma trận Embeddings: {embeddings.shape} ({embeddings.shape[0]} việc làm, {embeddings.shape[1]} chiều)")
print(f" Số lượng metadata tương ứng: {len(metadata)}")

# Kiểm tra L2 Norm của các vector
norms = np.linalg.norm(embeddings, axis=1)
print(f" L2 Norm trung bình: {norms.mean():.4f} (Độ lệch chuẩn: {norms.std():.6f})")

# Phân tích độ dài văn bản mô tả theo từng nguồn crawl
df_meta = pd.DataFrame(metadata)
df_meta['text_len'] = df_meta['combined_text'].str.len()
df_meta['word_count'] = df_meta['combined_text'].apply(lambda x: len(str(x).split()))

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
sns.boxplot(data=df_meta, x='source', y='text_len', palette='Blues', ax=axes[0])
axes[0].set_title("Phân Bố Độ Dài Ký Tự (Text Length) Theo Nguồn Tuyển Dụng", fontsize=11, fontweight='bold')
axes[0].set_ylabel("Số lượng ký tự")

sns.histplot(data=df_meta, x='word_count', hue='source', kde=True, bins=40, palette='Set2', ax=axes[1])
axes[1].set_title("Phân Bố Số Lượng Từ (Word Count) Của Tin Tuyển Dụng", fontsize=11, fontweight='bold')
axes[1].set_xlabel("Số từ")
plt.tight_layout()
plt.show()

print("\nThống kê độ dài văn bản theo sàn:")
print(df_meta.groupby('source')['word_count'].describe()[['count', 'mean', 'std', 'min', '50%', 'max']])"""))

    # Markdown Cell 2
    cells.append(create_markdown_cell("""---
#### 2. Phân Bố Độ Tương Đồng Cosine (Pairwise Cosine Similarity Distribution)

Một vấn đề phổ biến trong không gian vector đa chiều (như 384d của MiniLM) là **Hubness Problem** hoặc **Semantic Congestion** (các vector bị co cụm lại, khiến độ tương đồng trung bình quá cao hoặc quá thấp). 

Đoạn code dưới đây lấy mẫu ngẫu nhiên 1,000 công việc (tương đương $\\approx 500,000$ cặp khoảng cách) để tính toán hàm mật độ xác suất của Cosine Similarity."""))

    # Code Cell 2: Pairwise cosine distribution
    cells.append(create_code_cell("""# 2. Tính toán phân bố Pairwise Cosine Similarity trên 1,000 tin tuyển dụng ngẫu nhiên
from sklearn.metrics.pairwise import cosine_similarity

np.random.seed(42)
sample_indices = np.random.choice(len(embeddings), size=min(1000, len(embeddings)), replace=False)
sample_embs = embeddings[sample_indices]

# Tính ma trận tương đồng Cosine
cos_sim_matrix = cosine_similarity(sample_embs)
# Lấy nửa trên của ma trận (bỏ đường chéo chính)
triu_indices = np.triu_indices(len(sample_embs), k=1)
pairwise_similarities = cos_sim_matrix[triu_indices]

# Tính các chỉ số thống kê
sim_mean = np.mean(pairwise_similarities)
sim_std = np.std(pairwise_similarities)
sim_median = np.median(pairwise_similarities)
p5, p95 = np.percentile(pairwise_similarities, [5, 95])

print("=" * 60)
print("THỐNG KÊ PHÂN BỐ ĐỘ TƯƠNG ĐỒNG COSINE (N = 499,500 cặp)")
print("=" * 60)
print(f"• Mean (Trung bình):      {sim_mean:.4f}")
print(f"• Median (Trung vị):       {sim_median:.4f}")
print(f"• Standard Deviation:     {sim_std:.4f}")
print(f"• 5th Percentile (P5):    {p5:.4f}")
print(f"• 95th Percentile (P95):  {p95:.4f}")
print(f"• Min - Max:              {pairwise_similarities.min():.4f} - {pairwise_similarities.max():.4f}")

# Vẽ biểu đồ phân phối
plt.figure(figsize=(10, 4.5))
sns.histplot(pairwise_similarities, bins=60, kde=True, color='#2563EB', stat="density")
plt.axvline(sim_mean, color='red', linestyle='--', linewidth=1.5, label=f'Mean = {sim_mean:.3f}')
plt.axvline(sim_median, color='orange', linestyle=':', linewidth=1.5, label=f'Median = {sim_median:.3f}')
plt.axvline(p5, color='gray', linestyle='-.', alpha=0.7, label=f'P5={p5:.2f}, P95={p95:.2f}')
plt.axvline(p95, color='gray', linestyle='-.', alpha=0.7)

plt.title("Phân Bố Xác Suất Của Độ Tương Đồng Cosine Giữa Các Tin Tuyển Dụng IT", fontsize=12, fontweight='bold')
plt.xlabel("Cosine Similarity")
plt.ylabel("Mật độ xác suất (Density)")
plt.legend(frameon=True)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 3
    cells.append(create_markdown_cell("""---
#### 3. Ma Trận Khoảng Cách Ngữ Nghĩa Giữa Các Career Track / Domain (Cross-Track Centroid Heatmap)

Thị trường IT có nhiều chuyên môn khác nhau: Backend, Frontend, Data Engineer/Analyst, AI/ML, DevOps, Mobile, QA/QC.
Chúng ta gom nhóm các bài tuyển dụng theo chuyên môn, tính **Vector trọng tâm (Centroid Vector)** của từng chuyên môn trong không gian 384 chiều:
$$\\vec{c}_{track} = \\frac{1}{N} \\sum_{i \\in track} \\vec{v}_i$$
Sau đó tính toán mức độ gần gũi ngữ nghĩa giữa các lĩnh vực."""))

    # Code Cell 3: Cross track centroid heatmap
    cells.append(create_code_cell("""# 3. Phân tích tương quan ngữ nghĩa giữa các Domain / Career Track
# Nhận diện chuyên môn bài đăng dựa vào title và kỹ năng
def assign_track(title, skills):
    t = str(title).lower()
    s = [str(x).lower() for x in (skills or [])]
    
    if any(k in t for k in ['ai', 'machine learning', 'deep learning', 'nlp', 'computer vision', 'data science']):
        return 'AI / Machine Learning'
    if any(k in t for k in ['data engineer', 'data analyst', 'bi developer', 'big data', 'etl', 'sql']) or any(x in s for x in ['power bi', 'tableau', 'spark', 'hadoop']):
        return 'Data / Business Intelligence'
    if any(k in t for k in ['devops', 'cloud', 'aws', 'sre', 'system', 'kubernetes', 'infrastructure']):
        return 'DevOps / Cloud'
    if any(k in t for k in ['mobile', 'android', 'ios', 'flutter', 'react native']):
        return 'Mobile App Dev'
    if any(k in t for k in ['qa', 'qc', 'tester', 'test', 'kiem thu', 'automation test']):
        return 'QA / Software Testing'
    if any(k in t for k in ['frontend', 'front end', 'react', 'vue', 'angular']):
        return 'Frontend Dev'
    if any(k in t for k in ['backend', 'back end', 'java', 'golang', 'c#', '.net', 'php', 'python', 'node']):
        return 'Backend Dev'
    return 'Other / General Software'

# Phân loại track cho 3,249 việc làm
tracks = [assign_track(m.get('title', ''), m.get('skills', [])) for m in metadata]
df_meta['track'] = tracks

# Lấy các track chính (bỏ Other)
major_tracks = [
    'Backend Dev', 'Frontend Dev', 'Mobile App Dev', 
    'DevOps / Cloud', 'Data / Business Intelligence', 
    'AI / Machine Learning', 'QA / Software Testing'
]

centroids = {}
for tr in major_tracks:
    idxs = [i for i, t in enumerate(tracks) if t == tr]
    if idxs:
        # Vector trung bình chuẩn hóa L2
        c_vec = np.mean(embeddings[idxs], axis=0)
        c_vec = c_vec / np.linalg.norm(c_vec)
        centroids[tr] = c_vec
        print(f"• Track '{tr}': {len(idxs)} việc làm")

# Ma trận tương đồng giữa các Centroid
track_names = list(centroids.keys())
c_matrix = np.array([centroids[tr] for tr in track_names])
sim_matrix = cosine_similarity(c_matrix)

# Vẽ Heatmap
plt.figure(figsize=(9, 7))
sns.heatmap(sim_matrix, annot=True, fmt=".3f", cmap="YlGnBu",
            xticklabels=track_names, yticklabels=track_names,
            cbar_kws={'label': 'Cosine Similarity'})
plt.title("Ma Trận Tương Đồng Ngữ Nghĩa Giữa Các Nhóm Nghề IT (Cross-Track Centroid)", fontsize=11, fontweight='bold')
plt.xticks(rotation=30, ha='right')
plt.yticks(rotation=0)
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 4
    cells.append(create_markdown_cell("""---
#### 4. Chiếu Giảm Chiều Không Gian Ngữ Nghĩa Về 2D (PCA Projection)

Để có cái nhìn trực quan về sự phân bố và phân cụm của toàn bộ 3,249 tin việc làm, chúng ta dùng **Principal Component Analysis (PCA)** để nén từ 384 chiều về 2 chiều đại diện lớn nhất."""))

    # Code Cell 4: PCA visualization
    cells.append(create_code_cell("""# 4. Trực quan hóa 2D không gian ngữ nghĩa bằng PCA
from sklearn.decomposition import PCA

pca = PCA(n_components=2, random_state=42)
embs_2d = pca.fit_transform(embeddings)

print(f"Tỷ lệ phương sai giải thích được của 2 thành phần chính: {pca.explained_variance_ratio_ * 100}%")
print(f"Tổng phương sai lưu giữ trên 2D: {np.sum(pca.explained_variance_ratio_) * 100:.2f}%")

df_plot = pd.DataFrame({
    'PCA1': embs_2d[:, 0],
    'PCA2': embs_2d[:, 1],
    'Track': df_meta['track']
})

# Lọc chỉ hiển thị các track chính
df_plot_filtered = df_plot[df_plot['Track'].isin(major_tracks)]

plt.figure(figsize=(12, 8))
palette = sns.color_palette("tab10", len(major_tracks))
sns.scatterplot(
    data=df_plot_filtered,
    x='PCA1', y='PCA2',
    hue='Track',
    palette=palette,
    alpha=0.6,
    s=35,
    edgecolor='none'
)

# Đánh dấu tâm cụm của từng nhóm
for tr in major_tracks:
    sub = df_plot[df_plot['Track'] == tr]
    if len(sub) > 0:
        plt.scatter(sub['PCA1'].mean(), sub['PCA2'].mean(), color='black', marker='X', s=120)
        plt.annotate(
            tr, 
            (sub['PCA1'].mean(), sub['PCA2'].mean()),
            textcoords="offset points", 
            xytext=(0, 7), 
            ha='center', 
            fontsize=9, 
            fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.7)
        )

plt.title("Bản Đồ Không Gian Ngữ Nghĩa Của 3,249 Việc Làm IT (PCA 2D Projection)", fontsize=13, fontweight='bold')
plt.xlabel(f"PCA Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}%)")
plt.ylabel(f"PCA Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}%)")
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 5
    cells.append(create_markdown_cell("""---
#### 5. Khai Phá Các Cặp Tin Tuyển Dụng Đặc Biệt (Extreme Pairs Analysis)

Một ứng dụng giá trị của Semantic Embedding là:
- **Phát hiện trùng lặp (Near-Duplicate Detection)**: Tìm các bài tuyển dụng có Cosine Similarity $\\ge 0.95$ (do cùng 1 công ty đăng lên nhiều sàn TopCV, VietnamWorks, TopDev với tiêu đề hơi khác nhau).
- **Phát hiện đối nghịch ngữ nghĩa**: Tìm các vị trí công việc có khoảng cách xa nhất trong ngành IT."""))

    # Code Cell 5: Extreme pairs
    cells.append(create_code_cell("""# 5. Khai phá các cặp việc làm đặc biệt (Highest vs Lowest Similarity)
# Lấy mẫu 800 tin để tìm kiếm nhanh các cặp cực trị
np.random.seed(123)
sub_idx = np.random.choice(len(embeddings), size=min(800, len(embeddings)), replace=False)
sub_embs = embeddings[sub_idx]
sub_sim = cosine_similarity(sub_embs)

# Nửa trên ma trận
r_idx, c_idx = np.triu_indices(len(sub_embs), k=1)
sim_values = sub_sim[r_idx, c_idx]

# Sắp xếp chỉ số
sorted_args = np.argsort(sim_values)

print("=" * 80)
print("TOP 3 CẶP VIỆC LÀM TRÙNG LẶP / TƯƠNG ĐỒNG CAO NHẤT (NEAR-DUPLICATES)")
print("=" * 80)
for i in range(1, 4):
    pair_pos = sorted_args[-i]
    idx1 = sub_idx[r_idx[pair_pos]]
    idx2 = sub_idx[c_idx[pair_pos]]
    score = sim_values[pair_pos]
    m1, m2 = metadata[idx1], metadata[idx2]
    print(f"\n[Cặp {i} - Cosine: {score:.4f}]")
    print(f"  Tin A ({m1.get('source')}): [{m1.get('company')}] {m1.get('title')}")
    print(f"  Tin B ({m2.get('source')}): [{m2.get('company')}] {m2.get('title')}")

print("\n" + "=" * 80)
print("TOP 3 CẶP VIỆC LÀM KHÁC BIỆT NHẤT VỀ MẶT NGỮ NGHĨA")
print("=" * 80)
for i in range(3):
    pair_pos = sorted_args[i]
    idx1 = sub_idx[r_idx[pair_pos]]
    idx2 = sub_idx[c_idx[pair_pos]]
    score = sim_values[pair_pos]
    m1, m2 = metadata[idx1], metadata[idx2]
    print(f"\n[Cặp {i+1} - Cosine: {score:.4f}]")
    print(f"  Tin A ({m1.get('source')}): [{m1.get('company')}] {m1.get('title')}")
    print(f"  Tin B ({m2.get('source')}): [{m2.get('company')}] {m2.get('title')}")"""))

    nb["cells"].extend(cells)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Successfully updated {nb_path} with {len(cells)} new cells!")


def update_cf_notebook():
    nb_path = "notebook/04_recommender/collaborative_filtering_experiment.ipynb"
    print(f"Updating {nb_path}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Check if section 8 already exists
    has_part_8 = any("PHẦN 8" in "".join(c.get("source", [])) for c in nb["cells"])
    if has_part_8:
        print("Section 8 already exists in collaborative_filtering_experiment.ipynb, trimming.")
        new_cells = []
        for c in nb["cells"]:
            if "PHẦN 8" in "".join(c.get("source", [])):
                break
            new_cells.append(c)
        nb["cells"] = new_cells

    cells = []

    # Markdown Header for Section 8
    cells.append(create_markdown_cell("""---
## 8. Phân Tích Chuyên Sâu: Phân Bố Tương Tác & Đánh Giá Năng Lực TruncatedSVD

Phần này thực hiện phân tích thực nghiệm nâng cao trên **toàn bộ 22,032 bản ghi tương tác** giữa 800 ứng viên và các việc làm thực tế:
1. **Phân tích độ thưa (Matrix Sparsity) và phân bố Long-tail** của mức độ quan tâm công việc.
2. **Khảo sát đường cong phương sai tích lũy (Cumulative Explained Variance Ratio)** theo số lượng thành phần tiềm ẩn $k$.
3. **Đánh giá định lượng trên tập kiểm thử (Test Set)**: RMSE, MAE, Hit Rate@10 và Precision@10.
4. **Phân tích vấn đề Cold-Start** và tỷ lệ bao phủ của mô hình CF."""))

    # Code Cell 1: Sparsity and Long Tail Distribution
    cells.append(create_code_cell("""# 1. Phân tích độ thưa và quy luật phân phối Long-Tail của tương tác
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

print(f"Tổng số lượt tương tác thô: {len(df)}")
print(f"Số lượng người dùng duy nhất: {df['user_id'].nunique()}")
print(f"Số lượng việc làm có tương tác: {df['job_id'].nunique()}")

# Tính độ thưa của ma trận User-Job
n_users = df['user_id'].nunique()
n_jobs = df['job_id'].nunique()
n_ratings = len(df.drop_duplicates(subset=['user_id', 'job_id']))
sparsity = 1.0 - (n_ratings / (n_users * n_jobs))

print(f"Tổng số cặp (User, Job) duy nhất: {n_ratings}")
print(f"Độ thưa của ma trận tương tác (Sparsity): {sparsity * 100:.2f}%")

# Thống kê số lượng tương tác trên mỗi công việc
job_counts = df.groupby('job_id').size().sort_values(ascending=False).values

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))

# Biểu đồ Long-Tail
axes[0].plot(range(len(job_counts)), job_counts, color='#2563EB', linewidth=2)
axes[0].fill_between(range(len(job_counts)), job_counts, color='#93C5FD', alpha=0.4)
axes[0].set_title("Phân Bố Mức Độ Quan Tâm Công Việc (Long-Tail Distribution)", fontsize=11, fontweight='bold')
axes[0].set_xlabel("Thứ hạng công việc (Ranked by popularity)")
axes[0].set_ylabel("Số lượt tương tác")
axes[0].grid(alpha=0.3)

# Biểu đồ phân bố số lượng tương tác trên mỗi ứng viên
user_counts = df.groupby('user_id').size()
sns.histplot(user_counts, bins=25, kde=True, color='#059669', ax=axes[1])
axes[1].set_title("Phân Bố Số Lượt Tương Tác Của Mỗi Ứng Viên", fontsize=11, fontweight='bold')
axes[1].set_xlabel("Số lượt tương tác / ứng viên")
axes[1].set_ylabel("Số lượng ứng viên")
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.show()"""))

    # Markdown Cell 2
    cells.append(create_markdown_cell("""---
### 8.2 Khảo Sát Đường Cong Phương Sai Giải Thích (Explained Variance Curve)

Trong kỹ thuật phân rã ma trận **TruncatedSVD**, siêu tham số quan trọng nhất là số chiều tiềm ẩn $k$ (`n_components`).
- Nếu chọn $k$ quá nhỏ: Mất mát nhiều thông tin sở thích của ứng viên.
- Nếu chọn $k$ quá lớn: Mô hình bị quá khớp (overfitting) vào nhiễu và tốn tài nguyên tính toán.

Dưới đây là thực nghiệm quét giá trị $k \\in [5, 10, 15, 20, 30, 40, 50, 75, 100]$:"""))

    # Code Cell 2: SVD Explained Variance Analysis
    cells.append(create_code_cell("""# 2. Khảo sát tỉ mỉ tỉ lệ phương sai được giải thích (Explained Variance Ratio)
from sklearn.decomposition import TruncatedSVD

candidate_k = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100]
exp_var_ratios = []

for k in candidate_k:
    svd_test = TruncatedSVD(n_components=k, random_state=42)
    svd_test.fit(R)
    total_var = svd_test.explained_variance_ratio_.sum()
    exp_var_ratios.append(total_var)
    print(f"k = {k:3d} | Tổng phương sai lưu giữ: {total_var * 100:.2f}%")

plt.figure(figsize=(10, 5))
plt.plot(candidate_k, [v * 100 for v in exp_var_ratios], marker='o', linewidth=2.5, color='#DC2626')
plt.axvline(30, color='blue', linestyle='--', label='k=30 (Lựa chọn triển khai: 30.64%)')
plt.title("Đường Cong Phương Sai Tích Lũy Của TruncatedSVD Theo Số Chiều Tiềm Ẩn k", fontsize=12, fontweight='bold')
plt.xlabel("Số chiều tiềm ẩn (n_components)")
plt.ylabel("Cumulative Explained Variance (%)")
plt.grid(True, alpha=0.3)
plt.legend(frameon=True)
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 3
    cells.append(create_markdown_cell("""---
### 8.3 Đánh Giá Định Lượng: RMSE & Đánh Giá Top-K Gợi Ý (Hit Rate & Precision@10)

Đánh giá mô hình TruncatedSVD ($k=30$) trên tập Test độc lập:
- **RMSE (Root Mean Squared Error)**: Độ lệch dự đoán điểm rating.
- **Hit Rate@10**: Tỷ lệ người dùng có ít nhất 1 bài đăng tương tác thực tế nằm trong Top 10 gợi ý của mô hình CF.
- **Precision@10**: Tỷ lệ công việc được gợi ý thực sự phù hợp."""))

    # Code Cell 3: Quantitative Evaluation
    cells.append(create_code_cell("""# 3. Đánh giá Top-K Recommendation Metrics
# Dự đoán ma trận hoàn chỉnh R_pred = U * Sigma * V^T
R_dense = R.toarray()
U_matrix = svd_model.transform(R)
R_pred = U_matrix @ svd_model.components_

print(f"Ma trận dự đoán kích thước: {R_pred.shape}")

# Đánh giá Hit Rate@10 và Precision@10 trên mẫu 150 người dùng
test_users = np.random.choice(n_users, size=min(150, n_users), replace=False)
hits = 0
precisions = []

for u in test_users:
    # Các việc làm user thực tế đã tương tác điểm cao (>= 3.0)
    actual_positives = set(np.where(R_dense[u] >= 3.0)[0])
    if not actual_positives:
        continue
        
    # Top 10 việc làm có điểm dự đoán cao nhất
    top10_recs = np.argsort(R_pred[u])[::-1][:10]
    
    # Số lượng trúng
    intersection = actual_positives.intersection(set(top10_recs))
    if len(intersection) > 0:
        hits += 1
    precisions.append(len(intersection) / 10.0)

hit_rate_10 = hits / len(test_users)
avg_precision_10 = np.mean(precisions)

print("=" * 60)
print("KẾT QUẢ ĐÁNH GIÁ CHẤT LƯỢNG GỢI Ý COLLABORATIVE FILTERING")
print("=" * 60)
print(f"• Test Users Evaluated:   {len(test_users)}")
print(f"• Hit Rate@10:            {hit_rate_10 * 100:.2f}%")
print(f"• Mean Precision@10:      {avg_precision_10 * 100:.2f}%")
print(f"• Test RMSE:              {rmse:.4f}")
print(f"• Test MAE:               {mae:.4f}")"""))

    nb["cells"].extend(cells)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Successfully updated {nb_path} with {len(cells)} new cells!")


def update_hybrid_notebook():
    nb_path = "notebook/04_recommender/true_hybrid_recommender_experiment.ipynb"
    print(f"Updating {nb_path}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Check if section 10 already exists
    has_part_10 = any("PHẦN 10" in "".join(c.get("source", [])) for c in nb["cells"])
    if has_part_10:
        print("Section 10 already exists in true_hybrid_recommender_experiment.ipynb, trimming.")
        new_cells = []
        for c in nb["cells"]:
            if "PHẦN 10" in "".join(c.get("source", [])):
                break
            new_cells.append(c)
        nb["cells"] = new_cells

    cells = []

    # Markdown Header for Section 10
    cells.append(create_markdown_cell("""---
## 10. Khám Phá Phân Bố Điểm 3 Thành Phần & Thử Nghiệm Độ Nhạy Trọng Số (Ablation Study)

Trong kiến trúc **True Hybrid Recommender**:
$$\\text{Hybrid Score} = w_{sem} \\cdot S_{sem} + w_{skill} \\cdot S_{skill} + w_{cf} \\cdot S_{cf}$$
với bộ trọng số mặc định là **45% Semantic NLP · 30% Skill Overlap · 25% Collaborative Filtering**.

Phần này đi sâu vào phân tích:
1. **Phân bố thực tế của 3 thành phần điểm** trên toàn bộ 3,249 công việc.
2. **Ma trận tương quan giữa 3 thành phần** để chứng minh tính độc lập và bổ trợ lẫn nhau.
3. **Thực nghiệm quét trọng số (Weight Sensitivity Grid Search)** và đo lường sự dịch chuyển gợi ý (Jaccard Similarity).
4. **Độ phủ danh mục (Catalog Coverage)** trên toàn bộ kho việc làm thị trường."""))

    # Code Cell 1: Score distribution across all jobs
    cells.append(create_code_cell("""# 1. Khảo sát phân bố 3 thành phần điểm trên toàn bộ 3,249 việc làm
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Thu thập điểm Semantic, Skill và CF của toàn bộ kho việc làm đối với hồ sơ Backend Java mẫu
java_candidate_skills = ['Java', 'Spring Boot', 'PostgreSQL', 'Docker', 'Microservices']

# Tính điểm cho toàn bộ N việc làm
all_sem = []
all_ski = []
all_cf  = []

for i, m in enumerate(metadata):
    # 1. Semantic
    s_score = sem_scores[i]
    all_sem.append(s_score)
    
    # 2. Skill Overlap
    j_skills = m.get('skills', [])
    ski_score = compute_skill_score(java_candidate_skills, j_skills)
    all_ski.append(ski_score)
    
    # 3. CF Score
    cf_s = cf_scores[i]
    all_cf.append(cf_s)

df_scores = pd.DataFrame({
    'Semantic (NLP)': all_sem,
    'Skill Overlap': all_ski,
    'Collaborative (CF)': all_cf
})

# Trực quan hóa phân bố
fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

sns.histplot(df_scores['Semantic (NLP)'], bins=40, kde=True, color='#2563EB', ax=axes[0])
axes[0].set_title(f"Semantic NLP Score (Mean: {df_scores['Semantic (NLP)'].mean():.3f})", fontweight='bold')
axes[0].set_xlabel("Điểm ngữ nghĩa [0, 1]")

sns.histplot(df_scores['Skill Overlap'], bins=30, kde=True, color='#059669', ax=axes[1])
axes[1].set_title(f"Skill Overlap Score (Mean: {df_scores['Skill Overlap'].mean():.3f})", fontweight='bold')
axes[1].set_xlabel("Điểm kỹ năng [0, 1]")

sns.histplot(df_scores['Collaborative (CF)'], bins=40, kde=True, color='#D97706', ax=axes[2])
axes[2].set_title(f"CF Score (Mean: {df_scores['Collaborative (CF)'].mean():.3f})", fontweight='bold')
axes[2].set_xlabel("Điểm CF chuẩn hóa [0, 1]")

plt.tight_layout()
plt.show()

print("Thống kê mô tả chi tiết của 3 thành phần điểm:")
print(df_scores.describe().round(4))"""))

    # Markdown Cell 2
    cells.append(create_markdown_cell("""---
### 10.2 Ma Trận Tương Quan Giữa 3 Thành Phần Điểm (Orthogonality Analysis)

Nếu 2 thành phần có hệ số tương quan gần 1.0, chúng mang lại thông tin dư thừa.
Nếu hệ số tương quan thấp hoặc vừa phải (0.1 - 0.4), chúng bổ sung cho nhau rất tốt, khẳng định giá trị của kiến trúc True Hybrid."""))

    # Code Cell 2: Correlation Matrix
    cells.append(create_code_cell("""# 2. Tính ma trận tương quan Pearson và Spearman giữa 3 thành phần
pearson_corr = df_scores.corr(method='pearson')
spearman_corr = df_scores.corr(method='spearman')

fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

sns.heatmap(pearson_corr, annot=True, fmt=".3f", cmap="Blues", ax=axes[0], cbar_kws={'label': 'Pearson r'})
axes[0].set_title("Ma Trận Tương Quan Tuyến Tính (Pearson)", fontweight='bold')

sns.heatmap(spearman_corr, annot=True, fmt=".3f", cmap="Greens", ax=axes[1], cbar_kws={'label': 'Spearman rho'})
axes[1].set_title("Ma Trận Tương Quan Xếp Hạng (Spearman)", fontweight='bold')

plt.tight_layout()
plt.show()

print("Nhận xét về tính trực giao (Orthogonality):")
print(f"• Tương quan giữa Semantic và Skill: {pearson_corr.loc['Semantic (NLP)', 'Skill Overlap']:.3f} (Tương quan dương vừa phải)")
print(f"• Tương quan giữa Semantic và CF:    {pearson_corr.loc['Semantic (NLP)', 'Collaborative (CF)']:.3f} (Tín hiệu bổ trợ độc lập)")
print(f"• Tương quan giữa Skill và CF:       {pearson_corr.loc['Skill Overlap', 'Collaborative (CF)']:.3f}")"""))

    # Markdown Cell 3
    cells.append(create_markdown_cell("""---
### 10.3 Thử Nghiệm Quét Trọng Số (Weight Sensitivity Grid Search)

Thực nghiệm đo lường độ ổn định của danh sách Top 10 gợi ý khi thay đổi tỷ trọng giữa Semantic, Skill và CF qua 8 cấu hình trọng số khác nhau:"""))

    # Code Cell 3: Weight Sensitivity Grid Search
    cells.append(create_code_cell("""# 3. Thực nghiệm khảo sát độ nhạy trọng số (Grid Search Sensitivity)
configurations = [
    {"name": "Pure Semantic",    "w_sem": 1.00, "w_ski": 0.00, "w_cf": 0.00},
    {"name": "Pure Skill",       "w_sem": 0.00, "w_ski": 1.00, "w_cf": 0.00},
    {"name": "Pure CF",          "w_sem": 0.00, "w_ski": 0.00, "w_cf": 1.00},
    {"name": "Semantic + Skill", "w_sem": 0.60, "w_ski": 0.40, "w_cf": 0.00},
    {"name": "Skill Heavy",      "w_sem": 0.30, "w_ski": 0.50, "w_cf": 0.20},
    {"name": "CF Heavy",         "w_sem": 0.30, "w_ski": 0.20, "w_cf": 0.50},
    {"name": "Balanced (Equal)", "w_sem": 0.33, "w_ski": 0.33, "w_cf": 0.34},
    {"name": "True Hybrid (Chính)", "w_sem": 0.45, "w_ski": 0.30, "w_cf": 0.25},
]

top10_sets = {}
for cfg in configurations:
    scores = (
        cfg['w_sem'] * df_scores['Semantic (NLP)'] +
        cfg['w_ski'] * df_scores['Skill Overlap'] +
        cfg['w_cf']  * df_scores['Collaborative (CF)']
    )
    top10_idx = set(scores.nlargest(10).index)
    top10_sets[cfg['name']] = top10_idx

# Tính ma trận Jaccard Similarity giữa các danh sách Top 10
def jaccard(s1, s2):
    return len(s1.intersection(s2)) / len(s1.union(s2))

cfg_names = [c['name'] for c in configurations]
jaccard_matrix = np.zeros((len(configurations), len(configurations)))

for i, n1 in enumerate(cfg_names):
    for j, n2 in enumerate(cfg_names):
        jaccard_matrix[i, j] = jaccard(top10_sets[n1], top10_sets[n2])

plt.figure(figsize=(9, 7))
sns.heatmap(jaccard_matrix, annot=True, fmt=".2f", cmap="Oranges",
            xticklabels=cfg_names, yticklabels=cfg_names)
plt.title("Độ Trùng Lặp (Jaccard Similarity) Của Top 10 Khi Thay Đổi Bộ Trọng Số", fontsize=11, fontweight='bold')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 4
    cells.append(create_markdown_cell("""---
### 10.4 Độ Phủ Danh Mục (Catalog Coverage) & Đánh Giá Tổng Hợp

Đo lường tỷ lệ bao phủ của thuật toán True Hybrid trên toàn bộ kho 3,249 việc làm khi phục vụ đồng thời nhiều nhóm ứng viên khác nhau."""))

    # Code Cell 4: Catalog Coverage
    cells.append(create_code_cell("""# 4. Đo lường Catalog Coverage khi gợi ý cho nhiều nhóm Persona khác nhau
from src.recommender.synthetic_data import PERSONAS_DEF

all_recommended_jobs = set()
top_k_coverage = 20

for p in PERSONAS_DEF:
    p_skills = p['skills']
    p_text = f"Lập trình viên {p['name']}, chuyên môn {', '.join(p_skills)}"
    
    # Encode query
    q_vec = model.encode(p_text)
    q_vec = q_vec / np.linalg.norm(q_vec)
    
    # 1. Semantic
    p_sem = embeddings @ q_vec
    
    # 2. Skill
    p_ski = np.array([compute_skill_score(p_skills, m.get('skills', [])) for m in metadata])
    
    # 3. CF
    p_cf = cf_rec.get_recommendations_for_persona(p['id'], all_job_ids, top_k=len(all_job_ids))
    p_cf_arr = np.array([p_cf.get(jid, 0.0) for jid in all_job_ids])
    
    # True Hybrid
    p_hybrid = 0.45 * p_sem + 0.30 * p_ski + 0.25 * p_cf_arr
    top_indices = np.argsort(p_hybrid)[::-1][:top_k_coverage]
    
    for idx in top_indices:
        all_recommended_jobs.add(metadata[idx].get('job_id', idx))

total_catalog = len(metadata)
covered_jobs = len(all_recommended_jobs)
coverage_pct = (covered_jobs / total_catalog) * 100

print("=" * 65)
print("KẾT QUẢ ĐÁNH GIÁ ĐỘ PHỦ DANH MỤC (CATALOG COVERAGE)")
print("=" * 65)
print(f"• Tổng số việc làm trong kho:            {total_catalog}")
print(f"• Số việc làm được gợi ý cho 10 Persona: {covered_jobs}")
print(f"• Tỷ lệ bao phủ (Catalog Coverage):      {coverage_pct:.2f}%")
print(f"• Trung bình việc làm duy nhất / Persona: {covered_jobs / len(PERSONAS_DEF):.1f}")
print("=" * 65)"""))

    nb["cells"].extend(cells)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Successfully updated {nb_path} with {len(cells)} new cells!")

if __name__ == "__main__":
    update_semantic_embedding_notebook()
    update_cf_notebook()
    update_hybrid_notebook()
