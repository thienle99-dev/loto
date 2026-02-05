# Kế Hoạch Phát Triển Bot Random Wheel

## 📋 Tổng Quan
Bot random wheel cho phép người dùng quay số ngẫu nhiên từ một danh sách số được chọn, với các tùy chọn quản lý danh sách số.

## 🎯 Yêu Cầu Chức Năng

### 1. Chọn Danh Sách Số (x → y)
- **Input**: Người dùng nhập số bắt đầu (x) và số kết thúc (y)
- **Validation**: 
  - Kiểm tra x < y
  - Kiểm tra số hợp lệ (không âm, không quá lớn)
  - Giới hạn số lượng số trong danh sách (ví dụ: tối đa 1000 số)
- **Output**: Tạo danh sách số từ x đến y

### 2. Random Wheel
- **Chức năng chính**: Quay và chọn ngẫu nhiên một số từ danh sách
- **Hiển thị**: 
  - Animation quay wheel (optional)
  - Hiển thị số được chọn
  - Hiển thị số lượng số còn lại trong danh sách

### 3. Tùy Chọn Loại Bỏ Số Sau Khi Quay
- **Chế độ 1**: Loại bỏ số sau khi quay (không thể quay lại số đó)
- **Chế độ 2**: Giữ lại số (có thể quay lại số đó)
- **UI**: Toggle/Checkbox để bật/tắt chế độ này
- **Mặc định**: Có thể đặt mặc định là loại bỏ hoặc giữ lại

### 4. Làm Mới/Reset
- **Reset danh sách**: Khôi phục lại danh sách số ban đầu (x → y)
- **Reset cài đặt**: Đặt lại các tùy chọn về mặc định
- **Clear all**: Xóa toàn bộ và bắt đầu lại từ đầu

## 🏗️ Kiến Trúc Hệ Thống

### Cấu Trúc Thư Mục Đề Xuất
```
loto-bot/
├── src/
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── wheel.py          # Logic random wheel
│   │   └── commands.py       # Bot commands
│   ├── models/
│   │   ├── __init__.py
│   │   └── wheel_session.py  # Model quản lý session
│   ├── utils/
│   │   ├── __init__.py
│   │   └── validators.py     # Validation functions
│   └── main.py               # Entry point
├── config/
│   └── config.py             # Configuration
├── tests/
│   └── test_wheel.py
├── requirements.txt
├── README.md
└── PLAN.md
```

## 📐 Thiết Kế Chi Tiết

### 1. Model: WheelSession
```python
class WheelSession:
    - id: str                    # Session ID
    - start_number: int          # Số bắt đầu (x)
    - end_number: int           # Số kết thúc (y)
    - available_numbers: list    # Danh sách số còn lại
    - removed_numbers: list      # Danh sách số đã loại bỏ
    - remove_after_spin: bool   # Có loại bỏ sau khi quay không
    - created_at: datetime
    - last_spin: int            # Số vừa quay (nếu có)
```

### 2. Core Functions

#### `create_wheel_session(start: int, end: int) -> WheelSession`
- Tạo session mới với danh sách số từ start đến end
- Khởi tạo available_numbers với tất cả số trong khoảng

#### `spin_wheel(session: WheelSession) -> int`
- Chọn ngẫu nhiên một số từ available_numbers
- Nếu remove_after_spin = True: loại bỏ số đó khỏi available_numbers
- Lưu số vừa quay vào last_spin
- Trả về số được chọn

#### `reset_session(session: WheelSession) -> WheelSession`
- Khôi phục available_numbers về danh sách ban đầu
- Xóa removed_numbers
- Giữ nguyên cài đặt remove_after_spin

#### `set_remove_mode(session: WheelSession, remove: bool) -> WheelSession`
- Thay đổi chế độ loại bỏ số

### 3. Bot Commands (Nếu là Telegram/Discord Bot)

#### `/start` hoặc `/new`
- Bắt đầu session mới
- Hướng dẫn người dùng nhập số bắt đầu và kết thúc

#### `/setrange <x> <y>`
- Thiết lập khoảng số từ x đến y
- Validation và tạo session

#### `/spin`
- Quay wheel và hiển thị kết quả
- Hiển thị số còn lại (nếu có)

#### `/toggle_remove`
- Bật/tắt chế độ loại bỏ số sau khi quay

#### `/reset`
- Reset danh sách số về ban đầu

#### `/status`
- Hiển thị trạng thái hiện tại:
  - Khoảng số (x → y)
  - Số lượng số còn lại
  - Chế độ loại bỏ (bật/tắt)
  - Số vừa quay (nếu có)

