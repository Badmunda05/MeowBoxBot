"""
MeowBox File Uploader Bot
Author : @BadmundaXD
Updated: Private-only uploads | Group commands with membership check
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
BOT_USERNAME     = os.environ.get("BOT_USERNAME", "")
DEVELOPER_ID     = int(os.environ.get("DEVELOPER_ID", "0"))
WELCOME_IMAGE    = os.environ.get("WELCOME_IMAGE", "https://files.tgvibes.online/WZPorLVw.png")
FORCE_SUB        = os.environ.get("FORCE_SUB", "false").lower() == "true"
MAX_FILE_MB      = int(os.environ.get("MAX_FILE_MB", 512))
SOURCE_CODE_URL  = "https://github.com/Badmunda05/MeowBoxBot/fork"

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def clean_channel(username: str) -> str:
    return username.lstrip("@")


def is_private(update: Update) -> bool:
    return update.effective_chat.type == "private"


def is_group(update: Update) -> bool:
    return update.effective_chat.type in ("group", "supergroup")


async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME or not FORCE_SUB:
        return True
    try:
        member = await context.bot.get_chat_member(
            f"@{clean_channel(CHANNEL_USERNAME)}", user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning(f"Subscription check failed: {e}")
        return True


async def check_group_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME:
        return True
    try:
        member = await context.bot.get_chat_member(
            f"@{clean_channel(CHANNEL_USERNAME)}", user_id
        )
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        log.warning(f"Group membership check failed: {e}")
        return True


def fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:
        return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


# ─── Private Chat Handlers ────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    user = update.effective_user

    buttons = []
    if DEVELOPER_ID:
        buttons.append([InlineKeyboardButton("Developer 👨‍💻", url="https://t.me/BadMundaXD")])
    if CHANNEL_USERNAME:
        buttons.append([InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{clean_channel(CHANNEL_USERNAME)}")])
    buttons.append([InlineKeyboardButton("Source Code ↗️", url=SOURCE_CODE_URL)])

    caption = (
        f"<b>👋 Welcome, {user.first_name}!</b>\n\n"
        f"<b>🐱 MeowBox File Uploader</b>\n\n"
        f"Send me any <b>file, photo, video, audio, voice, or sticker</b> "
        f"and I'll upload it to <b>MeowBox</b> and give you a permanent direct link!\n\n"
        f"<b>✅ Supported:</b>\n"
        f"📷 Photos  •  🎬 Videos  •  📄 Documents\n"
        f"🎵 Audio  •  🎤 Voice  •  📹 Video Notes  •  🎭 Stickers\n\n"
        f"<b>📦 Max size:</b> {MAX_FILE_MB} MB\n\n"
        f"<i>Just send the file below 👇</i>"
    )

    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None

    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=WELCOME_IMAGE,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return
    except Exception as e:
        log.warning(f"send_photo failed: {e}")

    try:
        await update.message.reply_photo(
            photo=WELCOME_IMAGE,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        return
    except Exception as e:
        log.warning(f"reply_photo failed: {e}")

    try:
        await update.message.reply_text(
            caption,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    except Exception as e:
        log.error(f"Text fallback failed: {e}")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    await update.message.reply_text(
        "<b>📖 How to use MeowBox Bot</b>\n\n"
        "1️⃣ Send any photo, file, video, audio, voice, video note, or sticker\n"
        "2️⃣ Bot uploads it to MeowBox\n"
        "3️⃣ You get a permanent direct link!\n\n"
        "<b>Private Chat Commands:</b>\n"
        "/start — Welcome message\n"
        "/help — This message\n\n"
        f"<b>📦 Max file size:</b> {MAX_FILE_MB} MB\n"
        "<b>All formats accepted</b> (photos, videos, audio, stickers, voice, video notes)",
        parse_mode="HTML"
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming files — PRIVATE CHAT ONLY.
    Files sent in groups are completely ignored, no reply at all.
    """
    # Group messages — silently ignore, no reply
    if not is_private(update):
        return

    msg = update.message
    user_id = update.effective_user.id

    if not await check_subscription(user_id, context):
        ch = clean_channel(CHANNEL_USERNAME)
        await msg.reply_text(
            f"<b>🔒 Join Required</b>\n\n"
            f"Please join our channel first, then send the file again.\n\n"
            f"<a href='https://t.me/{ch}'>👉 Join @{ch}</a>",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    file_obj = None
    filename = "upload"
    file_type_label = "File"

    if msg.photo:
        file_obj = msg.photo[-1]
        filename = f"photo_{file_obj.file_id[-8:]}.jpg"
        file_type_label = "📷 Photo"
    elif msg.document:
        file_obj = msg.document
        filename = msg.document.file_name or f"file_{msg.document.file_id[-8:]}"
        file_type_label = "📄 Document"
    elif msg.video:
        file_obj = msg.video
        filename = f"video_{msg.video.file_id[-8:]}.mp4"
        file_type_label = "🎬 Video"
    elif msg.audio:
        file_obj = msg.audio
        filename = msg.audio.file_name or f"audio_{msg.audio.file_id[-8:]}.mp3"
        file_type_label = "🎵 Audio"
    elif msg.voice:
        file_obj = msg.voice
        filename = f"voice_{msg.voice.file_id[-8:]}.ogg"
        file_type_label = "🎤 Voice"
    elif msg.video_note:
        file_obj = msg.video_note
        filename = f"videonote_{msg.video_note.file_id[-8:]}.mp4"
        file_type_label = "📹 Video Note"
    elif msg.sticker:
        file_obj = msg.sticker
        ext = ".tgs" if msg.sticker.is_animated else ".webm" if msg.sticker.is_video else ".webp"
        filename = f"sticker_{msg.sticker.file_id[-8:]}{ext}"
        file_type_label = "🎭 Sticker"
    else:
        await msg.reply_text("❌ Unsupported file type.")
        return

    file_size = getattr(file_obj, "file_size", 0) or 0
    if file_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(
            f"❌ <b>File too large!</b>\n"
            f"Your file: <b>{fmt_size(file_size)}</b>\n"
            f"Max allowed: <b>{MAX_FILE_MB} MB</b>",
            parse_mode="HTML"
        )
        return

    status_msg = await msg.reply_text("⏳ <b>Uploading to MeowBox...</b>", parse_mode="HTML")

    path = None
    try:
        tg_file = await context.bot.get_file(file_obj.file_id)
        path = await tg_file.download_to_drive(filename)

        results = await upload_async(str(path))
        url = results[0]

        result_text = (
            f"<b>✅ Uploaded to MeowBox!</b>\n\n"
            f"<b>Type:</b> {file_type_label}\n"
            f"<b>📎 File:</b> <code>{filename}</code>\n"
            f"<b>📦 Size:</b> {fmt_size(file_size)}\n"
            f"<b>🔗 Link:</b> <code>{url}</code>\n\n"
            f"<i>♾️ Permanent — never expires</i>"
        )

        try:
            buttons = [
                [InlineKeyboardButton("📋 Copy Link", copy_text=url)],
                [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={url}")],
            ]
            await status_msg.edit_text(result_text, parse_mode="HTML",
                                        reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            buttons = [
                [InlineKeyboardButton("🔗 Open Link", url=url)],
                [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={url}")],
            ]
            await status_msg.edit_text(result_text, parse_mode="HTML",
                                        reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        log.error(f"Upload error: {e}")
        await status_msg.edit_text(f"❌ Upload failed: {e}")

    finally:
        if path and os.path.exists(str(path)):
            os.remove(str(path))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    await update.message.reply_text(
        "📸 Send me a <b>file, photo, video, audio, voice, video note, or sticker</b> "
        "to upload on MeowBox!\n\nUse /help for more info.",
        parse_mode="HTML"
    )


# ─── Group Commands ───────────────────────────────────────────────────────────

async def group_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tgm /tm /meowbox — works in groups only.
    Checks channel membership, then sends bot link.
    """
    msg = update.message
    if msg is None:
        return

    if not is_group(update):
        await msg.reply_text(
            "ℹ️ This command only works inside a <b>group</b>.",
            parse_mode="HTML"
        )
        return

    user = update.effective_user
    user_id = user.id

    has_joined = await check_group_membership(user_id, context)

    if not has_joined:
        ch = clean_channel(CHANNEL_USERNAME)
        await msg.reply_text(
            f"<b>👋 Hey {user.first_name}!</b>\n\n"
            f"Please <b>join our channel first</b>, then you can use this bot!\n\n"
            f"<a href='https://t.me/{ch}'>👉 Join @{ch}</a>\n\n"
            f"After joining, use this command again 👆",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # User has joined — send bot link
    bot_user = clean_channel(BOT_USERNAME) if BOT_USERNAME else None
    bot_link = f"https://t.me/{bot_user}" if bot_user else None

    buttons = []
    if bot_link:
        buttons.append([InlineKeyboardButton("📩 Open MeowBox Bot", url=bot_link)])
    if CHANNEL_USERNAME:
        buttons.append([InlineKeyboardButton("📢 Our Channel",
                        url=f"https://t.me/{clean_channel(CHANNEL_USERNAME)}")])

    await msg.reply_text(
        f"<b>👋 Hey {user.first_name}!</b>\n\n"
        f"<b>🐱 MeowBox File Uploader</b>\n\n"
        f"Send any file and get a permanent direct link!\n\n"
        f"<b>✅ Supported:</b>\n"
        f"📷 Photos  •  🎬 Videos  •  📄 Documents\n"
        f"🎵 Audio  •  🎤 Voice  •  📹 Video Notes  •  🎭 Stickers\n\n"
        f"<b>📦 Max size:</b> {MAX_FILE_MB} MB\n\n"
        f"<i>Click the button below to open a private chat and send your file 👇</i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("🚀 Starting MeowBox Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Private chat
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    # Group commands
    app.add_handler(CommandHandler("tgm", group_bot_command))
    app.add_handler(CommandHandler("tm", group_bot_command))
    app.add_handler(CommandHandler("meowbox", group_bot_command))

    # File handler — private chat only (group files are ignored at filter level)
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & (
            filters.PHOTO
            | filters.Document.ALL
            | filters.VIDEO
            | filters.AUDIO
            | filters.VOICE
            | filters.VIDEO_NOTE
            | filters.Sticker.ALL
        ),
        handle_file
    ))

    # Text handler — private only
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_text
    ))

    log.info("✅ Bot running!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
    
