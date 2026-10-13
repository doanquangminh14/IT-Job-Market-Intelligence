import streamlit as st
import pandas as pd
import plotly.express as px
from database import load_salary_experience_matrix, load_skill_demand
from components.ui import (
    apply_custom_theme,
    render_hero,
    render_kpi_card,
    render_section_title,
    render_sidebar_header
)
from components.charts import plot_bar_horizontal, plot_donut

st.set_page_config(page_title="Lương & Kinh Nghiệm", layout="wide")

apply_custom_theme()
render_sidebar_header()

render_hero(
    tag="PHÂN HỆ THU NHẬP • 2026",
    title="Phân Tích Mức Lương & Số Năm Kinh Nghiệm",
    subtitle="Khảo sát tương quan đa chiều giữa mức thu nhập chuẩn hóa VNĐ, số năm kinh nghiệm yêu cầu, cấp bậc chuyên môn và giá trị thị trường của từng kỹ năng"
)

# Nạp dữ liệu
df_sal = load_salary_experience_matrix()
df_skills = load_skill_demand()

# Bộ lọc Sidebar
st.sidebar.markdown("### Bộ Lọc Phân Tích Lương")
selected_cities = st.sidebar.multiselect("Lọc theo Thành phố:", options=sorted(df_sal["city"].dropna().unique()), default=[])
selected_seniority = st.sidebar.multiselect("Lọc theo Cấp bậc:", options=sorted(df_sal["seniority_level"].dropna().unique()), default=[])

filtered_sal = df_sal.copy()
if selected_cities:
    filtered_sal = filtered_sal[filtered_sal["city"].isin(selected_cities)]
if selected_seniority:
    filtered_sal = filtered_sal[filtered_sal["seniority_level"].isin(selected_seniority)]

# Tính toán các chỉ số KPI
fresher_sal = filtered_sal[filtered_sal["experience_bucket"] == "0 năm (Fresher/Intern)"]["avg_salary_max_vnd"].mean()
fresher_val = f"{fresher_sal/1e6:.1f} triệu" if pd.notna(fresher_sal) and fresher_sal > 0 else "Thỏa thuận"

senior_sal = filtered_sal[filtered_sal["seniority_level"].isin(["Senior", "Lead / Manager"])]["avg_salary_max_vnd"].mean()
senior_val = f"{senior_sal/1e6:.1f} triệu" if pd.notna(senior_sal) and senior_sal > 0 else "Thỏa thuận"

total_postings = filtered_sal["posting_count"].sum()
disclosed_postings = filtered_sal[filtered_sal["salary_type"].isin(["range", "fixed", "max_only"])]["posting_count"].sum()
disclosed_pct = (disclosed_postings / total_postings * 100) if total_postings > 0 else 0

top_sal_skill = df_skills[df_skills["total_job_count"] >= 10].sort_values("avg_skill_max_salary_vnd", ascending=False).iloc[0]
top_skill_name = top_sal_skill["skill_name"]
top_skill_sal = f"{top_sal_skill['avg_skill_max_salary_vnd']/1e6:.1f} triệu"

c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
with c_kpi1:
    render_kpi_card(
        title="Lương trần Fresher / Intern",
        value=fresher_val,
        subtext="Mức trần trung bình đầu vào",
        badge_text="Khởi điểm",
        badge_type="info"
    )
with c_kpi2:
    render_kpi_card(
        title="Lương trần Senior / Lead",
        value=senior_val,
        subtext="Mức trần trung bình cấp cao",
        badge_text="Kinh nghiệm cao",
        badge_type="success"
    )
with c_kpi3:
    render_kpi_card(
        title="Tỷ lệ minh bạch lương",
        value=f"{disclosed_pct:.1f}%",
        subtext=f"{disclosed_postings:,} tin có số liệu lương",
        badge_text="Công khai mức lương",
        badge_type="warning"
    )
with c_kpi4:
    render_kpi_card(
        title="Kỹ năng thu nhập cao nhất",
        value=top_skill_name,
        subtext=f"Mức trần TB: {top_skill_sal}",
        badge_text="Kỹ năng giá trị cao",
        badge_type="neutral"
    )

st.write("")

# 1. Tỷ lệ Công khai lương vs Mức lương theo thâm niên
col_type, col_exp = st.columns([2, 3])

