from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import json
import os
from datetime import datetime, timedelta

CHOOSING, CHOOSING_DATE, ENTER_CUSTOM_DATE, ENTER_AMOUNT, ENTER_COMMENT = range(5)

data_file = 'balance.json'
history_file = 'history.json'

if not os.path.exists(data_file):
    with open(data_file, 'w') as f:
        json.dump({'Я': 0, 'Илья': 0}, f)

if not os.path.exists(history_file):
    with open(history_file, 'w') as f:
        json.dump([], f)

def load_balance():
    with open(data_file, 'r') as f:
        return json.load(f)

def save_balance(data):
    with open(data_file, 'w') as f:
        json.dump(data, f)

def load_history():
    with open(history_file, 'r') as f:
        return json.load(f)

def save_history(history):
    with open(history_file, 'w') as f:
        json.dump(history, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_keyboard = [
        ['Заплатил Я', 'Заплатил Илья'],
        ['Проверить баланс', 'История'],
        ['Сбросить всё']
    ]
    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    )
    return CHOOSING

async def choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ['Заплатил Я', 'Заплатил Илья']:
        context.user_data['payer'] = 'Я' if text == 'Заплатил Я' else 'Илья'
        reply_keyboard = [['Позавчера', 'Вчера', 'Сегодня'], ['Другое']]
        await update.message.reply_text("Выбери дату:", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))
        return CHOOSING_DATE
    elif text == 'Проверить баланс':
        data = load_balance()
        diff = data['Я'] - data['Илья']
        if diff > 0:
            msg = f"Илья должен тебе {diff:.2f} ₽"
        elif diff < 0:
            msg = f"Ты должен Илье {-diff:.2f} ₽"
        else:
            msg = "Вы в расчете!"
        await update.message.reply_text(msg)
        return CHOOSING
    elif text == 'История':
        history = load_history()
        if not history:
            await update.message.reply_text("История пока пуста.")
        else:
            msg = "\n".join([f"{h['date']} / {h['payer']} / {h['amount']} ₽ / {h['comment']}" for h in history])
            await update.message.reply_text(msg)
        return CHOOSING
    elif text == 'Сбросить всё':
        save_balance({'Я': 0, 'Илья': 0})
        save_history([])
        await update.message.reply_text("Баланс и история очищены. Начинаем заново!")
        return await start(update, context)
    else:
        await update.message.reply_text("Неверная команда, попробуй снова.")
        return CHOOSING

async def choosing_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == 'Позавчера':
        date = (datetime.now() - timedelta(days=2)).strftime('%d.%m.%Y')
    elif text == 'Вчера':
        date = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
    elif text == 'Сегодня':
        date = datetime.now().strftime('%d.%m.%Y')
    elif text == 'Другое':
        await update.message.reply_text("Введи дату в формате ДД.ММ.ГГГГ:")
        return ENTER_CUSTOM_DATE
    else:
        await update.message.reply_text("Неверный выбор даты.")
        return CHOOSING_DATE

    context.user_data['date'] = date
    await update.message.reply_text("Введи сумму:")
    return ENTER_AMOUNT

async def enter_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_text = update.message.text
    try:
        datetime.strptime(date_text, '%d.%m.%Y')
    except ValueError:
        await update.message.reply_text("Некорректный формат. Введи дату как ДД.ММ.ГГГГ:")
        return ENTER_CUSTOM_DATE
    context.user_data['date'] = date_text
    await update.message.reply_text("Введи сумму:")
    return ENTER_AMOUNT

async def enter_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(',', '.'))
    except ValueError:
        await update.message.reply_text("Введите корректную сумму (например, 150.50):")
        return ENTER_AMOUNT
    context.user_data['amount'] = amount
    await update.message.reply_text("Напиши, на что потрачено:")
    return ENTER_COMMENT

async def enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment = update.message.text
    payer = context.user_data['payer']
    date = context.user_data['date']
    amount = context.user_data['amount']

    balance = load_balance()
    balance[payer] += amount
    save_balance(balance)

    history = load_history()
    history.append({'date': date, 'payer': payer, 'amount': amount, 'comment': comment})
    save_history(history)

    await update.message.reply_text(f"Записал: {date} / {payer} / {amount:.2f} ₽ / {comment}")
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Окей, отмена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

app = ApplicationBuilder().token('8288179417:AAFGu9DbyBEQZHROKGHNC5nbp88sXGLNJUE').build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice)],
        CHOOSING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choosing_date)],
        ENTER_CUSTOM_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_custom_date)],
        ENTER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_amount)],
        ENTER_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_comment)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(conv_handler)

print("Бот запущен!")
app.run_polling()