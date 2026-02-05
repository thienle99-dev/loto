# 🎰 Loto Bot - Random Wheel Bot

Bot quay số ngẫu nhiên với các tính năng quản lý danh sách số linh hoạt.

## ✨ Tính Năng

- ✅ Chọn khoảng số linh hoạt (mặc định 1 → 90 hoặc tùy chỉnh)
- ✅ Quay wheel và chọn số ngẫu nhiên, có thể loại bỏ số sau khi quay
- ✅ Quản lý session theo từng chat/group
- ✅ Nhiều người chơi có thể join cùng một game
- ✅ Host start/stop game rõ ràng (`/startsession`, `/endsession`)
- ✅ Người chơi check vé, tự động xác định trúng thưởng (ít nhất 5 số đã quay)
- ✅ Lưu lịch sử quay, kết quả game gần nhất và bảng xếp hạng trong từng chat

## 📁 Cấu Trúc Dự Án

```
loto-bot/
├── src/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── wheel.py          # Core wheel logic
│   │   ├── telegram_bot.py   # Telegram bot handlers
│   │   └── session_manager.py # User session manager
│   ├── models/
│   │   ├── __init__.py
│   │   └── wheel_session.py  # WheelSession model
│   ├── utils/
│   │   ├── __init__.py
│   │   └── validators.py     # Validation functions
│   └── main.py               # Entry point
├── config/
│   ├── __init__.py
│   └── config.py             # Configuration
├── tests/
│   └── test_wheel.py         # Unit tests
├── requirements.txt
├── .env.example              # Environment variables template
├── README.md
└── PLAN.md
```

## 🚀 Cài Đặt

