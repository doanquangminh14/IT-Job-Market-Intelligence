# 📋 Báo Cáo Kiểm Kê & Profiling Dữ Liệu Tuyển Dụng IT

> **Phạm vi khảo sát**: `2026-10-13`  
> **Thời điểm tạo báo cáo**: `2026-10-13 22:30:42`  
> **Số nguồn dữ liệu**: `3` (TopCV, TopDev, VietnamWorks)

---

## 1. Bảng Tổng Quan Chỉ Số Cốt Lõi

| Chỉ số kiểm kê | Giá trị | Ý nghĩa thực tế |
| :--- | :--- | :--- |
| **Tổng số listing thu thập** | **182** | Số lượng tin đã quét qua từ trang tìm kiếm |
| **Crawl detail thành công** | **182** | Số lượng tin đã có đầy đủ nội dung chi tiết |
| **Crawl detail thất bại** | **0** | Tin gặp lỗi HTTP hoặc WAF (Cần cào bù) |
| **Tin trong hàng đợi (Pending)** | **0** | Tin đã lưu listing nhưng chờ phiên cào tiếp |
| **URL bị trùng nội bộ sàn** | **0** | Các tin cùng 1 sàn bị trùng lặp link |
| **Tin trùng chéo giữa các sàn** | **0** | Cùng 1 công ty đăng tuyển chéo trên nhiều sàn |

---

## 2. Thống Kê Chi Tiết Từng Sàn Tuyển Dụng

| Nguồn | Listings | Details OK | URL Trùng | Lương cụ thể | Thương lượng | Có Hạn nộp | Ngôn ngữ chủ đạo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **topcv** | 145 | 145 | 0 | 86 (59.3%) | 59 (40.7%) | 100.0% | `vi` |
| **topdev** | 4 | 4 | 0 | 0 (0.0%) | 4 (100.0%) | 100.0% | `en` |
| **vietnamworks** | 33 | 33 | 0 | 5 (15.2%) | 28 (84.8%) | 100.0% | `en` |

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
| Mô tả công việc (`responsibilities_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Yêu cầu công việc (`requirements_raw`) | `1.4%` | `0.0%` | `0.0%` |
| Quyền lợi (`benefits_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Hạn nộp hồ sơ (`deadline_raw`) | `0.0%` | `0.0%` | `0.0%` |

> [!TIP]
> **Lưu ý nghiệp vụ về mức lương**: Mức lương ghi 'Thương lượng/Thoả thuận' không phải là dữ liệu thiếu (missing), mà là thông tin hợp lệ phản ánh chính sách của nhà tuyển dụng.

---

## 4. Phân Bố Ngôn Ngữ Tuyển Dụng

| Nguồn | Tiếng Việt (`vi`) | Tiếng Anh (`en`) | Song ngữ (`mixed`) | Khác / Ngắn |
| :--- | :--- | :--- | :--- | :--- |
| **topcv** | 127 (87.6%) | 8 (5.5%) | 10 (6.9%) | 0 (0.0%) |
| **topdev** | 2 (50.0%) | 2 (50.0%) | 0 (0.0%) | 0 (0.0%) |
| **vietnamworks** | 6 (18.2%) | 21 (63.6%) | 1 (3.0%) | 5 (15.2%) |

---

## 5. So Sánh Tính Đồng Nhất Của Cấu Trúc JSON (Schema Consistency)

- **Trạng thái đồng nhất**: ✅ **Đồng nhất 100% giữa các nguồn**
- **Số lượng trường chung (`common_keys`)**: `27` trường
- **Danh sách trường dùng chung**: `benefits_raw, company_location_raw, company_name_raw, company_size_raw, company_url, crawled_at, deadline_raw, detail_id, education_raw, employment_type_raw, experience_raw, industry_raw, job_url, location_raw, overview_raw, preferred_skills_raw, published_at_raw, required_skills_raw, requirements_raw, responsibilities_raw, salary_raw, source, source_job_id, title_raw, updated_at_raw, work_mode_raw, working_time_raw`
