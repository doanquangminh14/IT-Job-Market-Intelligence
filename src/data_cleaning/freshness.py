"""Tính lại cờ "tin còn hạn" (is_active) theo NGÀY HIỆN TẠI.

Notebook 02 / JobCleaner gắn is_active tại thời điểm làm sạch rồi ghi cứng vào jobs_clean.csv, nên vài ngày sau
cờ này đã cũ. Ứng dụng gọi hàm này mỗi lần nạp dữ liệu để không gợi ý tin đã hết hạn.
Quy tắc giống JobCleaner.parse_deadline: còn hạn nếu deadline >= hôm nay; không có / không đọc được deadline thì giữ giá trị cũ
(mặc định True).
"""
from typing import Optional

import pandas as pd


def refresh_is_active(df: pd.DataFrame, today: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    """Trả về bản sao của df với cột is_active tính lại từ cột deadline so với `today` (mặc định: hôm nay)."""
    out = df.copy()
    old = out['is_active'] if 'is_active' in out.columns else pd.Series(True, index=out.index)
    old = old.fillna(True).astype(bool)
    if 'deadline' not in out.columns:
        out['is_active'] = old
        return out
    today = (today or pd.Timestamp.now()).normalize()
    deadline = pd.to_datetime(out['deadline'].astype(str).str[:10], errors='coerce', format='%Y-%m-%d')
    out['is_active'] = (deadline >= today).where(deadline.notna(), old).astype(bool)
    return out
