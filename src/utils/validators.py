"""
Validation functions cho wheel bot
"""
from typing import Tuple, Optional


def validate_range(start: int, end: int) -> Tuple[bool, Optional[str]]:
    """
    Validate khoảng số từ start đến end
    
    Args:
        start: Số bắt đầu
        end: Số kết thúc
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if start < 0:
        return False, "Số bắt đầu phải >= 0"
    
    if end < 0:
        return False, "Số kết thúc phải >= 0"
    
    if start >= end:
        return False, "Số bắt đầu phải nhỏ hơn số kết thúc"
    
    max_numbers = 90
    if (end - start + 1) > max_numbers:
        return False, f"Khoảng số quá lớn. Tối đa {max_numbers} số"
    
    return True, None


def validate_number(value: any) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate và chuyển đổi giá trị thành số nguyên
    
    Args:
        value: Giá trị cần validate
    
    Returns:
        Tuple (is_valid, number, error_message)
    """
    try:
        number = int(value)
        if number < 0:
            return False, None, "Số phải >= 0"
        return True, number, None
    except (ValueError, TypeError):
        return False, None, f"'{value}' không phải là số hợp lệ"
