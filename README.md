# PDF Telegram Bot 🤖

ربات تلگرام برای پردازش فایل‌های PDF

## قابلیت‌ها

- ✏️ **تغییر نام PDF** - نام فایل رو تغییر بده
- 🖼️ **ست کردن کاور** - یه تصویر به عنوان صفحه اول اضافه کن
- 🔗 **ادغام PDF ها** - چند PDF رو با هم یکی کن

## نصب محلی

```bash
pip install -r requirements.txt
```

یه فایل `.env` بساز:
```
BOT_TOKEN=your_token_here
```

سپس اجرا کن:
```bash
python bot.py
```

## دپلوی روی Railway

1. ریپو رو به GitHub پوش کن
2. وارد [railway.app](https://railway.app) بشو
3. **New Project** → **Deploy from GitHub repo** رو انتخاب کن
4. ریپوی خودت رو انتخاب کن
5. بعد از ساخت پروژه، به **Variables** برو و اضافه کن:
   ```
   BOT_TOKEN = your_telegram_bot_token
   ```
6. Railway خودکار دپلوی می‌کنه ✅

## ساختار پروژه

```
pdf_bot/
├── bot.py              # فایل اصلی
├── handlers/
│   ├── __init__.py
│   ├── rename.py       # هندلر تغییر نام
│   ├── cover.py        # هندلر کاور
│   └── merge.py        # هندلر ادغام
├── requirements.txt
├── Procfile
├── runtime.txt
└── railway.toml
```
