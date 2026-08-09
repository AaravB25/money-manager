import time
import webbrowser
import threading
from db import init_db
from app import app

def open_browser():
    time.sleep(1.2)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print("Initializing Money Manager Database...")
    init_db()
    print("Database ready.")
    
    print("Starting Money Manager Server at http://127.0.0.1:5000 ...")
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(host='127.0.0.1', port=5000, debug=False)
