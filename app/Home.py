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
from app.components.market_insights import render_market_insights

# 1. Cấu hình trang Streamlit
st.set_page_config(
    page_title="Hệ Thống Phân Tích & Gợi Ý Việc Làm IT",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CSS Tùy biến Cao cấp, Tối giản, Hiện đại (Không dùng icon)
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stMarkdown, p, span, label, input, button {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Tùy biến Tab navigation */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    height: 42px;
    white-space: pre-wrap;
    background-color: #ffffff;
    border-radius: 8px 8px 0 0;
    padding: 8px 20px;
    font-weight: 600;
    color: #475569;
    border: 1px solid #e2e8f0;
}
.stTabs [aria-selected="true"] {
    background-color: #0f172a !important;
    color: #ffffff !important;
    border-color: #0f172a !important;
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

/* Khối tổng quan hồ sơ năng lực ứng viên */
.candidate-profile-box {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #0f172a;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
}

.candidate-profile-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #0f172a;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid #f1f5f9;
}

.skill-tag-cv {
    display: inline-block;
    font-size: 0.76rem;
    color: #1e40af;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    padding: 2px 8px;
    border-radius: 4px;
    margin-right: 4px;
    margin-bottom: 4px;
    font-weight: 500;
}

.skill-tag-extra {
    display: inline-block;
    font-size: 0.76rem;
    color: #6b21a8;
    background: #faf5ff;
    border: 1px solid #e9d5ff;
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

tab_recommender, tab_market = st.tabs([
    "Gợi Ý Việc Làm Phù Hợp",
    "Phân Tích Toàn Cảnh Thị Trường"
])

with tab_recommender:
    with st.container(border=True):
        col_form_title, col_sample = st.columns([2.5, 1.2])
        with col_form_title:
            st.markdown(
                '<p style="font-size:1.05rem; font-weight:700; color:#0f172a; margin:4px 0 0 0;">Thông Tin Tìm Kiếm & Hồ Sơ Năng Lực Ứng Viên</p>',
                unsafe_allow_html=True
            )
        with col_sample:
            if st.button("Nạp hồ sơ mẫu: Data Analyst", type="secondary", use_container_width=True):
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
                if "df_results" in st.session_state:
                    del st.session_state["df_results"]
                st.rerun()

        st.caption("Điền thông tin hồ sơ của bạn bên dưới hoặc bấm nút nạp hồ sơ mẫu để thử nghiệm nhanh hệ thống đề xuất việc làm.")
        st.write("")

        col_left, col_right = st.columns([1.4, 1.0])

        with col_left:
            st.markdown('<p style="font-size:0.86rem; font-weight:600; color:#334155; margin-bottom:6px;">1. Hồ sơ chuyên môn & Kỹ năng</p>', unsafe_allow_html=True)
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
                "Kỹ năng bổ sung (Công cụ, ngôn ngữ chưa đề cập trong văn bản CV):",
                options=all_skills_list,
                default=st.session_state.get("skills", ["Python", "Tableau"]),
                help="Hệ thống tự động quét kỹ năng từ văn bản CV ở trên; mục này cho phép bạn chọn thêm các kỹ năng khác để làm giàu hồ sơ năng lực."
            )

        with col_right:
            st.markdown('<p style="font-size:0.86rem; font-weight:600; color:#334155; margin-bottom:6px;">2. Tiêu chí tìm kiếm & Ràng buộc</p>', unsafe_allow_html=True)
            user_exp = st.number_input(
                "Số năm kinh nghiệm làm việc:",
                min_value=0.0,
                max_value=15.0,
                value=float(st.session_state.get("user_exp", 1.0)),
                step=0.5
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

            cities_options = ["Tất cả", "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Khác"]
            curr_city = st.session_state.get("preferred_city", "Tất cả")
            preferred_city = st.selectbox(
                "Khu vực làm việc ưu tiên:",
                options=cities_options,
                index=cities_options.index(curr_city) if curr_city in cities_options else 0
            )

            work_modes_options = ["Onsite", "Remote", "Hybrid"]
            curr_modes = st.session_state.get("preferred_work_modes", ["Onsite", "Remote", "Hybrid"])
            preferred_work_modes = st.multiselect(
                "Hình thức làm việc ưu tiên:",
                options=work_modes_options,
                default=curr_modes,
                help="Chọn một hoặc nhiều hình thức làm việc bạn mong muốn"
            )

            top_n = st.slider(
                "Số lượng công việc đề xuất:",
                min_value=1,
                max_value=20,
                value=int(st.session_state.get("top_n", 5))
            )

        st.write("")
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            btn_search = st.button("Tìm Kiếm Việc Làm Phù Hợp", type="primary", use_container_width=True)

    st.write("")

    # 6. Xử lý logic và hiển thị danh sách kết quả (Lưu vào session_state để không bị reset khi đổi chế độ xem)
    should_run_search = btn_search or ("df_results" not in st.session_state)

    if should_run_search:
        salary_filter = min_salary if min_salary > 0 else None

        with st.spinner("Đang tính toán mức độ tương đồng giữa hồ sơ và cơ sở dữ liệu việc làm..."):
            detected_skills = extract_skills_from_text(cv_text) if cv_text else []
            all_candidate_skills = list(dict.fromkeys(detected_skills + skills))

            df_results = recommender.recommend(
                target_title=target_title,
                cv_text=cv_text,
                skills=skills,
                user_exp=user_exp,
                preferred_city=preferred_city,
                preferred_work_modes=preferred_work_modes,
                min_salary=salary_filter,
                top_n=top_n
            )

            # Lưu kết quả và thông tin vào session_state
            st.session_state["df_results"] = df_results
            st.session_state["detected_skills"] = detected_skills
            st.session_state["all_candidate_skills"] = all_candidate_skills
            st.session_state["summary_target_title"] = target_title
            st.session_state["summary_user_exp"] = user_exp
            st.session_state["summary_preferred_city"] = preferred_city
            st.session_state["summary_preferred_work_modes"] = preferred_work_modes
            st.session_state["summary_min_salary"] = min_salary

    # Hiển thị kết quả từ session_state (bảo toàn khi người dùng bấm đổi radio view_mode)
    if "df_results" in st.session_state and st.session_state["df_results"] is not None:
        df_results = st.session_state["df_results"]
        detected_skills = st.session_state.get("detected_skills", [])
        all_candidate_skills = st.session_state.get("all_candidate_skills", [])
        sum_title = st.session_state.get("summary_target_title", target_title)
        sum_exp = st.session_state.get("summary_user_exp", user_exp)
        sum_city = st.session_state.get("summary_preferred_city", preferred_city)
        sum_modes = st.session_state.get("summary_preferred_work_modes", preferred_work_modes)
        sum_salary = st.session_state.get("summary_min_salary", min_salary)

        # Hộp tổng quan hồ sơ ứng viên đang được ghi nhận
        cv_skill_tags = " ".join([f"<span class='skill-tag-cv'>{s}</span>" for s in detected_skills]) if detected_skills else "<span style='color:#94a3b8; font-size:0.8rem;'>Không trích xuất được từ văn bản</span>"
        extra_skill_tags = " ".join([f"<span class='skill-tag-extra'>{s}</span>" for s in skills]) if skills else "<span style='color:#94a3b8; font-size:0.8rem;'>Không chọn kỹ năng bổ sung</span>"
        salary_text = f"Tối thiểu {sum_salary:,.0f} VNĐ/tháng" if sum_salary > 0 else "Bao gồm cả mức lương Thỏa thuận"
        modes_text = ", ".join(sum_modes) if sum_modes else "Tất cả"

        profile_box_html = f"""
        <div class="candidate-profile-box">
            <div class="candidate-profile-title">Hồ Sơ Năng Lực Ứng Viên Đang Được Ghi Nhận</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap:10px; margin-bottom:12px; font-size:0.83rem;">
                <div><span style="color:#64748b;">Vị trí mục tiêu:</span> <strong style="color:#0f172a;">{sum_title}</strong></div>
                <div><span style="color:#64748b;">Kinh nghiệm:</span> <strong style="color:#0f172a;">{sum_exp} năm</strong></div>
                <div><span style="color:#64748b;">Khu vực ưu tiên:</span> <strong style="color:#0f172a;">{sum_city}</strong></div>
                <div><span style="color:#64748b;">Hình thức:</span> <strong style="color:#0f172a;">{modes_text}</strong></div>
                <div><span style="color:#64748b;">Kỳ vọng lương:</span> <strong style="color:#0f172a;">{salary_text}</strong></div>
                <div><span style="color:#64748b;">Tổng kỹ năng sở hữu:</span> <strong style="color:#0f172a;">{len(all_candidate_skills)} kỹ năng</strong></div>
            </div>
            <div style="font-size:0.8rem; padding-top:10px; border-top:1px dashed #e2e8f0;">
                <div style="margin-bottom:6px;">
                    <span style="font-weight:600; color:#1e40af; display:inline-block; min-width:210px;">Kỹ năng trích xuất từ CV:</span>
                    {cv_skill_tags}
                </div>
                <div>
                    <span style="font-weight:600; color:#6b21a8; display:inline-block; min-width:210px;">Kỹ năng chọn bổ sung:</span>
                    {extra_skill_tags}
                </div>
            </div>
        </div>
        """
        st.markdown(profile_box_html, unsafe_allow_html=True)

        if df_results.empty:
            st.info("Không tìm thấy công việc nào thỏa mãn toàn bộ tiêu chí lọc. Bạn có thể thử giảm số năm kinh nghiệm hoặc đặt mức lương tối thiểu về 0 để mở rộng kết quả.")
        else:
            # Thanh tiêu đề và chuyển đổi chế độ xem kết quả có key để bảo toàn trạng thái
            col_results_title, col_view_toggle = st.columns([1.6, 1.4])
            with col_results_title:
                st.markdown(f'<p style="font-size:1.1rem; font-weight:700; color:#0f172a; margin:6px 0 0 0;">Danh Sách Đề Xuất Phù Hợp ({len(df_results)} vị trí)</p>', unsafe_allow_html=True)
            with col_view_toggle:
                view_mode = st.radio(
                    "Chế độ hiển thị:",
                    options=["Thẻ việc làm chi tiết", "Bảng so sánh tổng quan", "Xem cả hai"],
                    key="results_view_mode",
                    horizontal=True,
                    label_visibility="collapsed"
                )

            st.write("")

            # 1. Bảng so sánh tổng hợp
            if view_mode in ["Bảng so sánh tổng quan", "Xem cả hai"]:
                display_cols = [
                    'Tiêu đề', 'Công ty', 'Tổng điểm (%)', 'Lời giải thích',
                    'Độ phủ kỹ năng (%)', 'Kỹ năng đã có (Điểm mạnh)', 'Kỹ năng còn thiếu (Gap)',
                    'Kinh nghiệm yêu cầu', 'Thành phố', 'Hình thức', 'Mức lương'
                ]
                if 'job_url' in df_results.columns:
                    display_cols.append('job_url')

                st.dataframe(
                    df_results[display_cols],
                    column_config={
                        "job_url": st.column_config.LinkColumn(
                            "Trang Tuyển Dụng",
                            help="Bấm để mở trang tin tuyển dụng gốc",
                            display_text="Xem tin gốc"
                        ),
                        "Kỹ năng đã có (Điểm mạnh)": st.column_config.TextColumn(
                            "Kỹ năng đáp ứng (Khớp vị trí)",
                            help="Các kỹ năng bạn sở hữu trùng khớp với yêu cầu vị trí này"
                        ),
                        "Kỹ năng còn thiếu (Gap)": st.column_config.TextColumn(
                            "Kỹ năng vị trí yêu cầu còn thiếu",
                            help="Kỹ năng vị trí này yêu cầu mà bạn chưa có"
                        ),
                        "Tổng điểm (%)": st.column_config.NumberColumn("Độ phù hợp (%)", format="%.1f%%"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                st.write("")

            # 2. Thẻ chi tiết từng công việc
            if view_mode in ["Thẻ việc làm chi tiết", "Xem cả hai"]:
                for idx, row in df_results.iterrows():
                    matched_list = [s.strip() for s in str(row["Kỹ năng đã có (Điểm mạnh)"]).split(',') if s.strip()]
                    missing_list = [s.strip() for s in str(row["Kỹ năng còn thiếu (Gap)"]).split(',') if s.strip() and s.strip() != 'Đầy đủ']

                    matched_html = " ".join([f"<span class='skill-tag-matched'>{s}</span>" for s in matched_list]) if matched_list else "<span style='color:#94a3b8; font-size:0.8rem;'>Phù hợp theo vị trí công việc</span>"
                    missing_html = " ".join([f"<span class='skill-tag-missing'>{s}</span>" for s in missing_list[:5]]) if missing_list else "<span style='color:#059669; font-size:0.8rem; font-weight:600;'>Đáp ứng đầy đủ kỹ năng cốt lõi</span>"

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

                    rationale_text = str(row.get("Lời giải thích", "")).strip()
                    rationale_html = (
                        f'<div style="margin:10px 0; padding:10px 14px; background:#f8fafc; border-left:3px solid #2563eb; border-radius:4px; font-size:0.83rem; color:#334155; line-height:1.5;">'
                        f'<strong>Lý do gợi ý:</strong> {rationale_text}'
                        f'</div>'
                    ) if rationale_text else ''

                    score_breakdown_html = (
                        f'<div style="display:flex; gap:12px; flex-wrap:wrap; margin:8px 0; padding:6px 12px; background:#f8fafc; border-radius:6px; border:1px solid #f1f5f9; font-size:0.77rem; color:#64748b;">'
                        f'<span>Kỹ năng: <strong style="color:#0f172a;">{row.get("Điểm kỹ năng (%)", 0)}%</strong></span> &bull; '
                        f'<span>Nội dung: <strong style="color:#0f172a;">{row.get("Điểm văn bản (%)", 0)}%</strong></span> &bull; '
                        f'<span>Kinh nghiệm: <strong style="color:#0f172a;">{row.get("Điểm kinh nghiệm (%)", 0)}%</strong></span> &bull; '
                        f'<span>Vị trí / Hình thức: <strong style="color:#0f172a;">{row.get("Điểm vị trí/hình thức (%)", 0)}%</strong></span>'
                        f'</div>'
                    )

                    card_html = (
                        f'<div class="job-item">'
                        f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:16px;">'
                        f'<div style="display:flex; align-items:flex-start; gap:14px; flex:1;">'
                        f'{logo_html}'
                        f'<div>{title_html}<p class="job-company">{company_name}</p></div>'
                        f'</div>'
                        f'<div style="text-align:right; min-width:160px;">'
                        f'<span class="score-badge">Độ phù hợp: {row["Tổng điểm (%)"]}%</span>'
                        f'<div style="font-size:0.75rem; color:#64748b; margin-top:4px;">Độ phủ kỹ năng: <strong>{row["Độ phủ kỹ năng (%)"]}</strong></div>'
                        f'</div>'
                        f'</div>'
                        f'{score_breakdown_html}'
                        f'{rationale_html}'
                        f'<div style="margin:10px 0 8px 0;">'
                        f'<span class="meta-tag">Lương: <strong>{row["Mức lương"]}</strong></span>'
                        f'<span class="meta-tag">Khu vực: <strong>{row["Thành phố"]}</strong></span>'
                        f'<span class="meta-tag">Yêu cầu: <strong>{row["Kinh nghiệm yêu cầu"]}</strong></span>'
                        f'<span class="meta-tag">Hình thức: <strong>{row["Hình thức"]}</strong></span>'
                        f'</div>'
                        f'<div style="margin-top:12px; padding-top:12px; border-top:1px dashed #e2e8f0; display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">'
                        f'<div style="flex:1; min-width:280px;">'
                        f'<div style="margin-bottom:6px;"><span style="font-size:0.8rem; font-weight:600; color:#15803d; display:inline-block; min-width:220px;">Kỹ năng bạn đáp ứng (Khớp vị trí):</span> {matched_html}</div>'
                        f'<div><span style="font-size:0.8rem; font-weight:600; color:#b45309; display:inline-block; min-width:220px;">Kỹ năng vị trí yêu cầu còn thiếu:</span> {missing_html}</div>'
                        f'</div>'
                        f'<div>{btn_html}</div>'
                        f'</div>'
                        f'</div>'
                    )
                    st.markdown(card_html, unsafe_allow_html=True)

with tab_market:
    render_market_insights()
