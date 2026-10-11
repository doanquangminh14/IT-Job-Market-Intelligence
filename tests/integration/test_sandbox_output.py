import os
from src.crawlers.topcv import TopCVCrawler
from src.crawlers.topdev import TopDevCrawler
from src.crawlers.vietnamworks import VietnamWorksCrawler


def test_sandbox_output_isolation(tmp_path):
    """
    Kiểm tra đảm bảo: Khi truyền output_dir (sandbox) vào crawler,
    mọi file listings và details chỉ được lưu trong thư mục sandbox đó,
    hoàn toàn không ghi đè hay làm bẩn thư mục production data/raw/.
    """
    sandbox_topcv = str(tmp_path / "topcv")
    sandbox_topdev = str(tmp_path / "topdev")
    sandbox_vnw = str(tmp_path / "vietnamworks")

    crawler_topcv = TopCVCrawler(output_dir=sandbox_topcv)
    crawler_topdev = TopDevCrawler(output_dir=sandbox_topdev)
    crawler_vnw = VietnamWorksCrawler(output_dir=sandbox_vnw)

    assert crawler_topcv.base_raw_dir == sandbox_topcv
    assert sandbox_topcv in crawler_topcv.listings_dir
    assert sandbox_topcv in crawler_topcv.details_dir

    assert crawler_topdev.base_raw_dir == sandbox_topdev
    assert sandbox_topdev in crawler_topdev.listings_dir
    assert sandbox_topdev in crawler_topdev.details_dir

    assert crawler_vnw.base_raw_dir == sandbox_vnw
    assert sandbox_vnw in crawler_vnw.listings_dir
    assert sandbox_vnw in crawler_vnw.details_dir

    # Thử lưu một record mẫu vào sandbox
    sample_records = [{"id": 1, "title": "Test Sandbox Job"}]
    crawler_topcv.save_records(
        folder_path=crawler_topcv.listings_dir,
        file_prefix="test_page_001",
        records=sample_records
    )

    expected_csv = os.path.join(crawler_topcv.listings_dir, "test_page_001.csv")
    expected_json = os.path.join(crawler_topcv.listings_dir, "test_page_001.json")

    assert os.path.exists(expected_csv)
    assert os.path.exists(expected_json)
