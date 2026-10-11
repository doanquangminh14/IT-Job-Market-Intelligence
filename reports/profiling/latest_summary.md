# 📋 Báo Cáo Kiểm Kê & Profiling Dữ Liệu Tuyển Dụng IT

> **Phạm vi khảo sát**: `ALL_TIME`  
> **Thời điểm tạo báo cáo**: `2026-10-11 21:30:31`  
> **Số nguồn dữ liệu**: `3` (TopCV, TopDev, VietnamWorks)

---

## 1. Bảng Tổng Quan Chỉ Số Cốt Lõi

| Chỉ số kiểm kê | Giá trị | Ý nghĩa thực tế |
| :--- | :--- | :--- |
| **Tổng số listing thu thập** | **1,557** | Số lượng tin đã quét qua từ trang tìm kiếm |
| **Crawl detail thành công** | **1,510** | Số lượng tin đã có đầy đủ nội dung chi tiết |
| **Crawl detail thất bại** | **0** | Tin gặp lỗi HTTP hoặc WAF (Cần cào bù) |
| **Tin trong hàng đợi (Pending)** | **47** | Tin đã lưu listing nhưng chờ phiên cào tiếp |
| **URL bị trùng nội bộ sàn** | **9** | Các tin cùng 1 sàn bị trùng lặp link |
| **Tin trùng chéo giữa các sàn** | **13** | Cùng 1 công ty đăng tuyển chéo trên nhiều sàn |

---

## 2. Thống Kê Chi Tiết Từng Sàn Tuyển Dụng

| Nguồn | Listings | Details OK | URL Trùng | Lương cụ thể | Thương lượng | Có Hạn nộp | Ngôn ngữ chủ đạo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **topcv** | 761 | 714 | 9 | 413 (57.8%) | 301 (42.2%) | 100.0% | `vi` |
| **topdev** | 120 | 120 | 0 | 5 (4.2%) | 115 (95.8%) | 100.0% | `vi` |
| **vietnamworks** | 676 | 676 | 0 | 195 (28.8%) | 481 (71.2%) | 100.0% | `vi` |

---

## 3. Tỷ Lệ Hoàn Thiện Các Trường Dữ Liệu (Completeness Rate)

Bảng đánh giá tỷ lệ **bị thiếu (missing)** của các trường dữ liệu quan trọng:

| Tên trường dữ liệu | TopCV (% thiếu) | TopDev (% thiếu) | VietnamWorks (% thiếu) |
| :--- | :--- | :--- | :--- |
| Tiêu đề (`title_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Công ty (`company_name_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Địa điểm (`location_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Mức lương (`salary_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Kinh nghiệm (`experience_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Kỹ năng (`skills_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Mô tả công việc (`responsibilities_raw`) | `0.0%` | `0.0%` | `0.1%` |
| Yêu cầu công việc (`requirements_raw`) | `0.8%` | `0.0%` | `0.0%` |
| Quyền lợi (`benefits_raw`) | `0.0%` | `1.7%` | `0.0%` |
| Hạn nộp hồ sơ (`deadline_raw`) | `0.0%` | `0.0%` | `0.0%` |

> [!TIP]
> **Lưu ý nghiệp vụ về mức lương**: Mức lương ghi 'Thương lượng/Thoả thuận' không phải là dữ liệu thiếu (missing), mà là thông tin hợp lệ phản ánh chính sách của nhà tuyển dụng.

---

## 4. Phân Bố Ngôn Ngữ Tuyển Dụng

| Nguồn | Tiếng Việt (`vi`) | Tiếng Anh (`en`) | Song ngữ (`mixed`) | Khác / Ngắn |
| :--- | :--- | :--- | :--- | :--- |
| **topcv** | 556 (77.9%) | 86 (12.0%) | 70 (9.8%) | 2 (0.3%) |
| **topdev** | 68 (56.7%) | 33 (27.5%) | 18 (15.0%) | 1 (0.8%) |
| **vietnamworks** | 384 (56.8%) | 250 (37.0%) | 17 (2.5%) | 25 (3.7%) |

---

## 5. So Sánh Tính Đồng Nhất Của Cấu Trúc JSON (Schema Consistency)

- **Trạng thái đồng nhất**: ✅ **Đồng nhất 100% giữa các nguồn**
- **Số lượng trường chung (`common_keys`)**: `27` trường
- **Danh sách trường dùng chung**: `benefits_raw, company_location_raw, company_name_raw, company_size_raw, company_url, crawled_at, deadline_raw, detail_id, education_raw, employment_type_raw, experience_raw, industry_raw, job_url, location_raw, overview_raw, preferred_skills_raw, published_at_raw, required_skills_raw, requirements_raw, responsibilities_raw, salary_raw, source, source_job_id, title_raw, updated_at_raw, work_mode_raw, working_time_raw`

---

## 6. Mẫu Tin Đăng Tuyển Trùng Chéo Sàn (Cross-Portal Duplicates)

Hệ thống phát hiện **13** vị trí xuất hiện đồng thời trên từ 2 sàn trở lên:

1. **Database Engineer Dba** tại **Công Ty Tnhh Lg Cns Việt Nam** (Xuất hiện trên: `vietnamworks, topcv`)
2. **Ai Expert Khối Công Nghệ Thông Tin 2026Td450200** tại **Ngân Hàng Tmcp Quân Đội Mbbank** (Xuất hiện trên: `vietnamworks, topcv`)
3. **Fullstack Developer Junior Senior Khối Công Nghệ Thông Tin 2025Td922** tại **Ngân Hàng Tmcp Quân Đội Mbbank** (Xuất hiện trên: `vietnamworks, topcv`)
4. **Ai Software Engineer Pythongocc Backend Ai Agents Khối Công Nghệ Thông Tin 2026Td450888** tại **Ngân Hàng Tmcp Quân Đội Mbbank** (Xuất hiện trên: `vietnamworks, topcv`)
5. **Senior Ai Expert Khối Công Nghệ Thông Tin 2026Td450201** tại **Ngân Hàng Tmcp Quân Đội Mbbank** (Xuất hiện trên: `vietnamworks, topcv`)