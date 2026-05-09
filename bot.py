"""
MeowBox File Uploader Bot
Author : @BadmundaXD
Updated: /tgm reply in group → upload & give link IN GROUP | PM for direct files
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


async def upload_and_reply(msg_with_file, reply_target, context):
    """
    Core upload logic.
    msg_with_file = message containing the actual file
    reply_target  = message to reply to with the result
    """
    file_obj = None
    filename = "upload"
    file_type_label = "File"

    if msg_with_file.photo:
        file_obj = msg_with_file.photo[-1]
        filename = f"photo_{file_obj.file_id[-8:]}.jpg"
        file_type_label = "📷 Photo"
    elif msg_with_file.document:
        file_obj = msg_with_file.document
        filename = msg_with_file.document.file_name or f"file_{msg_with_file.document.file_id[-8:]}"
        file_type_label = "📄 Document"
    elif msg_with_file.video:
        file_obj = msg_with_file.video
        filename = f"video_{msg_with_file.video.file_id[-8:]}.mp4"
        file_type_label = "🎬 Video"
    elif msg_with_file.audio:
        file_obj = msg_with_file.audio
        filename = msg_with_file.audio.file_name or f"audio_{msg_with_file.audio.file_id[-8:]}.mp3"
        file_type_label = "🎵 Audio"
    elif msg_with_file.voice:
        file_obj = msg_with_file.voice
        filename = f"voice_{msg_with_file.voice.file_id[-8:]}.ogg"
        file_type_label = "🎤 Voice"
    elif msg_with_file.video_note:
        file_obj = msg_with_file.video_note
        filename = f"videonote_{msg_with_file.video_note.file_id[-8:]}.mp4"
        file_type_label = "📹 Video Note"
    elif msg_with_file.sticker:
        file_obj = msg_with_file.sticker
        ext = ".tgs" if msg_with_file.sticker.is_animated else ".webm" if msg_with_file.sticker.is_video else ".webp"
        filename = f"sticker_{msg_with_file.sticker.file_id[-8:]}{ext}"
        file_type_label = "🎭 Sticker"
    else:
        await reply_target.reply_text("❌ No supported file found in the replied message.")
        return

    file_size = getattr(file_obj, "file_size", 0) or 0
    if file_size > MAX_FILE_MB * 1024 * 1024:
        await reply_target.reply_text(
            f"❌ <b>File too large!</b>\n"
            f"Your file: <b>{fmt_size(file_size)}</b>\n"
            f"Max allowed: <b>{MAX_FILE_MB} MB</b>",
            parse_mode="HTML"
        )
        return

    status_msg = await reply_target.reply_text("⏳ <b>Uploading to MeowBox...</b>", parse_mode="HTML")

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
        await update.message.reply_text(caption, parse_mode="HTML", reply_markup=reply_markup)
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
    """Handle files sent directly in PRIVATE chat only."""
    if not is_private(update):
        return

    msg = update.message
    if msg is None:
        return

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

    await upload_and_reply(msg, msg, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_private(update):
        return

    await update.message.reply_text(
        "📸 Send me a <b>file, photo, video, audio, voice, video note, or sticker</b> "
        "to upload on MeowBox!\n\nUse /help for more info.",
        parse_mode="HTML"
    )


# ─── Group Command ────────────────────────────────────────────────────────────

async def group_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /tgm /tm /meowbox in GROUP:
      - Reply to any media  →  upload that file  →  send link IN THE GROUP
      - No reply            →  tell user how to use
    Also checks channel membership.
    """
    msg = update.message
    if msg is None:
        return

    # Private chat
    if is_private(update):
        await msg.reply_text(
            "📩 Just send the file directly here and I will give you the link!",
            parse_mode="HTML"
        )
        return

    if not is_group(update):
        return

    user = update.effective_user
    user_id = user.id

    # ── 1. Channel membership check ──
    has_joined = await check_group_membership(user_id, context)
    if not has_joined:
        ch = clean_channel(CHANNEL_USERNAME)
        await msg.reply_text(
            f"<b>👋 Hey {user.first_name}!</b>\n\n"
            f"Please join our channel first before using this bot!\n\n"
            f"<a href='https://t.me/{ch}'>👉 Join @{ch}</a>\n\n"
            f"After joining, use the command again. 👆",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        return

    # ── 2. Must be a reply to something ──
    replied = msg.reply_to_message
    if replied is None:
        await msg.reply_text(
            f"<b>👋 Hey {user.first_name}!</b>\n\n"
            f"Please <b>reply to a media message</b> and then use this command!\n\n"
            f"<b>How to use:</b>\n"
            f"1️⃣ Find any photo / video / file message in the group\n"
            f"2️⃣ <b>Reply</b> to that message\n"
            f"3️⃣ Type <code>/tgm</code> in the reply\n"
            f"4️⃣ Bot will send the link right here in the group ✅",
            parse_mode="HTML"
        )
        return

    # ── 3. Replied message must have a supported file ──
    has_media = any([
        replied.photo, replied.document, replied.video,
        replied.audio, replied.voice, replied.video_note, replied.sticker,
    ])
    if not has_media:
        await msg.reply_text(
            "❌ The replied message does not contain any supported file.\n\n"
            "Please reply to a 📷 Photo, 🎬 Video, 📄 Document, 🎵 Audio, 🎤 Voice, 📹 Video Note, or 🎭 Sticker.",
            parse_mode="HTML"
        )
        return

    # ── 4. Upload replied file & give link right here in group ──
    await upload_and_reply(replied, msg, context)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    log.info("🚀 Starting MeowBox Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Private
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))

    # Group commands — reply to media → upload → link in group
    app.add_handler(CommandHandler("tgm",     group_bot_command))
    app.add_handler(CommandHandler("tm",      group_bot_command))
    app.add_handler(CommandHandler("meowbox", group_bot_command))

    # Direct file upload — private only
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

    # Text — private only
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
        handle_text
    ))

    log.info("✅ Bot running!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
