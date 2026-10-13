import streamlit as st
import pandas as pd
import numpy as np
from database import load_skill_demand, load_skill_cooccurrence, load_jobs_with_skills_for_comparison
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header
)
from components.charts import plot_bar_horizontal, plot_stacked_bar, plot_heatmap

st.set_page_config(page_title="Kỹ Năng & Yêu Cầu Tuyển Dụng", layout="wide")

apply_custom_theme()
render_sidebar_header()

render_hero(
    tag="PHÂN HỆ KỸ NĂNG • 2026",
    title="Phân Tích Kỹ Năng & Yêu Cầu Tuyển Dụng IT",
    subtitle="Bóc tách 76 kỹ năng công nghệ chuẩn hóa, phân loại bắt buộc và ưu tiên, ma trận kỹ năng đi kèm và công cụ đối sánh trực quan giữa các vị trí"
)

# Nạp dữ liệu
df_skills = load_skill_demand()
df_cooccur = load_skill_cooccurrence()

# Bộ lọc Sidebar
st.sidebar.markdown("### Bộ Lọc Nhóm Kỹ Năng")
categories = sorted(df_skills["skill_category"].unique())
selected_cats = st.sidebar.multiselect("Lọc theo Nhóm chuyên môn:", options=categories, default=[])

filtered_skills = df_skills.copy()
if selected_cats:
    filtered_skills = filtered_skills[filtered_skills["skill_category"].isin(selected_cats)]

# KPI Cards tổng kết
top_skill_name = filtered_skills.iloc[0]["skill_name"] if len(filtered_skills) > 0 else "N/A"
top_skill_count = filtered_skills.iloc[0]["total_job_count"] if len(filtered_skills) > 0 else 0
top_pair = f"{df_cooccur.iloc[0]['skill_a']} + {df_cooccur.iloc[0]['skill_b']}" if len(df_cooccur) > 0 else "N/A"
pair_count = df_cooccur.iloc[0]['cooccurrence_count'] if len(df_cooccur) > 0 else 0

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
with c_kpi1:
    render_kpi_card(
        title="Tổng kỹ năng phân tích",
        value=f"{len(filtered_skills)} kỹ năng",
        subtext="Chuẩn hóa theo taxonomy",
        badge_text="Từ điển chuẩn",
        badge_type="info"
    )
with c_kpi2:
    render_kpi_card(
        title="Kỹ năng dẫn đầu nhu cầu",
        value=top_skill_name,
        subtext=f"{top_skill_count:,} tin yêu cầu",
        badge_text="Phổ biến nhất",
        badge_type="success"
    )
with c_kpi3:
    render_kpi_card(
        title="Cặp kỹ năng đi đôi nhiều nhất",
        value=top_pair,
        subtext=f"{pair_count:,} tin cùng đòi hỏi",
        badge_text="Combo công nghệ",
        badge_type="warning"
    )
with c_kpi4:
    total_req = filtered_skills["required_count"].sum()
    total_pref = filtered_skills["preferred_count"].sum()
    req_pct = total_req / max(1, (total_req + total_pref)) * 100
    render_kpi_card(
        title="Tỷ lệ yêu cầu bắt buộc",
        value=f"{req_pct:.1f}%",
        subtext=f"{total_req:,} lượt bắt buộc",
        badge_text="Tính chất yêu cầu",
        badge_type="neutral"
    )

st.write("")

# 1. Bảng xếp hạng Top Kỹ Năng & Tỷ lệ Bắt buộc vs Ưu tiên
c1, c2 = st.columns([3, 2])

with c1:
    render_section_title(
        title="Top Kỹ Năng Có Nhu Cầu Tuyển Dụng Cao Nhất",
        subtitle="Tổng số tin việc làm yêu cầu kỹ năng tương ứng"
    )
    top_k = st.slider("Số lượng kỹ năng hiển thị:", min_value=10, max_value=40, value=15)
    top_skills_df = filtered_skills.head(top_k)
    fig_skill = plot_bar_horizontal(top_skills_df, "total_job_count", "skill_name", "")
    st.plotly_chart(fig_skill, use_container_width=True)

with c2:
    render_section_title(
        title="Tỷ Lệ Bắt Buộc vs Ưu Tiên",
        subtitle="Required (Bắt buộc) so với Preferred (Ưu tiên)"
    )
    melted_df = top_skills_df[["skill_name", "required_count", "preferred_count"]].melt(
        id_vars=["skill_name"],
        value_vars=["required_count", "preferred_count"],
        var_name="Phân loại",
        value_name="Số lượng tin"
    )
    melted_df["Phân loại"] = melted_df["Phân loại"].map({"required_count": "Bắt buộc", "preferred_count": "Ưu tiên"})
    fig_stacked = plot_stacked_bar(melted_df, "skill_name", "Số lượng tin", "Phân loại", "")
    st.plotly_chart(fig_stacked, use_container_width=True)

