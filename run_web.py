import os
import sys
import uvicorn

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    print("=" * 70)
    print("   IT JOB MARKET INTELLIGENCE - NỀN TẢNG WEB THÔNG MINH")
    print("   Khởi chạy máy chủ FastAPI & Giao diện Web hiện đại...")
    print("   Truy cập tại: http://localhost:8000")
    print("   API Documentation: http://localhost:8000/docs")
    print("=" * 70)
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=True)
