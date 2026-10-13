import streamlit as st

def apply_custom_theme():
    """Nhúng hệ thống CSS thiết kế hiện đại chuẩn SaaS web application."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* Font toàn ứng dụng */
    html, body, [class*="css"], .stMarkdown, .stText, p, span, h1, h2, h3, h4, h5, h6, label, button, input {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Tối ưu hóa layout nền */
    .stApp {
        background-color: #f8fafc;
    }

    /* Ẩn bớt thanh Streamlit mặc định */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* Hero Banner Header */
    .web-hero {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0f172a 100%);
        border-radius: 16px;
        padding: 32px 36px;
        margin-bottom: 24px;
        color: #ffffff;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.12);
        border: 1px solid #334155;
        position: relative;
        overflow: hidden;
    }
    .hero-tag {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #38bdf8;
        background: rgba(56, 189, 248, 0.12);
        padding: 4px 12px;
        border-radius: 9999px;
        margin-bottom: 12px;
        border: 1px solid rgba(56, 189, 248, 0.25);
    }
    .hero-title {
        font-size: 2.15rem;
        font-weight: 800;
        color: #ffffff;
        margin: 0 0 10px 0;
        line-height: 1.25;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        margin: 0;
        line-height: 1.6;
        max-width: 900px;
    }

    /* KPI Cards phong cách Web */
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.03);
        transition: all 0.2s ease-in-out;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px -2px rgba(15, 23, 42, 0.07);
        border-color: #cbd5e1;
    }
    .kpi-label {
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.2;
        margin-bottom: 8px;
        white-space: normal;
        word-break: break-word;
    }
    .kpi-footer {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .kpi-badge {
        display: inline-flex;
        align-items: center;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 9999px;
        width: fit-content;
    }
    .kpi-badge-success {
        background: #ecfdf5;
        color: #047857;
        border: 1px solid #a7f3d0;
    }
    .kpi-badge-info {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }
    .kpi-badge-warning {
        background: #fffbeb;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    .kpi-badge-neutral {
        background: #f1f5f9;
        color: #475569;
        border: 1px solid #e2e8f0;
    }
    .kpi-subtext {
        font-size: 0.78rem;
        color: #64748b;
        line-height: 1.4;
    }

    /* Tiêu đề section */
    .section-header-box {
        margin-top: 14px;
        margin-bottom: 14px;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-accent-bar {
        width: 4px;
        height: 18px;
        background: #2563eb;
        border-radius: 2px;
        display: inline-block;
    }
    .section-subtitle {
        font-size: 0.85rem;
        color: #64748b;
        margin: 4px 0 0 12px;
    }

    /* Khung card bo góc cho đồ thị */
    .chart-container-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 1px 3px 0 rgba(15, 23, 42, 0.04);
        margin-bottom: 16px;
    }

    /* Sidebar thương hiệu */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    .sidebar-brand-box {
        padding: 16px;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border-radius: 12px;
        color: #ffffff;
        margin-bottom: 20px;
        border: 1px solid #334155;
    }
    .sidebar-tag {
        font-size: 0.65rem;
        font-weight: 700;
        color: #38bdf8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .sidebar-title {
        font-size: 1.05rem;
        font-weight: 800;
        margin: 4px 0 2px 0;
        color: #ffffff;
    }
    .sidebar-meta {
        font-size: 0.74rem;
        color: #94a3b8;
    }

    /* Navigation info cards */
    .nav-guide-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        height: 100%;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
    }
    .nav-guide-card:hover {
        border-color: #93c5fd;
        box-shadow: 0 6px 12px -2px rgba(37, 99, 235, 0.08);
        transform: translateY(-2px);
    }
    .nav-guide-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 8px;
    }
    .nav-guide-desc {
        font-size: 0.82rem;
        color: #64748b;
        line-height: 1.5;
        margin: 0;
    }

    /* Tinh chỉnh DataFrame bảng dữ liệu */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_hero(tag: str, title: str, subtitle: str):
    """Hiển thị Banner Hero chuyên nghiệp đầu mỗi trang."""
    html = f"""
    <div class="web-hero">
        <div class="hero-tag">{tag}</div>
        <h1 class="hero-title">{title}</h1>
        <p class="hero-subtitle">{subtitle}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_kpi_card(title: str, value: str, subtext: str = "", badge_text: str = "", badge_type: str = "neutral"):
    """Hiển thị Thẻ KPI Metric với định dạng card web hiện đại."""
    badge_html = ""
    if badge_text:
        badge_html = f'<span class="kpi-badge kpi-badge-{badge_type}">{badge_text}</span>'

    subtext_html = ""
    if subtext:
        subtext_html = f'<div class="kpi-subtext">{subtext}</div>'

    html = f"""
    <div class="kpi-card">
        <div>
            <div class="kpi-label">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
        <div class="kpi-footer">
            {badge_html}
            {subtext_html}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_section_title(title: str, subtitle: str = ""):
    """Hiển thị tiêu đề phân đoạn với thanh nhấn màu xanh hiện đại."""
    subtitle_html = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    html = f"""
    <div class="section-header-box">
        <h3 class="section-title"><span class="section-accent-bar"></span>{title}</h3>
        {subtitle_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def render_sidebar_header():
    """Hiển thị logo và thương hiệu chuyên nghiệp trên thanh bên Sidebar."""
    html = """
    <div class="sidebar-brand-box">
        <div class="sidebar-tag">INTELLIGENCE PLATFORM</div>
        <div class="sidebar-title">Vietnam IT Jobs</div>
        <div class="sidebar-meta">Kho dữ liệu: 2.509 tin tuyển dụng</div>
    </div>
    """
    st.sidebar.markdown(html, unsafe_allow_html=True)

def render_nav_card(title: str, desc: str):
    """Hiển thị thẻ điều hướng các phân hệ chuyên sâu."""
    html = f"""
    <div class="nav-guide-card">
        <div class="nav-guide-title">{title}</div>
        <p class="nav-guide-desc">{desc}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
