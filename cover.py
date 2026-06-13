import os
import tempfile
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

COVER_WAIT_PDF = 2
COVER_WAIT_IMAGE = 3


async def cover_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖼️ اول فایل PDF رو بفرست:")
    return COVER_WAIT_PDF


async def cover_receive_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ لطفاً فقط فایل PDF بفرست.")
        return COVER_WAIT_PDF

    context.user_data["cover_pdf_id"] = doc.file_id
    context.user_data["cover_pdf_name"] = doc.file_name
    await update.message.reply_text(
        "✅ PDF دریافت شد!\n\nحالا تصویر کاور رو بفرست (JPG یا PNG):"
    )
    return COVER_WAIT_IMAGE


async def cover_receive_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle both photo and document image
    if update.message.photo:
        img_file_obj = update.message.photo[-1]  # largest size
        img_ext = ".jpg"
    elif update.message.document:
        img_file_obj = update.message.document
        fname = img_file_obj.file_name.lower()
        if fname.endswith(".png"):
            img_ext = ".png"
        elif fname.endswith((".jpg", ".jpeg")):
            img_ext = ".jpg"
        else:
            await update.message.reply_text("❌ فقط تصویر JPG یا PNG قبول می‌شه.")
            return COVER_WAIT_IMAGE
    else:
        await update.message.reply_text("❌ لطفاً یه تصویر بفرست.")
        return COVER_WAIT_IMAGE

    pdf_id = context.user_data.get("cover_pdf_id")
    pdf_name = context.user_data.get("cover_pdf_name", "output.pdf")

    if not pdf_id:
        await update.message.reply_text("❌ خطا: PDF پیدا نشد. دوباره /cover بزن.")
        return ConversationHandler.END

    await update.message.reply_text("⏳ در حال ست کردن کاور...")

    try:
        tg_pdf = await context.bot.get_file(pdf_id)
        tg_img = await context.bot.get_file(img_file_obj.file_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "input.pdf")
            img_path = os.path.join(tmpdir, f"cover{img_ext}")
            cover_pdf_path = os.path.join(tmpdir, "cover_page.pdf")
            output_path = os.path.join(tmpdir, "output_with_cover.pdf")

            await tg_pdf.download_to_drive(pdf_path)
            await tg_img.download_to_drive(img_path)

            # Convert image to PDF page (A4 size)
            img = Image.open(img_path)
            img_width, img_height = img.size

            page_width, page_height = A4  # 595 x 842 points

            # Calculate scaling to fit A4 while keeping aspect ratio
            scale = min(page_width / img_width, page_height / img_height)
            scaled_w = img_width * scale
            scaled_h = img_height * scale
            x_offset = (page_width - scaled_w) / 2
            y_offset = (page_height - scaled_h) / 2

            c = canvas.Canvas(cover_pdf_path, pagesize=A4)
            c.drawImage(img_path, x_offset, y_offset, scaled_w, scaled_h)
            c.save()

            # Merge: cover + original PDF
            writer = PdfWriter()

            cover_reader = PdfReader(cover_pdf_path)
            writer.add_page(cover_reader.pages[0])

            original_reader = PdfReader(pdf_path)
            for page in original_reader.pages:
                writer.add_page(page)

            with open(output_path, "wb") as f:
                writer.write(f)

            base_name = os.path.splitext(pdf_name)[0]
            output_filename = f"{base_name}_with_cover.pdf"

            with open(output_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=output_filename,
                    caption=f"✅ کاور با موفقیت ست شد!\nصفحات: {len(original_reader.pages) + 1}",
                )

    except Exception as e:
        await update.message.reply_text(f"❌ خطا در پردازش: {str(e)}")

    context.user_data.clear()
    await update.message.reply_text("برای ادامه /start بزن.")
    return ConversationHandler.END
