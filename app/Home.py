import os
import sys
import re
import datetime
import urllib.parse
import uuid
import streamlit as st
import pandas as pd
import numpy as np

# Đảm bảo đường dẫn gốc dự án
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.recommender.content_based import ContentBasedRecommender, data_file_version
from src.recommender.collaborative import (CFModel, InteractionLog, build_training_events,
                                           simulated_data_available)
from src.recommender.hybrid import HybridRecommender
from src.data_cleaning.skill_canonical import TECH_LOOKUP, extract_skills_from_text
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

/* Trả lại font icon cho Streamlit: quy tắc trên ép mọi <span> sang Inter, làm icon (mũi tên của expander...)
   hiện thành chữ thô như "_arrow_right". Đặt SAU quy tắc trên để được ưu tiên. */
[data-testid="stIconMaterial"], [data-testid="stExpanderIcon"],
span.material-symbols-rounded, span[class*="material-symbols"], span[class*="MaterialSymbol"] {
    font-family: 'Material Symbols Rounded' !important;
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

.skill-tag-related {
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
# Khóa cache = (thời điểm sửa file dữ liệu, ngày hôm nay): chạy lại notebook 02 hoặc sang ngày mới thì nạp lại
# (ngày mới để tính lại tin nào đã hết hạn). Lưu ý: Streamlit KHÔNG đưa tham số bắt đầu bằng "_" vào khóa cache.
data_version = (data_file_version(), datetime.date.today().isoformat())

@st.cache_resource(show_spinner="Đang khởi động hệ thống gợi ý việc làm...")
def load_recommender(data_version: tuple):
    engine = ContentBasedRecommender()
    engine.load_or_train()
    return engine

recommender = load_recommender(data_version)
interaction_log = InteractionLog()


@st.cache_resource(show_spinner="Đang huấn luyện mô hình lọc cộng tác (ALS)...")
def load_cf_model(log_version: tuple, use_simulated: bool):
    """Huấn luyện lại ALS khi log tương tác đổi (khoảng 1 giây ở quy mô hiện tại; notebook 07, mục 6)."""
    return CFModel().fit(build_training_events(InteractionLog(), use_simulated))


def get_hybrid(use_simulated: bool) -> HybridRecommender:
    cf = load_cf_model(interaction_log.version(), use_simulated)
    return HybridRecommender(recommender, interaction_log, use_simulated, cf_model=cf)
jobs_df = recommender.jobs_df
all_skills_list = sorted(list(set(TECH_LOOKUP.values())))

# 4. Header Section
st.markdown(
    f"""
    <div class="header-box">
        <span class="header-tag">HỆ GỢI Ý HYBRID · CBF + CF</span>
        <h1 class="header-title">Hệ Thống Gợi Ý Việc Làm Theo Nhu Cầu</h1>
        <p class="header-subtitle">
            Gợi ý từ {len(jobs_df):,} tin tuyển dụng IT: khớp nội dung hồ sơ của bạn (CBF), và khi bạn đã bấm Quan tâm / Ứng tuyển thì kết hợp thêm hành vi của những người dùng giống bạn (CF).
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

            st.markdown('<p style="font-size:0.86rem; font-weight:600; color:#334155; margin:10px 0 6px 0;">3. Cá nhân hóa theo hành vi (Hybrid CBF + CF)</p>', unsafe_allow_html=True)
            if "user_id" not in st.session_state:
                st.session_state["user_id"] = f"khach-{uuid.uuid4().hex[:6]}"
            user_id = st.text_input(
                "Mã người dùng:",
                key="user_id",
                help="Các lượt 'Quan tâm' / 'Ứng tuyển' được lưu theo mã này. Dùng lại cùng mã ở lần sau để hệ thống nhớ sở thích của bạn."
            ).strip() or "khach"
            if "use_simulated" not in st.session_state:
                st.session_state["use_simulated"] = simulated_data_available()
            use_simulated = st.checkbox(
                "Dùng dữ liệu tương tác mô phỏng làm nền (demo)",
                key="use_simulated",
                disabled=not simulated_data_available(),
                help="Ứng dụng chưa có nhiều người dùng thật, nên có thể mượn 3.000 người dùng mô phỏng của notebook 06 "
                     "để mô hình CF có dữ liệu học. Đây là dữ liệu MÔ PHỎNG, chỉ dùng để trình diễn."
            )

        st.write("")
        col_btn, _ = st.columns([1, 2])
        with col_btn:
            btn_search = st.button("Tìm Kiếm Việc Làm Phù Hợp", type="primary", use_container_width=True)

    st.write("")

    # 6. Xử lý logic và hiển thị danh sách kết quả (Lưu vào session_state để không bị reset khi đổi chế độ xem)
    # force_search: bấm "Cập nhật gợi ý theo sở thích" ngay phía trên danh sách kết quả (không phải cuộn lên nút Tìm kiếm)
    user_triggered = bool(btn_search) or st.session_state.pop("force_search", False)
    should_run_search = user_triggered or ("df_results" not in st.session_state)

    if should_run_search:
        salary_filter = min_salary if min_salary > 0 else None

        with st.spinner("Đang tính toán mức độ tương đồng giữa hồ sơ và cơ sở dữ liệu việc làm..."):
            detected_skills = extract_skills_from_text(cv_text) if cv_text else []
            all_candidate_skills = list(dict.fromkeys(detected_skills + skills))

            hybrid = get_hybrid(use_simulated)
            df_results, rec_info = hybrid.recommend(
                user_id=user_id,
                top_n=top_n,
                target_title=target_title,
                cv_text=cv_text,
                skills=skills,
                user_exp=user_exp,
                preferred_city=preferred_city,
                preferred_work_modes=preferred_work_modes,
                min_salary=salary_filter,
            )
            # Lưu lượt hiển thị (vị trí + chế độ) để sau này đánh giá được trên log thật; KHÔNG ghi lần tự tìm khi mở trang
            if user_triggered and not df_results.empty:
                interaction_log.log_impressions(user_id, df_results["job_id"], source="recommend", mode=rec_info["mode"])

            # Lưu kết quả và thông tin vào session_state
            st.session_state["df_results"] = df_results
            st.session_state["rec_info"] = rec_info
            st.session_state["rec_user_id"] = user_id
            st.session_state["pending_feedback"] = False
            st.session_state["detected_skills"] = detected_skills
            st.session_state["all_candidate_skills"] = all_candidate_skills
            st.session_state["summary_target_title"] = target_title
            st.session_state["summary_user_exp"] = user_exp
            st.session_state["summary_preferred_city"] = preferred_city
            st.session_state["summary_preferred_work_modes"] = preferred_work_modes
            st.session_state["summary_min_salary"] = min_salary

    # Hiển thị kết quả từ session_state (bảo toàn qua các lần rerun, vd. khi bấm Quan tâm / Ứng tuyển)
    if "df_results" in st.session_state and st.session_state["df_results"] is not None:
        df_results = st.session_state["df_results"]
        detected_skills = st.session_state.get("detected_skills", [])
        all_candidate_skills = st.session_state.get("all_candidate_skills", [])
        sum_title = st.session_state.get("summary_target_title", target_title)
        sum_exp = st.session_state.get("summary_user_exp", user_exp)
        sum_city = st.session_state.get("summary_preferred_city", preferred_city)
        sum_modes = st.session_state.get("summary_preferred_work_modes", preferred_work_modes)
        sum_salary = st.session_state.get("summary_min_salary", min_salary)
        rec_info = st.session_state.get("rec_info", {})
        rec_mode = rec_info.get("mode", "CBF")
        fb_user = st.session_state.get("rec_user_id", user_id)
        n_feedback = len(interaction_log.user_job_ids(fb_user))

        # A. Thanh trạng thái: hồ sơ đang dùng + hệ thống đang ở bước nào (CBF ➔ phản hồi ➔ Hybrid)
        salary_text = f"từ {sum_salary / 1e6:,.0f} triệu" if sum_salary > 0 else "mọi mức lương"
        modes_text = ", ".join(sum_modes) if sum_modes else "mọi hình thức"
        profile_line = (f"<strong>{sum_title or 'Chưa nhập vị trí'}</strong> · {sum_exp:g} năm kinh nghiệm · {sum_city} · "
                        f"{modes_text} · {salary_text} · {len(all_candidate_skills)} kỹ năng")

        def step_html(num, title, desc, state):
            # state: 'done' (đã qua), 'active' (đang dùng), 'todo' (chưa tới)
            style = {"active": "background:#eff6ff; border:2px solid #2563eb; color:#0f172a;",
                     "done": "background:#f0fdf4; border:1px solid #86efac; color:#14532d;",
                     "todo": "background:#f8fafc; border:1px dashed #cbd5e1; color:#94a3b8;"}[state]
            tag = {"active": "ĐANG DÙNG", "done": "ĐÃ CÓ", "todo": "CHƯA"}[state]
            return (f'<div style="flex:1; min-width:180px; border-radius:10px; padding:10px 14px; {style}">'
                    f'<div style="font-size:0.7rem; font-weight:700; letter-spacing:0.05em; margin-bottom:2px;">BƯỚC {num} · {tag}</div>'
                    f'<div style="font-weight:700; font-size:0.92rem;">{title}</div>'
                    f'<div style="font-size:0.78rem; margin-top:2px;">{desc}</div></div>')

        arrow = '<div style="align-self:center; color:#94a3b8; font-weight:700;">➔</div>'
        steps = (
            step_html(1, "Gợi ý theo hồ sơ (CBF)", "Kỹ năng, CV, kinh nghiệm, địa điểm, lương",
                      "active" if rec_mode == "CBF" else "done")
            + arrow
            + step_html(2, f"Bạn đã quan tâm {n_feedback} tin", "Bấm Quan tâm / Ứng tuyển dưới mỗi tin",
                        "done" if n_feedback else "todo")
            + arrow
            + step_html(3, "Hybrid CBF + CF", "Thêm hành vi của người dùng giống bạn (ALS)",
                        "active" if rec_mode == "Hybrid" else "todo")
        )
        st.markdown(
            f'<div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 16px; margin-bottom:12px;">'
            f'<div style="font-size:0.85rem; color:#334155; margin-bottom:10px;">Hồ sơ đang dùng: {profile_line}</div>'
            f'<div style="display:flex; gap:8px; flex-wrap:wrap;">{steps}</div></div>',
            unsafe_allow_html=True
        )
        with st.expander("Chi tiết hồ sơ và chế độ gợi ý"):
            st.markdown(f"**Kỹ năng trích xuất từ CV:** {', '.join(detected_skills) if detected_skills else 'không có'}")
            st.markdown(f"**Kỹ năng chọn thêm:** {', '.join(skills) if skills else 'không có'}")
            if rec_info:
                st.markdown(f"**Chế độ {rec_mode}:** {rec_info.get('reason', '')}")
            if st.session_state.get("use_simulated"):
                st.caption(f"Dữ liệu CF gồm tương tác MÔ PHỎNG của notebook 06 làm nền (demo): "
                           f"{rec_info.get('cf_users', 0):,} người dùng, {rec_info.get('cf_items', 0):,} tin.")

        # C. Vừa bấm Quan tâm / Ứng tuyển ➔ cập nhật gợi ý ngay tại chỗ, không phải cuộn lên đầu trang
        if st.session_state.get("pending_feedback"):
            col_msg, col_btn_update = st.columns([2.2, 1])
            with col_msg:
                st.success(f"Đã ghi nhận {n_feedback} tin bạn quan tâm. Cập nhật để hệ thống kết hợp thêm hành vi "
                           f"của những người dùng giống bạn (Hybrid).")
            with col_btn_update:
                st.button("Cập nhật gợi ý theo sở thích", type="primary", use_container_width=True,
                          on_click=lambda: st.session_state.update(force_search=True), key="btn_update_recs")

        if df_results.empty:
            st.info("Không tìm thấy công việc nào thỏa mãn toàn bộ tiêu chí lọc. Bạn có thể thử giảm số năm kinh nghiệm hoặc đặt mức lương tối thiểu về 0 để mở rộng kết quả.")
        else:
            has_cf = "Điểm CF (%)" in df_results.columns
            order_text = ("xếp theo Hybrid: kết hợp khớp hồ sơ và hành vi người dùng giống bạn" if has_cf
                          else "xếp theo mức độ khớp hồ sơ (CBF)")
            st.markdown(f'<p style="font-size:1.1rem; font-weight:700; color:#0f172a; margin:10px 0 2px 0;">'
                        f'Danh sách đề xuất ({len(df_results)} vị trí)</p>'
                        f'<p style="font-size:0.8rem; color:#64748b; margin:0 0 10px 0;">Thứ tự {order_text}.</p>',
                        unsafe_allow_html=True)

            def bar_html(label, value, color, note=""):
                if value is None or pd.isna(value):
                    return (f'<div style="display:flex; align-items:center; gap:10px; margin:3px 0; font-size:0.8rem;">'
                            f'<span style="min-width:190px; color:#475569;">{label}</span>'
                            f'<span style="color:#94a3b8;">{note or "chưa có dữ liệu"}</span></div>')
                v = max(0.0, min(100.0, float(value)))
                return (f'<div style="display:flex; align-items:center; gap:10px; margin:3px 0; font-size:0.8rem;">'
                        f'<span style="min-width:190px; color:#475569;">{label}</span>'
                        f'<div style="flex:1; max-width:260px; height:9px; background:#e2e8f0; border-radius:5px; overflow:hidden;">'
                        f'<div style="width:{v:.0f}%; height:100%; background:{color};"></div></div>'
                        f'<strong style="min-width:48px; color:#0f172a;">{v:.0f}%</strong></div>')

            def skill_list(value, skip=("Đầy đủ", "Khớp theo vị trí/mô tả")):
                return [s.strip() for s in str(value or "").split(",") if s.strip() and s.strip() not in skip]

            # B. Thẻ việc làm: hạng ➔ thông tin ➔ vì sao được gợi ý ➔ kỹ năng ➔ phản hồi + chi tiết (thu gọn)
            for idx, row in df_results.iterrows():
                rank = int(row.get("Hạng", idx + 1))
                company_name = str(row["Công ty"])
                quoted_company = urllib.parse.quote(company_name)
                fallback_logo = f"https://ui-avatars.com/api/?name={quoted_company}&background=f1f5f9&color=2563eb&bold=true&size=128"
                raw_logo = str(row.get("company_logo_url", "") or "").strip()
                if "cdn-new.topcv.vn/unsafe/" in raw_logo:
                    raw_logo = re.sub(r'^https?://cdn-new\.topcv\.vn/unsafe/(https?://)', r'\1', raw_logo).strip()
                logo_src = raw_logo if (raw_logo and raw_logo.startswith("http")) else fallback_logo
                logo_html = f'<img src="{logo_src}" alt="{company_name}" class="company-logo" referrerpolicy="no-referrer" onerror="this.onerror=null; this.src=\'{fallback_logo}\';" />'

                job_url = str(row.get("job_url", "") or "").strip()
                if job_url.startswith("http"):
                    title_html = f'<a href="{job_url}" target="_blank" rel="noopener noreferrer" style="color:#1d4ed8; text-decoration:none; font-size:1.08rem; font-weight:700;">{row["Tiêu đề"]}</a>'
                    link_html = f'<a href="{job_url}" target="_blank" rel="noopener noreferrer" class="apply-btn" style="display:inline-block;">Xem tin gốc</a>'
                else:
                    title_html = f'<span style="font-size:1.08rem; font-weight:700; color:#0f172a;">{row["Tiêu đề"]}</span>'
                    link_html = ''

                meta = " · ".join(str(x) for x in (row["Thành phố"], row["Hình thức"], row["Mức lương"],
                                                    f'Yêu cầu: {row["Kinh nghiệm yêu cầu"]}'))
                bars = bar_html("Khớp hồ sơ (CBF)", row["Tổng điểm (%)"], "#2563eb")
                if has_cf:
                    bars += bar_html("Người dùng giống bạn (CF)", row.get("Điểm CF (%)"), "#7c3aed",
                                     note="tin mới, chưa ai tương tác: chỉ dùng điểm hồ sơ")

                matched, related, missing = (skill_list(row.get("Kỹ năng đã có (Điểm mạnh)")),
                                             skill_list(row.get("Kỹ năng gần nhau")),
                                             skill_list(row.get("Kỹ năng còn thiếu (Gap)")))
                skill_parts = []
                if matched:
                    skill_parts.append('<span style="font-weight:600; color:#15803d;">Đã có:</span> '
                                       + " ".join(f"<span class='skill-tag-matched'>{s}</span>" for s in matched))
                if related:
                    skill_parts.append('<span style="font-weight:600; color:#1d4ed8;">Gần với:</span> '
                                       + " ".join(f"<span class='skill-tag-related'>{s}</span>" for s in related))
                if missing:
                    skill_parts.append('<span style="font-weight:600; color:#b45309;">Còn thiếu:</span> '
                                       + " ".join(f"<span class='skill-tag-missing'>{s}</span>" for s in missing[:5]))
                elif matched or related:
                    skill_parts.append('<span style="font-weight:600; color:#059669;">Đáp ứng đủ kỹ năng tin yêu cầu</span>')
                skills_html = ('<div style="margin-top:10px; font-size:0.8rem; line-height:2;">'
                               + ' <span style="color:#cbd5e1;">|</span> '.join(skill_parts) + '</div>') if skill_parts else (
                    '<div style="margin-top:10px; font-size:0.8rem; color:#94a3b8;">Tin không ghi kỹ năng cụ thể: gợi ý dựa trên tiêu đề và mô tả</div>')

                card_html = (
                    f'<div class="job-item">'
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:14px;">'
                    f'<div style="display:flex; align-items:flex-start; gap:12px; flex:1;">'
                    f'<div style="min-width:42px; height:42px; border-radius:10px; background:#0f172a; color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center;">#{rank}</div>'
                    f'{logo_html}'
                    f'<div>{title_html}<p class="job-company">{company_name}</p>'
                    f'<div style="font-size:0.8rem; color:#64748b;">{meta}</div></div>'
                    f'</div>'
                    f'<div>{link_html}</div>'
                    f'</div>'
                    f'<div style="margin-top:12px; padding:10px 14px; background:#f8fafc; border-radius:8px;">'
                    f'<div style="font-size:0.75rem; font-weight:700; color:#334155; margin-bottom:4px;">VÌ SAO ĐƯỢC GỢI Ý</div>'
                    f'{bars}</div>'
                    f'{skills_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                # Phản hồi ➔ log tương tác ➔ dữ liệu cho CF (Quan tâm = lưu, trọng số 3; Ứng tuyển = 5) + chi tiết điểm thu gọn
                fb_job = str(row.get("job_id", ""))
                fb_done = st.session_state.setdefault("feedback_done", {})
                fb_cols = st.columns([1, 1, 3.2])
                for fb_col, fb_event, fb_label, fb_done_label in ((fb_cols[0], "save", "Quan tâm", "Đã quan tâm"),
                                                                   (fb_cols[1], "apply", "Ứng tuyển", "Đã ứng tuyển")):
                    fb_key = f"fb_{fb_event}_{fb_user}_{fb_job}"
                    with fb_col:
                        if st.button(fb_done_label if fb_key in fb_done else fb_label, key=fb_key,
                                     disabled=fb_key in fb_done, use_container_width=True):
                            interaction_log.log_event(fb_user, fb_job, fb_event, position=int(idx), source=rec_mode)
                            fb_done[fb_key] = True
                            st.session_state["pending_feedback"] = True
                            st.toast(f"Đã ghi nhận '{fb_label}' cho tin: {row['Tiêu đề']}")
                            st.rerun()
                with fb_cols[2]:
                    with st.expander("Chi tiết điểm"):
                        skill_score = row.get("Điểm kỹ năng (%)")
                        st.markdown(
                            f"- Kỹ năng: **{'không có dữ liệu' if pd.isna(skill_score) else f'{skill_score}%'}** "
                            f"(khớp {row.get('Độ phủ kỹ năng (%)', '')})\n"
                            f"- Văn bản (TF-IDF): **{row.get('Điểm văn bản (%)', 0)}%**\n"
                            f"- Kinh nghiệm: **{row.get('Điểm kinh nghiệm (%)', 0)}%**\n"
                            f"- Địa điểm / hình thức: **{row.get('Điểm vị trí/hình thức (%)', 0)}%**\n\n"
                            f"Điểm hồ sơ (CBF) = 0,30 kỹ năng + 0,40 văn bản + 0,10 kinh nghiệm + 0,10 địa điểm + 0,10 lương "
                            f"(thành phần thiếu dữ liệu được bỏ và chia lại trọng số)."
                        )
                        st.caption(f"Lý do: {row.get('Lời giải thích', '')}")
                st.write("")

            # D. Bảng tóm tắt (tùy chọn, thu gọn mặc định)
            with st.expander("Xem dạng bảng"):
                table = pd.DataFrame({
                    "Hạng": df_results.get("Hạng", pd.Series(range(1, len(df_results) + 1))),
                    "Tiêu đề": df_results["Tiêu đề"],
                    "Công ty": df_results["Công ty"],
                    "Khớp hồ sơ (CBF %)": df_results["Tổng điểm (%)"],
                })
                if has_cf:
                    table["Người giống bạn (CF %)"] = df_results["Điểm CF (%)"]
                table["Kỹ năng còn thiếu"] = df_results["Kỹ năng còn thiếu (Gap)"]
                if "job_url" in df_results.columns:
                    table["Tin gốc"] = df_results["job_url"]
                st.dataframe(table, hide_index=True, use_container_width=True,
                             column_config={"Tin gốc": st.column_config.LinkColumn("Tin gốc", display_text="Mở")})

with tab_market:
    render_market_insights()
