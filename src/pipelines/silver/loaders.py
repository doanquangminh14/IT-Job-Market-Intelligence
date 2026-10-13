from psycopg2.extras import execute_values

def load_companies(companies_list, conn):
    """
    Nạp danh sách công ty đã làm sạch vào bảng companies trong PostgreSQL.
    Áp dụng OVERRIDING SYSTEM VALUE và ON CONFLICT DO UPDATE để đảm bảo tính Idempotent.
    """
    records = [
        (
            c["company_id"],
            c["company_name_raw"],
            c["company_name_normalized"],
            c["website_domain"],
            c["company_url"],
            c["company_logo_url"],
            c["company_size_raw"],
            c["company_size_min"],
            c["company_size_max"],
            c["company_location_raw"],
            c["company_city"],
            c["industry_raw"],
            c["industry_normalized"]
        )
        for c in companies_list
    ]

    insert_sql = """
        INSERT INTO companies (
            company_id,
            company_name_raw,
            company_name_normalized,
            website_domain,
            company_url,
            company_logo_url,
            company_size_raw,
            company_size_min,
            company_size_max,
            company_location_raw,
            company_city,
            industry_raw,
            industry_normalized
        )
        OVERRIDING SYSTEM VALUE
        VALUES %s
        ON CONFLICT (company_id) DO UPDATE SET
            company_name_raw = EXCLUDED.company_name_raw,
            company_name_normalized = EXCLUDED.company_name_normalized,
            website_domain = EXCLUDED.website_domain,
            company_url = EXCLUDED.company_url,
            company_logo_url = EXCLUDED.company_logo_url,
            company_size_raw = EXCLUDED.company_size_raw,
            company_size_min = EXCLUDED.company_size_min,
            company_size_max = EXCLUDED.company_size_max,
            company_location_raw = EXCLUDED.company_location_raw,
            company_city = EXCLUDED.company_city,
            industry_raw = EXCLUDED.industry_raw,
            industry_normalized = EXCLUDED.industry_normalized,
            updated_at = CURRENT_TIMESTAMP;
    """

    print(f"-> [Loader: companies] Đang nạp {len(records):,} bản ghi vào PostgreSQL...")
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, records, page_size=500)
        conn.commit()

        cur.execute("SELECT count(*) FROM companies;")
        total_in_db = cur.fetchone()[0]

    print(f"   [Loader: companies] Nạp thành công! Tổng số bản ghi trong bảng 'companies': {total_in_db:,}")
    return total_in_db
