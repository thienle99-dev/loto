# 🎰 Loto Bot - Random Wheel Bot

Bot quay số ngẫu nhiên với các tính năng quản lý danh sách số linh hoạt.

## ✨ Tính Năng

- ✅ Chọn danh sách số từ x → y
- ✅ Quay wheel và chọn số ngẫu nhiên
- ✅ Tùy chọn loại bỏ số sau khi quay
- ✅ Reset danh sách về trạng thái ban đầu
- ✅ Quản lý session và trạng thái

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

### Telegram Bot Commands

Sau khi bot đã chạy, bạn có thể sử dụng các lệnh sau trên Telegram:

- `/start` - Bắt đầu hoặc xem hướng dẫn
- `/setrange <x> <y>` - Thiết lập khoảng số (ví dụ: `/setrange 1 100`)
- `/spin` - Quay wheel và chọn số ngẫu nhiên
- `/toggle_remove` - Bật/tắt chế độ loại bỏ số sau khi quay
- `/reset` - Reset danh sách số về ban đầu
- `/status` - Xem trạng thái session hiện tại
- `/clear` - Xóa toàn bộ session và bắt đầu lại
- `/help` - Xem hướng dẫn chi tiết

**Ví dụ sử dụng:**
```
/setrange 1 50
/spin
/spin
/toggle_remove
/spin
/reset
```

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
- [x] Telegram bot interface với đầy đủ commands
- [x] User session management (mỗi user có session riêng)
- [x] Validation và error handling
- [x] Unit tests

## 🚧 Tính Năng Tương Lai

- [ ] Discord bot interface
- [ ] Web dashboard
- [ ] Database persistence (SQLite/PostgreSQL)
- [ ] Statistics và history tracking
- [ ] Animation cho wheel (nếu là web app)
- [ ] Multi-language support

## 📝 License

MIT

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
