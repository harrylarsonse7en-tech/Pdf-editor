import os
import logging
import tempfile
import shutil

from pypdf import PdfWriter, PdfReader

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ---------- Modes ----------
MODE_NONE = "none"
MODE_MERGE = "merge"
MODE_RENAME_WAIT_FILE = "rename_wait_file"
MODE_RENAME_WAIT_NAME = "rename_wait_name"
MODE_THUMB_WAIT_FILE = "thumb_wait_file"
MODE_THUMB_WAIT_IMAGE = "thumb_wait_image"


def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔗 Merge PDFs", callback_data="merge")],
        [InlineKeyboardButton("✏️ Rename File", callback_data="rename")],
        [InlineKeyboardButton("🖼 Set Thumbnail (Cover)", callback_data="thumb")],
        [InlineKeyboardButton("❌ Cancel / Reset", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_user_dir(user_id: int) -> str:
    path = os.path.join(tempfile.gettempdir(), f"pdfbot_{user_id}")
    os.makedirs(path, exist_ok=True)
    return path


def reset_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    context.user_data.clear()
    context.user_data["mode"] = MODE_NONE
    user_dir = get_user_dir(user_id)
    shutil.rmtree(user_dir, ignore_errors=True)
    os.makedirs(user_dir, exist_ok=True)


# ---------- Command Handlers ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user(context, update.effective_user.id)
    await update.message.reply_text(
        "👋 Welcome! I can help you with PDF files.\n\n"
        "Choose an option below:",
        reply_markup=main_menu_keyboard(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use this bot*\n\n"
        "*Merge PDFs* — send several PDF files one after another, "
        "then type /done to merge them into one file.\n\n"
        "*Rename File* — send any file, then send the new name "
        "(with or without extension).\n\n"
        "*Set Thumbnail* — send a file (e.g. PDF), then send an image "
        "to use as its cover/thumbnail.\n\n"
        "Use /start anytime to return to the menu, /cancel to reset.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user(context, update.effective_user.id)
    await update.message.reply_text(
        "✅ Reset. Choose an option:", reply_markup=main_menu_keyboard()
    )


async def done_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    if mode != MODE_MERGE:
        await update.message.reply_text(
            "ℹ️ You're not in merge mode. Use /start to begin."
        )
        return

    files = context.user_data.get("merge_files", [])
    if len(files) < 2:
        await update.message.reply_text(
            "⚠️ Please send at least 2 PDF files before using /done."
        )
        return

    await update.message.reply_text("⏳ Merging your PDFs, please wait...")

    user_dir = get_user_dir(update.effective_user.id)
    output_path = os.path.join(user_dir, "merged.pdf")

    try:
        writer = PdfWriter()
        for file_path in files:
            reader = PdfReader(file_path)
            for page in reader.pages:
                writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)

        with open(output_path, "rb") as f:
            await update.message.reply_document(
                document=InputFile(f, filename="merged.pdf"),
                caption="✅ Here is your merged PDF!",
            )
    except Exception as e:
        logger.exception("Merge failed")
        await update.message.reply_text(f"❌ Failed to merge files: {e}")
    finally:
        reset_user(context, update.effective_user.id)
        await update.message.reply_text(
            "Choose another option:", reply_markup=main_menu_keyboard()
        )


# ---------- Callback Query Handler (menu buttons) ----------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data

    if choice == "merge":
        reset_user(context, user_id)
        context.user_data["mode"] = MODE_MERGE
        context.user_data["merge_files"] = []
        await query.edit_message_text(
            "🔗 *Merge mode*\n\n"
            "Send me 2 or more PDF files (one by one).\n"
            "When you're done, type /done to merge them.\n"
            "Type /cancel anytime to stop.",
            parse_mode="Markdown",
        )

    elif choice == "rename":
        reset_user(context, user_id)
        context.user_data["mode"] = MODE_RENAME_WAIT_FILE
        await query.edit_message_text(
            "✏️ *Rename mode*\n\n"
            "Send me the file you want to rename.\n"
            "Type /cancel anytime to stop.",
            parse_mode="Markdown",
        )

    elif choice == "thumb":
        reset_user(context, user_id)
        context.user_data["mode"] = MODE_THUMB_WAIT_FILE
        await query.edit_message_text(
            "🖼 *Set Thumbnail mode*\n\n"
            "Send me the file you want to add a cover/thumbnail to.\n"
            "Type /cancel anytime to stop.",
            parse_mode="Markdown",
        )

    elif choice == "cancel":
        reset_user(context, user_id)
        await query.edit_message_text(
            "✅ Reset. Choose an option:", reply_markup=main_menu_keyboard()
        )


# ---------- Document Handler ----------
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", MODE_NONE)
    user_id = update.effective_user.id
    user_dir = get_user_dir(user_id)
    doc = update.message.document

    if mode == MODE_MERGE:
        if doc.mime_type != "application/pdf" and not doc.file_name.lower().endswith(".pdf"):
            await update.message.reply_text("⚠️ Please send a PDF file.")
            return

        file = await doc.get_file()
        idx = len(context.user_data.get("merge_files", []))
        local_path = os.path.join(user_dir, f"part_{idx}.pdf")
        await file.download_to_drive(local_path)

        context.user_data.setdefault("merge_files", []).append(local_path)
        count = len(context.user_data["merge_files"])
        await update.message.reply_text(
            f"✅ Got it! ({count} file{'s' if count != 1 else ''} added)\n"
            f"Send another PDF, or type /done to merge."
        )

    elif mode == MODE_RENAME_WAIT_FILE:
        file = await doc.get_file()
        _, ext = os.path.splitext(doc.file_name or "")
        local_path = os.path.join(user_dir, f"rename_source{ext}")
        await file.download_to_drive(local_path)

        context.user_data["rename_file_path"] = local_path
        context.user_data["rename_original_ext"] = ext
        context.user_data["mode"] = MODE_RENAME_WAIT_NAME

        await update.message.reply_text(
            "✅ File received!\n\n"
            f"Original name: `{doc.file_name}`\n"
            f"Now send me the *new name* (you can include or omit the extension; "
            f"if omitted, I'll keep `{ext}`).",
            parse_mode="Markdown",
        )

    elif mode == MODE_THUMB_WAIT_FILE:
        file = await doc.get_file()
        _, ext = os.path.splitext(doc.file_name or "")
        local_path = os.path.join(user_dir, f"thumb_source{ext}")
        await file.download_to_drive(local_path)

        context.user_data["thumb_file_path"] = local_path
        context.user_data["thumb_file_name"] = doc.file_name or f"file{ext}"
        context.user_data["mode"] = MODE_THUMB_WAIT_IMAGE

        await update.message.reply_text(
            "✅ File received!\n\n"
            "Now send me the *image* you want to use as the cover/thumbnail.\n"
            "(Send it as a photo, not as a file/document.)",
            parse_mode="Markdown",
        )

    else:
        await update.message.reply_text(
            "👋 Use /start to choose what you'd like to do with this file.",
            reply_markup=main_menu_keyboard(),
        )


# ---------- Text Handler (for rename step) ----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", MODE_NONE)
    user_id = update.effective_user.id

    if mode == MODE_RENAME_WAIT_NAME:
        new_name = update.message.text.strip()
        source_path = context.user_data.get("rename_file_path")
        original_ext = context.user_data.get("rename_original_ext", "")

        if not source_path or not os.path.exists(source_path):
            await update.message.reply_text(
                "⚠️ Something went wrong, the original file was lost. "
                "Please /start again."
            )
            return

        # If user didn't include an extension, keep the original one
        _, new_ext = os.path.splitext(new_name)
        if not new_ext and original_ext:
            new_name = new_name + original_ext

        await update.message.reply_document(
            document=open(source_path, "rb"),
            filename=new_name,
            caption=f"✅ Renamed to `{new_name}`",
            parse_mode="Markdown",
        )

        reset_user(context, user_id)
        await update.message.reply_text(
            "Choose another option:", reply_markup=main_menu_keyboard()
        )

    else:
        await update.message.reply_text(
            "👋 Use /start to see the menu of options.",
            reply_markup=main_menu_keyboard(),
        )


# ---------- Photo Handler (for thumbnail step) ----------
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode", MODE_NONE)
    user_id = update.effective_user.id
    user_dir = get_user_dir(user_id)

    if mode == MODE_THUMB_WAIT_IMAGE:
        source_path = context.user_data.get("thumb_file_path")
        file_name = context.user_data.get("thumb_file_name", "file")

        if not source_path or not os.path.exists(source_path):
            await update.message.reply_text(
                "⚠️ Something went wrong, the original file was lost. "
                "Please /start again."
            )
            return

        # Get the largest photo size
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()
        thumb_path = os.path.join(user_dir, "thumb.jpg")
        await photo_file.download_to_drive(thumb_path)

        await update.message.reply_text("⏳ Applying thumbnail...")

        try:
            with open(source_path, "rb") as doc_f, open(thumb_path, "rb") as thumb_f:
                await update.message.reply_document(
                    document=doc_f,
                    filename=file_name,
                    thumbnail=thumb_f,
                    caption="✅ Here's your file with the new cover/thumbnail!",
                )
        except Exception as e:
            logger.exception("Thumbnail set failed")
            await update.message.reply_text(f"❌ Failed to set thumbnail: {e}")

        reset_user(context, user_id)
        await update.message.reply_text(
            "Choose another option:", reply_markup=main_menu_keyboard()
        )

    else:
        await update.message.reply_text(
            "👋 Use /start to see the menu of options.",
            reply_markup=main_menu_keyboard(),
        )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("done", done_merge))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info("Bot started, polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
