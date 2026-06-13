import os
import tempfile
from pypdf import PdfWriter, PdfReader
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

MERGE_COLLECTING = 4
MAX_FILES = 10


async def merge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["merge_files"] = []
    await update.message.reply_text(
        "🔗 PDF هایی که می‌خوای ادغام کنی رو یکی یکی بفرست.\n"
        f"(حداکثر {MAX_FILES} فایل)\n\n"
        "وقتی همه رو فرستادی /done بزن."
    )
    return MERGE_COLLECTING


async def merge_receive_pdfs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ فقط PDF قبول می‌شه.")
        return MERGE_COLLECTING

    files = context.user_data.get("merge_files", [])

    if len(files) >= MAX_FILES:
        await update.message.reply_text(
            f"❌ حداکثر {MAX_FILES} فایل مجاز است.\nبرای ادغام همین‌ها /done بزن."
        )
        return MERGE_COLLECTING

    files.append({"file_id": doc.file_id, "name": doc.file_name})
    context.user_data["merge_files"] = files

    file_list = "\n".join(
        [f"{i+1}. {f['name']}" for i, f in enumerate(files)]
    )
    await update.message.reply_text(
        f"✅ فایل {len(files)} دریافت شد.\n\n"
        f"📋 لیست فعلی:\n{file_list}\n\n"
        "PDF بعدی رو بفرست یا /done بزن."
    )
    return MERGE_COLLECTING


async def merge_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files = context.user_data.get("merge_files", [])

    if len(files) < 2:
        await update.message.reply_text(
            "❌ حداقل ۲ فایل PDF نیاز داری.\nادامه بده یا /cancel بزن."
        )
        return MERGE_COLLECTING

    await update.message.reply_text(f"⏳ در حال ادغام {len(files)} فایل...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = PdfWriter()
            total_pages = 0

            for i, file_info in enumerate(files):
                tg_file = await context.bot.get_file(file_info["file_id"])
                pdf_path = os.path.join(tmpdir, f"file_{i}.pdf")
                await tg_file.download_to_drive(pdf_path)

                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
                total_pages += len(reader.pages)

            output_path = os.path.join(tmpdir, "merged.pdf")
            with open(output_path, "wb") as f:
                writer.write(f)

            with open(output_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename="merged.pdf",
                    caption=(
                        f"✅ ادغام با موفقیت انجام شد!\n"
                        f"📄 تعداد فایل‌ها: {len(files)}\n"
                        f"📃 کل صفحات: {total_pages}"
                    ),
                )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ادغام: {str(e)}")

    context.user_data.clear()
    await update.message.reply_text("برای ادامه /start بزن.")
    return ConversationHandler.END
