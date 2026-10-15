import streamlit as st
import pandas as pd
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header
)
from src.recommender.matcher import recommend_jobs, extract_candidate_skills
from database import load_role_geo_matrix

st.set_page_config(page_title="Gợi Ý Việc Làm Thông Minh", layout="wide")

apply_custom_theme()
render_sidebar_header()

render_hero(
    tag="HƯỚNG NGHIỆP THÔNG MINH • AI JOB MATCHER",
    title="Trợ Lý Gợi Ý Việc Làm Cá Nhân Hóa",
    subtitle="Đề xuất các cơ hội nghề nghiệp tối ưu dựa trên mô hình học sâu ngữ nghĩa (Semantic Embedding) kết hợp độ trùng khớp kỹ năng chuyên môn từ 2,752 tin tuyển dụng thực tế"
)

# 1. Các hồ sơ mẫu thử nghiệm nhanh (Preset Profiles)
PRESETS = {
    "Chọn hồ sơ mẫu...": "",
    "Fresher Data Analyst (SQL / Python / Power BI)": (
        "Tôi là sinh viên mới tốt nghiệp ngành Công nghệ thông tin / Hệ thống thông tin, "
        "có nền tảng tốt về truy vấn dữ liệu SQL, phân tích dữ liệu với Python (Pandas, NumPy) "
        "và trực quan hóa báo cáo trên Power BI. Mong muốn tìm kiếm cơ hội việc làm vị trí "
        "Fresher hoặc Junior Data Analyst, sẵn sàng học hỏi thêm về Data Warehouse và Business Intelligence."
    ),
    "Junior Frontend Developer (React / TypeScript)": (
        "Lập trình viên Frontend có 1-2 năm kinh nghiệm làm việc chuyên sâu với React, TypeScript, "
        "Next.js, HTML5, CSS3, Tailwind CSS và thiết kế giao diện Figma. Có kinh nghiệm xây dựng ứng dụng "
        "Web responsive đa thiết bị, tối ưu hóa tốc độ tải trang và kết nối RESTful API."
    ),
    "Java Spring Boot Backend Engineer": (
        "Kỹ sư Backend với 2-3 năm kinh nghiệm lập trình Java, thành thạo framework Spring Boot, "
        "Spring Framework và kiến trúc Microservices. Nắm vững cơ sở dữ liệu quan hệ PostgreSQL, MySQL, "
        "thiết kế RESTful API chuẩn mực, tối ưu hóa câu lệnh truy vấn và xử lý caching với Redis."
    ),
    "DevOps / Cloud Engineer (AWS / Docker / K8s)": (
        "Kỹ sư DevOps có kinh nghiệm quản trị hạ tầng đám mây AWS, đóng gói ứng dụng bằng Docker "
        "và điều phối cụm Kubernetes (K8s). Thành thạo thiết lập quy trình tự động hóa CI/CD pipeline, "
        "quản trị hệ điều hành Linux và giám sát hệ thống với Prometheus, Grafana."
    )
}

# 2. Bộ lọc Sidebar
st.sidebar.markdown("### Bộ Lọc Tìm Kiếm")

# Lấy danh sách thành phố từ DB
df_roles = load_role_geo_matrix()
cities = ["Tất cả"] + sorted([c for c in df_roles["city"].dropna().unique() if c != "Khác"]) + ["Khác"]
selected_city = st.sidebar.selectbox("Địa điểm làm việc:", options=cities, index=0)

seniorities = ["Tất cả", "Intern / Fresher", "Junior", "Middle", "Senior", "Lead / Manager"]
selected_seniority = st.sidebar.selectbox("Cấp bậc mong muốn:", options=seniorities, index=0)

work_modes = ["Tất cả", "Onsite", "Remote", "Hybrid"]
selected_work_mode = st.sidebar.selectbox("Hình thức làm việc:", options=work_modes, index=0)

top_n = st.sidebar.slider("Số lượng việc làm đề xuất:", min_value=5, max_value=25, value=10)

