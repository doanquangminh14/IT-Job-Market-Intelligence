import json
import os
import sys

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
nb_path = os.path.join(PROJECT_ROOT, "notebook", "05_recommender", "content_base_filtering.ipynb")

cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# 📊 Kiểm Tra Thông Số Cơ Bản Tập Dữ Liệu Sạch (Content-Based Data Inspection)\n",
            "\n",
            "Notebook này nạp tập dữ liệu sạch vừa lưu từ `data/notebook/content_base/jobs_clean.csv` và kiểm tra toàn diện các thông số cơ bản:\n",
            "1. **Cấu trúc & Kích thước dữ liệu**\n",
            "2. **Độ đầy đủ (Missing rate / Completeness)**\n",
            "3. **Thống kê mô tả các trường số (Lương, Kinh nghiệm)**\n",
            "4. **Phân bố các trường phân loại (Thành phố, Work Mode, Employment Type, Is Active)**\n",
            "5. **Phân tích đặc trưng văn bản & Kỹ năng (Description length, Top Skills)**"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Nạp tập dữ liệu sạch từ file CSV"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "\n",
            "# 1. Đường dẫn file CSV sạch vừa lưu\n",
            "csv_path = os.path.abspath('../../data/notebook/content_base/jobs_clean.csv')\n",
            "if not os.path.exists(csv_path):\n",
            "    csv_path = os.path.abspath('data/notebook/content_base/jobs_clean.csv')\n",
            "\n",
            "# 2. Đọc file CSV\n",
            "jobs = pd.read_csv(csv_path)\n",
            "print(f\"✅ Đã nạp thành công: {jobs.shape[0]:,} dòng x {jobs.shape[1]} cột\")\n",
            "print(\"Danh sách các cột:\", list(jobs.columns))\n",
            "jobs.head(5)\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Kiểm tra Cấu trúc dữ liệu & Kiểu dữ liệu (Data Types)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print(\"=== TỔNG QUAN KIỂU DỮ LIỆU & BỘ NHỚ ===\")\n",
            "jobs.info()\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. Kiểm tra Độ đầy đủ dữ liệu (Completeness & Missing Rate)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "total_rows = len(jobs)\n",
            "missing_stats = []\n",
            "\n",
            "for col in jobs.columns:\n",
            "    null_count = jobs[col].isnull().sum()\n",
            "    # Đếm thêm chuỗi rỗng nếu là kiểu object/string\n",
            "    empty_count = (jobs[col].astype(str).str.strip() == '').sum() if jobs[col].dtype == 'object' else 0\n",
            "    total_missing = null_count + empty_count\n",
            "    missing_pct = (total_missing / total_rows) * 100\n",
            "    valid_pct = 100.0 - missing_pct\n",
            "    \n",
            "    missing_stats.append({\n",
            "        'Cột': col,\n",
            "        'Số dòng thiếu': total_missing,\n",
            "        'Tỷ lệ thiếu (%)': round(missing_pct, 2),\n",
            "        'Độ đầy đủ (%)': round(valid_pct, 2)\n",
            "    })\n",
            "\n",
            "df_missing = pd.DataFrame(missing_stats).sort_values(by='Độ đầy đủ (%)', ascending=False)\n",
            "display(df_missing)\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 4. Thống kê mô tả các trường số (Mức lương & Kinh nghiệm)\n",
            "\n",
            "Quy đổi cột lương sang đơn vị **triệu VNĐ/tháng** để dễ quan sát phân bố mức lương tối thiểu và tối đa."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Thống kê mô tả số năm kinh nghiệm\n",
            "print(\"=== PHÂN BỐ SỐ NĂM KINH NGHIỆM (NĂM) ===\")\n",
            "display(jobs[['experience_min', 'experience_max']].describe().round(2))\n",
            "\n",
            "# Thống kê mức lương theo đơn vị triệu VNĐ/tháng\n",
            "print(\"\\n=== PHÂN BỐ MỨC LƯƠNG (TRIỆU VNĐ/THÁNG) ===\")\n",
            "salary_summary = pd.DataFrame({\n",
            "    'Lương tối thiểu (triệu VNĐ)': (jobs['salary_min'] / 1_000_000).describe(),\n",
            "    'Lương tối đa (triệu VNĐ)': (jobs['salary_max'] / 1_000_000).describe()\n",
            "}).round(2)\n",
            "display(salary_summary)\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 5. Phân bố các trường phân loại (Categorical Distribution)"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 1. Phân bố theo thành phố\n",
            "print(\"=== 1. PHÂN BỐ THEO THÀNH PHỐ (CITY) ===\")\n",
            "city_df = jobs['city'].value_counts(dropna=False).reset_index()\n",
            "city_df.columns = ['Thành phố', 'Số lượng']\n",
            "city_df['Tỷ lệ (%)'] = (city_df['Số lượng'] / len(jobs) * 100).round(2)\n",
            "display(city_df)\n",
            "\n",
            "# 2. Phân bố theo mô hình làm việc\n",
            "print(\"\\n=== 2. PHÂN BỐ THEO MÔ HÌNH LÀM VIỆC (WORK_MODE) ===\")\n",
            "wm_df = jobs['work_mode'].value_counts(dropna=False).reset_index()\n",
            "wm_df.columns = ['Work Mode', 'Số lượng']\n",
            "wm_df['Tỷ lệ (%)'] = (wm_df['Số lượng'] / len(jobs) * 100).round(2)\n",
            "display(wm_df)\n",
            "\n",
            "# 3. Phân bố theo hình thức làm việc\n",
            "print(\"\\n=== 3. PHÂN BỐ THEO HÌNH THỨC LÀM VIỆC (EMPLOYMENT_TYPE) ===\")\n",
            "emp_df = jobs['employment_type'].value_counts(dropna=False).reset_index()\n",
            "emp_df.columns = ['Employment Type', 'Số lượng']\n",
            "emp_df['Tỷ lệ (%)'] = (emp_df['Số lượng'] / len(jobs) * 100).round(2)\n",
            "display(emp_df)\n",
            "\n",
            "# 4. Phân bố theo trạng thái hiệu lực\n",
            "print(\"\\n=== 4. TRẠNG THÁI HIỆU LỰC (IS_ACTIVE) ===\")\n",
            "act_df = jobs['is_active'].value_counts(dropna=False).reset_index()\n",
            "act_df.columns = ['Is Active', 'Số lượng']\n",
            "act_df['Tỷ lệ (%)'] = (act_df['Số lượng'] / len(jobs) * 100).round(2)\n",
            "display(act_df)\n"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 6. Phân tích đặc trưng văn bản & Top Kỹ năng yêu cầu"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# 1. Thống kê độ dài văn bản mô tả công việc (description_clean)\n",
            "desc_lengths = jobs['description_clean'].dropna().str.len()\n",
            "print(\"=== ĐỘ DÀI MÔ TẢ CÔNG VIỆC (SỐ KÝ TỰ) ===\")\n",
            "display(desc_lengths.describe().round(0))\n",
            "\n",
            "# 2. Bóc tách và đếm tần suất Top 20 kỹ năng yêu cầu\n",
            "from collections import Counter\n",
            "\n",
            "skill_counter = Counter()\n",
            "for text in jobs['required_skills'].dropna():\n",
            "    skills = [s.strip() for s in str(text).split(',') if s.strip()]\n",
            "    skill_counter.update(skills)\n",
            "\n",
            "top_skills_df = pd.DataFrame(skill_counter.most_common(20), columns=['Kỹ năng', 'Số lần xuất hiện'])\n",
            "top_skills_df['Tỷ lệ (%)'] = (top_skills_df['Số lần xuất hiện'] / len(jobs) * 100).round(2)\n",
            "\n",
            "print(\"\\n=== TOP 20 KỸ NĂNG XUẤT HIỆN NHIỀU NHẤT TRONG DATASET ===\")\n",
            "display(top_skills_df)\n"
        ]
    }
]

# Kiểm tra cú pháp bằng compile()
for i, cell in enumerate(cells):
    if cell["cell_type"] == "code":
        code = "".join(cell["source"])
        try:
            compile(code, f"Cell_{i}", "exec")
        except SyntaxError as e:
            print(f"Lỗi cú pháp ở Cell {i}: {e}")
            sys.exit(1)

nb_data = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"}
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb_data, f, ensure_ascii=False, indent=2)

print("Đã tạo notebook content_base_filtering.ipynb thành công!")
