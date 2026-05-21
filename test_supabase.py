from supabase import create_client
import os

# Your Supabase credentials
URL = "https://bblzmfxxdevafjyuigvw.supabase.co" # Replace with your URL
KEY = "sb_publishable_ntDVuI2D1W7ij-ZmBFoRsQ_8Z8O8Sll"  # Replace with your anon key

supabase = create_client(URL, KEY)

# Test connection
try:
    # Try to fetch data
    response = supabase.table('machines').select('*').execute()
    print("✅ Supabase connected successfully!")
    print(f"📊 Found {len(response.data)} machines")
    for machine in response.data:
        print(f"  - {machine['name']}: {machine['status']}")
except Exception as e:
    print(f"❌ Connection failed: {e}")