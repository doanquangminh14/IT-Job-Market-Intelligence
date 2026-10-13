import os
from contextlib import contextmanager
import psycopg2
from dotenv import load_dotenv

def get_db_config():
    """Đọc cấu hình cơ sở dữ liệu từ tệp .env một cách an toàn."""
    # Tìm tệp .env tại thư mục gốc của repository
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", 5432))
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    dbname = os.getenv("DB_NAME")

    if not all([user, password, dbname]):
        missing = [k for k, v in [("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", dbname)] if not v]
        raise ValueError(f"Lỗi: Thiếu các biến môi trường cấu hình database trong .env: {', '.join(missing)}")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname
    }

@contextmanager
def get_db_connection():
    """Context manager mở và đóng kết nối PostgreSQL tự động, rollback khi gặp lỗi."""
    config = get_db_config()
    conn = psycopg2.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        dbname=config["dbname"]
    )
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
