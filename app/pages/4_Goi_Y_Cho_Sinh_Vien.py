import streamlit as st
import pandas as pd
from database import load_student_career_jobs, load_jobs_with_skills_for_comparison
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header
)
from components.charts import plot_bar_horizontal, plot_donut

st.set_page_config(page_title="Gợi Ý Cho Sinh Viên & Fresher", layout="wide")

apply_custom_theme()
render_sidebar_header()

render_hero(
    tag="HƯỚNG NGHIỆP • SINH VIÊN & FRESHER IT",
    title="Góc Định Hướng Nghề Nghiệp: Sinh Viên & Fresher IT",
    subtitle="Cung cấp bức tranh toàn diện cho sinh viên mới ra trường và người chuyển ngành: Kỹ năng công nghệ trọng tâm, mức lương kỳ vọng thực tế và danh sách việc làm đang mở nhận hồ sơ"
)

# Nạp dữ liệu
df_student_jobs = load_student_career_jobs()
df_all_skills = load_jobs_with_skills_for_comparison()

# Lọc các kỹ năng được yêu cầu trong các vị trí Intern / Fresher
fresher_job_ids = set(df_student_jobs["job_id"])
sub_fresher_skills = df_all_skills[df_all_skills["job_id"].isin(fresher_job_ids)]

# 1. Các chỉ số KPI trọng điểm cho sinh viên
c1, c2, c3, c4 = st.columns(4)

with c1:
    render_kpi_card(
        title="Tổng tin mở cho Sinh viên",
        value=f"{len(df_student_jobs):,} tin",
        subtext="Bao gồm Thực tập sinh & Fresher",
        badge_text="Cơ hội đầu vào",
        badge_type="info"
    )

with c2:
    active_cnt = int((df_student_jobs["is_active"] == True).sum())
    active_pct = active_cnt / max(1, len(df_student_jobs)) * 100
    render_kpi_card(
        title="Vị trí đang nhận hồ sơ",
        value=f"{active_cnt:,} tin",
        subtext=f"Tỷ lệ còn hạn: {active_pct:.1f}%",
        badge_text="Đang mở tuyển",
        badge_type="success"
    )

with c3:
    sal_available = df_student_jobs[df_student_jobs["salary_max_vnd"].notna()]
    avg_fresher_sal = sal_available["salary_max_vnd"].mean() / 1e6 if len(sal_available) > 0 else 0
    render_kpi_card(
        title="Lương khởi điểm trung bình",
        value=f"{avg_fresher_sal:.1f} triệu/tháng",
        subtext="Trung bình các tin công bố lương",
        badge_text="Mức tham chiếu",
        badge_type="success"
    )

with c4:
    remote_cnt = int((df_student_jobs["work_mode"] == "Remote").sum())
    render_kpi_card(
        title="Cơ hội Remote / Linh hoạt",
        value=f"{remote_cnt} tin",
        subtext="Làm việc từ xa hoàn toàn",
        badge_text="Làm việc từ xa",
        badge_type="neutral"
    )

st.write("")

# 2. Top Kỹ năng sinh viên nên trang bị & Phân bố thành phố
col_k, col_g = st.columns([3, 2])

with col_k:
    render_section_title(
        title="Top Kỹ Năng Được Đòi Hỏi Nhiều Nhất Ở Vị Trí Đầu Vào",
        subtitle="Dữ liệu bóc tách từ các tin tuyển dụng Intern & Fresher thực tế"
    )
    skill_counts = sub_fresher_skills.groupby("skill_name")["job_id"].nunique().reset_index()
    skill_counts.columns = ["skill_name", "job_count"]
    skill_counts = skill_counts.sort_values("job_count", ascending=False).head(12)
    fig_k = plot_bar_horizontal(skill_counts, "job_count", "skill_name", "")
    st.plotly_chart(fig_k, use_container_width=True)

with col_g:
    render_section_title(
        title="Địa Điểm Tuyển Dụng Thực Tập & Fresher",
        subtitle="Cơ cấu nhu cầu nhân sự đầu vào theo địa phương"
    )
    city_counts = df_student_jobs.groupby("city")["job_id"].count().reset_index()
    city_counts.columns = ["city", "job_count"]
    fig_c = plot_donut(city_counts, "city", "job_count", "")
    st.plotly_chart(fig_c, use_container_width=True)

st.write("")

# 3. Bảng tra cứu danh sách tin tuyển dụng Intern / Fresher
render_section_title(
    title="Tra Cứu Danh Sách Việc Làm Thực Tập & Fresher Đang Tuyển",
    subtitle="Lọc và tìm kiếm trực tiếp các cơ hội việc làm phù hợp cho người mới bắt đầu"
)

col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_city = st.selectbox("Lọc theo Thành phố:", options=["Tất cả"] + sorted(df_student_jobs["city"].dropna().unique().tolist()))
with col_f2:
    filter_status = st.selectbox("Trạng thái tuyển dụng:", options=["Tất cả", "Chỉ xem tin còn hạn"])

filtered_jobs = df_student_jobs.copy()
if filter_city != "Tất cả":
    filtered_jobs = filtered_jobs[filtered_jobs["city"] == filter_city]
if filter_status == "Chỉ xem tin còn hạn":
    filtered_jobs = filtered_jobs[filtered_jobs["is_active"] == True]

view_table = filtered_jobs[[
    "title_normalized", "company_name_normalized", "city",
    "work_mode", "salary_type", "deadline", "source_job_url"
]].copy()

view_table.columns = ["Vị Trí Tuyển Dụng", "Công Ty", "Thành Phố", "Hình Thức", "Định Dạng Lương", "Hạn Nộp", "Link Chi Tiết"]
st.dataframe(
    view_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link Chi Tiết": st.column_config.LinkColumn("Đường Dẫn Ứng Tuyển")
    }
)
