# 📋 Báo Cáo Kiểm Kê & Profiling Dữ Liệu Tuyển Dụng IT

> **Phạm vi khảo sát**: `2026-10-12`  
> **Thời điểm tạo báo cáo**: `2026-10-12 21:49:51`  
> **Số nguồn dữ liệu**: `3` (TopCV, TopDev, VietnamWorks)

---

## 1. Bảng Tổng Quan Chỉ Số Cốt Lõi

| Chỉ số kiểm kê | Giá trị | Ý nghĩa thực tế |
| :--- | :--- | :--- |
| **Tổng số listing thu thập** | **826** | Số lượng tin đã quét qua từ trang tìm kiếm |
| **Crawl detail thành công** | **817** | Số lượng tin đã có đầy đủ nội dung chi tiết |
| **Crawl detail thất bại** | **0** | Tin gặp lỗi HTTP hoặc WAF (Cần cào bù) |
| **Tin trong hàng đợi (Pending)** | **0** | Tin đã lưu listing nhưng chờ phiên cào tiếp |
| **URL bị trùng nội bộ sàn** | **9** | Các tin cùng 1 sàn bị trùng lặp link |
| **Tin trùng chéo giữa các sàn** | **0** | Cùng 1 công ty đăng tuyển chéo trên nhiều sàn |

---

## 2. Thống Kê Chi Tiết Từng Sàn Tuyển Dụng

| Nguồn | Listings | Details OK | URL Trùng | Lương cụ thể | Thương lượng | Có Hạn nộp | Ngôn ngữ chủ đạo |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **topcv** | 456 | 447 | 9 | 261 (58.4%) | 186 (41.6%) | 100.0% | `vi` |
| **topdev** | 0 | 0 | 0 | 0 (0%) | 0 (0%) | 0% | `unknown` |
| **vietnamworks** | 370 | 370 | 0 | 110 (29.7%) | 260 (70.3%) | 100.0% | `vi` |

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
| Yêu cầu công việc (`requirements_raw`) | `0.2%` | `0.0%` | `0.0%` |
| Quyền lợi (`benefits_raw`) | `0.0%` | `0.0%` | `0.0%` |
| Hạn nộp hồ sơ (`deadline_raw`) | `0.0%` | `0.0%` | `0.0%` |

> [!TIP]
> **Lưu ý nghiệp vụ về mức lương**: Mức lương ghi 'Thương lượng/Thoả thuận' không phải là dữ liệu thiếu (missing), mà là thông tin hợp lệ phản ánh chính sách của nhà tuyển dụng.

---

## 4. Phân Bố Ngôn Ngữ Tuyển Dụng

| Nguồn | Tiếng Việt (`vi`) | Tiếng Anh (`en`) | Song ngữ (`mixed`) | Khác / Ngắn |
| :--- | :--- | :--- | :--- | :--- |
| **topcv** | 361 (80.8%) | 58 (13.0%) | 27 (6.0%) | 1 (0.2%) |
| **topdev** | 0 (0%) | 0 (0%) | 0 (0%) | 0 (0%) |
| **vietnamworks** | 186 (50.3%) | 160 (43.2%) | 10 (2.7%) | 14 (3.8%) |

---

## 5. So Sánh Tính Đồng Nhất Của Cấu Trúc JSON (Schema Consistency)

- **Trạng thái đồng nhất**: ⚠️ **Có trường chênh lệch giữa các sàn**
- **Số lượng trường chung (`common_keys`)**: `0` trường
- **Danh sách trường dùng chung**: ``