st.sidebar.markdown("---")
st.sidebar.markdown("### Tinh Chỉnh Thuật Toán (Hybrid)")
weight_sem = st.sidebar.slider("Trọng số Ngữ nghĩa (Semantic)", min_value=0.3, max_value=0.9, value=0.65, step=0.05)
weight_ski = round(1.0 - weight_sem, 2)
st.sidebar.caption(f"Trọng số Kỹ năng cứng (Skills): **{weight_ski}**")

# 3. Khu vực nhập liệu hồ sơ ứng viên
render_section_title(
    title="Nhập Hồ Sơ Năng Lực / Nguyện Vọng Nghề Nghiệp",
    subtitle="Dán nội dung tóm tắt kinh nghiệm từ CV của bạn hoặc chọn nhanh một hồ sơ mẫu bên dưới để kiểm thử"
)

selected_preset = st.selectbox("Nạp nhanh mẫu hồ sơ thử nghiệm:", options=list(PRESETS.keys()))

default_text = PRESETS[selected_preset] if selected_preset != "Chọn hồ sơ mẫu..." else ""

profile_text = st.text_area(
    "Nội dung hồ sơ ứng viên / CV tóm tắt:",
    value=default_text,
    height=150,
    placeholder="Ví dụ: Tôi có kinh nghiệm lập trình Backend với Python, Django, làm việc với PostgreSQL và Docker. Mong muốn tìm công việc từ xa (Remote)..."
)

col_btn, col_empty = st.columns([1, 4])
with col_btn:
    btn_search = st.button("Phân Tích & Gợi Ý Việc Làm", type="primary", use_container_width=True)

