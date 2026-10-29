import os
import sys
import re
import urllib.parse
import streamlit as st
import pandas as pd
import numpy as np

# Đảm bảo đường dẫn gốc dự án
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.recommender.content_based import get_content_based_recommender, ContentBasedRecommender
from src.data_cleaning.skill_canonical import CANONICAL_SKILL_MAP, extract_skills_from_text

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="Hệ Thống Gợi Ý Việc Làm IT",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS Tùy biến Cao cấp, Tối giản, Hiện đại (Không dùng icon)
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, p, span, label, input, button {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Nền trang nhẹ nhàng, tinh tế */
.stApp {
    background-color: #f8fafc;
}

#MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
    height: 0;
}

/* Khối Header tối giản, sang trọng */
.header-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.header-tag {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #475569;
    background: #f1f5f9;
    padding: 3px 10px;
    border-radius: 6px;
    margin-bottom: 10px;
    border: 1px solid #e2e8f0;
}

.header-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 8px 0;
    line-height: 1.3;
}

.header-subtitle {
    font-size: 0.92rem;
    color: #64748b;
    margin: 0;
    line-height: 1.55;
}

/* Khung form nhập liệu */
.form-panel {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 24px 28px;
    margin-bottom: 24px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.form-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin-bottom: 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #f1f5f9;
}

/* Tùy biến nút bấm chính sang trọng, màu Navy cao cấp */
div.stButton > button[kind="primary"] {
    background: #0f172a !important;
    color: #ffffff !important;
    border: 1px solid #0f172a !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
}

div.stButton > button[kind="primary"]:hover {
    background: #1e293b !important;
    border-color: #1e293b !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.15) !important;
}

div.stButton > button[kind="secondary"] {
    background: #f8fafc !important;
    color: #475569 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

div.stButton > button[kind="secondary"]:hover {
    background: #f1f5f9 !important;
    color: #0f172a !important;
    border-color: #94a3b8 !important;
}

/* Thẻ công việc tối giản */
.job-item {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 20px 22px;
    margin-bottom: 14px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
    transition: border-color 0.2s ease;
}

.job-item:hover {
    border-color: #cbd5e1;
}

.job-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: #1d4ed8 !important;
    margin: 0 0 3px 0;
    line-height: 1.4;
    transition: color 0.15s ease;
    cursor: pointer;
    text-decoration: underline !important;
}

.job-title-link {
    text-decoration: underline !important;
    color: #1d4ed8 !important;
    display: inline-block;
    cursor: pointer;
}

.job-title-link:hover .job-title {
    color: #1e40af !important;
    text-decoration: underline !important;
}

.company-logo {
    width: 48px;
    height: 48px;
    min-width: 48px;
    max-width: 48px;
    object-fit: contain;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
    padding: 3px;
    box-sizing: border-box;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.job-company {
    font-size: 0.9rem;
    font-weight: 500;
    color: #2563eb;
    margin: 2px 0 0 0;
}

.apply-btn {
    display: inline-flex;
    align-items: center;
    font-size: 0.8rem;
    font-weight: 600;
    color: #2563eb !important;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 6px 14px;
    border-radius: 6px;
    text-decoration: none !important;
    transition: all 0.15s ease;
}

.apply-btn:hover {
    background: #2563eb;
    border-color: #2563eb;
    color: #ffffff !important;
}

.score-badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 600;
    background: #f1f5f9;
    color: #0f172a;
    border: 1px solid #e2e8f0;
}

.meta-tag {
    display: inline-block;
    font-size: 0.8rem;
    color: #475569;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 3px 9px;
    border-radius: 6px;
    margin-right: 6px;
    margin-bottom: 4px;
    font-weight: 500;
}

.skill-tag-matched {
    display: inline-block;
    font-size: 0.76rem;
    color: #065f46;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    margin-bottom: 4px;
    font-weight: 500;
}

