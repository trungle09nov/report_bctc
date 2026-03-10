"""
Telegram Bot — dùng chung FinBotService với API
"""
import asyncio
import logging
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.constants import ParseMode

from core.analyst import FinBotService
from telegram.formatter import TelegramFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service = FinBotService(use_llm=True)
formatter = TelegramFormatter()

# user_id → {report_data, analysis_result}
user_sessions: dict[int, dict] = {}


# ── Handlers ─────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 *FinBot — Phân Tích Tài Chính*\n\n"
        "Gửi file báo cáo tài chính \\(\\*\\.md, \\*\\.txt\\) để tôi phân tích\\.\n\n"
        "*Lệnh:*\n"
        "/analyze — Phân tích đầy đủ báo cáo\n"
        "/metrics — Xem các chỉ số tài chính\n"
        "/flags — Xem bất thường phát hiện được\n"
        "/ask \\[câu hỏi\\] — Hỏi về báo cáo\n"
        "/clear — Xóa session hiện tại"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận file báo cáo"""
    doc = update.message.document
    filename = doc.file_name or ""

    if not any(filename.endswith(ext) for ext in [".md", ".txt", ".html"]):
        await update.message.reply_text(
            "⚠️ Hiện chỉ hỗ trợ file .md, .txt, .html\n"
            "Bạn có thể dùng tool convert PDF → Markdown trước."
        )
        return

    msg = await update.message.reply_text("⏳ Đang đọc file...")

    try:
        file = await doc.get_file()
        content_bytes = await file.download_as_bytearray()
        content = content_bytes.decode("utf-8", errors="replace")

        data = service.parse_content(content, filename=filename)
        user_id = update.effective_user.id
        user_sessions[user_id] = {"data": data, "result": None, "history": []}

        sections = []
        if data.balance_sheet_current.items:
            sections.append("✅ Bảng cân đối kế toán")
        if data.income_current.items:
            sections.append("✅ Kết quả kinh doanh")
        if data.cashflow_current.items:
            sections.append("✅ Lưu chuyển tiền tệ")
        if data.segments:
            sections.append("✅ Phân tích phân khúc")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Phân tích đầy đủ", callback_data="analyze")],
            [InlineKeyboardButton("📈 Chỉ xem metrics", callback_data="metrics")],
        ])

        text = (
            f"✅ *Đã nhận báo cáo!*\n\n"
            f"🏢 {data.company_name or 'Không xác định'}\n"
            f"📅 {data.period or 'Không xác định'}\n"
            f"📋 {'Hợp nhất' if data.is_consolidated else 'Công ty mẹ'}"
            f"{'  •  Holding company' if data.is_holding_company else ''}\n\n"
            f"*Đã parse:*\n" + "\n".join(sections)
        )

        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

    except Exception as e:
        await msg.edit_text(f"❌ Lỗi đọc file: {str(e)}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)

    if not session:
        await query.edit_message_text("Session đã hết hạn. Vui lòng upload lại file.")
        return

    data = session["data"]

    if query.data == "analyze":
        await query.edit_message_text("⏳ Đang phân tích (có thể mất 15-30 giây)...")
        try:
            result = service.analyze(data)
            session["result"] = result
            text = formatter.format_full_analysis(data, result)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(f"❌ Lỗi phân tích: {str(e)}")

    elif query.data == "metrics":
        try:
            result = service.calculate(data)
            session["result"] = result
            text = formatter.format_metrics(data, result)
            await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await query.edit_message_text(f"❌ Lỗi: {str(e)}")


async def cmd_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Vui lòng gửi file báo cáo trước.")
        return

    msg = await update.message.reply_text("⏳ Đang phân tích...")
    try:
        result = service.analyze(session["data"])
        session["result"] = result
        text = formatter.format_full_analysis(session["data"], result)
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")


async def cmd_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Vui lòng gửi file báo cáo trước.")
        return

    result = session.get("result") or service.calculate(session["data"])
    session["result"] = result
    text = formatter.format_metrics(session["data"], result)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_flags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Vui lòng gửi file báo cáo trước.")
        return

    result = session.get("result") or service.calculate(session["data"])
    session["result"] = result
    text = formatter.format_flags(result)
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("Vui lòng gửi file báo cáo trước.")
        return

    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("Vui lòng nhập câu hỏi. VD: /ask Tại sao lợi nhuận tăng?")
        return

    result = session.get("result") or service.calculate(session["data"])
    session["result"] = result

    msg = await update.message.reply_text("⏳ Đang xử lý câu hỏi...")
    try:
        response = service.chat(
            session["data"], result, question,
            history=session.get("history", [])
        )
        # Lưu history cho multi-turn
        session.setdefault("history", []).extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": response.get("answer", "")},
        ])

        text = formatter.format_chat_response(question, response)
        await msg.edit_text(text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("✅ Đã xóa session. Bạn có thể upload báo cáo mới.")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN không được set")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("analyze", cmd_analyze))
    app.add_handler(CommandHandler("metrics", cmd_metrics))
    app.add_handler(CommandHandler("flags", cmd_flags))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("FinBot Telegram đang chạy...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
