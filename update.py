import sys
import json
from datetime import datetime, timedelta
from supabase import create_client

# Import credentials
try:
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    print("Error: supabase_config.py not found")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get arguments
machine = sys.argv[1]  # "Washer_1" or "Washer_2"
action = sys.argv[2]   # "lock" or "free"
user_id = sys.argv[3] if len(sys.argv) > 3 else ""
username = sys.argv[4] if len(sys.argv) > 4 else ""

if action == "lock":
    end_time = datetime.now() + timedelta(minutes=45)
    
    # Update machine status
    supabase.table('machines').update({
        'status': 'busy',
        'user_id': user_id,
        'username': username,
        'end_time': end_time.isoformat(),
        'updated_at': datetime.now().isoformat()
    }).eq('name', machine).execute()
    
    # Create reminder
    supabase.table('reminders').insert({
        'machine_id': 1 if machine == 'Washer_1' else 2,
        'user_id': user_id,
        'username': username,
        'chat_id': int(user_id),  # Telegram user ID as chat_id
        'end_time': end_time.isoformat()
    }).execute()
    
    print(f"✅ {machine} locked until {end_time.strftime('%H:%M')}")

elif action == "free":
    supabase.table('machines').update({
        'status': 'available',
        'user_id': '',
        'username': '',
        'end_time': None,
        'updated_at': datetime.now().isoformat()
    }).eq('name', machine).execute()
    
    print(f"✅ {machine} is now available")