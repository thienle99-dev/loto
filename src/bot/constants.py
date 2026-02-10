from pathlib import Path

# Cấu hình mặc định cho ván game
MAX_NUMBERS = 90
DEFAULT_REMOVE_AFTER_SPIN = True
BET_AMOUNT = 5.0

# Cooldown chống spam
COOLDOWN_SPIN_SECONDS = 0.5  # Giảm từ 2s xuống 0.5s để tăng tốc
COOLDOWN_CHECK_SECONDS = 2
COOLDOWN_GENERAL_SECONDS = 0.3  # Rate limit cho các lệnh thông thường (giảm từ 1s)

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
TICKET_NAMES = {
    "cam1": "Cam 1", "cam2": "Cam 2",
    "do1": "Đỏ 1", "do2": "Đỏ 2",
    "duong1": "Dương 1", "duong2": "Dương 2",
    "hong1": "Hồng 1", "hong2": "Hồng 2",
    "luc1": "Lục 1", "luc2": "Lục 2",
    "tim1": "Tím 1", "tim2": "Tím 2",
    "vang1": "Vàng 1", "vang2": "Vàng 2",
    "xanh1": "Xanh 1", "xanh2": "Xanh 2",
}

# Các câu thoại vui khi số đợi xuất hiện
WAITING_RESPONSES = [
    " Số **{number}** về rồi kìa! {mentions} đâu ra nhận hàng!",
    "🚀 Chờ đợi là hạnh phúc! Em **{number}** đã cập bến. Chúc mừng {mentions}!",
    "📢 Loa loa! Tin chuẩn chưa anh em? Số **{number}** nổ rồi kìa {mentions} ơi!",
    "🎉 Cuối cùng thì **{number}** cũng chịu ra mặt! {mentions} check ngay đi!",
    "👀 Ơ kìa, ai đợi số **{number}** thì dậy đi thôi! {mentions} dậy đi!",
    "🎲 Cầu được ước thấy! Số **{number}** đã về đội của {mentions}!",
    "💥 Bùm! **{number}** xuất hiện như một vị thần! {mentions} sướng nhé!",
    "🆘 Giải cứu thành công! Em **{number}** đã được giải thoát. {mentions} mau nhận người thân!",
    "💎 Kim cương quan điểm luôn! Số **{number}** đỉnh nóc, kịch trần. {mentions} đâu rồi!",
    "📞 Alo alo, tổng đài báo số **{number}** vừa gọi tên {mentions}. Nghe máy đi!",
    "🧘 Tĩnh tâm nào... **{number}** đã đến! {mentions} hít thở sâu và nhận hàng!",
    "🦄 Ảo thật đấy! Số **{number}** lù lù xuất hiện. {mentions} có tin được không?",
    "🏃 Chạy đi đâu cho thoát! **{number}** tóm được {mentions} rồi nhé!",
    "🎯 Bách phát bách trúng! **{number}** găm thẳng vào tim {mentions}!",
    "🥂 Nâng ly lên nào! **{number}** đã về, party thôi {mentions} ơi!",
    "🤫 Suỵt... nghe nói **{number}** là con số định mệnh của {mentions} đấy!",
    "🛒 Chốt đơn! **{number}** đã vào giỏ hàng của {mentions}. Thanh toán niềm vui nào!",
    "🌈 Sau cơn mưa trời lại sáng, sau bao ngày đợi **{number}** cũng sang. Chúc mừng {mentions}!",
]

# Các câu tiêu đề khi quay số
SPIN_HEADERS = [
    "✨ *Số quay ra:*",
]
TICKET_DISPLAY_NAMES: dict[str, str] = {
    "cam1": "Cam số 1",
    "cam2": "Cam số 2",
    "do1": "Đỏ số 1",
    "do2": "Đỏ số 2",
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
