"""Các lệnh dòng lệnh của dự án. Chạy: `python -m src.cli <lệnh> [tham số]` hoặc `itjobs <lệnh> [tham số]`.

    crawl     cào tin tuyển dụng vào data/raw/
    quality   kiểm định data/raw, gộp vào Master Bronze (data/bronze/)
    profile   kiểm kê dữ liệu thô, xuất báo cáo reports/profiling/
    pipeline  cào ➔ kiểm định Bronze ➔ nạp Silver PostgreSQL
"""
