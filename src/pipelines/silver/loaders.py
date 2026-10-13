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

def load_skills(skills_list, conn):
    """
    Nạp danh mục kỹ năng vào bảng skills trong PostgreSQL.
    Áp dụng OVERRIDING SYSTEM VALUE và ON CONFLICT DO UPDATE để đảm bảo tính Idempotent.
    """
    records = [
        (
            s["skill_id"],
            s["parent_id"],
            s["skill_name"],
            s["skill_normalized"],
            s["skill_category"],
            s["description"],
            s["is_active"]
        )
        for s in skills_list
    ]

    insert_sql = """
        INSERT INTO skills (
            skill_id,
            parent_id,
            skill_name,
            skill_normalized,
            skill_category,
            description,
            is_active
        )
        OVERRIDING SYSTEM VALUE
        VALUES %s
        ON CONFLICT (skill_id) DO UPDATE SET
            parent_id = EXCLUDED.parent_id,
            skill_name = EXCLUDED.skill_name,
            skill_normalized = EXCLUDED.skill_normalized,
            skill_category = EXCLUDED.skill_category,
            description = EXCLUDED.description,
            is_active = EXCLUDED.is_active,
            updated_at = CURRENT_TIMESTAMP;
    """

    print(f"-> [Loader: skills] Đang nạp {len(records):,} kỹ năng vào PostgreSQL...")
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, records, page_size=100)
        conn.commit()

        cur.execute("SELECT count(*) FROM skills;")
        total_in_db = cur.fetchone()[0]

    print(f"   [Loader: skills] Nạp thành công! Tổng số bản ghi trong bảng 'skills': {total_in_db:,}")
    return total_in_db

def load_jobs(jobs_list, conn):
    """
    Nạp danh sách tin tuyển dụng chuẩn hóa vào bảng jobs trong PostgreSQL.
    Áp dụng OVERRIDING SYSTEM VALUE và ON CONFLICT DO UPDATE để đảm bảo tính Idempotent.
    """
    records = [
        (
            j['job_id'],
            j['primary_source_id'],
            j['company_id'],
            j['canonical_job_id'],
            j['title_raw'],
            j['title_normalized'],
            j['seniority_level'],
            j['location_raw'],
            j['city'],
            j['work_mode_raw'],
            j['work_mode'],
            j['employment_type'],
            j['working_time_raw'],
            j['salary_raw'],
            j['salary_min'],
            j['salary_max'],
            j['salary_currency'],
            j['salary_period'],
            j['salary_type'],
            j['salary_min_vnd'],
            j['salary_max_vnd'],
            j['experience_raw'],
            j['experience_min_years'],
            j['experience_max_years'],
            j['education_raw'],
            j['education_level'],
            j['published_at'],
            j['updated_at_source'],
            j['deadline'],
            j['is_active']
        )
        for j in jobs_list
    ]

    insert_sql = """
        INSERT INTO jobs (
            job_id,
            primary_source_id,
            company_id,
            canonical_job_id,
            title_raw,
            title_normalized,
            seniority_level,
            location_raw,
            city,
            work_mode_raw,
            work_mode,
            employment_type,
            working_time_raw,
            salary_raw,
            salary_min,
            salary_max,
            salary_currency,
            salary_period,
            salary_type,
            salary_min_vnd,
            salary_max_vnd,
            experience_raw,
            experience_min_years,
            experience_max_years,
            education_raw,
            education_level,
            published_at,
            updated_at_source,
            deadline,
            is_active
        )
        OVERRIDING SYSTEM VALUE
        VALUES %s
        ON CONFLICT (job_id) DO UPDATE SET
            primary_source_id = EXCLUDED.primary_source_id,
            company_id = EXCLUDED.company_id,
            canonical_job_id = EXCLUDED.canonical_job_id,
            title_raw = EXCLUDED.title_raw,
            title_normalized = EXCLUDED.title_normalized,
            seniority_level = EXCLUDED.seniority_level,
            location_raw = EXCLUDED.location_raw,
            city = EXCLUDED.city,
            work_mode_raw = EXCLUDED.work_mode_raw,
            work_mode = EXCLUDED.work_mode,
            employment_type = EXCLUDED.employment_type,
            working_time_raw = EXCLUDED.working_time_raw,
            salary_raw = EXCLUDED.salary_raw,
            salary_min = EXCLUDED.salary_min,
            salary_max = EXCLUDED.salary_max,
            salary_currency = EXCLUDED.salary_currency,
            salary_period = EXCLUDED.salary_period,
            salary_type = EXCLUDED.salary_type,
            salary_min_vnd = EXCLUDED.salary_min_vnd,
            salary_max_vnd = EXCLUDED.salary_max_vnd,
            experience_raw = EXCLUDED.experience_raw,
            experience_min_years = EXCLUDED.experience_min_years,
            experience_max_years = EXCLUDED.experience_max_years,
            education_raw = EXCLUDED.education_raw,
            education_level = EXCLUDED.education_level,
            published_at = EXCLUDED.published_at,
            updated_at_source = EXCLUDED.updated_at_source,
            deadline = EXCLUDED.deadline,
            is_active = EXCLUDED.is_active,
            updated_at = CURRENT_TIMESTAMP;
    """

    print(f"-> [Loader: jobs] Đang nạp {len(records):,} việc làm vào PostgreSQL...")
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, records, page_size=500)
        conn.commit()

        cur.execute("SELECT count(*) FROM jobs;")
        total_in_db = cur.fetchone()[0]

    print(f"   [Loader: jobs] Nạp thành công! Tổng số bản ghi trong bảng 'jobs': {total_in_db:,}")
    return total_in_db

def load_job_descriptions(desc_list, conn):
    """
    Nạp nội dung văn bản chi tiết vào bảng job_descriptions trong PostgreSQL.
    Quan hệ 1-1 với jobs thông qua khóa chính job_id.
    """
    records = [
        (
            d['job_id'],
            d['overview_raw'],
            d['responsibilities_raw'],
            d['requirements_raw'],
            d['benefits_raw'],
            d['description_clean'],
            d['requirements_clean'],
            d['benefits_clean'],
            d['language'],
            d['text_hash']
        )
        for d in desc_list
    ]

    insert_sql = """
        INSERT INTO job_descriptions (
            job_id,
            overview_raw,
            responsibilities_raw,
            requirements_raw,
            benefits_raw,
            description_clean,
            requirements_clean,
            benefits_clean,
            language,
            text_hash
        )
        VALUES %s
        ON CONFLICT (job_id) DO UPDATE SET
            overview_raw = EXCLUDED.overview_raw,
            responsibilities_raw = EXCLUDED.responsibilities_raw,
            requirements_raw = EXCLUDED.requirements_raw,
            benefits_raw = EXCLUDED.benefits_raw,
            description_clean = EXCLUDED.description_clean,
            requirements_clean = EXCLUDED.requirements_clean,
            benefits_clean = EXCLUDED.benefits_clean,
            language = EXCLUDED.language,
            text_hash = EXCLUDED.text_hash,
            cleaned_at = CURRENT_TIMESTAMP;
    """

    print(f"-> [Loader: job_descriptions] Đang nạp {len(records):,} bản ghi mô tả vào PostgreSQL...")
    with conn.cursor() as cur:
        execute_values(cur, insert_sql, records, page_size=500)
        conn.commit()

        cur.execute("SELECT count(*) FROM job_descriptions;")
        total_in_db = cur.fetchone()[0]

    print(f"   [Loader: job_descriptions] Nạp thành công! Tổng số bản ghi trong bảng 'job_descriptions': {total_in_db:,}")
    return total_in_db
