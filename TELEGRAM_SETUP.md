# Hướng Dẫn Setup Telegram Bot

## Bước 1: Tạo Bot Token

1. Mở Telegram và tìm [@BotFather](https://t.me/BotFather)
2. Gửi lệnh `/newbot`
3. Nhập tên cho bot (ví dụ: "My Loto Bot")
4. Nhập username cho bot (phải kết thúc bằng `bot`, ví dụ: `my_loto_bot`)
5. Copy token được cung cấp (có dạng: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

## Bước 2: Cấu Hình Bot Token

1. Tạo file `.env` trong thư mục gốc của project:
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

2. Mở file `.env` và thêm token:
```
TELEGRAM_BOT_TOKEN=your_token_here
```

## Bước 3: Cài Đặt Dependencies

```bash
# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Bước 4: Chạy Bot

```bash
# Cách 1: Chạy từ thư mục gốc (khuyến nghị)
python run_bot.py

# Cách 2: Chạy trực tiếp
python src/main.py
```

Bạn sẽ thấy thông báo:
```
Đang khởi động bot...
Bot đã sẵn sàng!
```

## Bước 5: Test Bot

1. Mở Telegram và tìm bot của bạn (theo username đã đặt)
2. Gửi lệnh `/start` để bắt đầu
3. Thử các lệnh:
   - `/setrange 1 100` - Tạo danh sách từ 1 đến 100
   - `/spin` - Quay wheel
   - `/status` - Xem trạng thái
   - `/reset` - Reset danh sách
   - `/help` - Xem hướng dẫn

## Troubleshooting

### Lỗi: "TELEGRAM_BOT_TOKEN không được tìm thấy!"
- Kiểm tra file `.env` có tồn tại không
- Kiểm tra token trong file `.env` có đúng format không
- Đảm bảo file `.env` nằm trong thư mục gốc của project

### Lỗi: "Unauthorized" hoặc "Invalid token"
- Kiểm tra lại token từ BotFather
- Đảm bảo không có khoảng trắng thừa trong token

### Bot không phản hồi
- Kiểm tra bot đã được start chưa (`python src/main.py`)
- Kiểm tra internet connection
- Xem logs trong console để tìm lỗi

## Các Lệnh Bot

| Lệnh | Mô tả | Ví dụ |
|------|-------|-------|
| `/start` | Bắt đầu bot | `/start` |
| `/setrange <x> <y>` | Thiết lập khoảng số | `/setrange 1 100` |
| `/spin` | Quay wheel | `/spin` |
| `/toggle_remove` | Bật/tắt loại bỏ số | `/toggle_remove` |
| `/reset` | Reset danh sách | `/reset` |
| `/status` | Xem trạng thái | `/status` |
| `/clear` | Xóa session | `/clear` |
| `/help` | Hướng dẫn | `/help` |

## Lưu Ý

- Mỗi user có session riêng biệt
- Session được lưu trong memory (sẽ mất khi restart bot)
- Để lưu trữ lâu dài, cần thêm database (sẽ implement sau)
