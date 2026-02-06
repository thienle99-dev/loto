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
3. Thử các lệnh (theo bộ lệnh tiếng Việt mới):
   - `/moi Loto test` - Tạo game mới với khoảng mặc định `1 -> 90`
   - `/pham_vi 1 100` - Tạo game mới với khoảng số tuỳ chỉnh
   - `/bat_dau` - Host bấm để bắt đầu game
   - `/lay_ve <mã_vé>` - Người chơi lấy vé để tham gia (ví dụ: `/lay_ve tim1`)
   - `/quay` - Quay số
   - `/kinh 1 5 10 20 30` - Kiểm tra vé
   - `/ket_thuc` - Kết thúc game hiện tại
   - `/ket_qua` - Xem lại kết quả game gần nhất
   - `/xep_hang` - Xem bảng xếp hạng

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
| `/start` | Bắt đầu bot, hiện welcome message | `/start` |
| `/menu` | Mở bàn phím nhanh các lệnh chính | `/menu` |
| `/vong_moi <tên_vòng>` | Tạo vòng chơi mới trong chat | `/vong_moi Loto tối nay` |
| `/moi <tên_game>` | Tạo game mới với dãy mặc định `1 -> 90` | `/moi Ván 1` |
| `/pham_vi <x> <y>` | Tạo game mới với khoảng số tuỳ chỉnh | `/pham_vi 1 100` |
| `/bat_dau` | Host bấm để bắt đầu game | `/bat_dau` |
| `/lay_ve <mã_vé>` | Lấy vé để tham gia game (bắt buộc trước khi chơi) | `/lay_ve tim1` |
| `/danh_sach` | Xem danh sách người đã lấy vé | `/danh_sach` |
| `/tra_ve` | Trả vé và rời game nếu game chưa bắt đầu | `/tra_ve` |
| `/quay` | Quay số | `/quay` |
| `/kinh <dãy_số>` | Kiểm tra vé so với các số đã quay | `/kinh 1 5 10 20 30` |
| `/lich_su` | Xem lịch sử quay của game hiện tại | `/lich_su` |
| `/trang_thai` | Xem trạng thái game hiện tại | `/trang_thai` |
| `/dat_lai` | Reset lại dãy số của game hiện tại | `/dat_lai` |
| `/ket_thuc` | Kết thúc game hiện tại (chỉ host) | `/ket_thuc` |
| `/ket_qua` | Xem kết quả game gần nhất trong chat | `/ket_qua` |
| `/xep_hang` | Xem bảng xếp hạng trúng thưởng hoặc người lấy vé | `/xep_hang`, `/xep_hang join` |
| `/xoa` | Xoá session/game hiện tại trong chat | `/xoa` |
| `/tro_giup` | Xem hướng dẫn chi tiết | `/tro_giup` |

## Lưu Ý

- Mỗi user có session riêng biệt
- Session được lưu trong memory (sẽ mất khi restart bot)
- Để lưu trữ lâu dài, cần thêm database (sẽ implement sau)
