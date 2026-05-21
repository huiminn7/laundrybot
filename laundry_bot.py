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
    # Arranging 6 washers into a neat 2-column grid
    keyboard = [
        [InlineKeyboardButton("📊 View KK12 Live Status", callback_data="status")],
        [
            InlineKeyboardButton("🔒 W1", callback_data="lock_1"), 
            InlineKeyboardButton("🔒 W2", callback_data="lock_2"),
            InlineKeyboardButton("🔒 W3", callback_data="lock_3")
        ],
        [
            InlineKeyboardButton("🔒 W4", callback_data="lock_4"), 
            InlineKeyboardButton("🔒 W5", callback_data="lock_5"),
            InlineKeyboardButton("🔒 W6", callback_data="lock_6")
        ],
        [InlineKeyboardButton("🔓 Unlock My Machine", callback_data="unlock")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🏢 *KK12 Laundry Tracker*\n\nSelamat Datang! Use the buttons below to check or lock a washing machine:",
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

# ========== BUTTON HANDLER ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        await status(update, context)
    elif query.data.startswith("lock_"):
        # Extracts the number from "lock_1", "lock_2", etc.
        washer_num = query.data.split("_")[1] 
        machine_name = f"Washer_{washer_num}"
        await lock_machine(update, context, machine_name)
    elif query.data == "unlock":
        await unlock(update, context)

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