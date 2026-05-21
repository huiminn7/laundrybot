import asyncio
import subprocess
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

# Initialize Supabase client for reading status
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== SEND MESSAGE HELPER ==========
async def send_message(update, context, text):
    """Helper to send message from either command or callback"""
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")

# ========== COMMAND: /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # First Step: User selects their specific college
    keyboard = [
        [InlineKeyboardButton("🏢 KK12 (12th College)", callback_data="select_KK12")],
        [InlineKeyboardButton("🏢 KK10 (10th College)", callback_data="select_KK10")],
        [InlineKeyboardButton("🏢 KK1 (1st College)", callback_data="select_KK1")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏢 *UM Centralized Laundry Tracker*\n\nSila pilih Kolej Kediaman anda:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========== COMMAND: /status ==========
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Fetch live data directly from Supabase
    response = supabase.table('machines').select('*').execute()
    db = {row['name']: row for row in response.data}
    
    text = "🧺 *Live Laundry Status*\n\n"
    for machine, info in db.items():
        status_icon = "🟢" if info["status"] == "available" else "🔴"
        text += f"{status_icon} *{machine.replace('_', ' ')}*: {info['status'].title()}\n"
        if info["status"] == "busy" and info.get("username"):
            text += f"   👤 Used by: @{info['username']}\n"
    
    await send_message(update, context, text)

# ========== LOCK MACHINE ==========
async def lock_machine(update: Update, context: ContextTypes.DEFAULT_TYPE, machine: str):
    user = update.effective_user
    user_id = str(user.id)
    username = user.first_name if user.first_name else user.username
    
    # Check current status in Supabase before locking
    response = supabase.table('machines').select('status').eq('name', machine).execute()
    
    if response.data and response.data[0]['status'] == 'busy':
        await send_message(update, context, f"❌ *{machine.replace('_', ' ')}* is already in use!")
        return
    
    # Let update.py handle the Supabase insertion and reminder creation
    subprocess.run(["python", "update.py", machine, "lock", user_id, username])
    
    await send_message(
        update, context,
        f"✅ *{machine.replace('_', ' ')} LOCKED!*\n\n"
        f"Your laundry will be done in 45 minutes.\n"
        f"I'll automatically notify you when it's finished!"
    )

# ========== UNLOCK MACHINE ==========
async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # Find which machine this user locked
    response = supabase.table('machines').select('name').eq('user_id', user_id).eq('status', 'busy').execute()
    
    if not response.data:
        await send_message(update, context, "❌ You don't have any locked machines right now.")
        return
    
    found_machine = response.data[0]['name']
    
    # Let update.py handle the database reset
    subprocess.run(["python", "update.py", found_machine, "free"])
    
    await send_message(update, context, f"✅ *{found_machine.replace('_', ' ')} UNLOCKED!* Thank you for clearing the machine.")

# ========== SHOW LAUNDRY OPTIONS FOR SELECTED KK ==========
async def show_kk_menu(update, context, kk_name):
    # Fetch live data specifically for this KK
    response = supabase.table('machines').select('*').eq('kk_name', kk_name).execute()
    machines = response.data
    
    if not machines:
        await send_message(update, context, f"❌ No machines registered for {kk_name} yet.")
        return

    # 1. Put the Status Button right at the top of the KK menu!
    keyboard = [
        [InlineKeyboardButton(f"📊 View {kk_name} Live Status", callback_data=f"status_kk:{kk_name}")]
    ]
    
    # 2. Build the dynamic washer buttons (2 items per row)
    row = []
    for m in sorted(machines, key=lambda x: x['name']):
        status_label = "🔴" if m['status'] == 'busy' else "🔒"
        button = InlineKeyboardButton(f"{status_label} {m['name'].replace('_', ' ')}", callback_data=f"lock:{m['name']}:{kk_name}")
        row.append(button)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    # 3. Append navigation buttons at the bottom
    keyboard.append([InlineKeyboardButton("🔓 Unlock My Machine", callback_data=f"unlock_prompt:{kk_name}")])
    keyboard.append([InlineKeyboardButton("⬅️ Back to College List", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🏢 *{kk_name} Laundry Management*\n\nChoose an option below:"
    await send_message(update, context, text)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ========== BUTTON HANDLER (UPDATED FOR DYNAMIC SPLITTING) ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "back_to_main":
        # Returns user to selection layout
        keyboard = [
            [InlineKeyboardButton("🏢 KK12", callback_data="select_KK12")],
            [InlineKeyboardButton("🏢 KK10", callback_data="select_KK10")],
            [InlineKeyboardButton("🏢 KK1", callback_data="select_KK1")],
        ]
        await query.edit_message_text("🏢 *UM Centralized Laundry Tracker*\n\nSila pilih Kolej Kediaman anda:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data.startswith("select_"):
        kk_name = data.split("_")[1]
        await show_kk_menu(update, context, kk_name)
        
    # === ADDED: Handle the live status checking for a specific KK ===
    elif data.startswith("status_kk:"):
        kk_name = data.split(":")[1]
        
        # Fetch live data from Supabase filtered by the college
        response = supabase.table('machines').select('*').eq('kk_name', kk_name).execute()
        db = {row['name']: row for row in response.data}
        
        text = f"🧺 *Live Status for {kk_name}*\n\n"
        for machine, info in sorted(db.items()):
            status_icon = "🟢" if info["status"] == "available" else "🔴"
            text += f"{status_icon} *{machine.replace('_', ' ')}*: {info['status'].title()}\n"
            if info["status"] == "busy" and info.get("username"):
                text += f"   👤 Used by: @{info['username']}\n"
        
        # Send the status summary as a clear, separate message
        await query.message.reply_text(text, parse_mode="Markdown")
        # Keep the interaction menu available so the user doesn't have to re-trigger /start
        await show_kk_menu(update, context, kk_name)
        
    elif data.startswith("lock:"):
        _, machine, kk_name = data.split(":")
        user = update.effective_user
        user_id = str(user.id)
        username = user.first_name if user.first_name else user.username
        
        # Verify status directly
        res = supabase.table('machines').select('status').eq('name', machine).eq('kk_name', kk_name).execute()
        if res.data and res.data[0]['status'] == 'busy':
            await query.message.reply_text(f"❌ *{machine.replace('_', ' ')}* inside {kk_name} is already being used!")
            return
            
        subprocess.run(["python", "update.py", machine, "lock", user_id, username, kk_name])
        await query.message.reply_text(f"✅ *{machine.replace('_', ' ')} ({kk_name}) LOCKED!* Check your live dashboard updates.")
        await show_kk_menu(update, context, kk_name) # Refresh layout states
        
    elif data.startswith("unlock_prompt:"):
        kk_name = data.split(":")[1]
        user_id = str(update.effective_user.id)
        
        res = supabase.table('machines').select('name').eq('user_id', user_id).eq('status', 'busy').eq('kk_name', kk_name).execute()
        if not res.data:
            await query.message.reply_text(f"❌ You don't have any active locked machines inside {kk_name}.")
            return
            
        target_machine = res.data[0]['name']
        subprocess.run(["python", "update.py", target_machine, "free", "", "", kk_name])
        await query.message.reply_text(f"🔓 *{target_machine.replace('_', ' ')} ({kk_name}) has been unlocked!*")
        await show_kk_menu(update, context, kk_name)
        
# ========== MAIN ==========
async def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Laundry Bot is running...")
    print("✅ Ready! Send /start to the bot on Telegram")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())