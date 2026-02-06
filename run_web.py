import uvicorn
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("🚀 Starting Web Server for Loto Bot...")
    print("🌍 Open the following URL in your browser to test:")
    print("   http://localhost:8000")
    print("   (Or use your ngrok/tunnel URL for Telegram Web App)")
    
    # Run uvicorn programmatically
    # "src.web_server:app" refers to src/web_server.py -> app object
    uvicorn.run("src.web_server:app", host="0.0.0.0", port=8000, reload=True)