with col_type:
    render_section_title(
        title="Cơ Cấu Định Dạng Lương",
        subtitle="Tỷ lệ công bố lương cụ thể so với thỏa thuận"
    )
    type_agg = filtered_sal.groupby("salary_type")["posting_count"].sum().reset_index()
    type_names = {
        "negotiable": "Thỏa thuận",
        "fixed": "Lương cố định",
        "undisclosed": "Không công bố",
        "range": "Khoảng Min - Max",
        "max_only": "Lên đến (Max)"
    }
    type_agg["Loại lương"] = type_agg["salary_type"].map(type_names).fillna("Khác")
    fig_type = plot_donut(type_agg, "Loại lương", "posting_count", "")
    st.plotly_chart(fig_type, use_container_width=True)

with col_exp:
    render_section_title(
        title="Dải Lương Trung Bình Theo Thâm Niên",
        subtitle="Mức lương Min và Max bình quân (Triệu VNĐ/tháng)"
    )
    exp_order = ["0 năm (Fresher/Intern)", "1 năm", "2 - 3 năm", "3 - 5 năm", "Trên 5 năm"]
    exp_df = filtered_sal[filtered_sal["experience_bucket"].isin(exp_order)].copy()
    exp_agg = exp_df.groupby("experience_bucket").agg(
        avg_min=("avg_salary_min_vnd", "mean"),
        avg_max=("avg_salary_max_vnd", "mean"),
        tin_tuyen=("posting_count", "sum")
    ).reindex(exp_order).reset_index().dropna(subset=["avg_max"])

    exp_agg["avg_min_trieu"] = (exp_agg["avg_min"] / 1e6).round(1)
    exp_agg["avg_max_trieu"] = (exp_agg["avg_max"] / 1e6).round(1)

    fig_exp = px.bar(
        exp_agg,
        x="experience_bucket",
        y=["avg_min_trieu", "avg_max_trieu"],
        barmode="group",
        labels={"value": "Mức lương (Triệu VNĐ/tháng)", "experience_bucket": "Kinh nghiệm", "variable": "Chỉ số"},
        color_discrete_sequence=["#38bdf8", "#2563eb"]
    )
    fig_exp.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569"),
        margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_exp.for_each_trace(lambda t: t.update(name={"avg_min_trieu": "Lương Min TB", "avg_max_trieu": "Lương Max TB"}[t.name]))
    st.plotly_chart(fig_exp, use_container_width=True)

st.write("")

# 2. Benchmark lương theo Cấp bậc chuyên môn
render_section_title(
    title="Benchmark Khung Lương Theo Cấp Bậc Chuyên Môn",
    subtitle="Mức lương trần trung bình quy đổi về Triệu VNĐ/tháng theo từng cấp bậc chuyên gia"
)
sen_agg = filtered_sal[filtered_sal["avg_salary_max_vnd"].notna()].groupby("seniority_level").agg(
    avg_min=("avg_salary_min_vnd", "mean"),
    avg_max=("avg_salary_max_vnd", "mean"),
    tin=("posting_count", "sum")
).reset_index()
sen_agg["avg_min_trieu"] = (sen_agg["avg_min"] / 1e6).round(1)
sen_agg["avg_max_trieu"] = (sen_agg["avg_max"] / 1e6).round(1)
sen_agg = sen_agg.sort_values("avg_max_trieu", ascending=False)

fig_sen = px.bar(
    sen_agg,
    x="seniority_level",
    y="avg_max_trieu",
    color="avg_max_trieu",
    color_continuous_scale="Teal",
    text_auto=True
)
fig_sen.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans, sans-serif", color="#475569"),
    xaxis_title="Cấp bậc",
    yaxis_title="Triệu VNĐ/tháng",
    showlegend=False,
    coloraxis_showscale=False,
    margin=dict(l=20, r=20, t=20, b=20)
)
st.plotly_chart(fig_sen, use_container_width=True)

st.write("")

# 3. Kỹ năng có mức lương hấp dẫn nhất thị trường
render_section_title(
    title="Top Kỹ Năng Công Nghệ Mang Lại Thu Nhập Trần Cao Nhất",
    subtitle="Xếp hạng các kỹ năng có mức lương trần bình quân (avg_skill_max_salary_vnd) cao nhất (mẫu tối thiểu 10 tin)"
)

top_sal_skills = df_skills[df_skills["avg_skill_max_salary_vnd"].notna()].copy()
top_sal_skills = top_sal_skills[top_sal_skills["total_job_count"] >= 10]
top_sal_skills["max_trieu"] = (top_sal_skills["avg_skill_max_salary_vnd"] / 1e6).round(1)
top_sal_skills = top_sal_skills.sort_values("max_trieu", ascending=False).head(15)

fig_skill_sal = plot_bar_horizontal(top_sal_skills, "max_trieu", "skill_name", "")
st.plotly_chart(fig_skill_sal, use_container_width=True)
