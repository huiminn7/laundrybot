import sys
import json
from datetime import datetime, timedelta
from supabase import create_client

# Import credentials
try:
    from config import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    print("Error: config.py not found")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get arguments (Added kk_name as sys.argv[5])
machine = sys.argv[1]  # "Washer_1"
action = sys.argv[2]   # "lock" or "free"
user_id = sys.argv[3] if len(sys.argv) > 3 else ""
username = sys.argv[4] if len(sys.argv) > 4 else ""
kk_name = sys.argv[5] if len(sys.argv) > 5 else "KK12" # Defaults to KK12 if blank

if action == "lock":
    end_time = datetime.now() + timedelta(minutes=1)
    
    # Target specific machine inside the specific KK
    # Create reminder dynamically for any washer number (Washer_1 to Washer_6)
    try:
        washer_number = int(machine.split('_')[1]) # Extracts 1 from "Washer_1", 3 from "Washer_3" etc.
    except:
        washer_number = 1 # Fallback default
        
    supabase.table('reminders').insert({
        'machine_id': washer_number,
        'user_id': user_id,
        'username': username,
        'chat_id': int(user_id),  # Telegram user ID as chat_id
        'end_time': end_time.isoformat()
    }).execute()
    
    print(f"✅ {kk_name} {machine} locked until {end_time.strftime('%H:%M')}")

elif action == "free":
    supabase.table('machines').update({
        'status': 'available',
        'user_id': '',
        'username': '',
        'end_time': None,
        'updated_at': datetime.now().isoformat()
    }).eq('name', machine).eq('kk_name', kk_name).execute() # CRITICAL FIX
    
    print(f"✅ {kk_name} {machine} is now available")