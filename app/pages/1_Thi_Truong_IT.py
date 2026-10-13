import streamlit as st
import pandas as pd
from database import load_role_geo_matrix, load_company_rankings
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header
)
from components.charts import plot_bar_horizontal, plot_donut

st.set_page_config(page_title="Thị Trường Tuyển Dụng IT", layout="wide")

apply_custom_theme()
render_sidebar_header()

render_hero(
    tag="PHÂN HỆ THỊ TRƯỜNG • 2026",
    title="Phân Tích Toàn Cảnh Thị Trường Tuyển Dụng IT",
    subtitle="Nghiên cứu nhu cầu tuyển dụng thực tế theo chức danh, địa bàn tỉnh thành, hình thức làm việc và mạng lưới doanh nghiệp công nghệ"
)

# Nạp dữ liệu
df_roles = load_role_geo_matrix()
df_companies = load_company_rankings()

# Bộ lọc tại Sidebar
st.sidebar.markdown("### Bộ Lọc Phân Tích")
selected_city = st.sidebar.multiselect("Lọc theo Tỉnh / Thành phố:", options=sorted(df_roles["city"].dropna().unique()), default=[])
selected_work_mode = st.sidebar.multiselect("Lọc theo Hình thức làm việc:", options=sorted(df_roles["work_mode"].dropna().unique()), default=[])
selected_seniority = st.sidebar.multiselect("Lọc theo Cấp bậc chuyên môn:", options=sorted(df_roles["seniority_level"].dropna().unique()), default=[])

filtered_df = df_roles.copy()
if selected_city:
    filtered_df = filtered_df[filtered_df["city"].isin(selected_city)]
if selected_work_mode:
    filtered_df = filtered_df[filtered_df["work_mode"].isin(selected_work_mode)]
if selected_seniority:
    filtered_df = filtered_df[filtered_df["seniority_level"].isin(selected_seniority)]

# KPI tóm tắt kết quả lọc
total_filtered_jobs = filtered_df["posting_count"].sum()
top_role = filtered_df.groupby("title_normalized")["posting_count"].sum().idxmax() if len(filtered_df) > 0 else "N/A"
top_city = filtered_df.groupby("city")["posting_count"].sum().idxmax() if len(filtered_df) > 0 else "N/A"
remote_cnt = filtered_df[filtered_df["work_mode"].isin(["Remote", "Hybrid"])]["posting_count"].sum()
remote_pct = (remote_cnt / total_filtered_jobs * 100) if total_filtered_jobs > 0 else 0

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
with c_kpi1:
    render_kpi_card(
        title="Tổng tin đang lọc",
        value=f"{total_filtered_jobs:,} tin",
        subtext="Theo tiêu chí lọc bên trái",
        badge_text="Bộ lọc hiện tại",
        badge_type="info"
    )
with c_kpi2:
    render_kpi_card(
        title="Vị trí có nhu cầu lớn nhất",
        value=top_role,
        subtext="Chức danh tuyển dụng nhiều nhất",
        badge_text="Dẫn đầu nhu cầu",
        badge_type="success"
    )
with c_kpi3:
    render_kpi_card(
        title="Thủ phủ công nghệ",
        value=top_city,
        subtext="Địa phương tập trung việc làm cao nhất",
        badge_text="Khu vực trọng điểm",
        badge_type="warning"
    )
with c_kpi4:
    render_kpi_card(
        title="Tỷ lệ Remote / Hybrid",
        value=f"{remote_pct:.1f}%",
        subtext=f"{remote_cnt:,} tin làm việc linh hoạt",
        badge_text="Xu hướng làm việc",
        badge_type="neutral"
    )

st.write("")

# 1. Biểu đồ Vị trí tuyển dụng & Hình thức làm việc
c1, c2 = st.columns([3, 2])

with c1:
    render_section_title(
        title="Xếp Hạng Chức Danh Có Nhu Cầu Cao Nhất",
        subtitle="Số lượng vị trí tuyển dụng theo từng chuyên môn kỹ thuật"
    )
    top_n = st.slider("Số lượng vị trí hiển thị:", min_value=5, max_value=30, value=12)
    roles_agg = filtered_df.groupby("title_normalized")["posting_count"].sum().reset_index()
    roles_agg = roles_agg.sort_values("posting_count", ascending=False).head(top_n)
    fig_roles = plot_bar_horizontal(roles_agg, "posting_count", "title_normalized", "")
    st.plotly_chart(fig_roles, use_container_width=True)

with c2:
    render_section_title(
        title="Cơ Cấu Hình Thức Làm Việc",
        subtitle="Tỷ trọng giữa Onsite, Remote và Hybrid"
    )
    wm_agg = filtered_df.groupby("work_mode")["posting_count"].sum().reset_index()
    fig_wm = plot_donut(wm_agg, "work_mode", "posting_count", "")
    st.plotly_chart(fig_wm, use_container_width=True)

st.write("")

# 2. Phân bố theo địa lý & Nhóm ngành nghề
c3, c4 = st.columns([2, 3])

with c3:
    render_section_title(
        title="Phân Bố Theo Địa Phương",
        subtitle="Nhu cầu nhân sự theo từng tỉnh / thành phố"
    )
    city_agg = filtered_df.groupby("city")["posting_count"].sum().reset_index().sort_values("posting_count", ascending=False)
    fig_city = plot_bar_horizontal(city_agg, "posting_count", "city", "")
    st.plotly_chart(fig_city, use_container_width=True)

with c4:
    render_section_title(
        title="Top Ngành Nghề Doanh Nghiệp Tuyển Dụng",
        subtitle="Các lĩnh vực kinh doanh cần nhiều nhân lực IT nhất"
    )
    ind_agg = df_companies.groupby("industry")["total_postings"].sum().reset_index().sort_values("total_postings", ascending=False).head(10)
    fig_ind = plot_bar_horizontal(ind_agg, "total_postings", "industry", "")
    st.plotly_chart(fig_ind, use_container_width=True)

st.write("")

# 3. Bảng xếp hạng Top Doanh nghiệp tuyển dụng nhiều nhất
render_section_title(
    title="Bảng Xếp Hạng Top Doanh Nghiệp Tuyển Dụng IT Lớn Nhất",
    subtitle="Danh sách các công ty có lượng tin tuyển dụng hoạt động tích cực nhất"
)
top_comp_view = df_companies[["company_name_normalized", "company_city", "industry", "total_postings", "active_postings"]].copy()
top_comp_view.columns = ["Tên Công Ty", "Trụ Sở", "Lĩnh Vực Hoạt Động", "Tổng Tin Tuyển", "Tin Còn Hạn"]
st.dataframe(
    top_comp_view.head(20),
    use_container_width=True,
    hide_index=True
)
