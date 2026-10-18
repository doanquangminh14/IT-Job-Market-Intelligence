import json

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

def update_nlp_deepdive_notebook():
    nb_path = "notebook/03_nlp_embeddings/nlp_pipeline_deepdive.ipynb"
    print(f"Updating {nb_path}...")
    with open(nb_path, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Check if section 11 already exists
    new_cells = []
    for c in nb["cells"]:
        if "PHẦN 11" in "".join(c.get("source", [])):
            break
        new_cells.append(c)
    nb["cells"] = new_cells

    cells = []

    # Markdown Header for Section 11
    cells.append(create_markdown_cell("""---
### PHẦN 11: KHÁM PHÁ & THỰC NGHIỆM PHÂN BỐ DỮ LIỆU NLP TRÊN TOÀN BỘ 3,349 TIN TUYỂN DỤNG THỰC TẾ

Phần này áp dụng pipeline NLP (bóc tách kỹ năng chuẩn hóa, phân tích mức lương và năm kinh nghiệm) trên **toàn bộ 3,349 tin tuyển dụng thực tế** thu thập từ 3 sàn (TopCV: 2,000, VietnamWorks: 1,218, TopDev: 131) để rút ra các phân bố cốt lõi của thị trường IT Việt Nam:
1. **Phân bố số lượng kỹ năng yêu cầu trên mỗi bài đăng** (Skill density).
2. **Top 25 kỹ năng công nghệ có nhu cầu tuyển dụng cao nhất** (bao gồm các kỹ năng mới cập nhật: Power BI, Tableau, Airflow, Figma, v.v.).
3. **Phân bố mức lương thực tế theo chuyên môn** (Data/AI, Backend, Frontend, DevOps, Mobile).
4. **Phân bố số năm kinh nghiệm yêu cầu** trên thị trường IT."""))

    # Code Cell 1: Extract skills across all 3,349 jobs and calculate distributions
    cells.append(create_code_cell("""# 1. Chạy bóc tách kỹ năng chuẩn hóa trên toàn bộ 3,349 bài tuyển dụng
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

skill_patterns = get_skill_patterns()

# Kết hợp tiêu đề + mô tả + yêu cầu để trích xuất kỹ năng
all_extracted_skills = []
skill_counts_per_job = []

for idx, row in df.iterrows():
    combined_text = f"{str(row.get('title', ''))} {str(row.get('description', ''))} {str(row.get('requirements', ''))}"
    job_skills = set()
    for pattern, skill_name, cat in skill_patterns:
        if pattern.search(combined_text):
            job_skills.add(skill_name)
    all_extracted_skills.append(list(job_skills))
    skill_counts_per_job.append(len(job_skills))

df['extracted_skills'] = all_extracted_skills
df['skill_count'] = skill_counts_per_job

print("=" * 60)
print("THỐNG KÊ MẬT ĐỘ KỸ NĂNG TRÊN 3,349 TIN TUYỂN DỤNG")
print("=" * 60)
print(f"• Trung bình số kỹ năng / bài đăng: {np.mean(skill_counts_per_job):.2f}")
print(f"• Trung vị số kỹ năng:              {np.median(skill_counts_per_job):.1f}")
print(f"• Bài đăng có nhiều kỹ năng nhất:   {np.max(skill_counts_per_job)}")
print(f"• Tỷ lệ bài đăng nhận diện >= 1 kỹ năng: {(np.array(skill_counts_per_job) > 0).mean()*100:.2f}%")

# Vẽ biểu đồ phân bố số kỹ năng trên mỗi JD
plt.figure(figsize=(10, 4.5))
sns.histplot(skill_counts_per_job, bins=25, kde=True, color='#2563EB', discrete=True)
plt.title("Phân Bố Số Lượng Kỹ Năng Yêu Cầu Trên Mỗi Tin Tuyển Dụng (Skill Density)", fontsize=11, fontweight='bold')
plt.xlabel("Số lượng kỹ năng bóc tách được / JD")
plt.ylabel("Số lượng tin tuyển dụng")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.show()"""))

    # Markdown Cell 2
    cells.append(create_markdown_cell("""---
#### 2. Top 25 Kỹ Năng Công Nghệ Nóng Nhất Thị Trường IT Việt Nam

Tổng hợp tần suất xuất hiện của tất cả các kỹ năng được bóc tách từ 3,349 tin tuyển dụng thực tế."""))

    # Code Cell 2: Top Skills Distribution
    cells.append(create_code_cell("""# 2. Xếp hạng Top 25 kỹ năng công nghệ phổ biến nhất
flat_skills = [s for sublist in all_extracted_skills for s in sublist]
skill_freq = Counter(flat_skills)
top_25 = skill_freq.most_common(25)

df_top_skills = pd.DataFrame(top_25, columns=['Skill', 'Frequency'])
df_top_skills['Percentage'] = (df_top_skills['Frequency'] / len(df)) * 100

plt.figure(figsize=(12, 6.5))
sns.barplot(data=df_top_skills, x='Percentage', y='Skill', palette='Blues_r')
plt.title(f"Top 25 Kỹ Năng Xuất Hiện Nhiều Nhất Trong {len(df):,} Việc Làm IT", fontsize=12, fontweight='bold')
plt.xlabel("Tỷ lệ xuất hiện trên tổng số tin tuyển dụng (%)")
plt.ylabel("Kỹ năng chuẩn hóa")
plt.grid(axis='x', alpha=0.3)

for i, row in df_top_skills.iterrows():
    plt.text(row['Percentage'] + 0.3, i, f"{row['Frequency']:,} ({row['Percentage']:.1f}%)", va='center', fontsize=9)

plt.tight_layout()
plt.show()"""))

    # Markdown Cell 3
    cells.append(create_markdown_cell("""---
#### 3. Phân Bố Mức Lương & Số Năm Kinh Nghiệm Theo Nhóm Chuyên Môn

Phân tích mức lương min/max và số năm kinh nghiệm yêu cầu được chuẩn hóa bằng Regex & Entity Extraction."""))

    # Code Cell 3: Salary and Experience Distribution
    cells.append(create_code_cell("""# 3. Phân tích mức lương và kinh nghiệm yêu cầu
# Bóc tách lương và kinh nghiệm cho các bản ghi có dữ liệu
salary_records = []
for idx, row in df.iterrows():
    raw_sal = str(row.get('salary', ''))
    raw_exp = str(row.get('experience', ''))
    
    sal_info = parse_salary(raw_sal)
    exp_info = parse_experience_years(raw_exp)
    
    # Chỉ lấy các tin có mức lương VND cụ thể (triệu đồng)
    if sal_info and sal_info.get('salary_min') and sal_info.get('salary_max'):
        min_mil = sal_info['salary_min'] / 1_000_000
        max_mil = sal_info['salary_max'] / 1_000_000
        if 5 <= min_mil <= 150 and 5 <= max_mil <= 200: # Lọc ngoại lai hợp lý
            salary_records.append({
                'title': row.get('title', ''),
                'salary_min': min_mil,
                'salary_max': max_mil,
                'salary_avg': (min_mil + max_mil) / 2.0,
                'exp_years': exp_info.get('experience_years_min') if exp_info else None
            })

df_sal = pd.DataFrame(salary_records)
print(f"Số lượng tin tuyển dụng có khoảng lương rõ ràng (VND): {len(df_sal):,} tin")
print(f"• Mức lương Min trung bình: {df_sal['salary_min'].mean():.1f} triệu VNĐ")
print(f"• Mức lương Max trung bình: {df_sal['salary_max'].mean():.1f} triệu VNĐ")
print(f"• Mức lương kỳ vọng (Avg):  {df_sal['salary_avg'].mean():.1f} triệu VNĐ")

fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))

sns.histplot(df_sal['salary_avg'], bins=35, kde=True, color='#059669', ax=axes[0])
axes[0].set_title("Phân Bố Mức Lương Trung Bình (Triệu VNĐ/tháng)", fontweight='bold')
axes[0].set_xlabel("Mức lương (Triệu VNĐ)")
axes[0].set_ylabel("Số lượng tin tuyển dụng")
axes[0].grid(alpha=0.3)

# Phân bố số năm kinh nghiệm
valid_exp = df_sal['exp_years'].dropna()
sns.countplot(x=valid_exp.astype(int), palette='Purples', ax=axes[1])
axes[1].set_title("Phân Bố Số Năm Kinh Nghiệm Yêu Cầu Tối Thiểu", fontweight='bold')
axes[1].set_xlabel("Số năm kinh nghiệm tối thiểu")
axes[1].set_ylabel("Số lượng tin tuyển dụng")
axes[1].grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.show()"""))

    nb["cells"].extend(cells)
    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print(f"Successfully updated {nb_path} with {len(cells)} new cells!")

if __name__ == "__main__":
    update_nlp_deepdive_notebook()