### Yêu Cầu
- Python 3.8+
- Telegram Bot Token (lấy từ [@BotFather](https://t.me/BotFather))

### Setup Telegram Bot

1. **Tạo Bot Token:**
   - Mở Telegram và tìm [@BotFather](https://t.me/BotFather)
   - Gửi lệnh `/newbot` và làm theo hướng dẫn
   - Copy token được cung cấp

2. **Cài đặt dependencies:**
```bash
# Clone repository (nếu có)
# cd loto-bot

# Tạo virtual environment (khuyến nghị)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

3. **Cấu hình Bot Token:**
```bash
# Copy file .env.example thành .env
cp .env.example .env

# Hoặc tạo file .env và thêm:
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

4. **Chạy bot:**
```bash
# Cách 1: Chạy từ thư mục gốc (khuyến nghị)
python run_bot.py

# Cách 2: Chạy trực tiếp
python src/main.py
```

## 💻 Sử Dụng

### Flow chơi game trong Telegram

Sau khi bot đã chạy (`python run_bot.py`), thêm bot vào group và sử dụng các lệnh sau:

#### 1. Host tạo & bắt đầu game

- `/newsession <tên_game>`  
  - Tạo game mới trong chat với khoảng số mặc định `1 -> MAX_NUMBERS` (mặc định 90).  
  - Ví dụ: `/newsession Loto tối nay`

- Hoặc `/setrange <x> <y>`  
  - Tạo game mới với khoảng số tùy chỉnh.  
  - Ví dụ: `/setrange 1 100`

- `/startsession`  
  - Chỉ **host** (người tạo game) mới được bấm để *bắt đầu* game.  
  - Sau khi start, mọi người mới được `/spin` và `/check`.

> Mỗi chat chỉ có **1 game hoạt động** tại một thời điểm.  
> Nếu đang có game, phải `/endsession` hoặc `/clear` trước khi tạo game mới.

#### 2. Người chơi tham gia

- `/join`  
  - Tham gia game hiện tại trong chat.
- `/players`  
  - Xem danh sách người chơi (host được đánh dấu ⭐).
- `/out`  
  - Rời game nếu game **chưa start**.  
  - Sau khi `/startsession`, không thể dùng `/out` nữa (chốt danh sách người chơi).

#### 3. Quay số & kiểm tra vé

- `/spin`  
  - Quay số một lần (chỉ khi game đã `/startsession`).  
  - Có cooldown nhẹ để tránh spam liên tục.

- `/history`  
  - Hiển thị **toàn bộ** lịch sử quay của game hiện tại (từ lần quay đầu tiên đến giờ).

- `/status`  
  - Xem trạng thái game: khoảng số, tổng số, đã quay bao nhiêu, còn lại bao nhiêu, chế độ loại bỏ,...

- `/check <dãy_số>`  
  - Kiểm tra vé của người chơi so với kết quả đã quay.  
  - Dãy số có thể cách nhau bởi khoảng trắng hoặc dấu phẩy:
    - Ví dụ: `/check 1 5 10 20 30`  
    - Hoặc: `/check 1,5,10,20,30`
  - Một vé được coi là **trúng thưởng** nếu:
    - Có **ít nhất 5 số** đã nằm trong danh sách số đã quay,
    - Không có số nào ngoài khoảng game,
    - Không có số nào thuộc nhóm “chưa quay”.

#### 4. Kết thúc & xem lại kết quả

- `/endsession`  
  - Chỉ host được phép kết thúc game.  
  - Khi kết thúc, bot sẽ:
    - Cập nhật số lần tham gia của từng người chơi,
    - Lưu lại danh sách số đã quay và người trúng cho chat.

- `/lastresult`  
  - Hiển thị kết quả **game gần nhất** trong chat:
    - Tên game, host,
    - Thời điểm kết thúc,
    - Tổng số lượt quay,
    - Một phần danh sách số đã quay,
    - Danh sách người trúng (nếu có).

- `/leaderboard`  
  - Top người trúng thưởng nhiều nhất trong chat.

- `/leaderboard join`  
  - Top người tham gia nhiều game nhất trong chat.

#### 5. Quản lý & tiện ích khác

- `/reset`  
  - Reset lại dãy số của game hiện tại về ban đầu (lịch sử quay bị xóa, game tiếp tục).

- `/clear`  
  - Xóa session/game hiện tại trong chat mà **không** lưu kết quả.

- `/toggle_remove`  
  - Bật/tắt chế độ loại bỏ số sau khi quay (số đã quay có còn xuất hiện lại hay không).

- `/menu`  
  - Mở bàn phím nhanh chứa các lệnh chính, giúp thao tác trên mobile dễ hơn.

- `/start`, `/help`  
  - Hiển thị hướng dẫn tổng quan và hướng dẫn chi tiết (đã cập nhật theo flow mới).

### Core API (Python)

```python
from src.bot.wheel import (
    create_wheel_session,
    spin_wheel,
    reset_session,
    set_remove_mode,
    get_session_status
)

# Tạo session mới
session = create_wheel_session(start=1, end=10, remove_after_spin=True)

# Quay wheel
number = spin_wheel(session)
print(f"Số được chọn: {number}")

# Xem trạng thái
status = get_session_status(session)
print(f"Số còn lại: {status['remaining_count']}")

# Reset session
reset_session(session)

# Thay đổi chế độ loại bỏ
set_remove_mode(session, remove=False)
```

### Ví Dụ Đầy Đủ

```python
from src.bot.wheel import create_wheel_session, spin_wheel, reset_session

# Tạo session từ 1 đến 100
session = create_wheel_session(1, 100, remove_after_spin=True)

print(f"Tổng số: {session.get_total_numbers()}")
print(f"Số còn lại: {session.get_remaining_count()}")

# Quay 5 lần
for i in range(5):
    number = spin_wheel(session)
    print(f"Lần {i+1}: {number} (Còn lại: {session.get_remaining_count()})")

# Reset về ban đầu
reset_session(session)
print(f"Sau reset: {session.get_remaining_count()}")
```

## 🧪 Testing

```bash
# Chạy tests
python -m pytest tests/

# Hoặc với unittest
python -m unittest tests.test_wheel
```

## 📋 Tính Năng Đã Hoàn Thành

- [x] Core wheel logic với WheelSession model
- [x] Telegram bot interface với flow game loto hoàn chỉnh
- [x] Session management theo từng chat/group
- [x] Validation và error handling
- [x] Unit tests
- [x] Lịch sử quay, kết quả game gần nhất và thống kê leaderboard theo chat

## 🚧 Tính Năng Tương Lai

- [ ] Discord bot interface
- [ ] Web dashboard
- [ ] Database persistence (SQLite/PostgreSQL)
- [ ] Lưu thống kê và history vào database (hiện tại in-memory)
- [ ] Animation cho wheel (nếu là web app)
- [ ] Multi-language support

## 📝 License

MIT

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
"# loto" 
