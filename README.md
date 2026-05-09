# MeowBox File Uploader Bot 🐱

A Telegram bot that uploads any file to MeowBox and returns a permanent direct link.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
nano .env
python bot.py
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| BOT_TOKEN | ✅ | Your bot token from BotFather |
| MEOWBOX_URL | ✅ | Your MeowBox server upload URL |
| CHANNEL_USERNAME | ❌ | Force subscribe channel e.g. @MyChannel |
| FORCE_SUB | ❌ | true / false (default: false) |
| DEVELOPER_ID | ❌ | Your Telegram user ID |
| MAX_FILE_MB | ❌ | Max file size in MB (default: 512) |

## Features

- ✅ Supports Photos, Videos, Documents, Audio, Voice
- ✅ Permanent direct links via MeowBox
- ✅ Optional force subscribe to a channel
- ✅ Automatic file size validation
- ✅ Local file cleanup after upload
- ✅ Run with Screen or PM2
