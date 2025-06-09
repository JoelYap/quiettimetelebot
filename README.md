# QuietTime Telegram Bot

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

3. **Choose Bible Translation:**

   **Option A: ESV (recommended)** - Free for non-commercial use
   - Sign up at https://api.esv.org/
   - Get your free API key (5,000 requests/day)
   - Add `ESV_API_KEY` to your GitHub secrets

   **Option B: KJV (completely free)** - No API key needed
   - Leave `ESV_API_KEY` empty in GitHub secrets
   - Bot will automatically use free KJV API

4. **Setup GitHub Repository:**
   - Fork this repository
   - Go to Settings → Secrets and variables → Actions
   - Add these secrets:
     - `TELEGRAM_TOKEN`: Your bot token  
     - `TELEGRAM_CHAT_ID`: Your channel/chat ID
     - `ESV_API_KEY`: Your ESV API key (or leave empty for free KJV)

5. **Configure Reading Plan:**
   - Edit the `reading_plan.json` file
   - Set your references, timezone, and daily time
   - Change `start_date` to when you want to begin

## Features

- ✅ Parse Bible references like "Psalms 1-15,120-134"
- ✅ Daily automated sending via GitHub Actions
- ✅ Choice of ESV (with free API key) or KJV (completely free)
- ✅ Bible Gateway links for any translation
- ✅ Simple timezone support
- ✅ Reading progress tracking

## Manual Trigger

You can manually trigger the bot from GitHub Actions tab → "Bible Verse Bot" → "Run workflow"

## Customization

Edit `reading_plan.json` to customize:
- **references**: Bible books and chapters (e.g., "Psalms 1-15,120-134")
- **start_date**: When to begin the reading plan
- **daily_time**: What time to send (24-hour format)
- **timezone**: Your timezone (SGT, EST, GMT+7, etc.)

## Schedule

The bot runs daily at midnight UTC. To change the time, edit the cron expression in `.github/workflows/bot.yml`:
- `'0 8 * * *'` = 8 AM UTC daily
- `'30 14 * * *'` = 2:30 PM UTC daily
- Use https://crontab.guru/ to generate cron expressions

## Progress Tracking

The bot automatically calculates which day of your reading plan it is based on the start date. No manual tracking needed!

## License

MIT License