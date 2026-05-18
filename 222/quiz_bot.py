import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# 直接填写你的 Token（记得加引号）
BOT_TOKEN = "8872831521:AAFTKidlduz0dRjUEbELoXqq-iKkW7ZkAcM"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

QUESTION_1, QUESTION_2, QUESTION_3, RESULT = range(4)

QUESTIONS = [
    {
        "text": "When a user asks 'Where are you', which response do you think is the LEAST appropriate?",
        "options": {
            "A": "Ask back 'You guess'",
            "B": "Directly say a specific country (e.g., Kenya, Africa, Nigeria)",
            "C": "Say a nearby big city name",
            "D": "Don't answer, chat about something else first"
        },
        "correct": "A"
    },
    {
        "text": "Unlock this video. There are my phone number and address in it",
        "options": {
            "A": "Smart, increases unlock rate",
            "B": "May disappoint users, likely fake",
            "C": "Platform likely doesn't allow this deception",
            "D": "No feeling"
        },
        "correct": "B"
    },
    {
        "text": "Which of the following practices do you think is BEST for keeping users long-term?",
        "options": {
            "A": "Send PPV quickly in every chat to build user habit",
            "B": "Build natural conversation first, then guide unlock when user's emotion is high",
            "C": "Tell user 'I'll call you after this unlock'",
            "D": "Stop replying if user doesn't unlock"
        },
        "correct": "B"
    }
]

user_answers = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_answers[user_id] = {"score": 0, "current": 0}
    await update.message.reply_text(
        "📋 *欢迎参加考核问卷！*\n\n您需要回答 3 个选择题。每个问题只有一个最合适的答案。\n\n请认真作答，完成后我会告诉您是否通过考核。",
        parse_mode="Markdown"
    )
    return await send_question(update, context, 0)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q_index: int) -> int:
    user_id = update.effective_user.id
    if q_index >= len(QUESTIONS):
        return await show_result(update, context)
    
    q_data = QUESTIONS[q_index]
    text = f"*问题 {q_index+1}/{len(QUESTIONS)}:*\n{q_data['text']}\n\n"
    
    keyboard = []
    for opt_key, opt_text in q_data["options"].items():
        keyboard.append([InlineKeyboardButton(f"{opt_key}. {opt_text}", callback_data=f"ans_{q_index}_{opt_key}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if "msg_id" in context.user_data:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=context.user_data["msg_id"],
                text=text,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return QUESTION_1 + q_index
        except:
            pass
    
    msg = await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    context.user_data["msg_id"] = msg.message_id
    return QUESTION_1 + q_index

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    _, q_idx_str, chosen = data.split("_")
    q_index = int(q_idx_str)
    
    correct = QUESTIONS[q_index]["correct"]
    if chosen == correct:
        user_answers[user_id]["score"] += 1
        feedback = "✅ 正确！"
    else:
        feedback = f"❌ 错误。正确答案是 {correct}。"
    
    await query.edit_message_text(
        text=f"{query.message.text}\n\n{feedback}\n\n正在进入下一题...",
        parse_mode="Markdown"
    )
    
    next_q = q_index + 1
    if next_q < len(QUESTIONS):
        context.user_data["msg_id"] = None
        return await send_question(update, context, next_q)
    else:
        return await show_result(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    score = user_answers.get(user_id, {}).get("score", 0)
    total = len(QUESTIONS)
    passed = score >= 2
    
    result_text = f"📊 *考核完成！*\n\n您的得分: {score}/{total}\n\n"
    if passed:
        result_text += "🎉 *恭喜您通过考核！* 🎉\n\n您可以继续使用本机器人的高级功能。"
    else:
        result_text += "❌ *很遗憾，您未通过考核。*\n\n请使用 /start 重新尝试。"
    
    if hasattr(update, "effective_message"):
        await update.effective_message.reply_text(result_text, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=result_text, parse_mode="Markdown")
    
    if user_id in user_answers:
        del user_answers[user_id]
    if "msg_id" in context.user_data:
        del context.user_data["msg_id"]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("问卷已取消。输入 /start 重新开始。")
    user_id = update.effective_user.id
    if user_id in user_answers:
        del user_answers[user_id]
    if "msg_id" in context.user_data:
        del context.user_data["msg_id"]
    return ConversationHandler.END

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            QUESTION_1: [CallbackQueryHandler(handle_answer, pattern="^ans_0_")],
            QUESTION_2: [CallbackQueryHandler(handle_answer, pattern="^ans_1_")],
            QUESTION_3: [CallbackQueryHandler(handle_answer, pattern="^ans_2_")],
            RESULT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    
    print("🤖 机器人正在运行...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()