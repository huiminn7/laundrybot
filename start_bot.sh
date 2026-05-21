#!/bin/bash
# Use Render's official port variable for the dummy web server
python -m http.server $PORT &

# The -u flag forces Python to print logs to Render immediately
python -u reminder.py & 
python -u laundry_bot.py