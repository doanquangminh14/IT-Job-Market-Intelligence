import os
import sys
import psycopg2
from dotenv import load_dotenv

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def init_silver_schema():
    load_dotenv()

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", 5432))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dbname = os.getenv("DB_NAME")

    # Kiểm tra biến môi trường bắt buộc, không hardcode thông tin nhạy cảm vào code
    if not all([user, password, dbname]):
        missing = [k for k, v in [("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", dbname)] if not v]
        raise ValueError(f"Lỗi: Thiếu các biến môi trường cấu hình database trong tệp .env: {', '.join(missing)}")

    sql_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sql", "schema_silver.sql")
    if not os.path.exists(sql_file_path):
        sql_file_path = "sql/schema_silver.sql"

    print(f"Đang đọc tệp schema SQL: {sql_file_path}")
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    print(f"Đang kết nối tới PostgreSQL ({host}:{port}/{dbname}) ...")
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname
    )
    conn.autocommit = True
    cur = conn.cursor()

    print("Đang thực thi khởi tạo schema trong PostgreSQL ...")
    cur.execute(sql_script)

    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]

    print(f"\nĐã khởi tạo thành công {len(tables)} bảng trong cơ sở dữ liệu '{dbname}':")
    for tbl in tables:
        cur.execute(f"SELECT count(*) FROM {tbl};")
        count = cur.fetchone()[0]
        cur.execute(f"""
            SELECT count(*) 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = '{tbl}';
        """)
        col_count = cur.fetchone()[0]
        print(f"  - {tbl:20s}: {col_count:2d} cột | {count:4d} bản ghi")

    cur.close()
    conn.close()
    print("\nQuá trình khởi tạo cơ sở dữ liệu hoàn tất an toàn.")

if __name__ == "__main__":
    init_silver_schema()