.skill-tag-missing {
    display: inline-block;
    font-size: 0.76rem;
    color: #92400e;
    background: #fffbeb;
    border: 1px solid #fde68a;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    margin-bottom: 4px;
    font-weight: 500;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 3. Nạp mô hình Content-Based Recommender (Tự động nhận diện khi có dữ liệu mới)
silver_data_path = os.path.join(project_root, "data", "silver", "jobs_cleaned.parquet")
data_last_modified = os.path.getmtime(silver_data_path) if os.path.exists(silver_data_path) else 0

@st.cache_resource(show_spinner="Đang khởi động hệ thống gợi ý việc làm...")
def load_recommender(_mtime: float = 0.0):
    engine = ContentBasedRecommender()
    engine.load_or_train()
    return engine

recommender = load_recommender(_mtime=data_last_modified)
jobs_df = recommender.jobs_df
all_skills_list = sorted(list(set(CANONICAL_SKILL_MAP.values())))

# 4. Header Section
st.markdown(
    f"""
    <div class="header-box">
        <span class="header-tag">CONTENT-BASED FILTERING SYSTEM</span>
        <h1 class="header-title">Hệ Thống Gợi Ý Việc Làm Theo Nhu Cầu</h1>
        <p class="header-subtitle">
            Phân tích mức độ tương đồng giữa hồ sơ năng lực của ứng viên và yêu cầu tuyển dụng từ {len(jobs_df):,} vị trí việc làm IT đã được làm sạch và chuẩn hóa.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Nút nạp mẫu dữ liệu nhanh
col_sample_btn, _ = st.columns([1, 3])
with col_sample_btn:
    if st.button("Nạp dữ liệu mẫu: Data Analyst (Lương >= 12 triệu)", type="secondary", use_container_width=True):
        st.session_state["target_title"] = "Data Analyst"
        st.session_state["cv_text"] = (
            "Chuyên viên phân tích dữ liệu với 1 năm kinh nghiệm.\n"
            "Sử dụng thành thạo SQL để truy vấn và xử lý dữ liệu lớn, thành thạo Excel và Power BI xây dựng Dashboard quản trị kinh doanh."
        )
        st.session_state["skills"] = ["Python", "Tableau"]
        st.session_state["user_exp"] = 1.0
        st.session_state["preferred_city"] = "Tất cả"
        st.session_state["min_salary"] = 12000000
        st.session_state["top_n"] = 5

st.write("")

# 5. Form Nhập Liệu
st.markdown('<div class="form-panel"><div class="form-title">Thông Tin Tìm Kiếm & Hồ Sơ Ứng Viên</div>', unsafe_allow_html=True)

col_left, col_right = st.columns([1.5, 1])

with col_left:
    target_title = st.text_input(
        "Vị trí mong muốn ứng tuyển:",
        value=st.session_state.get("target_title", "Data Analyst"),
        placeholder="Ví dụ: Data Analyst, Backend Developer, DevOps Engineer..."
    )

    cv_text = st.text_area(
        "Nội dung hồ sơ năng lực / Tóm tắt CV:",
        value=st.session_state.get(
            "cv_text",
            "Chuyên viên phân tích dữ liệu với 1 năm kinh nghiệm.\n"
            "Sử dụng thành thạo SQL để truy vấn và xử lý dữ liệu lớn, thành thạo Excel và Power BI xây dựng Dashboard quản trị kinh doanh."
        ),
        height=125,
        placeholder="Mô tả tóm tắt kinh nghiệm làm việc, dự án hoặc công nghệ bạn đã sử dụng..."
    )

    skills = st.multiselect(
        "Kỹ năng bổ sung:",
        options=all_skills_list,
        default=st.session_state.get("skills", ["Python", "Tableau"]),
        help="Chọn thêm các kỹ năng quan trọng nếu chưa đề cập trong đoạn văn bản CV ở trên"
    )

with col_right:
    user_exp = st.number_input(
        "Số năm kinh nghiệm làm việc:",
        min_value=0.0,
        max_value=15.0,
        value=float(st.session_state.get("user_exp", 1.0)),
        step=0.5
    )

    cities_options = ["Tất cả", "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Khác"]
    curr_city = st.session_state.get("preferred_city", "Tất cả")
    preferred_city = st.selectbox(
        "Khu vực làm việc ưu tiên:",
        options=cities_options,
        index=cities_options.index(curr_city) if curr_city in cities_options else 0
    )

    min_salary = st.number_input(
        "Mức lương tối thiểu kỳ vọng (VNĐ/tháng):",
        min_value=0,
        max_value=100_000_000,
        value=int(st.session_state.get("min_salary", 12_000_000)),
        step=1_000_000,
        format="%d",
        help="Nhập 0 nếu bạn muốn hiển thị cả các vị trí có mức lương Thỏa thuận"
    )

    top_n = st.slider(
        "Số lượng công việc đề xuất:",
        min_value=1,
        max_value=20,
        value=int(st.session_state.get("top_n", 5))
    )

st.markdown('</div>', unsafe_allow_html=True)

col_action, _ = st.columns([1, 3])
with col_action:
    btn_search = st.button("Tìm Kiếm Việc Làm Phù Hợp", type="primary", use_container_width=True)

st.write("")

# 6. Xử lý logic và hiển thị danh sách kết quả
if btn_search or ("target_title" in st.session_state):
    salary_filter = min_salary if min_salary > 0 else None

    with st.spinner("Đang tính toán độ tương đồng nội dung..."):
        detected_skills = extract_skills_from_text(cv_text) if cv_text else []
        all_candidate_skills = list(set(detected_skills + skills))

        df_results = recommender.recommend(
            target_title=target_title,
            cv_text=cv_text,
            skills=skills,
            user_exp=user_exp,
            preferred_city=preferred_city,
            min_salary=salary_filter,
            top_n=top_n
        )

    st.markdown("### Kết Quả Đề Xuất Phù Hợp")
    
    if all_candidate_skills:
        skill_tags = " ".join([f"<span class='meta-tag'>{s}</span>" for s in all_candidate_skills])
        st.markdown(f"<div style='margin-bottom:16px;'><span style='font-size:0.85rem; color:#64748b; font-weight:600;'>Kỹ năng ghi nhận từ hồ sơ:</span> {skill_tags}</div>", unsafe_allow_html=True)

    if df_results.empty:
        st.info("Không tìm thấy công việc nào thỏa mãn toàn bộ tiêu chí lọc. Bạn có thể thử giảm số năm kinh nghiệm hoặc đặt mức lương tối thiểu về 0 để mở rộng kết quả.")
    else:
        # Bảng tổng hợp
        display_cols = [
            'Tiêu đề', 'Công ty', 'Độ phù hợp (%)', 'Độ phủ kỹ năng (%)',
            'Kỹ năng đã có (Điểm mạnh)', 'Kỹ năng còn thiếu (Gap)',
            'Kinh nghiệm yêu cầu', 'Thành phố', 'Hình thức', 'Mức lương'
        ]
        if 'job_url' in df_results.columns:
            display_cols.append('job_url')

        st.dataframe(
            df_results[display_cols],
            column_config={
                "job_url": st.column_config.LinkColumn(
                    "Trang Ứng Tuyển",
                    help="Bấm để mở trang tin tuyển dụng gốc",
                    display_text="Xem tin tuyển dụng"
                )
            },
            use_container_width=True,
            hide_index=True
        )

        st.write("")
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:12px;'>Chi Tiết Từng Vị Trí Đề Xuất:</p>", unsafe_allow_html=True)

        for idx, row in df_results.iterrows():
            matched_list = [s.strip() for s in str(row["Kỹ năng đã có (Điểm mạnh)"]).split(',') if s.strip()]
            missing_list = [s.strip() for s in str(row["Kỹ năng còn thiếu (Gap)"]).split(',') if s.strip() and s.strip() != 'Đầy đủ']

            matched_html = " ".join([f"<span class='skill-tag-matched'>{s}</span>" for s in matched_list]) if matched_list else "<span style='color:#94a3b8; font-size:0.8rem;'>Phù hợp theo vị trí công việc</span>"
            missing_html = " ".join([f"<span class='skill-tag-missing'>{s}</span>" for s in missing_list[:5]]) if missing_list else "<span style='color:#059669; font-size:0.8rem; font-weight:500;'>Đáp ứng đầy đủ kỹ năng cốt lõi</span>"

            company_name = str(row["Công ty"])
            quoted_company = urllib.parse.quote(company_name)
            fallback_logo = f"https://ui-avatars.com/api/?name={quoted_company}&background=f1f5f9&color=2563eb&bold=true&size=128"
            
            raw_logo = str(row.get("company_logo_url", "") or "").strip()
            if "cdn-new.topcv.vn/unsafe/" in raw_logo:
                raw_logo = re.sub(r'^https?://cdn-new\.topcv\.vn/unsafe/(https?://)', r'\1', raw_logo).strip()
                
            logo_src = raw_logo if (raw_logo and raw_logo.startswith("http")) else fallback_logo
            logo_html = f'<img src="{logo_src}" alt="{company_name}" class="company-logo" referrerpolicy="no-referrer" onerror="this.onerror=null; this.src=\'{fallback_logo}\';" />'

            job_url = str(row.get("job_url", "") or "").strip()
            if job_url and job_url.startswith("http"):
                title_html = f'<a href="{job_url}" target="_blank" rel="noopener noreferrer" style="color:#1d4ed8; text-decoration:underline; font-size:1.15rem; font-weight:700; cursor:pointer;" title="Bấm để mở trang ứng tuyển gốc">{row["Tiêu đề"]}</a>'
                btn_html = f'<a href="{job_url}" target="_blank" rel="noopener noreferrer" class="apply-btn" style="cursor:pointer; display:inline-block;">Xem tin tuyển dụng gốc</a>'
            else:
                title_html = f'<span style="font-size:1.15rem; font-weight:700; color:#0f172a;">{row["Tiêu đề"]}</span>'
                btn_html = ''

            card_html = (
                f'<div class="job-item">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">'
                f'<div style="display:flex; align-items:flex-start; gap:14px; flex:1;">'
                f'{logo_html}'
                f'<div>{title_html}<p class="job-company">{company_name}</p></div>'
                f'</div>'
                f'<div style="text-align:right; min-width:140px;">'
                f'<span class="score-badge">Độ phù hợp: {row["Độ phù hợp (%)"]}%</span>'
                f'<div style="font-size:0.75rem; color:#64748b; margin-top:4px;">Độ phủ kỹ năng: <strong>{row["Độ phủ kỹ năng (%)"]}</strong></div>'
                f'</div>'
                f'</div>'
                f'<div style="margin:12px 0 8px 0;">'
                f'<span class="meta-tag">Lương: {row["Mức lương"]}</span>'
                f'<span class="meta-tag">Khu vực: {row["Thành phố"]}</span>'
                f'<span class="meta-tag">Yêu cầu: {row["Kinh nghiệm yêu cầu"]}</span>'
                f'<span class="meta-tag">Hình thức: {row["Hình thức"]}</span>'
                f'</div>'
                f'<div style="margin-top:10px; padding-top:10px; border-top:1px dashed #e2e8f0; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">'
                f'<div style="flex:1;">'
                f'<div style="margin-bottom:4px;"><span style="font-size:0.78rem; font-weight:600; color:#334155;">Kỹ năng bạn đã có:</span> {matched_html}</div>'
                f'<div><span style="font-size:0.78rem; font-weight:600; color:#334155;">Kỹ năng cần bổ sung:</span> {missing_html}</div>'
                f'</div>'
                f'<div>{btn_html}</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
