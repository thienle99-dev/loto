"""
Configuration cho Telegram bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

# Bot Settings
MAX_NUMBERS = 90  # Giới hạn số lượng số trong danh sách
DEFAULT_REMOVE_AFTER_SPIN = True  # Mặc định có loại bỏ số sau khi quay
WEB_APP_URL = os.getenv('WEB_APP_URL', 'https://your-public-url.com')  # URL cho Mini App

# Admin Settings
# Danh sách ID admin (comma separated string in .env: ADMIN_IDS=123,456)
admin_ids_raw = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(',') if x.strip().isdigit()]

# Messages
WELCOME_MESSAGE = r"""
🎰 *Chào mừng đến với Loto Bot\!*  
Bot hỗ trợ chơi loto / quay số trong nhóm chat với nhiều tiện ích quản lý phòng chơi.

📖 *Flow cơ bản:*
1️⃣ *Bắt buộc:* Host tạo *vòng chơi* trước khi tạo game  
   • `/vong_moi <tên_vòng>` \- gom nhiều game vào cùng một vòng (vd: `Loto tối nay`)

2️⃣ Host tạo *game* trong chat / trong vòng  
   • `/moi <tên_game>` \- tạo game với dãy mặc định `1 -> {MAX_NUMBERS}`  
   • Hoặc `/pham_vi <x> <y>` \- tự chọn khoảng số cho game

3️⃣ Host bắt đầu game  
   • `/bat_dau` \- sau khi đã tạo game

4️⃣ Người chơi lấy vé (bắt buộc), xem danh sách  
   • `/lay_ve <mã_vé>` \- lấy vé để tham gia game \\(bắt buộc trước khi chơi\\)  
   • `/danh_sach` \- xem danh sách người đã lấy vé  
   • `/tra_ve` \- trả vé và rời game nếu *chưa* start  

5️⃣ Quay số & kiểm tra vé  
   • Host: `/quay` \- quay số (chỉ sau khi `/bat_dau`)  
   • Người chơi: `/kinh <dãy_số>` để kiểm tra vé  
   • Nếu có *ít nhất 5 số* khớp với các số đã quay (và không có số ngoài dãy) thì được tính là *trúng thưởng*

6️⃣ Kết thúc & xem kết quả  
   • `/ket_thuc` \- kết thúc game hiện tại (chỉ host)  
   • `/ket_qua` \- xem lại kết quả game gần nhất trong chat  
   • `/xep_hang` hoặc `/xep_hang join` \- xem bảng xếp hạng

ℹ️ *Lệnh nhanh khác:*  
• `/trang_thai` \- xem trạng thái game hiện tại  
• `/lich_su` \- lịch sử quay của game  
• `/dat_lai` \- reset lại dãy số của game đang chơi  
• `/xoa` \- xoá session trong chat  
• `/menu` \- mở bàn phím nhanh các lệnh  
• `/tro_giup` \- xem lại hướng dẫn chi tiết
"""

HELP_MESSAGE = r"""
📖 *Hướng dẫn chi tiết Loto Bot (snake_case commands):*

1️⃣ *Tạo vòng chơi & game (Host)*
   • *Bắt buộc:* `/vong_moi <tên_vòng>` \- tạo vòng chơi trước khi có thể tạo ván game  
     Ví dụ: `/vong_moi Loto tối nay`
   • `/moi <tên_game>` \- tạo game mới với dãy mặc định `1 -> {MAX_NUMBERS}`  
     Ví dụ: `/moi Ván 1`  
   • Hoặc: `/pham_vi 1 90` \- tự chọn khoảng số cho game  
   • `/bat_dau` \- host bấm để *bắt đầu* game (sau đó mới được `/quay` và `/kinh`)

2️⃣ *Người chơi lấy vé và tham gia game*
   • `/lay_ve <mã_vé>` \- lấy vé để tham gia \\(bắt buộc trước khi chơi\\)  
   • `/danh_sach` \- xem danh sách người đã lấy vé  
   • `/tra_ve` \- trả vé và rời game nếu game *chưa start*  

3️⃣ *Quay số & kiểm tra vé*
   • `/quay` \- quay số (chỉ khi game đã `/bat_dau`)  
   • `/lich_su` \- xem toàn bộ lịch sử quay của game hiện tại  
   • `/trang_thai` \- xem trạng thái game: khoảng số, đã quay bao nhiêu lần, còn bao nhiêu số,...  
   • `/kinh <dãy_số>` \- kiểm tra vé, ví dụ:
     `/kinh 1 5 10 20 30` hoặc `/kinh 1,5,10,20,30`  
     → Nếu vé có *ít nhất 5 số* đã quay, không có số ngoài dãy, bot sẽ báo *trúng thưởng* kèm các số khớp

4️⃣ *Kết thúc & xem lại kết quả*
   • `/ket_thuc` \- chỉ host (người tạo game) mới được phép kết thúc game  
   • `/ket_qua` \- xem lại kết quả game gần nhất trong chat: tên game, host, số đã quay, danh sách người trúng  
   • `/xep_hang` \- top người trúng thưởng nhiều nhất  
   • `/xep_hang join` \- top người lấy vé / tham gia nhiều game nhất

5️⃣ *Quản lý & tiện ích khác*
   • `/dat_lai` \- reset dãy số của game hiện tại về ban đầu  
   • `/xoa` \- xoá session trong chat  
   • `/xoa_kinh` \- xoá vé trúng thưởng gần nhất của chính mình  
   • `/menu` \- mở bàn phím nhanh các lệnh thường dùng  

💡 *Ví dụ flow đầy đủ:*  
`/vong_moi Loto tối nay`  
`/moi Ván 1`  
`/bat_dau`  
Mọi người: `/lay_ve tim1` (hoặc mã vé khác) → host: `/quay` vài lần → mọi người: `/kinh 1 5 10 20 30`  
Kết thúc: `/ket_thuc` → xem lại: `/ket_qua` → xem top: `/xep_hang`
"""