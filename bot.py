import telebot
import pandas as pd
import os
import sys
from telebot import types
from dotenv import load_dotenv

RELOAD_FLAG = 'reload.flag'

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота с токеном из .env
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
if not TOKEN:
    raise ValueError("Токен бота не найден в .env файле")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не найден в .env файле")
ADMIN_ID = int(ADMIN_ID)

bot = telebot.TeleBot(TOKEN)

# Загрузка данных о ноутбуках
def load_data():
    try:
        return pd.read_csv('data.csv')
    except FileNotFoundError:
        return pd.DataFrame()

def get_available_options(df, column):
    return sorted(df[column].unique().tolist())

# Клавиатура выбора характеристик
def create_spec_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Размер экрана 📏', 'Герцовка 🔄', 'Разрешение 🖥️')
    keyboard.row('Процессор 💻', 'Видеокарта 🎮', 'Оперативная память 💾')
    keyboard.row('Накопитель 💿', 'Найти ноутбуки 🔍', 'В меню ↩️')
    keyboard.row('Сбросить 🔁')
    return keyboard

# Главное меню
def create_main_keyboard(is_admin=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Начать подбор 🚀', 'Помощь ℹ️')
    if is_admin:
        keyboard.row('Очистить чат 🧹')
    return keyboard

# Словарь соответствия характеристик и колонок
def get_spec_mapping():
    return {
        'Размер экрана': 'Screen Size',
        'Герцовка': 'Refresh Rate',
        'Разрешение': 'Resolution',
        'Процессор': 'Processor',
        'Видеокарта': 'Graphics Card',
        'Оперативная память': 'RAM',
        'Накопитель': 'Storage'
    }

# Хранение предпочтений пользователя
user_preferences = {}

def create_options_keyboard(options, spec):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for option in options:
        callback_data = f"{spec}:{option}"
        buttons.append(types.InlineKeyboardButton(text=str(option), callback_data=callback_data))
    keyboard.add(*buttons)
    return keyboard

def get_filtered_options(df, user_prefs):
    filtered_df = df.copy()
    for spec, value in user_prefs.items():
        if spec in df.columns:
            filtered_df = filtered_df[filtered_df[spec].astype(str).str.contains(str(value), case=False)]
    return filtered_df

@bot.message_handler(commands=['start'])
def start(message):
    user_preferences[message.chat.id] = {}
    is_admin = (message.from_user.id == ADMIN_ID)
    bot.send_message(message.chat.id, 
                     "👋 Добро пожаловать в бот подбора ноутбуков! 🖥️\n"
                     "Я помогу вам найти идеальный ноутбук по вашим предпочтениям.\n"
                     "Используйте /help для просмотра доступных команд.",
                     reply_markup=create_main_keyboard(is_admin))

@bot.message_handler(commands=['help'])
def help(message):
    help_text = (
        "📋 Доступные команды:\n"
        "/start - Запустить бота 🚀\n"
        "/help - Показать это сообщение ℹ️\n"
        "/reload - Перезагрузить бота 🔄\n"
        "/reset - Сбросить выбранные характеристики 🔁\n\n"
        "Для подбора ноутбука нажмите 'Начать подбор 🚀' и следуйте инструкциям."
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['reload'])
def reload(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔️ У вас нет прав для перезагрузки бота.")
        return
    bot.send_message(message.chat.id, "🔄 Перезагрузка бота...")
    with open(RELOAD_FLAG, 'w') as f:
        f.write(str(message.chat.id))
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.message_handler(commands=['reset'])
def reset(message):
    user_preferences[message.chat.id] = {}
    bot.send_message(message.chat.id, "🔄 Все выбранные характеристики сброшены!", 
                     reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Сбросить 🔁')
def reset_button(message):
    user_preferences[message.chat.id] = {}
    bot.send_message(message.chat.id, "🔄 Все выбранные характеристики сброшены!")
    bot.send_message(message.chat.id, 
                     "🔍 Выберите характеристику, которую хотите установить:",
                     reply_markup=create_spec_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Начать подбор 🚀')
def start_selection(message):
    bot.send_message(message.chat.id, 
                     "🔍 Выберите характеристику, которую хотите установить:",
                     reply_markup=create_spec_keyboard())

@bot.message_handler(func=lambda message: message.text == 'В меню ↩️')
def back_to_main(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    bot.send_message(message.chat.id, 
                     "🏠 Главное меню:",
                     reply_markup=create_main_keyboard(is_admin))

@bot.message_handler(func=lambda message: message.text in ['Размер экрана 📏', 'Герцовка 🔄', 'Разрешение 🖥️', 
                                                         'Процессор 💻', 'Видеокарта 🎮', 'Оперативная память 💾', 'Накопитель 💿'])
def handle_spec_selection(message):
    display_spec = ' '.join(message.text.split()[:-1])  # Убираем эмодзи
    spec_mapping = get_spec_mapping()
    spec = spec_mapping[display_spec]
    df = load_data()
    if df.empty:
        bot.send_message(message.chat.id, "❌ Нет данных о ноутбуках!")
        return
    filtered_df = get_filtered_options(df, user_preferences.get(message.chat.id, {}))
    available_options = get_available_options(filtered_df, spec)
    if not available_options:
        bot.send_message(message.chat.id, "❌ Нет доступных опций для этой характеристики с текущими фильтрами!")
        return
    options_text = f"Доступные варианты для '{display_spec}':\n" + "\n".join([f"• {option}" for option in available_options])
    bot.send_message(message.chat.id, 
                     f"Выберите {display_spec}:\n\n{options_text}",
                     reply_markup=create_options_keyboard(available_options, spec))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    spec, value = call.data.split(':')
    if call.message.chat.id not in user_preferences:
        user_preferences[call.message.chat.id] = {}
    user_preferences[call.message.chat.id][spec] = value
    bot.answer_callback_query(call.id, f"✅ {spec} установлено: {value}")
    bot.edit_message_text(
        f"✅ {spec} установлено: {value}\n\nТекущие выбранные характеристики:\n" + 
        "\n".join([f"• {k}: {v}" for k, v in user_preferences[call.message.chat.id].items()]),
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda message: message.text == 'Найти ноутбуки 🔍')
def find_laptops(message):
    if message.chat.id not in user_preferences or not user_preferences[message.chat.id]:
        bot.send_message(message.chat.id, "⚠️ Сначала выберите хотя бы одну характеристику!")
        return
    df = load_data()
    if df.empty:
        bot.send_message(message.chat.id, "❌ Нет данных о ноутбуках!")
        return
    filtered_df = df.copy()
    for spec, value in user_preferences[message.chat.id].items():
        if spec in df.columns:
            filtered_df = filtered_df[filtered_df[spec].astype(str).str.contains(str(value), case=False)]
    if filtered_df.empty:
        bot.send_message(message.chat.id, "🔍 Не найдено ноутбуков, соответствующих вашим критериям!")
    else:
        for _, laptop in filtered_df.iterrows():
            result = "💻 Найден ноутбук:\n"
            for column in df.columns:
                if column not in ['Images', 'Link']:
                    result += f"{column}: {laptop[column]}\n"
            # Добавляем ссылку, если есть
            if 'Link' in df.columns and pd.notna(laptop['Link']) and str(laptop['Link']).strip():
                result += f"🔗 [Ссылка на ноутбук]({laptop['Link']})\n"
            # Отправка фото, если есть
            if 'Images' in df.columns and pd.notna(laptop['Images']):
                images = [url.strip() for url in str(laptop['Images']).split(',') if url.strip()]
                if len(images) == 1:
                    bot.send_photo(message.chat.id, images[0], caption=result, parse_mode='Markdown')
                elif len(images) > 1:
                    media = [types.InputMediaPhoto(url) for url in images]
                    media[0].caption = result
                    media[0].parse_mode = 'Markdown'
                    bot.send_media_group(message.chat.id, media)
                else:
                    bot.send_message(message.chat.id, result, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, result, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == 'Помощь ℹ️')
def help_button(message):
    help(message)

@bot.message_handler(func=lambda message: message.text == 'Очистить чат 🧹')
def clear_chat(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔️ У вас нет прав для этой операции.")
        return
    cleaning_msg = bot.send_message(message.chat.id, "🧹 Очищаю чат...")
    # Сразу удаляем сообщение 'Очищаю чат...'
    try:
        bot.delete_message(message.chat.id, cleaning_msg.message_id)
    except Exception:
        pass
    # Удаляем последние 100 сообщений (бот может удалять только свои и, если админ, чужие тоже)
    try:
        for msg_id in range(message.message_id, message.message_id-100, -1):
            try:
                bot.delete_message(message.chat.id, msg_id)
            except Exception:
                pass
    except Exception:
        pass

if __name__ == '__main__':
    if os.path.exists(RELOAD_FLAG):
        with open(RELOAD_FLAG, 'r') as f:
            chat_id = int(f.read().strip())
        bot.send_message(chat_id, "✅ Бот успешно перезагружен!")
        os.remove(RELOAD_FLAG)
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)
