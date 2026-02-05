"""
Demo script để test core functionality
"""
# -*- coding: utf-8 -*-
import sys
import io

# Fix encoding cho Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.bot.wheel import (
    create_wheel_session,
    spin_wheel,
    reset_session,
    set_remove_mode,
    get_session_status
)


def print_separator():
    print("-" * 50)


def demo_basic_usage():
    """Demo sử dụng cơ bản"""
    print("\n[DEMO] Su dung co ban")
    print_separator()
    
    # Tạo session từ 1 đến 20
    session = create_wheel_session(1, 20, remove_after_spin=True)
    print(f"[OK] Da tao session: {session.start_number} -> {session.end_number}")
    print(f"[INFO] Tong so: {session.get_total_numbers()}")
    print(f"[INFO] So con lai: {session.get_remaining_count()}")
    
    # Quay 5 lần
    print("\n[SPIN] Quay wheel 5 lan:")
    for i in range(5):
        number = spin_wheel(session)
        print(f"  Lần {i+1}: {number:2d} | Còn lại: {session.get_remaining_count()}")
    
    # Xem trạng thái
    print("\n[STATUS] Trang thai session:")
    status = get_session_status(session)
    for key, value in status.items():
        print(f"  {key}: {value}")


def demo_without_remove():
    """Demo với chế độ không loại bỏ"""
    print("\n[DEMO] Che do khong loai bo so")
    print_separator()
    
    session = create_wheel_session(1, 5, remove_after_spin=False)
    print(f"[OK] Da tao session: {session.start_number} -> {session.end_number}")
    print(f"[SETTING] Che do loai bo: {session.remove_after_spin}")
    
    # Quay nhiều lần
    print("\n[SPIN] Quay wheel 10 lan (khong loai bo):")
    results = []
    for i in range(10):
        number = spin_wheel(session)
        results.append(number)
        print(f"  Lần {i+1}: {number}")
    
    print(f"\n[INFO] So con lai: {session.get_remaining_count()} (van day du)")
    print(f"[INFO] So da quay: {len(results)}")


def demo_reset():
    """Demo reset session"""
    print("\n[DEMO] Reset session")
    print_separator()
    
    session = create_wheel_session(1, 10, remove_after_spin=True)
    print(f"[OK] Da tao session: {session.start_number} -> {session.end_number}")
    
    # Quay một vài lần
    print("\n[SPIN] Quay 3 lan:")
    for i in range(3):
        number = spin_wheel(session)
        print(f"  Lần {i+1}: {number}")
    
    print(f"\n[INFO] Truoc reset: Con lai {session.get_remaining_count()}/{session.get_total_numbers()}")
    
    # Reset
    reset_session(session)
    print(f"[RESET] Da reset!")
    print(f"[INFO] Sau reset: Con lai {session.get_remaining_count()}/{session.get_total_numbers()}")


def demo_toggle_mode():
    """Demo thay đổi chế độ loại bỏ"""
    print("\n[DEMO] Thay doi che do loai bo")
    print_separator()
    
    session = create_wheel_session(1, 10, remove_after_spin=True)
    print(f"[OK] Da tao session")
    print(f"[SETTING] Che do ban dau: Loai bo = {session.remove_after_spin}")
    
    # Quay với chế độ loại bỏ
    print("\n[SPIN] Quay 3 lan (voi loai bo):")
    for i in range(3):
        number = spin_wheel(session)
        print(f"  Lần {i+1}: {number} | Còn lại: {session.get_remaining_count()}")
    
    # Tắt chế độ loại bỏ
    set_remove_mode(session, False)
    print(f"\n[SETTING] Da tat che do loai bo")
    
    # Quay tiếp
    print("\n[SPIN] Quay them 3 lan (khong loai bo):")
    for i in range(3):
        number = spin_wheel(session)
        print(f"  Lần {i+4}: {number} | Còn lại: {session.get_remaining_count()}")


def demo_edge_cases():
    """Demo các trường hợp đặc biệt"""
    print("\n[DEMO] Truong hop dac biet")
    print_separator()
    
    # Session với 1 số
    print("\n[1] Session voi 1 so:")
    session = create_wheel_session(5, 5, remove_after_spin=True)
    number = spin_wheel(session)
    print(f"   So duoc chon: {number}")
    print(f"   Danh sach rong: {session.is_empty()}")
    
    try:
        spin_wheel(session)
    except ValueError as e:
        print(f"   [ERROR] Loi khi quay tiep: {e}")
    
    # Session lớn
    print("\n[2] Session lon (1-1000):")
    session = create_wheel_session(1, 1000, remove_after_spin=True)
    print(f"   Tong so: {session.get_total_numbers()}")
    number = spin_wheel(session)
    print(f"   So duoc chon: {number}")
    print(f"   Con lai: {session.get_remaining_count()}")


if __name__ == "__main__":
    print("=" * 50)
    print("LOTO BOT - RANDOM WHEEL DEMO")
    print("=" * 50)
    
    demo_basic_usage()
    demo_without_remove()
    demo_reset()
    demo_toggle_mode()
    demo_edge_cases()
    
    print("\n" + "=" * 50)
    print("[OK] Demo hoan thanh!")
    print("=" * 50)
