from pathlib import Path

# Vòng chơi (vòng mới) đang hoạt động theo chat:
# {chat_id: {"round_name": str, "owner_id": int, "created_at": str}}
active_rounds: dict[int, dict] = {}

# Cooldown chống spam
COOLDOWN_SPIN_SECONDS = 2
COOLDOWN_CHECK_SECONDS = 2

# Danh sách mã vé (mã màu viết tắt)
TICKET_CODES = [
    "cam1",
    "cam2",
    "do1",
    "do2",
    "duong1",
    "duong2",
    "hong1",
    "hong2",
    "luc1",
    "luc2",
    "tim1",
    "tim2",
    "vang1",
    "vang2",
    "xanh1",
    "xanh2",
]

# Map mã vé -> đường dẫn ảnh tương ứng (chỉ gửi ảnh nếu file tồn tại)
TICKET_IMAGES: dict[str, Path] = {
    "cam1": Path(__file__).parent.parent.parent / "images" / "cam_1.jpg",
    "cam2": Path(__file__).parent.parent.parent / "images" / "cam_2.jpg",
    "do1": Path(__file__).parent.parent.parent / "images" / "do_1.jpg",
    "do2": Path(__file__).parent.parent.parent / "images" / "do_2.jpg",
    "duong1": Path(__file__).parent.parent.parent / "images" / "duong_1.jpg",
    "duong2": Path(__file__).parent.parent.parent / "images" / "duong_2.jpg",
    "hong1": Path(__file__).parent.parent.parent / "images" / "hong_1.jpg",
    "hong2": Path(__file__).parent.parent.parent / "images" / "hong_2.jpg",
    "luc1": Path(__file__).parent.parent.parent / "images" / "luc_1.jpg",
    "luc2": Path(__file__).parent.parent.parent / "images" / "luc_2.jpg",
    "tim1": Path(__file__).parent.parent.parent / "images" / "tim_1.jpg",
    "tim2": Path(__file__).parent.parent.parent / "images" / "tim_2.jpg",
    "vang1": Path(__file__).parent.parent.parent / "images" / "vang_1.jpg",
    "vang2": Path(__file__).parent.parent.parent / "images" / "vang_2.jpg",
    "xanh1": Path(__file__).parent.parent.parent / "images" / "xanh_1.jpg",
    "xanh2": Path(__file__).parent.parent.parent / "images" / "xanh_2.jpg",
}

# Map mã vé -> tên hiển thị (tiếng Việt)
TICKET_DISPLAY_NAMES: dict[str, str] = {
    "cam1": "Cam số 1",
    "cam2": "Cam số 2",
    "do1": "Đổ số 1",
    "do2": "Đổ số 2",
    "duong1": "Xanh dương số 1",
    "duong2": "Xanh dương số 2",
    "hong1": "Hồng số 1",
    "hong2": "Hồng số 2",
    "luc1": "Xanh lục số 1",
    "luc2": "Xanh lục số 2",
    "tim1": "Tím số 1",
    "tim2": "Tím số 2",
    "vang1": "Vàng số 1",
    "vang2": "Vàng số 2",
    "xanh1": "Xanh số 1",
    "xanh2": "Xanh số 2",
}

# Lưu kết quả game gần nhất theo chat (cache RAM): {chat_id: {...}}
last_results: dict[int, dict] = {}

# Thống kê wins/participations theo chat (cache RAM)
stats: dict[int, dict] = {}
