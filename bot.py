import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os
import json

# === НАСТРОЙКИ — БЕРУТСЯ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_CREDENTIALS_JSON = os.environ['GOOGLE_CREDENTIALS_JSON']

# Сопоставление user_id → имя
USER_MAPPING = {
    598771387: "Стас",
    1192201108: "Иргуст"
    841899396: "Коля"
}
# ===========================================

# Инициализация
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Загружаем учётные данные Google из строки JSON
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)

def get_or_create_worksheet_by_chat_id(chat_id):
    sheet_name = f"project_{abs(chat_id)}"
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=5)
        worksheet.append_row(["Дата и время", "Кто", "Сумма", "Описание", "Название группы"])
    return worksheet

def parse_single_expense(line):
    match = re.match(r'^(\d+(?:\.\d+)?)\s*[-–—]\s*(.+)$', line.strip())
    if match:
        return float(match.group(1)), match.group(2).strip()
    return None, None

def parse_expenses_multiline(text):
    lines = text.split('\n')
    expenses = []
    for line in lines:
        if line.strip() == '':
            continue
        amount, desc = parse_single_expense(line)
        if amount is not None and desc:
            expenses.append((amount, desc))
    return expenses

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.from_user.id == bot.get_me().id:
        return

    if message.chat.type not in ['group', 'supergroup']:
        return

    expenses = parse_expenses_multiline(message.text)
    if not expenses:
        return

    worksheet = get_or_create_worksheet_by_chat_id(message.chat.id)

    user_id = message.from_user.id
    name = USER_MAPPING.get(user_id, f"ID_{user_id}")
    current_group_name = message.chat.title or f"Без названия (ID: {message.chat.id})"
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    for amount, desc in expenses:
        row = [date, name, amount, desc, current_group_name]
        worksheet.append_row(row)
        print(f"✅ Добавлена трата в группу ID {message.chat.id}: {name} — {amount} — {desc}")

if __name__ == '__main__':
    print("✅ Бот запущен на сервере (работает по ID группы).")
    bot.polling(none_stop=True)