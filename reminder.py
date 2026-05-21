import asyncio
from datetime import datetime, timezone
from telegram import Bot
from supabase import create_client

# ========== CONFIG ==========
try:
    from config import TOKEN, SUPABASE_URL, SUPABASE_KEY
except ImportError:
    print("❌ Error: config.py not found.")
    exit(1)

# Initialize Supabase and Telegram Bot
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=TOKEN)

async def check_reminders():
    print("⏳ Starting the background reminder loop...")
    
    while True:
        try:
            # 1. Get current time in UTC to match Supabase's isoformat
            now = datetime.now(timezone.utc)
            
            # 2. Fetch all reminders that have expired AND haven't been sent yet
            # (Assuming you add a 'sent' boolean column to your reminders table, defaulting to FALSE)
            response = supabase.table('reminders').select('*').eq('sent', False).execute()
            
            for reminder in response.data:
                # Convert Supabase string time back to a Python datetime object
                end_time_str = reminder['end_time']
                
                # Note: If your end_time in Supabase doesn't have a timezone, 
                # you might need to adjust this parsing logic.
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                
                # 3. If the current time has passed the end_time
                if now >= end_time:
                    machine_name = "Washer 1" if reminder['machine_id'] == 1 else "Washer 2"
                    chat_id = reminder['chat_id']
                    
                    print(f"🔔 Sending reminder to {reminder['username']} for {machine_name}")
                    
                    # 4. Send the Telegram message
                    message = f"🚨 *BEEP BEEP!*\n\nWei @{reminder['username']}, your laundry in *{machine_name}* is done!\n\nPlease go collect it now so others can use the machine."
                    
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                    
                    # 5. Mark the reminder as sent in Supabase so we don't spam them
                    supabase.table('reminders').update({'sent': True}).eq('id', reminder['id']).execute()
                    
                    # 6. Optional: Auto-free the machine in the database 
                    # (You might want them to manually click "Unlock" instead to ensure they actually took their clothes out)
                    
        except Exception as e:
            print(f"⚠️ Error checking reminders: {e}")
            
        # Wait 60 seconds before checking the database again
        await asyncio.sleep(60)

if __name__ == "__main__":
    # Run the async loop
    asyncio.run(check_reminders())