import hashlib

def _generate_numbers_for_id(ticket_id: str) -> list:
    """Tạo ra 15 số (3 hàng, mỗi hàng 5 số) cố định cho mỗi mã vé"""
    # Sử dụng hash của ticket_id làm seed để đảm bảo bộ số luôn cố định cho từng loại vé
    seed = int(hashlib.md5(ticket_id.encode()).hexdigest(), 16) % 10**8
    import random
    rng = random.Random(seed)
    
    # Lấy 15 số ngẫu nhiên không trùng lặp từ 1-90
    all_numbers = sorted(rng.sample(range(1, 91), 15))
    
    # Chia thành 3 hàng, mỗi hàng 5 số
    return [
        all_numbers[0:5],
        all_numbers[5:10],
        all_numbers[10:15]
    ]

# Mapping mã vé -> bộ số tương ứng
TICKET_NUMBERS = {
    "cam1": _generate_numbers_for_id("cam1"),
    "cam2": _generate_numbers_for_id("cam2"),
    "do1": _generate_numbers_for_id("do1"),
    "do2": _generate_numbers_for_id("do2"),
    "duong1": _generate_numbers_for_id("duong1"),
    "duong2": _generate_numbers_for_id("duong2"),
    "hong1": _generate_numbers_for_id("hong1"),
    "hong2": _generate_numbers_for_id("hong2"),
    "luc1": _generate_numbers_for_id("luc1"),
    "luc2": _generate_numbers_for_id("luc2"),
    "tim1": _generate_numbers_for_id("tim1"),
    "tim2": _generate_numbers_for_id("tim2"),
    "vang1": _generate_numbers_for_id("vang1"),
    "vang2": _generate_numbers_for_id("vang2"),
    "xanh1": _generate_numbers_for_id("xanh1"),
    "xanh2": _generate_numbers_for_id("xanh2"),
}

def get_ticket_numbers(ticket_id: str) -> list:
    """Lấy danh sách các hàng số của vé"""
    return TICKET_NUMBERS.get(ticket_id, [])