st.write("")

# 2. Ma trận Kỹ năng thường xuất hiện cùng nhau (Co-occurrence)
render_section_title(
    title="Ma Trận Đồng Xuất Hiện Giữa Các Kỹ Năng (Co-occurrence)",
    subtitle="Các cặp công nghệ thường được nhà tuyển dụng đòi hỏi đồng thời trong cùng một bản mô tả công việc"
)

col_heat, col_table = st.columns([3, 2])

with col_heat:
    top_15_names = df_skills.head(15)["skill_name"].tolist()
    sub_cooccur = df_cooccur[df_cooccur["skill_a"].isin(top_15_names) & df_cooccur["skill_b"].isin(top_15_names)]
    
    matrix = pd.DataFrame(0, index=top_15_names, columns=top_15_names)
    for _, row in sub_cooccur.iterrows():
        matrix.loc[row["skill_a"], row["skill_b"]] = row["cooccurrence_count"]
        matrix.loc[row["skill_b"], row["skill_a"]] = row["cooccurrence_count"]
    
    fig_heat = plot_heatmap(matrix, "Ma Trận Đồng Xuất Hiện Top 15 Kỹ Năng IT")
    st.plotly_chart(fig_heat, use_container_width=True)

with col_table:
    st.markdown("##### Top Cặp Kỹ Năng Đi Đôi Nhiều Nhất")
    co_view = df_cooccur[["skill_a", "skill_b", "cooccurrence_count"]].head(15).copy()
    co_view.columns = ["Kỹ Năng 1", "Kỹ Năng 2", "Số Tin Cùng Yêu Cầu"]
    st.dataframe(co_view, use_container_width=True, hide_index=True)

st.write("")

# 3. Công cụ Đối sánh kỹ năng giữa 2 Vị trí việc làm
render_section_title(
    title="Công Cụ Đối Sánh Kỹ Năng Giữa 2 Vị Trí (Role Comparison)",
    subtitle="Phân tích sự khác biệt về stack công nghệ giữa hai vị trí (Ví dụ: Data Analyst vs Data Engineer)"
)

df_job_skills_all = load_jobs_with_skills_for_comparison()
all_titles = sorted(df_job_skills_all["title_normalized"].value_counts().head(50).index.tolist())

col_r1, col_r2 = st.columns(2)
with col_r1:
    role_1 = st.selectbox("Chọn Vị trí 1:", options=all_titles, index=all_titles.index("Data Analyst") if "Data Analyst" in all_titles else 0)
with col_r2:
    role_2 = st.selectbox("Chọn Vị trí 2:", options=all_titles, index=all_titles.index("Data Engineer") if "Data Engineer" in all_titles else 1)

if role_1 and role_2:
    sub_r1 = df_job_skills_all[df_job_skills_all["title_normalized"] == role_1]
    sub_r2 = df_job_skills_all[df_job_skills_all["title_normalized"] == role_2]

    skills_r1 = sub_r1.groupby("skill_name")["job_id"].nunique().reset_index()
    skills_r1["pct"] = (skills_r1["job_id"] / max(1, sub_r1["job_id"].nunique()) * 100).round(1)
    skills_r1 = skills_r1.sort_values("pct", ascending=False).head(10)

    skills_r2 = sub_r2.groupby("skill_name")["job_id"].nunique().reset_index()
    skills_r2["pct"] = (skills_r2["job_id"] / max(1, sub_r2["job_id"].nunique()) * 100).round(1)
    skills_r2 = skills_r2.sort_values("pct", ascending=False).head(10)

    c_cmp1, c_cmp2 = st.columns(2)
    with c_cmp1:
        st.markdown(f"**Top Kỹ Năng Của {role_1}** ({sub_r1['job_id'].nunique()} tin)")
        fig_r1 = plot_bar_horizontal(skills_r1, "pct", "skill_name", "")
        st.plotly_chart(fig_r1, use_container_width=True)

    with c_cmp2:
        st.markdown(f"**Top Kỹ Năng Của {role_2}** ({sub_r2['job_id'].nunique()} tin)")
        fig_r2 = plot_bar_horizontal(skills_r2, "pct", "skill_name", "")
        st.plotly_chart(fig_r2, use_container_width=True)
