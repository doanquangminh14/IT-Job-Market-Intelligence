import os
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests
from bs4 import BeautifulSoup

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.pipelines.silver.db import get_db_connection

def fetch_topcv_salary(row):
    jid, url = row
    try:
        session = requests.Session(impersonate="chrome124")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.topcv.vn/"
        }
        res = session.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    d = json.loads((s.string if s.string else s.text) or "")
                    if d.get("@type") == "JobPosting":
                        bs = d.get("baseSalary") or {}
                        val = bs.get("value") or {}
                        if isinstance(val, dict):
                            min_v = val.get("minValue")
                            max_v = val.get("maxValue")
                            v_exact = val.get("value")
                            if min_v is not None and max_v is not None and str(min_v).strip() != "" and str(max_v).strip() != "":
                                f_min, f_max = float(min_v), float(max_v)
                                if f_min == f_max:
                                    return jid, str(min_v), f_min, f_max, "fixed"
                                return jid, f"{min_v} - {max_v}", f_min, f_max, "range"
                            elif min_v is not None and str(min_v).strip() != "":
                                return jid, f"Từ {min_v}", float(min_v), None, "min_only"
                            elif max_v is not None and str(max_v).strip() != "":
                                return jid, f"Lên tới {max_v}", None, float(max_v), "max_only"
                            elif v_exact is not None and str(v_exact).strip() != "":
                                return jid, str(v_exact), float(v_exact), float(v_exact), "fixed"
                        elif isinstance(val, (int, float)):
                            return jid, str(val), float(val), float(val), "fixed"
                except Exception:
                    pass
        elif res.status_code == 404:
            # Job expired
            return jid, None, None, None, "expired"
    except Exception:
        pass
    return jid, None, None, None, None

def run_fix(batch_size=100, max_workers=10):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT j.job_id, s.source_job_url 
                FROM jobs j 
                JOIN job_source_records s ON j.job_id = s.job_id 
                WHERE j.salary_raw ~ '^[0-9]+$' AND s.source_id = 1
                LIMIT %s
            """, [batch_size])
            rows = cur.fetchall()

    if not rows:
        print("Không còn công việc TopCV nào có salary_raw dạng số đơn!")
        return 0

    print(f"Bắt đầu cập nhật dải lương cho {len(rows)} việc làm TopCV...")
    success_count = 0
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_topcv_salary, r): r[0] for r in rows}
        updates = []
        for future in as_completed(futures):
            res = future.result()
            jid, s_raw, s_min, s_max, s_type = res
            if s_raw:
                updates.append((s_raw, s_min, s_max, s_type, jid))

    if updates:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for s_raw, s_min, s_max, s_type, jid in updates:
                    cur.execute("""
                        UPDATE jobs 
                        SET salary_raw = %s, salary_min_vnd = %s, salary_max_vnd = %s, salary_type = %s
                        WHERE job_id = %s
                    """, (s_raw, s_min, s_max, s_type, jid))
            conn.commit()
        success_count = len(updates)

    print(f"Hoàn thành: Đã cập nhật thành công {success_count}/{len(rows)} jobs trong {time.time()-t0:.1f}s.")
    return success_count

if __name__ == "__main__":
    run_fix(batch_size=100, max_workers=10)