if btn_search or (profile_text and selected_preset != "Chọn hồ sơ mẫu..."):
    if not profile_text.strip():
        st.warning("Vui lòng nhập nội dung hồ sơ hoặc chọn một hồ sơ mẫu để hệ thống phân tích.")
    else:
        with st.spinner("Đang mã hóa ngữ nghĩa vector và tính toán độ phù hợp trên toàn bộ 2,752 việc làm..."):
            detected_skills, recommendations = recommend_jobs(
                candidate_profile_text=profile_text,
                top_n=top_n,
                filter_city=selected_city,
                filter_seniority=selected_seniority,
                filter_work_mode=selected_work_mode,
                weight_semantic=weight_sem,
                weight_skills=weight_ski
            )

        st.write("")

        # Hiển thị kỹ năng nhận diện
        if detected_skills:
            st.markdown("##### Kỹ năng công nghệ nhận diện từ hồ sơ của bạn:")
            skill_chips = " ".join([f"`{s}`" for s in detected_skills])
            st.markdown(f"{skill_chips}")
        else:
            st.info("Chưa phát hiện tên kỹ năng công nghệ cụ thể trong hồ sơ. Hệ thống sẽ áp dụng 100% độ tương đồng ngữ nghĩa để gợi ý việc làm.")

        st.write("")

        if not recommendations:
            st.warning("Không tìm thấy việc làm nào thỏa mãn bộ lọc đã chọn. Bạn hãy thử nới lỏng các tiêu chí lọc ở thanh bên (ví dụ chọn Địa điểm: Tất cả).")
        else:
            # KPI Cards tóm tắt
            best_match = recommendations[0]["match_score"]
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                render_kpi_card(
                    title="Độ phù hợp cao nhất",
                    value=f"{best_match}%",
                    subtext="Xếp hạng 1 trong danh sách",
                    badge_text="Khớp cao nhất",
                    badge_type="success" if best_match >= 75 else "info"
                )
            with c2:
                render_kpi_card(
                    title="Việc làm đề xuất",
                    value=f"{len(recommendations)} tin",
                    subtext="Thỏa mãn tiêu chí lọc",
                    badge_text="Đã xếp hạng",
                    badge_type="neutral"
                )
            with c3:
                render_kpi_card(
                    title="Kỹ năng của bạn",
                    value=f"{len(detected_skills)} kỹ năng",
                    subtext="Chuẩn hóa theo taxonomy",
                    badge_text="Nhận diện tự động",
                    badge_type="info"
                )
            with c4:
                top_role = recommendations[0]["title"]
                render_kpi_card(
                    title="Vị trí tương đồng nhất",
                    value=top_role,
                    subtext="Khớp chuyên môn cao nhất",
                    badge_text="Đề xuất ưu tiên",
                    badge_type="warning"
                )

            st.write("")
            render_section_title(
                title="Bảng Xếp Hạng Việc Làm Phù Hợp Nhất Dành Cho Bạn",
                subtitle="Được tính toán từ mô hình Semantic Vector kết hợp tỷ lệ kỹ năng đáp ứng thực tế"
            )

            # Hiển thị từng Card công việc
            for idx, job in enumerate(recommendations, 1):
                score = job["match_score"]
                badge_color = "#10b981" if score >= 70 else ("#2563eb" if score >= 55 else "#64748b")
                
                matched_html = " ".join([f'<span style="background:#ecfdf5; color:#047857; border:1px solid #a7f3d0; padding:2px 8px; border-radius:9999px; font-size:0.75rem; font-weight:600; margin-right:4px;">{s}</span>' for s in job["matched_skills"]]) if job["matched_skills"] else '<span style="color:#94a3b8; font-size:0.8rem;">Chưa có kỹ năng trùng khớp</span>'
                missing_html = " ".join([f'<span style="background:#fffbeb; color:#b45309; border:1px solid #fde68a; padding:2px 8px; border-radius:9999px; font-size:0.75rem; font-weight:600; margin-right:4px;">{s}</span>' for s in job["missing_skills"][:6]]) if job["missing_skills"] else '<span style="color:#94a3b8; font-size:0.8rem;">Bạn đã đáp ứng đủ kỹ năng yêu cầu</span>'

                card_html = f"""
                <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:14px; padding:20px 24px; margin-bottom:16px; box-shadow:0 1px 3px rgba(15,23,42,0.04); transition:all 0.2s ease;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div>
                            <span style="font-size:0.75rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.05em;">HẠNG #{idx:02d}</span>
                            <h4 style="margin:2px 0 4px 0; color:#0f172a; font-size:1.2rem; font-weight:700;">{job['title']}</h4>
                            <p style="margin:0; font-size:0.9rem; font-weight:600; color:#2563eb;">{job['company']}</p>
                        </div>
                        <div style="text-align:right;">
                            <span style="display:inline-block; background:{badge_color}; color:#ffffff; font-weight:800; font-size:0.88rem; padding:4px 12px; border-radius:9999px; box-shadow:0 2px 4px rgba(0,0,0,0.08);">
                                Phù hợp: {score}%
                            </span>
                            <div style="font-size:0.75rem; color:#64748b; margin-top:4px;">Ngữ nghĩa: {job['semantic_score']}% | Kỹ năng: {job['skill_score']}%</div>
                        </div>
                    </div>
                    
                    <div style="display:flex; flex-wrap:wrap; gap:16px; font-size:0.85rem; color:#475569; margin:10px 0; padding:10px 0; border-top:1px solid #f1f5f9; border-bottom:1px solid #f1f5f9;">
                        <div><strong>Địa điểm:</strong> {job['city']}</div>
                        <div><strong>Hình thức:</strong> {job['work_mode']}</div>
                        <div><strong>Cấp bậc:</strong> {job['seniority_level']}</div>
                        <div><strong>Mức lương:</strong> <span style="color:#059669; font-weight:700;">{job['salary_str']}</span></div>
                    </div>

                    <div style="margin-top:10px;">
                        <div style="margin-bottom:6px;"><strong style="font-size:0.82rem; color:#0f172a;">Kỹ năng bạn đã có:</strong> {matched_html}</div>
                        <div><strong style="font-size:0.82rem; color:#0f172a;">Kỹ năng khuyên trang bị thêm:</strong> {missing_html}</div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Nút ứng tuyển
                if job.get("url"):
                    st.link_button(f"Ứng Tuyển Vị Trí #{idx:02d} Tại Sàn Nguồn", url=job["url"], use_container_width=False)
                st.write("")
