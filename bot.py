import os
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from handlers.rename import rename_start, rename_receive_pdf, rename_receive_name
from handlers.cover import cover_start, cover_receive_pdf, cover_receive_image
from handlers.merge import merge_start, merge_receive_pdfs, merge_done

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# States
RENAME_WAIT_PDF, RENAME_WAIT_NAME = range(2)
COVER_WAIT_PDF, COVER_WAIT_IMAGE = range(2, 4)
MERGE_COLLECTING = 4

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("✏️ تغییر نام PDF", callback_data="rename")],
        [InlineKeyboardButton("🖼️ ست کردن کاور", callback_data="cover")],
        [InlineKeyboardButton("🔗 ادغام PDF ها", callback_data="merge")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "سلام! 👋\nبا این ربات می‌تونی:\n\n"
        "✏️ نام PDF رو تغییر بدی\n"
        "🖼️ کاور (صفحه اول) برای PDF ست کنی\n"
        "🔗 چند PDF رو با هم ادغام کنی\n\n"
        "یه گزینه انتخاب کن:",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 راهنما:\n\n"
        "/start - منوی اصلی\n"
        "/rename - تغییر نام PDF\n"
        "/cover - ست کردن کاور\n"
        "/merge - ادغام PDF ها\n"
        "/cancel - لغو عملیات جاری"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ عملیات لغو شد.\n\nبرای شروع مجدد /start بزن.")
    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "rename":
        await query.edit_message_text("✏️ فایل PDF که می‌خوای تغییر نام بدی رو بفرست:")
        return RENAME_WAIT_PDF
    elif data == "cover":
        await query.edit_message_text("🖼️ اول فایل PDF رو بفرست:")
        return COVER_WAIT_PDF
    elif data == "merge":
        context.user_data["merge_files"] = []
        await query.edit_message_text(
            "🔗 PDF هایی که می‌خوای ادغام کنی رو یکی یکی بفرست.\n"
            "وقتی تموم شد /done بزن."
        )
        return MERGE_COLLECTING


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_handler, pattern="^(rename|cover|merge)$"),
            CommandHandler("rename", rename_start),
            CommandHandler("cover", cover_start),
            CommandHandler("merge", merge_start),
        ],
        states={
            RENAME_WAIT_PDF: [
                MessageHandler(filters.Document.PDF, rename_receive_pdf),
                CallbackQueryHandler(button_handler, pattern="^(rename|cover|merge)$"),
            ],
            RENAME_WAIT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, rename_receive_name),
            ],
            COVER_WAIT_PDF: [
                MessageHandler(filters.Document.PDF, cover_receive_pdf),
                CallbackQueryHandler(button_handler, pattern="^(rename|cover|merge)$"),
            ],
            COVER_WAIT_IMAGE: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, cover_receive_image),
            ],
            MERGE_COLLECTING: [
                MessageHandler(filters.Document.PDF, merge_receive_pdfs),
                CommandHandler("done", merge_done),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
