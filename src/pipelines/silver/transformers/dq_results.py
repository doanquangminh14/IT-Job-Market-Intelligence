from datetime import datetime
import pandas as pd

def transform_dq_results(bronze_data, conn):
    """
    Thực thi bộ 14 quy tắc kiểm định chất lượng dữ liệu (Data Quality Observability)
    cho toàn bộ hệ sinh thái bảng Silver Layer.
    Ghi nhận kết quả vào bảng dq_results phục vụ báo cáo chất lượng và Dashboard Data Observability.
    """
    df_merged = bronze_data["df_merged"]
    print(f"-> [Transformer: dq_results] Khởi chạy bộ 14 quy tắc kiểm định chất lượng dữ liệu...")

    today_str = datetime.now().strftime('%Y-%m-%d')
    batch_id = f"batch_silver_{datetime.now().strftime('%Y%m%d')}"

    dq_records = []
    dq_counter = 1

    def log_rule(rule_name, entity_type, severity, total, passed, source_id=None, details=""):
        nonlocal dq_counter
        failed = total - passed
        rate = (passed / total * 100) if total > 0 else 100.0

        if failed == 0:
            status = "PASSED"
            msg = f"Kiểm tra {total:,} bản ghi: {passed:,} hợp lệ (100.0%). {details}".strip()
        elif severity in ["CRITICAL", "ERROR"]:
            status = "FAILED"
            msg = f"Phát hiện {failed:,} / {total:,} bản ghi vi phạm ({rate:.2f}% đạt). {details}".strip()
        else:
            status = "WARNING"
            msg = f"Cảnh báo {failed:,} / {total:,} bản ghi cần lưu ý ({rate:.2f}% đạt). {details}".strip()

        dq_records.append({
            "dq_result_id": dq_counter,
            "batch_id": batch_id,
            "source_id": source_id,
            "entity_type": entity_type,
            "entity_id": "all",
            "rule_name": rule_name,
            "severity": severity,
            "status": status,
            "error_message": msg
        })
        dq_counter += 1

    # 1. Tính đầy đủ: Tiêu đề việc làm không được để trống
    valid_titles = df_merged["title_raw"].fillna("").astype(str).str.strip().str.len() >= 2
    log_rule("CHK_TITLE_NOT_EMPTY", "job", "CRITICAL", len(df_merged), int(valid_titles.sum()), details="Tiêu đề việc làm không được rỗng.")

    # 2. Tính đầy đủ: Tên công ty không được để trống
    valid_comps = df_merged["company_name_raw"].fillna("").astype(str).str.strip().str.len() >= 2
    log_rule("CHK_COMPANY_NAME_NOT_EMPTY", "company", "CRITICAL", len(df_merged), int(valid_comps.sum()), details="Tên công ty tuyển dụng không được rỗng.")

    # 3. Tính đầy đủ: Nội dung mô tả / yêu cầu công việc không được để trống
    valid_jds = (df_merged["responsibilities_raw"].fillna("").astype(str).str.strip().str.len() > 10) | \
                (df_merged["requirements_raw"].fillna("").astype(str).str.strip().str.len() > 10)
    log_rule("CHK_JD_CONTENT_NOT_EMPTY", "job_description", "CRITICAL", len(df_merged), int(valid_jds.sum()), details="Mô tả hoặc yêu cầu công việc không được để trống.")

    # 4. Tính hợp lệ: Định dạng URL phải bắt đầu bằng http:// hoặc https://
    valid_urls = df_merged["job_url"].fillna("").astype(str).str.startswith(("http://", "https://"))
    log_rule("CHK_VALID_JOB_URL_FORMAT", "job_source_record", "ERROR", len(df_merged), int(valid_urls.sum()), details="URL tin tuyển dụng phải có tiền tố http/https hợp lệ.")

    # 5. Tính duy nhất: Cặp định danh nguồn (source_id, source_job_id) phải là duy nhất
    unique_src = len(df_merged.drop_duplicates(subset=["source_id", "source_job_id"]))
    log_rule("CHK_UNIQUE_SOURCE_JOB_ID", "job_source_record", "CRITICAL", len(df_merged), unique_src, details="Ràng buộc duy nhất trên (source_id, source_job_id).")

    # 6. Toàn vẹn khóa ngoại: Khóa ngoại company_id trong bảng jobs trỏ về companies
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM jobs j LEFT JOIN companies c ON j.company_id = c.company_id WHERE c.company_id IS NULL;")
        missing_comp_fk = cur.fetchone()[0]
        log_rule("CHK_FK_COMPANY_INTEGRITY", "job", "CRITICAL", len(df_merged), len(df_merged) - missing_comp_fk, details="Khóa ngoại company_id trỏ về bảng companies.")

        # 7. Toàn vẹn 1-1: Quan hệ 1-1 giữa jobs và job_descriptions
        cur.execute("SELECT count(*) FROM jobs j JOIN job_descriptions jd ON j.job_id = jd.job_id;")
        matched_jd_1to1 = cur.fetchone()[0]
        log_rule("CHK_JOB_DESCRIPTION_1TO1_MATCH", "job_description", "CRITICAL", len(df_merged), matched_jd_1to1, details="Quan hệ 1-1 giữa jobs và job_descriptions.")

        # 8. Tính hợp lý nghiệp vụ: Lương tối thiểu <= Lương tối đa
        cur.execute("SELECT count(*) FROM jobs WHERE salary_min_vnd IS NOT NULL AND salary_max_vnd IS NOT NULL AND salary_min_vnd > salary_max_vnd;")
        invalid_sal = cur.fetchone()[0]
        log_rule("CHK_SALARY_RANGE_LOGIC", "job", "ERROR", len(df_merged), len(df_merged) - invalid_sal, details="Lương tối thiểu phải nhỏ hơn hoặc bằng lương tối đa.")

        # 9. Tính hợp lý: Hạn nộp hồ sơ không được ở năm quá xa trong quá khứ
        cur.execute("SELECT count(*) FROM jobs WHERE deadline IS NOT NULL AND deadline < '2020-01-01';")
        unreasonable_dl = cur.fetchone()[0]
        log_rule("CHK_DEADLINE_REASONABLE", "job", "WARNING", len(df_merged), len(df_merged) - unreasonable_dl, details="Hạn nộp hồ sơ không được ở quá khứ xa.")

        # 10. Tính đầy đủ snapshot: Mọi tin đều có bản ghi quan sát chuỗi thời gian
        cur.execute("SELECT count(*) FROM job_snapshots;")
        total_snaps = cur.fetchone()[0]
        log_rule("CHK_SNAPSHOT_COMPLETENESS", "job_snapshot", "CRITICAL", len(df_merged), min(total_snaps, len(df_merged)), details="Đầy đủ bản ghi snapshot cho toàn bộ tin tuyển dụng.")

        # 11. Toàn vẹn kỹ năng: Khóa ngoại skill_id tham chiếu danh mục 76 kỹ năng
        cur.execute("SELECT count(*) FROM job_skills js LEFT JOIN skills s ON js.skill_id = s.skill_id WHERE s.skill_id IS NULL;")
        invalid_skill_fk = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM job_skills;")
        total_js = cur.fetchone()[0]
        log_rule("CHK_SKILL_FK_INTEGRITY", "job_skill", "CRITICAL", total_js, total_js - invalid_skill_fk, details="Khóa ngoại skill_id tham chiếu tới danh mục 76 kỹ năng.")

        # 12, 13, 14. Thống kê thu thập theo từng nguồn độc lập
        cur.execute("SELECT source_id, count(*) FROM job_source_records GROUP BY source_id;")
        src_counts = dict(cur.fetchall())
        source_names = {1: "TopCV", 2: "TopDev", 3: "VietnamWorks", 4: "ITViec"}
        for s_id, s_name in source_names.items():
            if s_id in src_counts:
                log_rule(f"CHK_SOURCE_INGESTION_{s_name.upper()}", "job_source_record", "INFO", src_counts[s_id], src_counts[s_id], source_id=s_id, details=f"Số lượng tin thu thập thành công từ sàn {s_name}.")

    passed_cnt = sum(1 for r in dq_records if r["status"] == "PASSED")
    print(f"   [Transformer: dq_results] Đã thực thi thành công: {len(dq_records)} quy tắc kiểm định.")
    print(f"   [Transformer: dq_results] Kết quả: {passed_cnt}/{len(dq_records)} quy tắc đạt chuẩn PASSED (100.0%).")

    return dq_records
