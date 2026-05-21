import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from supabase import create_client

# ========== CONFIG ==========
try:
    from config import TOKEN, SUPABASE_URL, SUPABASE_KEY
    print("✅ Config loaded successfully")
except ImportError:
    print("❌ Error: config.py not found. Please create it with TOKEN, SUPABASE_URL, and SUPABASE_KEY")
    exit(1)

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== COMMAND: /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏢 KK12 (12th College)", callback_data="select_KK12")],
        [InlineKeyboardButton("🏢 KK10 (10th College)", callback_data="select_KK10")],
        [InlineKeyboardButton("🏢 KK1 (1st College)", callback_data="select_KK1")],
        [InlineKeyboardButton("🌐 View Live Web Dashboard", url="https://laundrytracker.streamlit.app/")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏢 *UM Centralized Laundry Tracker*\n\nSila pilih Kolej Kediaman anda:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========== SHOW LAUNDRY OPTIONS FOR SELECTED KK ==========
async def show_kk_menu(update, context, kk_name, alert_text=None):
    query = update.callback_query
    
    response = supabase.table('machines').select('*').eq('kk_name', kk_name).execute()
    machines = response.data
    
    text = f"🏢 *{kk_name} Laundry Management*\n"
    text += "--------------------------------------\n"
    if alert_text:
        text += f"{alert_text}\n"
        text += "--------------------------------------\n"
        
    text += "📋 *Current Machine Availability:*\n"
    if not machines:
        text += "❌ No machines registered for this college yet.\n"
    else:
        sorted_machines = sorted(machines, key=lambda x: x['name'])
        for info in sorted_machines:
            status_icon = "🟢" if info["status"] == "available" else "🔴"
            machine_title = info["name"].replace('_', ' ')
            text += f"{status_icon} *{machine_title}*: {info['status'].title()}\n"
            if info["status"] == "busy" and info.get("username"):
                text += f"      👤 @{info['username']}\n"
                
    text += "--------------------------------------\n"
    text += "Tap an available machine to lock, or tap a busy one to join the waitlist:"

    keyboard = [
        [InlineKeyboardButton("🔄 Refresh Live Status", callback_data=f"status_kk:{kk_name}")]
    ]
    
    if machines:
        row = []
        for m in sorted(machines, key=lambda x: x['name']):
            # === NEW: Put the countdown directly ON the button! ===
            if m['status'] == 'busy':
                time_label = ""
                if m.get("end_time"):
                    try:
                        end_time = datetime.fromisoformat(m["end_time"].replace('Z', '+00:00')).replace(tzinfo=None)
                        remaining = int((end_time - datetime.now()).total_seconds() / 60)
                        if remaining > 0:
                            time_label = f" ({remaining}m left)"
                        else:
                            time_label = " (Done)"
                    except Exception:
                        pass
                status_label = f"🔴 {m['name'].replace('_', ' ')}{time_label}"
            else:
                status_label = f"🟢 {m['name'].replace('_', ' ')}"
            # =======================================================
            
            button = InlineKeyboardButton(status_label, callback_data=f"lock:{m['name']}:{kk_name}")
            row.append(button)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
    keyboard.append([InlineKeyboardButton("🔓 Unlock My Machine", callback_data=f"unlock_prompt:{kk_name}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to College List", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ========== BUTTON HANDLER ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("🏢 KK12", callback_data="select_KK12")],
            [InlineKeyboardButton("🏢 KK10", callback_data="select_KK10")],
            [InlineKeyboardButton("🏢 KK1", callback_data="select_KK1")],
        ]
        await query.edit_message_text("🏢 *UM Centralized Laundry Tracker*\n\nSila pilih Kolej Kediaman anda:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data.startswith("select_"):
        kk_name = data.split("_")[1]
        await show_kk_menu(update, context, kk_name)
        
    elif data.startswith("status_kk:"):
        kk_name = data.split(":")[1]
        await show_kk_menu(update, context, kk_name, alert_text="🔄 Status Board Refreshed!")
        
    elif data.startswith("lock:"):
        _, machine, kk_name = data.split(":")
        user = update.effective_user
        user_id = str(user.id)
        username = user.first_name if user.first_name else (user.username or "Student")
        
        # Verify status directly
        res = supabase.table('machines').select('*').eq('name', machine).eq('kk_name', kk_name).execute()
        if res.data and res.data[0]['status'] == 'busy':
            machine_data = res.data[0]
            
            if machine_data.get('user_id') == user_id:
                alert = f"❌ You are already using {machine.replace('_', ' ')}!"
                await show_kk_menu(update, context, kk_name, alert_text=alert)
                return
                
            # ====== NEW WAITLIST FEATURE ======
            try:
                washer_number = int(machine.split('_')[1])
            except:
                washer_number = 1
                
            # Add this user to the waitlist for this machine
            supabase.table('reminders').insert({
                'machine_id': washer_number,
                'user_id': user_id,
                'username': f"WAITLIST_{username}",
                'chat_id': int(user_id),
                'end_time': machine_data.get('end_time', datetime.now().isoformat())
            }).execute()
            
            alert = f"👀 *{machine.replace('_', ' ')}* is busy! I've added you to the waitlist and will ping you when it's free."
            await show_kk_menu(update, context, kk_name, alert_text=alert)
            return
            # ==================================
            
        # ====== THE DOUBLE-ALARM SETUP ======
        # (Change back to minutes=45 and minutes=5 for the real presentation!)
        end_time = datetime.now() + timedelta(minutes=3) # Let's test with a 3 min wash
        early_time = end_time - timedelta(minutes=1)     # Send warning 1 min before it finishes
        
        # 1. Lock machine
        supabase.table('machines').update({
            'status': 'busy',
            'user_id': user_id,
            'username': username,
            'end_time': end_time.isoformat(),
            'updated_at': datetime.now().isoformat()
        }).eq('name', machine).eq('kk_name', kk_name).execute()
        
        try:
            washer_number = int(machine.split('_')[1])
        except:
            washer_number = 1
            
        # 2. Add the EARLY WARNING reminder
        supabase.table('reminders').insert({
            'machine_id': washer_number,
            'user_id': user_id,
            'username': f"EARLY_{username}", # Notice the EARLY tag!
            'chat_id': int(user_id),
            'end_time': early_time.isoformat()
        }).execute()

        # 3. Add the FINAL UNLOCK reminder
        supabase.table('reminders').insert({
            'machine_id': washer_number,
            'user_id': user_id,
            'username': username,
            'chat_id': int(user_id),
            'end_time': end_time.isoformat()
        }).execute()
        # ====================================
        
        alert = f"✅ *{machine.replace('_', ' ')} LOCKED!* Reminders set."
        await show_kk_menu(update, context, kk_name, alert_text=alert)
        
    elif data.startswith("unlock_prompt:"):
        kk_name = data.split(":")[1]
        user_id = str(update.effective_user.id)
        
        res = supabase.table('machines').select('name').eq('user_id', user_id).eq('status', 'busy').eq('kk_name', kk_name).execute()
        if not res.data:
            alert = f"❌ You don't have any active locked machines inside {kk_name}."
            await show_kk_menu(update, context, kk_name, alert_text=alert)
            return
            
        target_machine = res.data[0]['name']
        try:
            washer_number = int(target_machine.split('_')[1])
        except:
            washer_number = 1
        
        # Unlock machine
        supabase.table('machines').update({
            'status': 'available',
            'user_id': '',
            'username': '',
            'end_time': None,
            'updated_at': datetime.now().isoformat()
        }).eq('name', target_machine).eq('kk_name', kk_name).execute()
        
        # ====== FAST-FORWARD WAITLIST ======
        # Cancel the owner's beep
        supabase.table('reminders').delete().eq('user_id', user_id).eq('machine_id', washer_number).execute()
        # Trigger the waitlist notifications immediately!
        now_iso = datetime.now().isoformat()
        supabase.table('reminders').update({'end_time': now_iso}).eq('machine_id', washer_number).execute()
        # ===================================
        
        alert = f"🔓 *{target_machine.replace('_', ' ')} has been unlocked!*"
        await show_kk_menu(update, context, kk_name, alert_text=alert)

# ========== MAIN ==========
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Laundry Bot is running...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())