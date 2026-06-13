# PDF Toolbox Telegram Bot

A Telegram bot (like @ilovepdfs_bot) with three features:

- 🔗 **Merge PDFs** — combine multiple PDFs into one
- ✏️ **Rename File** — rename any file you send
- 🖼 **Set Thumbnail** — attach a custom cover image (thumbnail) to a file

## 1. Create your bot & get a token

1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts, choose a name and username.
3. BotFather gives you a **token** like `123456789:ABCdefGhIJKlmNoPQRstuVWXyz`.
4. Keep this token secret.

## 2. Deploy on Railway

1. Create a new project on [railway.app](https://railway.app).
2. Choose **"Deploy from GitHub repo"** (push this folder to a GitHub repo first),
   or use **"Empty Project"** and upload these files via the Railway CLI.
3. In the project's **Variables** tab, add:
   - `BOT_TOKEN` = your token from BotFather
4. Railway will detect the `Procfile` and run `python bot.py` as a **worker**
   (no public URL/port needed — the bot uses polling).
5. Make sure the service type is set to **Worker** (not Web), since this bot
   doesn't listen on a port.
6. Deploy. Check the logs — you should see `Bot started, polling...`.

### Files in this project
- `bot.py` — the bot code
- `requirements.txt` — Python dependencies
- `Procfile` — tells Railway how to run the bot

## 3. Using the bot

Send `/start` to your bot in Telegram to see the menu:

- **Merge PDFs**: send 2+ PDF files, then `/done` to merge.
- **Rename File**: send any file, then send the new name (with or without
  extension — the original extension is kept if you omit it).
- **Set Thumbnail**: send a file, then send a photo to use as its cover.
  This sets Telegram's file preview thumbnail (does not edit PDF pages).

Use `/cancel` anytime to reset, `/help` for instructions.

## Notes / possible extensions
- Add a "compress PDF", "PDF to images", or "split PDF" feature using `pypdf`
  or `pdf2image`.
- For very large files, consider increasing Railway's resource limits.
- All temp files are stored per-user in the OS temp directory and cleaned up
  after each operation.
