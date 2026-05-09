# -*- coding: utf-8 -*-
"""
MeowBox File Uploader Bot
Author : @BadmundaXD
"""

import os
import logging
from dotenv import load_dotenv
from meowbox import upload_async
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.environ["BOT_TOKEN"]
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME", "")
DEVELOPER_ID     = int(os.environ.get("DEVELOPER_ID", "0"))
WELCOME_IMAGE    = os.environ.get("WELCOME_IMAGE", "https://files.tgvibes.online/WZPorLVw.png")
FORCE_SUB        = os.environ.get("FORCE_SUB", "false").lower() == "true"
MAX_FILE_MB      = int(os.environ.get("MAX_FILE_MB", 512))

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_channel(username: str) -> str:
    return username.lstrip("@")

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME or not FORCE_SUB:
        return True
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning(f"Subscription check failed: {e}")
        return True

def fmt_size(b: int) -> str:
    if b < 1024: return f"{b} B"
    if b < 1024**2: return f"{b/1024:.1f} KB"
    if b < 1024**3: return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"

# ─── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    buttons = []
    if DEVELOPER_ID:
        buttons.append([InlineKeyboardButton("Developer 👨‍💻", url=f"tg://user?id={DEVELOPER_ID}")])
    if CHANNEL_USERNAME:
        buttons.append([InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{clean_channel(CHANNEL_USERNAME)}")])

    caption = (
        f"<b>👋 Welcome, {user.first_name}!</b>\n\n"
        f"<b>🐱 MeowBox File Uploader</b>\n\n"
        f"Send me any file or photo and I'll upload it to <b>MeowBox</b> and give you a direct link!\n\n"
        f"<b>Supported:</b> Photos, Videos, Documents, Audio — up to <b>{MAX_FILE_MB} MB</b>\n\n"
        f"<i>Just send the file below 👇</i>"
    )

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=WELCOME_IMAGE,
            caption=caption,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
        )
    except Exception:
        await update.message.reply_text(
            caption, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
        )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📖 How to use MeowBox Bot</b>\n\n"
        "1️⃣ Send any photo, file, video, or audio\n"
        "2️⃣ Bot uploads it to MeowBox\n"
        "3️⃣ You get a permanent direct link!\n\n"
        "<b>Commands:</b>\n"
        "/start — Welcome message\n"
        "/help — This message\n\n"
        f"<b>Max file size:</b> {MAX_FILE_MB} MB\n"
        "<b>All formats accepted</b> (except .exe, .php etc.)",
        parse_mode="HTML"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = update.effective_user.id

    # Force subscribe check
    if not await check_subscription(user_id, context):
        ch = clean_channel(CHANNEL_USERNAME)
        await msg.reply_text(
            f"<b>🔒 Join Required</b>\n\n"
            f"Please join our channel first!\n\n"
            f"<a href='https://t.me/{ch}'>👉 Join @{ch}</a>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # Determine file object
    file_obj = None
    filename = "upload"

    if msg.photo:
        file_obj = msg.photo[-1]
        filename = f"photo_{file_obj.file_id[-8:]}.jpg"
    elif msg.document:
        file_obj = msg.document
        filename = msg.document.file_name or f"file_{msg.document.file_id[-8:]}"
    elif msg.video:
        file_obj = msg.video
        filename = f"video_{msg.video.file_id[-8:]}.mp4"
    elif msg.audio:
        file_obj = msg.audio
        filename = msg.audio.file_name or f"audio_{msg.audio.file_id[-8:]}.mp3"
    elif msg.voice:
        file_obj = msg.voice
        filename = f"voice_{msg.voice.file_id[-8:]}.ogg"
    elif msg.video_note:
        file_obj = msg.video_note
        filename = f"videonote_{msg.video_note.file_id[-8:]}.mp4"
    elif msg.sticker:
        file_obj = msg.sticker
        filename = f"sticker_{msg.sticker.file_id[-8:]}.webp"
    else:
        await msg.reply_text("❌ Unsupported file type.")
        return

    # Size check
    file_size = getattr(file_obj, "file_size", 0) or 0
    if file_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(
            f"❌ File too large!\n"
            f"Your file: <b>{fmt_size(file_size)}</b>\n"
            f"Max allowed: <b>{MAX_FILE_MB} MB</b>",
            parse_mode="HTML"
        )
        return

    status_msg = await msg.reply_text("⏳ <b>Uploading to MeowBox...</b>", parse_mode="HTML")

    path = None
    try:
        # Download file from Telegram
        tg_file = await context.bot.get_file(file_obj.file_id)
        path = await tg_file.download_to_drive(filename)

        # Upload using meowbox library
        results = await upload_async(str(path))
        url = results[0]["url"]

        buttons = [
            [InlineKeyboardButton("🔗 Open Link", url=url)],
            [InlineKeyboardButton("📤 Share", url=f"tg://msg_url?url={url}")],
        ]

        await status_msg.edit_text(
            f"<b>✅ Uploaded on MeowBox!</b>\n\n"
            f"<b>📎 File:</b> <code>{filename}</code>\n"
            f"<b>📦 Size:</b> {fmt_size(file_size)}\n"
            f"<b>🔗 Link:</b> <code>{url}</code>\n\n"
            f"<i>♾️ Permanent — never expires</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        log.error(f"Upload error: {e}")
        await status_msg.edit_text(f"❌ Upload failed: {e}")

    finally:
        if path and os.path.exists(str(path)):
            os.remove(str(path))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Send me a <b>file, photo, video or audio</b> to upload on MeowBox!\n\nUse /help for more info.",
        parse_mode="HTML"
    )

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("🚀 Starting MeowBox Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.Document.ALL | filters.VIDEO |
        filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE | filters.Sticker.ALL,
        handle_file
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("✅ Bot running!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
