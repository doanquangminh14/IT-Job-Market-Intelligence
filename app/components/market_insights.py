import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# Đảm bảo đường dẫn gốc dự án
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.components.charts import (
    plot_bar_horizontal,
    plot_donut,
    plot_stacked_bar,
    plot_boxplot,
    plot_histogram
)

from src.data_cleaning.freshness import refresh_is_active
from src.recommender.content_based import data_file_version


@st.cache_data
def _load_cleaned_jobs_cached(data_version: tuple) -> pd.DataFrame:
    """Nạp dữ liệu sạch (cùng file với hệ gợi ý). Khóa cache = (file, thời điểm sửa, ngày hôm nay)."""
    (path, _), _today = data_version
    if not path:
        return pd.DataFrame()
    df = pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    return refresh_is_active(df)          # tin còn hạn tính theo ngày hôm nay


def load_raw_cleaned_jobs() -> pd.DataFrame:
    """Chạy lại notebook 02 (file đổi) hoặc sang ngày mới thì tự nạp lại."""
    return _load_cleaned_jobs_cached((data_file_version(), pd.Timestamp.now().date().isoformat()))


def render_market_insights():
    """Hàm hiển thị giao diện phân tích toàn cảnh thị trường tuyển dụng IT."""
    
    # Header khối phân tích
    st.markdown("""
    <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:12px; padding:24px 28px; margin-bottom:20px; box-shadow:0 1px 3px rgba(15,23,42,0.03);">
        <span style="display:inline-block; font-size:0.72rem; font-weight:700; letter-spacing:0.08em; text-transform:uppercase; color:#2563eb; background:#eff6ff; padding:3px 10px; border-radius:6px; margin-bottom:8px; border:1px solid #bfdbfe;">
            THỊ TRƯỜNG TUYỂN DỤNG IT VIỆT NAM
        </span>
        <h2 style="font-size:1.6rem; font-weight:700; color:#0f172a; margin:0 0 6px 0;">Báo Cáo Phân Tích Toàn Cảnh Thị Trường</h2>
        <p style="font-size:0.9rem; color:#64748b; margin:0; line-height:1.5;">
            Khảo sát nhu cầu tuyển dụng thực tế, cơ cấu kỹ năng công nghệ, phân bố mức lương và xu hướng làm việc từ dữ liệu cào đa nền tảng
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    df_raw = load_raw_cleaned_jobs()
    if df_raw.empty:
        st.error("Không tìm thấy tệp dữ liệu việc làm. Vui lòng kiểm tra lại thư mục data/.")
        return

    # Khung bộ lọc tương tác
    with st.expander("Tùy Chỉnh Bộ Lọc Phân Tích Thị Trường", expanded=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            all_cities = ["Tất cả"] + sorted([str(c) for c in df_raw['city'].dropna().unique() if str(c).strip()])
            filter_city = st.selectbox("Khu vực / Thành phố:", options=all_cities, index=0)
            
        with col_f2:
            all_modes = ["Tất cả"] + sorted([str(m) for m in df_raw['work_mode'].dropna().unique() if str(m).strip()])
            filter_mode = st.selectbox("Hình thức làm việc:", options=all_modes, index=0)
            
        with col_f3:
            all_active = ["Tất cả", "Chỉ tin còn hạn (is_active)", "Tin đã hết hạn"]
            filter_active = st.selectbox("Trạng thái tuyển dụng:", options=all_active, index=0)

    # Áp dụng bộ lọc
    filtered_df = df_raw.copy()
    if filter_city != "Tất cả":
        filtered_df = filtered_df[filtered_df['city'] == filter_city]
    if filter_mode != "Tất cả":
        filtered_df = filtered_df[filtered_df['work_mode'] == filter_mode]
    if filter_active == "Chỉ tin còn hạn (is_active)":
        filtered_df = filtered_df[filtered_df['is_active'] == True]
    elif filter_active == "Tin đã hết hạn":
        filtered_df = filtered_df[filtered_df['is_active'] == False]

    total_filtered = len(filtered_df)
    if total_filtered == 0:
        st.warning("Không có dữ liệu phù hợp với tiêu chí lọc đã chọn. Vui lòng mở rộng bộ lọc.")
        return

    # 1. Khối KPI Cards
    active_cnt = int(filtered_df['is_active'].sum()) if 'is_active' in filtered_df else 0
    active_pct = round(active_cnt / total_filtered * 100, 1) if total_filtered > 0 else 0.0

    remote_hybrid_cnt = int(filtered_df['work_mode'].isin(['Remote', 'Hybrid']).sum())
    remote_pct = round(remote_hybrid_cnt / total_filtered * 100, 1) if total_filtered > 0 else 0.0

    sal_valid = filtered_df[filtered_df['salary_max'].notna() & (filtered_df['salary_max'] > 0)]
    median_sal_max = round(sal_valid['salary_max'].median() / 1e6, 1) if not sal_valid.empty else 0.0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px 20px;">
            <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">Tổng tin tuyển dụng</div>
            <div style="font-size:1.6rem; font-weight:700; color:#0f172a; margin:4px 0;">{total_filtered:,}</div>
            <div style="font-size:0.78rem; color:#64748b;">Theo bộ lọc hiện tại</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi2:
        st.markdown(f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px 20px;">
            <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">Tin còn hiệu lực</div>
            <div style="font-size:1.6rem; font-weight:700; color:#059669; margin:4px 0;">{active_cnt:,} <span style="font-size:0.9rem; font-weight:500;">({active_pct}%)</span></div>
            <div style="font-size:0.78rem; color:#64748b;">Đang mở ứng tuyển</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi3:
        st.markdown(f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px 20px;">
            <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">Lương trung vị (Tối đa)</div>
            <div style="font-size:1.6rem; font-weight:700; color:#2563eb; margin:4px 0;">{median_sal_max} <span style="font-size:0.9rem; font-weight:500;">triệu/tháng</span></div>
            <div style="font-size:0.78rem; color:#64748b;">Dựa trên {len(sal_valid):,} tin có lương</div>
        </div>
        """, unsafe_allow_html=True)
        
    with kpi4:
        st.markdown(f"""
        <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px; padding:16px 20px;">
            <div style="font-size:0.75rem; font-weight:600; color:#64748b; text-transform:uppercase;">Làm việc linh hoạt</div>
            <div style="font-size:1.6rem; font-weight:700; color:#d97706; margin:4px 0;">{remote_pct}%</div>
            <div style="font-size:0.78rem; color:#64748b;">{remote_hybrid_cnt:,} tin Remote / Hybrid</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # 2. Hàng Biểu đồ 1: Top Kỹ Năng & Cơ Cấu Làm Việc
    c1, c2 = st.columns([3, 2])
    
    with c1:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Top 15 Kỹ Năng Công Nghệ Yêu Cầu Phổ Biến Nhất:</p>", unsafe_allow_html=True)
        skills_series = filtered_df['required_skills'].dropna().str.split(',').explode().str.strip()
        top15_skills = skills_series[skills_series != ''].value_counts().head(15).reset_index()
        top15_skills.columns = ['Kỹ năng', 'Số tin yêu cầu']
        
        fig_skills = px.bar(
            top15_skills,
            x='Số tin yêu cầu',
            y='Kỹ năng',
            orientation='h',
            color='Số tin yêu cầu',
            color_continuous_scale="Purples",
            text_auto=True
        )
        fig_skills.update_layout(
            yaxis=dict(autorange="reversed"),
            xaxis_title="Số lượng tin tuyển dụng",
            yaxis_title="",
            coloraxis_showscale=False,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_skills, use_container_width=True)

    with c2:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Cơ Cấu Mô Hình Làm Việc (Work Mode):</p>", unsafe_allow_html=True)
        wm_counts = filtered_df['work_mode'].value_counts().reset_index()
        wm_counts.columns = ['Mô hình', 'Số lượng']
        
        fig_wm = plot_donut(wm_counts, 'Mô hình', 'Số lượng', "")
        st.plotly_chart(fig_wm, use_container_width=True)

    st.write("")

    # 3. Hàng Biểu đồ 2: Phân Bố Lương & Phân Bố Kinh Nghiệm
    c3, c4 = st.columns([3, 2])
    
    with c3:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Boxplot Phân Bố Mức Lương Tối Đa Theo Thành Phố (Triệu VNĐ/tháng):</p>", unsafe_allow_html=True)
        sal_chart_df = filtered_df[
            filtered_df['salary_max'].notna() &
            (filtered_df['salary_max'] <= 80e6) &
            (filtered_df['salary_max'] > 0)
        ].copy()
        sal_chart_df['Lương tối đa (Triệu VNĐ)'] = sal_chart_df['salary_max'] / 1e6
        
        if not sal_chart_df.empty:
            fig_sal = plot_boxplot(sal_chart_df, 'city', 'Lương tối đa (Triệu VNĐ)', "")
            st.plotly_chart(fig_sal, use_container_width=True)
        else:
            st.info("Chưa đủ dữ liệu lương để vẽ biểu đồ Boxplot theo bộ lọc này.")

    with c4:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Phân Bố Số Năm Kinh Nghiệm Tối Thiểu:</p>", unsafe_allow_html=True)
        exp_chart_df = filtered_df[filtered_df['experience_min'].notna() & (filtered_df['experience_min'] <= 10)].copy()
        exp_chart_df['Số năm kinh nghiệm'] = exp_chart_df['experience_min']
        
        if not exp_chart_df.empty:
            fig_exp = plot_histogram(exp_chart_df, 'Số năm kinh nghiệm', "", nbins=11)
            st.plotly_chart(fig_exp, use_container_width=True)
        else:
            st.info("Chưa có thông tin kinh nghiệm phù hợp để hiển thị.")

    st.write("")

    # 4. Hàng Biểu đồ 3: Phân Bố Địa Phương & Tỷ Lệ Tin Còn Hạn
    c5, c6 = st.columns([3, 2])
    
    with c5:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Phân Bố Việc Làm Theo Địa Phương (Tỉnh / Thành Phố):</p>", unsafe_allow_html=True)
        city_counts = filtered_df['city'].value_counts().reset_index()
        city_counts.columns = ['Thành phố', 'Số tin']
        fig_city = plot_bar_horizontal(city_counts, 'Số tin', 'Thành phố', "")
        st.plotly_chart(fig_city, use_container_width=True)

    with c6:
        st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Tỷ Lệ Tin Tuyển Dụng Còn Hiệu Lực (is_active):</p>", unsafe_allow_html=True)
        active_counts = filtered_df['is_active'].value_counts().reset_index()
        active_counts['Trạng thái'] = active_counts['is_active'].map({True: 'Còn hạn', False: 'Đã đóng/Hết hạn'})
        active_counts.columns = ['is_active', 'Số lượng', 'Trạng thái']
        fig_act = plot_donut(active_counts, 'Trạng thái', 'Số lượng', "")
        st.plotly_chart(fig_act, use_container_width=True)

    st.write("")

    # 5. Bảng Doanh Nghiệp Tuyển Dụng Tích Cực Nhất
    st.markdown("<p style='font-size:0.95rem; font-weight:600; color:#0f172a; margin-bottom:8px;'>Top 15 Doanh Nghiệp Có Lượng Tuyển Dụng Lớn Nhất:</p>", unsafe_allow_html=True)
    comp_group = filtered_df.groupby('company_name').agg(
        Tong_tin=('job_id', 'count'),
        Tin_con_han=('is_active', lambda x: int(x.sum())),
        Khu_vuc=('city', lambda x: x.mode()[0] if not x.empty else 'N/A')
    ).reset_index().sort_values(by='Tong_tin', ascending=False).head(15)
    
    comp_group.columns = ['Tên Doanh Nghiệp', 'Tổng Tin Tuyển Dụng', 'Tin Còn Hiệu Lực', 'Khu Vực Phổ Biến']
    st.dataframe(comp_group, use_container_width=True, hide_index=True)

