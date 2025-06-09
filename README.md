# Simple Bible Verse Bot

A minimal Telegram bot that sends daily Bible verses via GitHub Actions.

## Setup

1. **Create Telegram Bot:**
   - Message @BotFather on Telegram
   - Use `/newbot` to create your bot
   - Save the token

2. **Get your Chat ID:**
   - Add your bot to your channel as admin
   - Send a test message to the channel
   - Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Find your chat ID (negative number for channels)

3. **Get ESV API Key:**
   - Sign up at https://api.esv.org/
   - Get your free API key

4. **Setup GitHub Repository:**
   - Fork this repository
   - Go to Settings → Secrets and variables → Actions
   - Add these secrets:
     - `TELEGRAM_TOKEN`: Your bot token
     - `TELEGRAM_CHAT_ID`: Your channel/chat ID
     - `ESV_API_KEY`: Your ESV API key

5. **Configure Reading Plan:**
   - Edit the sample plan in `bot.py` (line 185-191)
   - Set your references, timezone, and daily time

## Features

- ✅ Parse Bible references like "Psalms 1-15,120-134"
- ✅ Daily automated sending via GitHub Actions
- ✅ ESV Bible text with Bible Gateway links
- ✅ Simple timezone support
- ✅ Reading progress tracking

## Manual Trigger

You can manually trigger the bot from GitHub Actions tab → "Bible Verse Bot" → "Run workflow"