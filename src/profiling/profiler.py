import glob
import json
import os
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from src.crawlers.base import PROJECT_ROOT
from src.profiling.language import detect_job_language


class DataProfiler:
    """
    Module Kiểm kê và Đo lường chất lượng dữ liệu thô (Raw Data Profiling).
    Quét toàn bộ thư mục data/raw/ hoặc theo ngày chỉ định và trả lời 6 câu hỏi cốt lõi:
    1. Có bao nhiêu listing?
    2. Bao nhiêu tin đã crawl detail thành công?
    3. Có bao nhiêu URL hoặc tin bị trùng (nội bộ & chéo nguồn)?
    4. Những trường nào thường bị thiếu (Completeness Rate)?
    5. Có bao nhiêu nguồn và phân bố ngôn ngữ (vi, en, mixed)?
    6. Cấu trúc JSON giữa các nguồn có đồng nhất hay khác nhau?
    """

    def __init__(self, raw_dir: Optional[str] = None):
        self.raw_dir = raw_dir if raw_dir else os.path.join(PROJECT_ROOT, "data", "raw")
        self.sources = ["topcv", "topdev", "vietnamworks"]

    def _load_json_files(self, file_pattern: str) -> List[Dict[str, Any]]:
        """Đọc và gom tất cả các bản ghi JSON từ danh sách file phù hợp"""
        records: List[Dict[str, Any]] = []
        for file_path in glob.glob(file_pattern, recursive=True):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records.extend(data)
                    elif isinstance(data, dict):
                        records.append(data)
            except Exception as e:
                pass
        return records

    def get_available_dates(self) -> List[str]:
        """Lấy danh sách tất cả các ngày có dữ liệu cào trong data/raw/"""
        dates_found = set()
        for src in self.sources:
            for sub in ["listings", "details"]:
                sub_dir = os.path.join(self.raw_dir, src, sub)
                if os.path.isdir(sub_dir):
                    for entry in os.listdir(sub_dir):
                        if re.match(r"^\d{4}-\d{2}-\d{2}$", entry):
                            dates_found.add(entry)
        return sorted(list(dates_found))

    def load_data(
        self,
        target_date: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]]]:
        """
        Đọc dữ liệu listing và details từ ổ cứng.
        Trả về: (listings_by_source, details_by_source)
        """
        listings_by_source: Dict[str, List[Dict[str, Any]]] = {}
        details_by_source: Dict[str, List[Dict[str, Any]]] = {}

        selected_sources = [source_filter] if source_filter and source_filter in self.sources else self.sources

        date_subpath = target_date if target_date else "*"

        for src in selected_sources:
            # 1. Đọc listings
            list_pat = os.path.join(self.raw_dir, src, "listings", date_subpath, "*.json")
            listings_by_source[src] = self._load_json_files(list_pat)

            # 2. Đọc details
            det_pat = os.path.join(self.raw_dir, src, "details", date_subpath, "*.json")
            details_by_source[src] = self._load_json_files(det_pat)

        return listings_by_source, details_by_source

    def profile_source(
        self,
        source: str,
        listings: List[Dict[str, Any]],
        details: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Tính toán toàn bộ các chỉ số kiểm kê và chất lượng cho 1 nguồn cụ thể"""
        total_listings = len(listings)
        total_details = len(details)

        # 1. Trạng thái crawl detail từ file listing
        status_counts = Counter()
        for item in listings:
            st = item.get("detail_status", "pending")
            status_counts[st] += 1

        success_count = status_counts.get("success", 0)
        failed_count = status_counts.get("failed", 0)
        pending_count = status_counts.get("pending", 0)

        # 2. Trùng lặp nội bộ nguồn (Duplicate URLs & Job IDs)
        urls = [item.get("job_url", "").strip() for item in listings if item.get("job_url")]
        url_counts = Counter(urls)
        dup_urls_count = sum(c - 1 for c in url_counts.values() if c > 1)

        job_ids = [str(item.get("source_job_id", "")).strip() for item in listings if item.get("source_job_id")]
        id_counts = Counter(job_ids)
        dup_ids_count = sum(c - 1 for c in id_counts.values() if c > 1)

        # 3. Phân tích trường thiếu (Missing Values) trên tập Detail
        # Nếu chưa có details, fallback sang kiểm tra trên listings
        eval_set = details if details else listings
        eval_len = len(eval_set)

        missing_counts = defaultdict(int)
        salary_breakdown = {
            "has_numeric_range": 0,
            "negotiable": 0,
            "missing": 0
        }
        deadline_stats = {
            "valid_date": 0,
            "missing": 0
        }
        language_stats = Counter()

        check_fields = [
            "title_raw", "company_name_raw", "location_raw", "salary_raw",
            "experience_raw", "skills_raw", "responsibilities_raw",
            "requirements_raw", "benefits_raw", "deadline_raw"
        ]

        sample_keys = set()

        for item in eval_set:
            sample_keys.update(item.keys())

            # Missing fields
            for field in check_fields:
                val = item.get(field)
                if field == "skills_raw" and not val:
                    val = item.get("required_skills_raw")
                if not val or not str(val).strip():
                    missing_counts[field] += 1

            # Salary breakdown
            sal = str(item.get("salary_raw", "")).strip().lower()
            if not sal:
                salary_breakdown["missing"] += 1
            elif any(w in sal for w in ["thỏa thuận", "thoả thuận", "thương lượng", "negotiable", "cạnh tranh"]):
                salary_breakdown["negotiable"] += 1
            else:
                salary_breakdown["has_numeric_range"] += 1

            # Deadline breakdown
            dl = str(item.get("deadline_raw", "")).strip()
            if re.match(r"^\d{4}-\d{2}-\d{2}", dl):
                deadline_stats["valid_date"] += 1
            else:
                deadline_stats["missing"] += 1

            # Ngôn ngữ
            full_text = " ".join([
                str(item.get("title_raw", "")),
                str(item.get("responsibilities_raw", "")),
                str(item.get("requirements_raw", ""))
            ])
            lang = detect_job_language(full_text)
            language_stats[lang] += 1

        missing_percentages = {}
        for field in check_fields:
            cnt = missing_counts[field]
            pct = round((cnt / eval_len * 100), 1) if eval_len > 0 else 0.0
            missing_percentages[field] = {
                "count": cnt,
                "percentage": pct
            }

        return {
            "source": source,
            "total_listings": total_listings,
            "total_details": total_details,
            "success_details": success_count,
            "failed_details": failed_count,
            "pending_details": pending_count,
            "duplicate_urls": dup_urls_count,
            "duplicate_job_ids": dup_ids_count,
            "eval_count": eval_len,
            "missing_fields": missing_percentages,
            "salary_breakdown": salary_breakdown,
            "deadline_stats": deadline_stats,
            "language_distribution": dict(language_stats),
            "schema_keys": sorted(list(sample_keys))
        }

    def run_profiling(
        self,
        target_date: Optional[str] = None,
        source_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Thực thi kiểm kê và profiling trên phạm vi chỉ định.
        Trả về kết quả tổng hợp của từng nguồn và toàn bộ kho dữ liệu.
        """
        listings_by_src, details_by_src = self.load_data(target_date, source_filter)

        sources_profile = {}
        overall_total_listings = 0
        overall_total_details = 0
        overall_success_details = 0
        overall_failed_details = 0
        overall_pending_details = 0
        overall_duplicate_urls = 0
        overall_duplicate_ids = 0

        all_details: List[Dict[str, Any]] = []

        for src, listings in listings_by_src.items():
            details = details_by_src.get(src, [])
            all_details.extend(details)

            prof = self.profile_source(src, listings, details)
            sources_profile[src] = prof

            overall_total_listings += prof["total_listings"]
            overall_total_details += prof["total_details"]
            overall_success_details += prof["success_details"]
            overall_failed_details += prof["failed_details"]
            overall_pending_details += prof["pending_details"]
            overall_duplicate_urls += prof["duplicate_urls"]
            overall_duplicate_ids += prof["duplicate_job_ids"]

        # Trùng lặp chéo nguồn (Cross-portal duplicates)
        cross_portal_duplicates = self._check_cross_portal_duplicates(all_details)

        # So sánh Schema giữa các nguồn
        schema_comparison = self._compare_schemas(sources_profile)

        return {
            "target_date": target_date if target_date else "ALL_TIME",
            "available_dates": self.get_available_dates(),
            "sources_count": len(sources_profile),
            "overall": {
                "total_listings": overall_total_listings,
                "total_details": overall_total_details,
                "success_details": overall_success_details,
                "failed_details": overall_failed_details,
                "pending_details": overall_pending_details,
                "duplicate_urls": overall_duplicate_urls,
                "duplicate_job_ids": overall_duplicate_ids,
                "cross_portal_duplicates": cross_portal_duplicates["count"],
            },
            "sources": sources_profile,
            "cross_portal_duplicates": cross_portal_duplicates,
            "schema_comparison": schema_comparison
        }

    def _check_cross_portal_duplicates(self, all_details: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phát hiện các tin trùng lặp giữa các nguồn khác nhau dựa trên cặp:
        (Tên công ty chuẩn hóa, Tiêu đề công việc chuẩn hóa)
        """
        seen_pairs: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)

        for item in all_details:
            title = re.sub(r"[^\w\s]", "", str(item.get("title_raw", "")).lower()).strip()
            title = re.sub(r"\s+", " ", title)
            comp = re.sub(r"[^\w\s]", "", str(item.get("company_name_raw", "")).lower()).strip()
            comp = re.sub(r"\s+", " ", comp)
            src = str(item.get("source", ""))
            url = str(item.get("job_url", ""))

            if title and comp:
                seen_pairs[(comp, title)].append({"source": src, "url": url})

        duplicate_groups = []
        for (comp, title), occurrences in seen_pairs.items():
            sources_involved = {occ["source"] for occ in occurrences}
            if len(sources_involved) > 1:
                duplicate_groups.append({
                    "company": comp,
                    "title": title,
                    "sources": list(sources_involved),
                    "urls": occurrences
                })

        return {
            "count": len(duplicate_groups),
            "groups": duplicate_groups[:10]  # Lưu tối đa 10 mẫu tiêu biểu
        }

    def _compare_schemas(self, sources_profile: Dict[str, Any]) -> Dict[str, Any]:
        """So sánh các key trong cấu trúc JSON giữa các nguồn để kiểm tra tính nhất quán"""
        all_keys: Set[str] = set()
        keys_by_source: Dict[str, Set[str]] = {}

        for src, prof in sources_profile.items():
            k_set = set(prof.get("schema_keys", []))
            keys_by_source[src] = k_set
            all_keys.update(k_set)

        common_keys = set.intersection(*keys_by_source.values()) if keys_by_source else set()
        diff_keys: Dict[str, List[str]] = {}
        for src, k_set in keys_by_source.items():
            diff_keys[src] = sorted(list(k_set - common_keys))

        return {
            "common_keys": sorted(list(common_keys)),
            "all_unique_keys_count": len(all_keys),
            "is_schema_uniform": len(all_keys) == len(common_keys) and len(all_keys) > 0,
            "discrepancies": diff_keys
        }
