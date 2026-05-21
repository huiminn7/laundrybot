@echo off
    echo 🚀 Booting up the KK12 Laundry System...

    echo Starting Streamlit Dashboard...
    start cmd /k "streamlit run app.py"

    echo Starting Telegram Bot...
    start cmd /k "python laundry_bot.py"

    echo Starting Reminder Engine...
    start cmd /k "python reminder_loop.py"

    echo ✅ All systems are running in the background!
    ```
  
  
    Now, whenever you want to test the app, just double-click `start_laundry.bat` in your file explorer. It will instantly pop open three terminal windows and start everything for you automatically!