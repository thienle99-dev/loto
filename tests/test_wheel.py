"""
Unit tests cho core wheel logic
"""
import unittest
from src.models.wheel_session import WheelSession
from src.bot.wheel import (
    create_wheel_session,
    spin_wheel,
    reset_session,
    set_remove_mode,
    get_session_status
)


class TestWheelSession(unittest.TestCase):
    """Test WheelSession model"""
    
    def test_create_session(self):
        """Test tạo session hợp lệ"""
        session = create_wheel_session(1, 10)
        self.assertEqual(session.start_number, 1)
        self.assertEqual(session.end_number, 10)
        self.assertEqual(session.get_total_numbers(), 10)
        self.assertEqual(session.get_remaining_count(), 10)
    
    def test_create_session_invalid_range(self):
        """Test tạo session với khoảng không hợp lệ"""
        with self.assertRaises(ValueError):
            create_wheel_session(10, 5)  # start > end
    
    def test_create_session_negative(self):
        """Test tạo session với số âm"""
        with self.assertRaises(ValueError):
            create_wheel_session(-1, 10)


class TestSpinWheel(unittest.TestCase):
    """Test spin wheel functionality"""
    
    def setUp(self):
        """Setup test session"""
        self.session = create_wheel_session(1, 10, remove_after_spin=True)
    
    def test_spin_wheel(self):
        """Test quay wheel"""
        result = spin_wheel(self.session)
        self.assertIn(result, range(1, 11))
        self.assertEqual(self.session.get_remaining_count(), 9)
        self.assertEqual(self.session.last_spin, result)
        self.assertEqual(self.session.spin_count, 1)
    
    def test_spin_wheel_with_remove(self):
        """Test quay wheel với chế độ loại bỏ"""
        session = create_wheel_session(1, 5, remove_after_spin=True)
        results = []
        
        for _ in range(5):
            result = spin_wheel(session)
            results.append(result)
            self.assertNotIn(result, session.available_numbers)
        
        # Sau 5 lần quay, danh sách phải rỗng
        self.assertTrue(session.is_empty())
        self.assertEqual(len(results), 5)
        self.assertEqual(len(set(results)), 5)  # Tất cả số phải khác nhau
    
    def test_spin_wheel_without_remove(self):
        """Test quay wheel không loại bỏ"""
        session = create_wheel_session(1, 5, remove_after_spin=False)
        
        for _ in range(10):
            spin_wheel(session)
        
        # Danh sách vẫn đầy đủ
        self.assertEqual(session.get_remaining_count(), 5)
    
    def test_spin_wheel_empty_list(self):
        """Test quay wheel khi danh sách rỗng"""
        session = create_wheel_session(1, 1, remove_after_spin=True)
        spin_wheel(session)
        
        with self.assertRaises(ValueError):
            spin_wheel(session)


class TestResetSession(unittest.TestCase):
    """Test reset session functionality"""
    
    def test_reset_session(self):
        """Test reset session"""
        session = create_wheel_session(1, 10, remove_after_spin=True)
        
        # Quay một vài lần
        spin_wheel(session)
        spin_wheel(session)
        
        self.assertLess(session.get_remaining_count(), 10)
        
        # Reset
        reset_session(session)
        
        self.assertEqual(session.get_remaining_count(), 10)
        self.assertEqual(len(session.removed_numbers), 0)
        self.assertIsNone(session.last_spin)
        self.assertEqual(session.spin_count, 0)


class TestSetRemoveMode(unittest.TestCase):
    """Test set remove mode functionality"""
    
    def test_set_remove_mode(self):
        """Test thay đổi chế độ loại bỏ"""
        session = create_wheel_session(1, 10, remove_after_spin=True)
        self.assertTrue(session.remove_after_spin)
        
        set_remove_mode(session, False)
        self.assertFalse(session.remove_after_spin)
        
        set_remove_mode(session, True)
        self.assertTrue(session.remove_after_spin)


class TestGetSessionStatus(unittest.TestCase):
    """Test get session status"""
    
    def test_get_session_status(self):
        """Test lấy thông tin trạng thái"""
        session = create_wheel_session(1, 10, remove_after_spin=True)
        status = get_session_status(session)
        
        self.assertEqual(status['range'], "1 -> 10")
        self.assertEqual(status['total_numbers'], 10)
        self.assertEqual(status['remaining_count'], 10)
        self.assertEqual(status['removed_count'], 0)
        self.assertTrue(status['remove_after_spin'])
        self.assertIsNone(status['last_spin'])
        self.assertEqual(status['spin_count'], 0)
        self.assertFalse(status['is_empty'])


if __name__ == '__main__':
    unittest.main()
