"""Bộ điều phối lệnh: `python -m src.cli <lệnh> [tham số]` (xem src/cli/__init__.py)."""
import importlib
import sys

# Tên lệnh ➔ module trong src.cli. Module chỉ được import khi chạy lệnh đó (crawl không cần nạp pandas/psycopg2).
COMMANDS = {
    "crawl": "Cào tin tuyển dụng vào data/raw/",
    "quality": "Kiểm định data/raw, gộp vào Master Bronze",
    "profile": "Kiểm kê dữ liệu thô, xuất báo cáo",
    "pipeline": "Cào ➔ kiểm định Bronze ➔ nạp Silver PostgreSQL",
}


def _usage() -> str:
    lines = ["Cách dùng: python -m src.cli <lệnh> [tham số]   (thêm -h sau lệnh để xem tham số)", "", "Lệnh:"]
    lines += [f"  {name:<10}{desc}" for name, desc in COMMANDS.items()]
    return "\n".join(lines)


def main(argv=None) -> None:
    # Terminal Windows mặc định cp1252 không in được tiếng Việt
    for stream in (sys.stdout, sys.stderr):
        if stream and stream.encoding and stream.encoding.lower() != "utf-8":
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] in ("-h", "--help"):
        print(_usage())
        return
    name, rest = argv[0], argv[1:]
    if name not in COMMANDS:
        print(f"Không có lệnh '{name}'.\n\n{_usage()}", file=sys.stderr)
        sys.exit(2)
    importlib.import_module(f"src.cli.{name}").main(rest)


if __name__ == "__main__":
    main()
