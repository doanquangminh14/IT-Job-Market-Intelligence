"""
Chạy lại toàn bộ chuỗi xử lý sau khi crawl thêm dữ liệu, và LƯU output vào từng notebook (như bấm "Run All").

    python scripts/refresh_pipeline.py                 # Bronze ➔ notebook 02 ➔ 04 ➔ 05 ➔ 06
    python scripts/refresh_pipeline.py --skip-quality  # bỏ bước Bronze (đã chạy main_quality.py --save-bronze)
    python scripts/refresh_pipeline.py --only 05 06    # chỉ chạy lại một số notebook

Thứ tự:
  1. main_quality.py --save-bronze : kiểm định toàn bộ data/raw, gộp vào data/bronze (tin crawl lại ghi đè bản cũ)
  2. notebook 02 : làm sạch + khử trùng lặp ➔ data/notebook/content_base/jobs_clean.csv và data/silver/ (GHI ĐÈ)
  3. notebook 04 : EDA
  4. notebook 05 : CBF + đánh giá (khoảng 3 phút)
  5. notebook 06 : CF trên dữ liệu mô phỏng ➔ data/simulated/ (GHI ĐÈ)
Dừng ngay ở bước lỗi đầu tiên; notebook lỗi KHÔNG bị ghi đè.
Streamlit tự nạp lại dữ liệu mới (khóa cache theo thời điểm sửa file), không cần sửa gì; mô hình TF-IDF tự huấn luyện lại.
"""
import argparse
import json
import os
import queue
import re
import subprocess
import sys
import time
from pathlib import Path

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = {
    "02": ROOT / "notebook" / "02_data_pipeline" / "02_data_cleaning_and_deduplication.ipynb",
    "04": ROOT / "notebook" / "04_eda" / "01_eda_job_market_insights.ipynb",
    "05": ROOT / "notebook" / "05_recommender" / "01_cbf_engine_and_evaluation.ipynb",
    "06": ROOT / "notebook" / "06_recommender_cf" / "01_simulation_and_matrix_factorization.ipynb",
}
ANSI = re.compile(chr(27) + r"\[[0-9;]*m")


def run_notebook(nb_path: Path, per_cell_timeout: int = 1800) -> bool:
    """Chạy từng cell trong kernel Python hiện tại (.venv), lưu output vào chính file. Trả về False nếu có lỗi."""
    from jupyter_client import KernelManager

    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]   # kernel dùng đúng .venv
    os.environ["PYTHONUTF8"] = "1"
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    km = KernelManager(kernel_name="python3")
    km.start_kernel(cwd=str(nb_path.parent))
    kc = km.client()
    kc.start_channels()
    kc.wait_for_ready(timeout=120)
    failed = None
    try:
        for i, cell in enumerate(nb["cells"]):
            if cell["cell_type"] != "code":
                continue
            t0, msg_id = time.time(), kc.execute("".join(cell["source"]))
            outputs, exec_count = [], None
            while True:
                try:
                    msg = kc.get_iopub_msg(timeout=per_cell_timeout)
                except queue.Empty:
                    failed = (i, "Timeout", f"quá {per_cell_timeout}s")
                    break
                if msg["parent_header"].get("msg_id") != msg_id:
                    continue
                t, c = msg["msg_type"], msg["content"]
                if t == "stream":
                    if outputs and outputs[-1]["output_type"] == "stream" and outputs[-1]["name"] == c["name"]:
                        outputs[-1]["text"] += c["text"]
                    else:
                        outputs.append({"output_type": "stream", "name": c["name"], "text": c["text"]})
                elif t in ("display_data", "execute_result"):
                    o = {"output_type": t, "data": c["data"], "metadata": c.get("metadata", {})}
                    if t == "execute_result":
                        o["execution_count"] = c["execution_count"]
                    outputs.append(o)
                elif t == "error":
                    outputs.append({"output_type": "error", "ename": c["ename"], "evalue": c["evalue"], "traceback": c["traceback"]})
                    failed = (i, c["ename"], c["evalue"], c["traceback"])
                elif t == "execute_input":
                    exec_count = c["execution_count"]
                elif t == "status" and c["execution_state"] == "idle":
                    break
            for o in outputs:   # chuẩn nbformat: text là danh sách các dòng
                if o["output_type"] == "stream":
                    o["text"] = o["text"].splitlines(keepends=True)
                if "data" in o:
                    o["data"] = {k: (v.splitlines(keepends=True) if isinstance(v, str) and k.startswith("text/") else v)
                                 for k, v in o["data"].items()}
            cell["outputs"], cell["execution_count"] = outputs, exec_count
            print(f"    cell {i:2d} ({time.time() - t0:5.1f}s)" + ("  <-- LỖI" if failed else ""), flush=True)
            if failed:
                break
    finally:
        kc.stop_channels()
        km.shutdown_kernel(now=True)

    if failed:
        print(f"  LỖI ở cell {failed[0]}: {failed[1]}: {failed[2]}")
        if len(failed) > 3:
            print(ANSI.sub("", "\n".join(failed[3]))[-1500:])
        print("  (notebook không bị ghi đè)")
        return False
    nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser(description="Chạy lại Bronze ➔ notebook 02 ➔ 04 ➔ 05 ➔ 06 sau khi crawl thêm dữ liệu.")
    ap.add_argument("--skip-quality", action="store_true", help="bỏ bước main_quality.py --save-bronze")
    ap.add_argument("--only", nargs="+", choices=list(NOTEBOOKS), help="chỉ chạy các notebook này (vd. --only 05 06)")
    args = ap.parse_args()

    t_start = time.time()
    if not args.skip_quality and not args.only:
        print("[1] Kiểm định & gộp dữ liệu raw vào Bronze (main_quality.py --save-bronze)")
        r = subprocess.run([sys.executable, str(ROOT / "main_quality.py"), "--save-bronze"], cwd=str(ROOT))
        if r.returncode != 0:
            sys.exit("Bước Bronze lỗi, dừng.")

    for key in (args.only or list(NOTEBOOKS)):
        path = NOTEBOOKS[key]
        print(f"[notebook {key}] {path.relative_to(ROOT)}", flush=True)
        t0 = time.time()
        if not run_notebook(path):
            sys.exit(f"Dừng ở notebook {key}.")
        print(f"  xong ({time.time() - t0:.0f}s)")

    csv = ROOT / "data" / "notebook" / "content_base" / "jobs_clean.csv"
    if csv.exists():
        import pandas as pd
        df = pd.read_csv(csv)
        print(f"\nDữ liệu sạch: {len(df):,} tin, {int(df['is_it'].sum()):,} tin IT, "
              f"{int(df['is_active'].sum()):,} tin còn hạn (tại thời điểm làm sạch)")
    print(f"Hoàn tất sau {(time.time() - t_start) / 60:.1f} phút. Mở lại / làm mới Streamlit để xem số liệu mới.")


if __name__ == "__main__":
    main()
