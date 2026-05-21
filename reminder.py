import asyncio
from datetime import datetime
from telegram import Bot
from supabase import create_client

# ========== CONFIG ==========
try:
    from config import TOKEN, SUPABASE_URL, SUPABASE_KEY
except ImportError:
    print("❌ Error: config.py not found.")
    exit(1)

bot = Bot(token=TOKEN)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def check_reminders():
    print("⏳ Laundry Reminder Engine is online and watching the clock...")
    
    while True:
        try:
            now = datetime.now().isoformat()
            
            # Find alarms that are finished
            response = supabase.table('reminders').select('*').lte('end_time', now).execute()
            expired_reminders = response.data
            
            for reminder in expired_reminders:
                chat_id = reminder['chat_id']
                machine_num = reminder.get('machine_id', 'Unknown')
                username = reminder.get('username', '')
                
                # ====== 1. EARLY WARNING NOTIFICATION ======
                if username.startswith('EARLY_'):
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"⚠️ *HEADS UP!*\n\nWasher {machine_num} will be finished in 5 minutes! ⏳\n\nPlease get ready to collect your clothes.",
                            parse_mode="Markdown"
                        )
                        print(f"✅ Sent early warning to user {chat_id}")
                    except Exception:
                        pass
                        
                # ====== 2. WAITLIST NOTIFICATION ======
                elif username.startswith('WAITLIST_'):
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🏃‍♂️ *QUICK!* Washer {machine_num} is finally FREE!\n\nOpen the menu to lock it before someone else does.",
                            parse_mode="Markdown"
                        )
                        print(f"✅ Waitlist pinged for user {chat_id}")
                    except Exception:
                        pass
                
                # ====== 3. OWNER NOTIFICATION & FINAL UNLOCK ======
                else:
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🔔 *BEEP BEEP!*\n\nYour laundry in Washer {machine_num} is finished!\n\nThe machine has been auto-unlocked for the next user.",
                            parse_mode="Markdown"
                        )
                        print(f"✅ Notified owner {chat_id}")
                    except Exception:
                        pass
                    
                    try:
                        supabase.table('machines').update({
                            'status': 'available',
                            'user_id': '',
                            'username': '',
                            'end_time': None
                        }).eq('user_id', str(chat_id)).execute()
                    except Exception:
                        pass
                
                # Clean up the reminder from the database so it doesn't spam
                supabase.table('reminders').delete().eq('id', reminder['id']).execute()
        except Exception as e:
            print(f"⚠️ Warning in background loop: {e}")
            
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(check_reminders())