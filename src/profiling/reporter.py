import csv
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.crawlers.base import PROJECT_ROOT


class ReportGenerator:
    """
    Sinh báo cáo Kiểm kê & Đo lường chất lượng dữ liệu:
    - In bảng tổng quan màu sắc/rõ ràng ra Console
    - Xuất file Markdown chi tiết: latest_summary.md hoặc daily/{date}.md
    - Cập nhật dòng chỉ số vào file lịch sử: history_metrics.csv
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir if output_dir else os.path.join(PROJECT_ROOT, "reports", "profiling")
        self.daily_dir = os.path.join(self.output_dir, "daily")
        self.history_csv_path = os.path.join(self.output_dir, "history_metrics.csv")

        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.daily_dir, exist_ok=True)

    def print_console_summary(self, profile_result: Dict[str, Any]) -> None:
        """In bản tóm tắt nhanh gọn ra màn hình Terminal"""
        overall = profile_result["overall"]
        target_date = profile_result["target_date"]

        print("\n" + "=" * 80)
        print(f"📊 BÁO CÁO KIỂM KÊ & PROFILING DỮ LIỆU THÔ (PHẠM VI: {target_date.upper()})")
        print("=" * 80)
        print(f"- Số nguồn cào khảo sát     : {profile_result['sources_count']} nguồn")
        print(f"- Tổng số listing ghi nhận   : {overall['total_listings']:,} tin")
        print(f"- Crawl detail thành công   : {overall['success_details']:,} tin")
        print(f"- Crawl detail thất bại     : {overall['failed_details']:,} tin")
        print(f"- Tin chờ crawl (pending)   : {overall['pending_details']:,} tin")
        print(f"- Số URL bị trùng nội bộ    : {overall['duplicate_urls']:,} URLs")
        print(f"- Tin trùng chéo giữa các sàn: {overall['cross_portal_duplicates']:,} cặp (Cùng công ty & tiêu đề)")

        print("-" * 80)
        print(f"{'Nguồn':<15} | {'Listings':<10} | {'Detail OK':<10} | {'URL Trùng':<10} | {'Có Lương %':<12} | {'Có Hạn Nộp %':<12}")
        print("-" * 80)

        for src, p in profile_result["sources"].items():
            eval_c = p["eval_count"]
            has_sal_pct = round(p["salary_breakdown"]["has_numeric_range"] / eval_c * 100, 1) if eval_c > 0 else 0
            has_dl_pct = round(p["deadline_stats"]["valid_date"] / eval_c * 100, 1) if eval_c > 0 else 0

            print(
                f"{src:<15} | "
                f"{p['total_listings']:<10} | "
                f"{p['success_details']:<10} | "
                f"{p['duplicate_urls']:<10} | "
                f"{has_sal_pct}%{'':<6} | "
                f"{has_dl_pct}%"
            )

        print("=" * 80 + "\n")

    def generate_markdown_report(self, profile_result: Dict[str, Any]) -> str:
        """Tạo nội dung báo cáo chuẩn GitHub Flavored Markdown"""
        overall = profile_result["overall"]
        target_date = profile_result["target_date"]
        schema_comp = profile_result["schema_comparison"]
        cross_dups = profile_result["cross_portal_duplicates"]

        md_lines = [
            f"# 📋 Báo Cáo Kiểm Kê & Profiling Dữ Liệu Tuyển Dụng IT",
            f"",
            f"> **Phạm vi khảo sát**: `{target_date}`  ",
            f"> **Thời điểm tạo báo cáo**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ",
            f"> **Số nguồn dữ liệu**: `{profile_result['sources_count']}` (TopCV, TopDev, VietnamWorks)",
            f"",
            f"---",
            f"",
            f"## 1. Bảng Tổng Quan Chỉ Số Cốt Lõi",
            f"",
            f"| Chỉ số kiểm kê | Giá trị | Ý nghĩa thực tế |",
            f"| :--- | :--- | :--- |",
            f"| **Tổng số listing thu thập** | **{overall['total_listings']:,}** | Số lượng tin đã quét qua từ trang tìm kiếm |",
            f"| **Crawl detail thành công** | **{overall['success_details']:,}** | Số lượng tin đã có đầy đủ nội dung chi tiết |",
            f"| **Crawl detail thất bại** | **{overall['failed_details']:,}** | Tin gặp lỗi HTTP hoặc WAF (Cần cào bù) |",
            f"| **Tin trong hàng đợi (Pending)** | **{overall['pending_details']:,}** | Tin đã lưu listing nhưng chờ phiên cào tiếp |",
            f"| **URL bị trùng nội bộ sàn** | **{overall['duplicate_urls']:,}** | Các tin cùng 1 sàn bị trùng lặp link |",
            f"| **Tin trùng chéo giữa các sàn** | **{overall['cross_portal_duplicates']:,}** | Cùng 1 công ty đăng tuyển chéo trên nhiều sàn |",
            f"",
            f"---",
            f"",
            f"## 2. Thống Kê Chi Tiết Từng Sàn Tuyển Dụng",
            f"",
            f"| Nguồn | Listings | Details OK | URL Trùng | Lương cụ thể | Thương lượng | Có Hạn nộp | Ngôn ngữ chủ đạo |",
            f"| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]

        for src, p in profile_result["sources"].items():
            eval_c = p["eval_count"]
            num_sal = p["salary_breakdown"]["has_numeric_range"]
            neg_sal = p["salary_breakdown"]["negotiable"]
            num_sal_pct = round(num_sal / eval_c * 100, 1) if eval_c > 0 else 0
            neg_sal_pct = round(neg_sal / eval_c * 100, 1) if eval_c > 0 else 0
            dl_pct = round(p["deadline_stats"]["valid_date"] / eval_c * 100, 1) if eval_c > 0 else 0

            # Ngôn ngữ chiếm ưu thế
            lang_dist = p["language_distribution"]
            dom_lang = max(lang_dist.items(), key=lambda x: x[1])[0] if lang_dist else "unknown"

            md_lines.append(
                f"| **{src}** | {p['total_listings']:,} | {p['success_details']:,} | {p['duplicate_urls']:,} | "
                f"{num_sal:,} ({num_sal_pct}%) | {neg_sal:,} ({neg_sal_pct}%) | {dl_pct}% | `{dom_lang}` |"
            )

        md_lines.extend([
            f"",
            f"---",
            f"",
            f"## 3. Tỷ Lệ Hoàn Thiện Các Trường Dữ Liệu (Completeness Rate)",
            f"",
            f"Bảng đánh giá tỷ lệ **bị thiếu (missing)** của các trường dữ liệu quan trọng:",
            f"",
            f"| Tên trường dữ liệu | TopCV (% thiếu) | TopDev (% thiếu) | VietnamWorks (% thiếu) |",
            f"| :--- | :--- | :--- | :--- |",
        ])

        fields_to_show = [
            ("Tiêu đề (`title_raw`)", "title_raw"),
            ("Công ty (`company_name_raw`)", "company_name_raw"),
            ("Địa điểm (`location_raw`)", "location_raw"),
            ("Mức lương (`salary_raw`)", "salary_raw"),
            ("Kinh nghiệm (`experience_raw`)", "experience_raw"),
            ("Kỹ năng (`skills_raw`)", "skills_raw"),
            ("Mô tả công việc (`responsibilities_raw`)", "responsibilities_raw"),
            ("Yêu cầu công việc (`requirements_raw`)", "requirements_raw"),
            ("Quyền lợi (`benefits_raw`)", "benefits_raw"),
            ("Hạn nộp hồ sơ (`deadline_raw`)", "deadline_raw"),
        ]

        for label, f_key in fields_to_show:
            tc_miss = profile_result["sources"].get("topcv", {}).get("missing_fields", {}).get(f_key, {}).get("percentage", 0.0)
            td_miss = profile_result["sources"].get("topdev", {}).get("missing_fields", {}).get(f_key, {}).get("percentage", 0.0)
            vn_miss = profile_result["sources"].get("vietnamworks", {}).get("missing_fields", {}).get(f_key, {}).get("percentage", 0.0)

            md_lines.append(f"| {label} | `{tc_miss}%` | `{td_miss}%` | `{vn_miss}%` |")

        md_lines.extend([
            f"",
            f"> [!TIP]",
            f"> **Lưu ý nghiệp vụ về mức lương**: Mức lương ghi 'Thương lượng/Thoả thuận' không phải là dữ liệu thiếu (missing), mà là thông tin hợp lệ phản ánh chính sách của nhà tuyển dụng.",
            f"",
            f"---",
            f"",
            f"## 4. Phân Bố Ngôn Ngữ Tuyển Dụng",
            f"",
            f"| Nguồn | Tiếng Việt (`vi`) | Tiếng Anh (`en`) | Song ngữ (`mixed`) | Khác / Ngắn |",
            f"| :--- | :--- | :--- | :--- | :--- |",
        ])

        for src, p in profile_result["sources"].items():
            ld = p["language_distribution"]
            ec = p["eval_count"]
            vi_c = ld.get("vi", 0)
            en_c = ld.get("en", 0)
            mix_c = ld.get("mixed", 0)
            unk_c = ld.get("unknown", 0)

            vi_pct = round(vi_c / ec * 100, 1) if ec > 0 else 0
            en_pct = round(en_c / ec * 100, 1) if ec > 0 else 0
            mix_pct = round(mix_c / ec * 100, 1) if ec > 0 else 0
            unk_pct = round(unk_c / ec * 100, 1) if ec > 0 else 0

            md_lines.append(
                f"| **{src}** | {vi_c} ({vi_pct}%) | {en_c} ({en_pct}%) | {mix_c} ({mix_pct}%) | {unk_c} ({unk_pct}%) |"
            )

        md_lines.extend([
            f"",
            f"---",
            f"",
            f"## 5. So Sánh Tính Đồng Nhất Của Cấu Trúc JSON (Schema Consistency)",
            f"",
            f"- **Trạng thái đồng nhất**: {'✅ **Đồng nhất 100% giữa các nguồn**' if schema_comp['is_schema_uniform'] else '⚠️ **Có trường chênh lệch giữa các sàn**'}",
            f"- **Số lượng trường chung (`common_keys`)**: `{len(schema_comp['common_keys'])}` trường",
            f"- **Danh sách trường dùng chung**: `{', '.join(schema_comp['common_keys'])}`",
            f"",
        ])

        if cross_dups["count"] > 0:
            md_lines.extend([
                f"---",
                f"",
                f"## 6. Mẫu Tin Đăng Tuyển Trùng Chéo Sàn (Cross-Portal Duplicates)",
                f"",
                f"Hệ thống phát hiện **{cross_dups['count']}** vị trí xuất hiện đồng thời trên từ 2 sàn trở lên:",
                f"",
            ])
            for i, group in enumerate(cross_dups["groups"][:5], 1):
                md_lines.append(f"{i}. **{group['title'].title()}** tại **{group['company'].title()}** (Xuất hiện trên: `{', '.join(group['sources'])}`)")

        return "\n".join(md_lines)

    def save_reports(self, profile_result: Dict[str, Any]) -> Tuple[str, str]:
        """Lưu báo cáo ra file Markdown và cập nhật file lịch sử metrics CSV"""
        target_date = profile_result["target_date"]
        md_content = self.generate_markdown_report(profile_result)

        # 1. Lưu file Markdown
        if target_date == "ALL_TIME":
            md_filepath = os.path.join(self.output_dir, "latest_summary.md")
        else:
            md_filepath = os.path.join(self.daily_dir, f"{target_date}.md")
            # Đồng thời cập nhật luôn latest_summary.md
            latest_path = os.path.join(self.output_dir, "latest_summary.md")
            with open(latest_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        with open(md_filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

        # 2. Ghi nối (Append) vào history_metrics.csv
        self._append_history_metrics(profile_result)

        return md_filepath, self.history_csv_path

    def _append_history_metrics(self, profile_result: Dict[str, Any]) -> None:
        """Ghi chỉ số thống kê của từng nguồn vào CSV để phục vụ vẽ đồ thị xu hướng"""
        file_exists = os.path.exists(self.history_csv_path)
        eval_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        target_date = profile_result["target_date"]

        fieldnames = [
            "evaluated_at", "target_date", "source", "total_listings",
            "total_details", "success_details", "failed_details",
            "duplicate_urls", "has_numeric_salary_pct", "negotiable_salary_pct",
            "valid_deadline_pct", "lang_vi_pct", "lang_en_pct", "lang_mixed_pct"
        ]

        rows = []
        for src, p in profile_result["sources"].items():
            ec = p["eval_count"]
            num_sal = p["salary_breakdown"]["has_numeric_range"]
            neg_sal = p["salary_breakdown"]["negotiable"]
            dl_cnt = p["deadline_stats"]["valid_date"]
            ld = p["language_distribution"]

            rows.append({
                "evaluated_at": eval_time,
                "target_date": target_date,
                "source": src,
                "total_listings": p["total_listings"],
                "total_details": p["total_details"],
                "success_details": p["success_details"],
                "failed_details": p["failed_details"],
                "duplicate_urls": p["duplicate_urls"],
                "has_numeric_salary_pct": round(num_sal / ec * 100, 1) if ec > 0 else 0,
                "negotiable_salary_pct": round(neg_sal / ec * 100, 1) if ec > 0 else 0,
                "valid_deadline_pct": round(dl_cnt / ec * 100, 1) if ec > 0 else 0,
                "lang_vi_pct": round(ld.get("vi", 0) / ec * 100, 1) if ec > 0 else 0,
                "lang_en_pct": round(ld.get("en", 0) / ec * 100, 1) if ec > 0 else 0,
                "lang_mixed_pct": round(ld.get("mixed", 0) / ec * 100, 1) if ec > 0 else 0,
            })

        with open(self.history_csv_path, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows)
