import streamlit as st
import pandas as pd
from config import PAGE_CONFIG
from database import load_market_kpis, load_role_geo_matrix
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header,
    render_nav_card
)
from components.charts import plot_bar_horizontal, plot_donut

st.set_page_config(
    page_title=PAGE_CONFIG["page_title"],
    layout=PAGE_CONFIG["layout"],
    initial_sidebar_state=PAGE_CONFIG["initial_sidebar_state"]
)

# Kích hoạt giao diện SaaS web hiện đại
apply_custom_theme()
render_sidebar_header()

# Hero Banner
render_hero(
    tag="BÁO CÁO TOÀN CẢNH • 2026",
    title="IT Job Market Intelligence Dashboard",
    subtitle="Hệ thống giám sát và phân tích thông minh thị trường tuyển dụng Công nghệ thông tin Việt Nam dựa trên dữ liệu chuẩn hóa từ TopCV, TopDev, VietnamWorks"
)

# 1. Thẻ chỉ số tổng quan (Executive KPI Cards)
try:
    kpis = load_market_kpis()
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        render_kpi_card(
            title="Tổng số việc làm",
            value=f"{int(kpis['total_jobs']):,} tin",
            subtext="Thu thập từ các sàn tuyển dụng",
            badge_text="Dữ liệu làm sạch",
            badge_type="info"
        )
    with col2:
        active_pct = kpis['active_jobs'] / kpis['total_jobs'] * 100
        render_kpi_card(
            title="Đang mở tuyển dụng",
            value=f"{int(kpis['active_jobs']):,} tin",
            subtext=f"Tỷ lệ còn hạn ứng tuyển: {active_pct:.1f}%",
            badge_text="Đang nhận hồ sơ",
            badge_type="success"
        )
    with col3:
        render_kpi_card(
            title="Doanh nghiệp IT",
            value=f"{int(kpis['total_companies']):,} cty",
            subtext="Khử trùng lặp và phân loại ngành",
            badge_text="Doanh nghiệp xác thực",
            badge_type="neutral"
        )
    with col4:
        render_kpi_card(
            title="Kỹ năng theo dõi",
            value=f"{int(kpis['total_unique_skills'])} kỹ năng",
            subtext="Chuẩn hóa theo 10 nhóm chuyên môn",
            badge_text="Taxonomy chuẩn",
            badge_type="warning"
        )
    with col5:
        avg_max = kpis.get('avg_salary_max_vnd')
        val_str = f"{avg_max/1e6:.1f} triệu" if avg_max else "Thỏa thuận"
        render_kpi_card(
            title="Lương trần trung bình",
            value=val_str,
            subtext="Mức lương chuẩn hóa VNĐ/tháng",
            badge_text="Tin có công bố",
            badge_type="success"
        )

    st.write("")

    # 2. Hai biểu đồ tổng quan nhanh
    col_chart1, col_chart2 = st.columns([3, 2])

    df_roles = load_role_geo_matrix()

    with col_chart1:
        render_section_title(
            title="Top 10 Vị Trí Tuyển Dụng Sôi Động Nhất",
            subtitle="Số lượng vị trí đang có nhu cầu nhân sự dẫn đầu thị trường"
        )
        top_roles = df_roles.groupby("title_normalized")["posting_count"].sum().reset_index()
        top_roles = top_roles.sort_values("posting_count", ascending=False).head(10)
        fig_roles = plot_bar_horizontal(top_roles, "posting_count", "title_normalized", "")
        st.plotly_chart(fig_roles, use_container_width=True)

    with col_chart2:
        render_section_title(
            title="Phân Bố Việc Làm Theo Địa Phương",
            subtitle="Tỷ trọng cơ hội việc làm giữa các trung tâm công nghệ"
        )
        city_dist = df_roles.groupby("city")["posting_count"].sum().reset_index()
        fig_city = plot_donut(city_dist, "city", "posting_count", "")
        st.plotly_chart(fig_city, use_container_width=True)

    st.write("")

    # 3. Điều hướng các phân hệ chuyên sâu
    render_section_title(
        title="Các Phân Hệ Phân Tích Chuyên Sâu",
        subtitle="Chọn phân hệ trong Menu thanh bên trái để xem báo cáo chi tiết"
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_nav_card(
            title="1. Thị Trường IT",
            desc="Nhu cầu tuyển dụng theo chức danh, địa bàn tỉnh thành, top doanh nghiệp và hình thức Onsite / Remote / Hybrid."
        )
    with c2:
        render_nav_card(
            title="2. Kỹ Năng & Yêu Cầu",
            desc="Phân tích 76 kỹ năng IT chuẩn hóa, tỷ lệ bắt buộc so với ưu tiên, ma trận kỹ năng đi kèm và so sánh vai trò."
        )
    with c3:
        render_nav_card(
            title="3. Lương & Kinh Nghiệm",
            desc="Benchmark khung thu nhập VNĐ theo cấp bậc chuyên môn, thâm niên số năm kinh nghiệm và kỹ năng lương cao."
        )
    with c4:
        render_nav_card(
            title="4. Cho Sinh Viên",
            desc="Định hướng nghề nghiệp dành riêng cho Intern / Fresher: Kỹ năng trọng tâm, mức lương kỳ vọng và việc làm đang mở."
        )
    with c5:
        render_nav_card(
            title="5. Gợi Ý Việc Làm AI",
            desc="Trợ lý cá nhân hóa: Dán CV hoặc kỹ năng để nhận ngay việc làm phù hợp nhất bằng mô hình Semantic Vector AI."
        )

except Exception as e:
    st.error(f"Lỗi kết nối cơ sở dữ liệu hoặc nạp dữ liệu: {e}")
    st.warning("Vui lòng kiểm tra lại cấu hình .env và đảm bảo dịch vụ PostgreSQL đang hoạt động.")
