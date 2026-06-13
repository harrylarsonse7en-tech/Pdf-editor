import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

RENAME_WAIT_PDF = 0
RENAME_WAIT_NAME = 1


async def rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️ فایل PDF که می‌خوای تغییر نام بدی رو بفرست:")
    return RENAME_WAIT_PDF


async def rename_receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ لطفاً فقط فایل PDF بفرست.")
        return RENAME_WAIT_PDF

    context.user_data["rename_file_id"] = doc.file_id
    context.user_data["rename_original_name"] = doc.file_name
    await update.message.reply_text(
        f"✅ فایل دریافت شد: `{doc.file_name}`\n\nحالا اسم جدید رو بنویس (بدون پسوند .pdf):",
        parse_mode="Markdown",
    )
    return RENAME_WAIT_NAME


async def rename_receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text.strip()

    # Clean filename
    forbidden = r'\/:*?"<>|'
    for ch in forbidden:
        new_name = new_name.replace(ch, "_")

    if not new_name:
        await update.message.reply_text("❌ اسم نامعتبر است. دوباره امتحان کن:")
        return RENAME_WAIT_NAME

    file_id = context.user_data.get("rename_file_id")
    if not file_id:
        await update.message.reply_text("❌ خطا: فایل پیدا نشد. دوباره /rename بزن.")
        return ConversationHandler.END

    await update.message.reply_text("⏳ در حال پردازش...")

    try:
        tg_file = await context.bot.get_file(file_id)
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            await tg_file.download_to_drive(pdf_path)

            output_filename = f"{new_name}.pdf"
            output_path = os.path.join(tmpdir, output_filename)

            # Simply copy with new name (rename doesn't change content)
            import shutil
            shutil.copy2(pdf_path, output_path)

            with open(output_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=output_filename,
                    caption=f"✅ نام تغییر یافت به: `{output_filename}`",
                    parse_mode="Markdown",
                )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش: {str(e)}")

    context.user_data.clear()
    await update.message.reply_text("برای ادامه /start بزن.")
    return ConversationHandler.END
