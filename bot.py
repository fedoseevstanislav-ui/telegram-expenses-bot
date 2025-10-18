import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re

# === НАСТРОЙКИ — ЗАМЕНИТЕ СВОИМИ ДАННЫМИ ===
TELEGRAM_TOKEN = '7857843250:AAErnJdkRKX2BsRlNrT9rFhrgyvyB67daxU'
SPREADSHEET_ID = '1eWAGa2ENOwbX8Kj7Nd9_FhmW0GZwcuFzzXdeJeiaORg'

# Сопоставление user_id → имя
USER_MAPPING = {
   598771387: "Стас",
    1192201108: "Иргуст"
}
# ===========================================

# Инициализация
bot = telebot.TeleBot(TELEGRAM_TOKEN)

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)

def get_or_create_worksheet_by_chat_id(chat_id):
    """Возвращает лист по ID группы. Название листа: project_1234567890"""
    # ID групп в Telegram отрицательные, поэтому берём модуль
    sheet_name = f"project_{abs(chat_id)}"
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        # Создаём новый лист
        worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=5)
        # Добавляем заголовки
        worksheet.append_row(["Дата и время", "Кто", "Сумма", "Описание", "Название группы"])
    return worksheet

def parse_single_expense(line):
    """Проверяет одну строку: похожа ли она на трату?"""
    match = re.match(r'^(\d+(?:\.\d+)?)\s*[-–—]\s*(.+)$', line.strip())
    if match:
        return float(match.group(1)), match.group(2).strip()
    return None, None

def parse_expenses_multiline(text):
    """Разбивает текст на строки и ищет траты в каждой."""
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
        return  # игнорировать свои сообщения

    if message.chat.type not in ['group', 'supergroup']:
        return  # работаем только в группах

    expenses = parse_expenses_multiline(message.text)
    if not expenses:
        return  # нет трат — выходим

    # Получаем или создаём лист по ID группы
    worksheet = get_or_create_worksheet_by_chat_id(message.chat.id)

    # Определяем имя отправителя
    user_id = message.from_user.id
    name = USER_MAPPING.get(user_id, f"ID_{user_id}")

    # Текущее название группы (для отображения в таблице)
    current_group_name = message.chat.title or f"Без названия (ID: {message.chat.id})"

    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    for amount, desc in expenses:
        row = [date, name, amount, desc, current_group_name]
        worksheet.append_row(row)
        print(f"✅ Добавлена трата в группу ID {message.chat.id}: {name} — {amount} — {desc}")

if __name__ == '__main__':
    print("✅ Бот запущен (работает по ID группы).")
    print("👉 Добавьте его в любую группу и сделайте админом.")
    print("   Можно свободно переименовывать группу — данные не развалятся!")
    bot.polling(none_stop=True)