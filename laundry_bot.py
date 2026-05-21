import json
import asyncio
import subprocess
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ========== CONFIG ==========
# Method 1: Try to import from config.py (local)
try:
    from config import TOKEN
    print("✅ Using token from config.py")
except ImportError:
    # Method 2: Use hardcoded token (for testing only)
    TOKEN = "8878015971:AAFcOM26YNS6k7MJ2G3q0zkRpS-3YHyI2aE"
    print("⚠️ Using hardcoded token")

# Supabase config
try:
    from supabase_config import SUPABASE_URL, SUPABASE_KEY
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase connected")
except ImportError:
    print("⚠️ Supabase config not found, using local JSON")
    supabase = None

# ========== DATABASE FUNCTIONS ==========
DB_FILE = "laundry_db.json"

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"Washer_1": {"status": "available"}, "Washer_2": {"status": "available"}}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

# ========== COMMAND: /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 View Status", callback_data="status")],
        [InlineKeyboardButton("🔒 Lock Washer 1", callback_data="lock_1")],
        [InlineKeyboardButton("🔒 Lock Washer 2", callback_data="lock_2")],
        [InlineKeyboardButton("🔓 Unlock", callback_data="unlock")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🧺 *Laundry Bot*\n\nUse the buttons below:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========== COMMAND: /status ==========
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    
    text = "🧺 *Laundry Status*\n\n"
    for machine, info in db.items():
        status_icon = "🟢" if info["status"] == "available" else "🔴"
        text += f"{status_icon} *{machine}*: {info['status']}\n"
    
    await update.message.reply_text(text, parse_mode="Markdown")

# ========== LOCK MACHINE ==========
async def lock_machine(update: Update, context: ContextTypes.DEFAULT_TYPE, machine: str):
    user = update.effective_user
    user_id = str(user.id)
    username = user.first_name
    
    db = load_db()
    
    if db[machine]["status"] == "busy":
        await update.message.reply_text(f"❌ {machine} is already in use!")
        return
    
    # Lock the machine
    db[machine]["status"] = "busy"
    db[machine]["user_id"] = user_id
    db[machine]["username"] = username
    save_db(db)
    
    # Call update.py
    subprocess.run(["python", "update.py", machine, "lock", user_id, username])
    
    await update.message.reply_text(
        f"✅ *{machine} LOCKED!*\n\n"
        f"Your laundry will be done in 45 minutes.\n"
        f"I'll notify you when it's finished!",
        parse_mode="Markdown"
    )

# ========== UNLOCK MACHINE ==========
async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    
    # Find which machine this user locked
    found = None
    for machine, info in db.items():
        if info.get("user_id") == user_id and info["status"] == "busy":
            found = machine
            break
    
    if not found:
        await update.message.reply_text("❌ You don't have any locked machines.")
        return
    
    # Unlock the machine
    db[found]["status"] = "available"
    db[found]["user_id"] = ""
    db[found]["username"] = ""
    save_db(db)
    
    # Call update.py
    subprocess.run(["python", "update.py", found, "free", "", ""])
    
    await update.message.reply_text(f"✅ *{found} UNLOCKED!*", parse_mode="Markdown")

# ========== BUTTON HANDLER ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "status":
        await status(update, context)
    elif query.data == "lock_1":
        await lock_machine(update, context, "Washer_1")
    elif query.data == "lock_2":
        await lock_machine(update, context, "Washer_2")
    elif query.data == "unlock":
        await unlock(update, context)

# ========== MAIN ==========
async def main():
    app = Application.builder().token(TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("🤖 Laundry Bot is running...")
    print("✅ Bot started! Send /start on Telegram")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())