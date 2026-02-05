"""
Script để chạy bot từ thư mục gốc
"""
import sys
from pathlib import Path

# Đảm bảo thư mục gốc trong PYTHONPATH
root_dir = Path(__file__).parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Import và chạy main
from src.main import main

if __name__ == "__main__":
    main()