#### `/clear`
- Xóa toàn bộ và bắt đầu lại

## 🎨 UI/UX Flow (Nếu là Web App)

### Flow 1: Thiết Lập Ban Đầu
1. Người dùng nhập số bắt đầu (x)
2. Người dùng nhập số kết thúc (y)
3. Hiển thị danh sách số đã tạo
4. Chọn chế độ loại bỏ (checkbox)

### Flow 2: Quay Wheel
1. Click nút "Quay"
2. Hiển thị animation (optional)
3. Hiển thị số được chọn
4. Cập nhật danh sách số còn lại (nếu remove_after_spin = True)
5. Hiển thị thông báo số lượng số còn lại

### Flow 3: Quản Lý
- Nút "Reset": Khôi phục danh sách
- Nút "Clear": Xóa toàn bộ
- Toggle "Loại bỏ sau khi quay": Bật/tắt chế độ

## 🔧 Công Nghệ Đề Xuất

### Option 1: Python Bot (Telegram/Discord)
- **Framework**: python-telegram-bot hoặc discord.py
- **Database**: SQLite (đơn giản) hoặc PostgreSQL (nâng cao)
- **Libraries**: random, datetime

### Option 2: Web Application
- **Frontend**: React/Vue.js với animation library
- **Backend**: FastAPI/Flask (Python) hoặc Node.js/Express
- **Database**: SQLite hoặc PostgreSQL
- **Animation**: CSS animations hoặc libraries như react-wheel-of-fortune

### Option 3: Discord Bot với Web Dashboard
- **Bot**: discord.py
- **Dashboard**: React + FastAPI
- **Database**: PostgreSQL

## 📝 Implementation Steps

### Phase 1: Core Logic (Week 1)
- [ ] Tạo model WheelSession
- [ ] Implement create_wheel_session()
- [ ] Implement spin_wheel()
- [ ] Implement reset_session()
- [ ] Implement set_remove_mode()
- [ ] Unit tests cho core logic

### Phase 2: Bot Interface (Week 2)
- [ ] Setup bot framework (Telegram/Discord)
- [ ] Implement commands: /start, /setrange, /spin
- [ ] Implement commands: /toggle_remove, /reset, /status
- [ ] Error handling và validation
- [ ] User session management

### Phase 3: UI Enhancement (Week 3)
- [ ] Thêm animation cho wheel (optional)
- [ ] Cải thiện message formatting
- [ ] Thêm statistics (số lần quay, số đã loại bỏ, etc.)
- [ ] Thêm export/import session (optional)

### Phase 4: Testing & Polish (Week 4)
- [ ] Integration testing
- [ ] User acceptance testing
- [ ] Bug fixes
- [ ] Documentation
- [ ] Deployment

## 🎯 Features Nâng Cao (Future)

1. **Multiple Sessions**: Quản lý nhiều wheel session cùng lúc
2. **History**: Lưu lịch sử các số đã quay
3. **Statistics**: Thống kê số lần xuất hiện của mỗi số
4. **Custom Weights**: Đặt trọng số cho từng số (xác suất khác nhau)
5. **Export/Import**: Xuất/nhập session để chia sẻ
6. **Multi-language**: Hỗ trợ nhiều ngôn ngữ
7. **Admin Commands**: Quản lý bot (nếu cần)

## 📊 Database Schema (Nếu dùng Database)

```sql
CREATE TABLE wheel_sessions (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50),
    start_number INTEGER NOT NULL,
    end_number INTEGER NOT NULL,
    available_numbers TEXT NOT NULL,  -- JSON array
    removed_numbers TEXT DEFAULT '[]', -- JSON array
    remove_after_spin BOOLEAN DEFAULT TRUE,
    last_spin INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE spin_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) REFERENCES wheel_sessions(id),
    number INTEGER NOT NULL,
    spun_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## ✅ Checklist Trước Khi Bắt Đầu

- [ ] Xác định platform (Telegram/Discord/Web)
- [ ] Setup development environment
- [ ] Tạo project structure
- [ ] Setup version control (Git)
- [ ] Tạo requirements.txt / package.json
- [ ] Setup testing framework
- [ ] Tạo README.md với hướng dẫn setup

## 📌 Notes

- **Performance**: Nếu danh sách số lớn (>1000), cần optimize việc random selection
- **Security**: Validate tất cả user inputs để tránh injection attacks
- **UX**: Hiển thị rõ ràng số còn lại và số đã loại bỏ
- **Error Handling**: Xử lý các trường hợp edge cases (danh sách rỗng, số không hợp lệ, etc.)
