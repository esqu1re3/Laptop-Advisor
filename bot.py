import telebot
import pandas as pd
import os
import sys
from telebot import types
from telebot.async_telebot import AsyncTeleBot
import asyncio
import logging
from dotenv import load_dotenv

RELOAD_FLAG = 'reload.flag'

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
if not TOKEN:
    raise ValueError("Токен бота не найден в .env файле")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не найден в .env файле")
ADMIN_ID = int(ADMIN_ID)

# Логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

bot = AsyncTeleBot(TOKEN)

def load_data():
    try:
        return pd.read_csv('corrected_data.csv')
    except FileNotFoundError:
        return pd.DataFrame()

def get_available_options(df, column):
    return sorted(df[column].unique().tolist())

def create_spec_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Размер экрана 📏', 'Герцовка 🔄', 'Разрешение 🖥️')
    keyboard.row('Процессор 💻', 'Видеокарта 🎮', 'Оперативная память 💾')
    keyboard.row('Накопитель 💿', 'Найти ноутбуки 🔍', 'В меню ↩️')
    keyboard.row('Сбросить 🔁')
    return keyboard

def create_main_keyboard(is_admin=False):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Начать подбор 🚀', 'Помощь ℹ️')
    if is_admin:
        keyboard.row('Очистить чат 🧹')
        keyboard.row('Перезагрузить бота 🔄')
    return keyboard

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

user_preferences = {}
user_ids = set()
filter_stats = {}

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

def get_user_log_name(user):
    uname = user.username if hasattr(user, 'username') and user.username else None
    fname = user.first_name or ''
    lname = user.last_name or ''
    full_name = (fname + ' ' + lname).strip()
    if uname:
        # Если username и имя совпадают, не дублируем
        if uname.lower() == full_name.lower():
            return f"@{uname}"
        else:
            return f"@{uname} ({full_name})"
    else:
        return full_name

@bot.message_handler(commands=['start'])
async def start(message):
    user_preferences[message.chat.id] = {}
    user_ids.add(message.chat.id)
    user_log_name = get_user_log_name(message.from_user)
    logger.info(f"Пользователь {user_log_name} начал работу. Всего пользователей: {len(user_ids)}")
    is_admin = (message.from_user.id == ADMIN_ID)
    await bot.send_message(message.chat.id, 
                     "👋 Добро пожаловать в бот подбора ноутбуков! 🖥️\n"
                     "Я помогу вам найти идеальный ноутбук по вашим предпочтениям.\n"
                     "Используйте /help для просмотра доступных команд.",
                     reply_markup=create_main_keyboard(is_admin))

@bot.message_handler(commands=['help'])
async def help(message):
    help_text = (
        "📋 Доступные команды:\n"
        "/start - Запустить бота 🚀\n"
        "/help - Показать это сообщение ℹ️\n"
        "/reload - Перезагрузить бота 🔄\n"
        "/reset - Сбросить выбранные характеристики 🔁\n\n"
        "Для подбора ноутбука нажмите 'Начать подбор 🚀' и следуйте инструкциям."
    )
    await bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['reload'])
async def reload(message):
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(message.chat.id, "⛔️ У вас нет прав для перезагрузки бота.")
        return
    await bot.send_message(message.chat.id, "🔄 Перезагрузка бота...")
    with open(RELOAD_FLAG, 'w') as f:
        f.write(str(message.chat.id))
    python = sys.executable
    os.execl(python, python, *sys.argv)

@bot.message_handler(commands=['reset'])
async def reset(message):
    user_preferences[message.chat.id] = {}
    await bot.send_message(message.chat.id, "🔄 Все выбранные характеристики сброшены!", 
                     reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Сбросить 🔁')
async def reset_button(message):
    user_preferences[message.chat.id] = {}
    await bot.send_message(message.chat.id, "🔄 Все выбранные характеристики сброшены!")
    await bot.send_message(message.chat.id, 
                     "🔍 Выберите характеристику, которую хотите установить:",
                     reply_markup=create_spec_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Начать подбор 🚀')
async def start_selection(message):
    await bot.send_message(message.chat.id, 
                     "🔍 Выберите характеристику, которую хотите установить:",
                     reply_markup=create_spec_keyboard())

@bot.message_handler(func=lambda message: message.text == 'В меню ↩️')
async def back_to_main(message):
    is_admin = (message.from_user.id == ADMIN_ID)
    await bot.send_message(message.chat.id, 
                     "🏠 Главное меню:",
                     reply_markup=create_main_keyboard(is_admin))

@bot.message_handler(func=lambda message: message.text in ['Размер экрана 📏', 'Герцовка 🔄', 'Разрешение 🖥️', 
                                                         'Процессор 💻', 'Видеокарта 🎮', 'Оперативная память 💾', 'Накопитель 💿'])
async def handle_spec_selection(message):
    display_spec = ' '.join(message.text.split()[:-1]) 
    spec_mapping = get_spec_mapping()
    spec = spec_mapping[display_spec]
    df = load_data()
    if df.empty:
        await bot.send_message(message.chat.id, "❌ Нет данных о ноутбуках!")
        return
    filtered_df = get_filtered_options(df, user_preferences.get(message.chat.id, {}))
    available_options = get_available_options(filtered_df, spec)
    if not available_options:
        await bot.send_message(message.chat.id, "❌ Нет доступных опций для этой характеристики с текущими фильтрами!")
        return
    options_text = f"Доступные варианты для '{display_spec}':\n" + "\n".join([f"• {option}" for option in available_options])
    await bot.send_message(message.chat.id, 
                     f"Выберите {display_spec}:\n\n{options_text}",
                     reply_markup=create_options_keyboard(available_options, spec))

@bot.callback_query_handler(func=lambda call: True)
async def handle_callback(call):
    spec, value = call.data.split(':')
    if call.message.chat.id not in user_preferences:
        user_preferences[call.message.chat.id] = {}
    user_preferences[call.message.chat.id][spec] = value
    column_rus_emoji = {
        'Screen Size': '📏 Размер экрана',
        'Refresh Rate': '🔄 Частота обновления',
        'Resolution': '🖥️ Разрешение экрана',
        'Processor': '💻 Процессор',
        'Graphics Card': '🎮 Видеокарта',
        'RAM': '💾 Объем оперативной памяти',
        'Storage': '💿 Объем постоянной памяти',
        'Price': '💰 Цена',
        'Model': 'Модель'
    }
    rus_emoji = column_rus_emoji.get(spec, spec)
    await bot.answer_callback_query(call.id, f"✅ {rus_emoji} установлено: {value}")
    selected_specs = [f"• {column_rus_emoji.get(k, k)}: {v}" for k, v in user_preferences[call.message.chat.id].items()]
    await bot.edit_message_text(
        f"✅ {rus_emoji} установлено: {value}\n\nТекущие выбранные характеристики:\n" + 
        "\n".join(selected_specs),
        call.message.chat.id,
        call.message.message_id
    )
    filter_stats[spec] = filter_stats.get(spec, 0) + 1

@bot.message_handler(func=lambda message: message.text == 'Найти ноутбуки 🔍')
async def find_laptops(message):
    try:
        if message.chat.id not in user_preferences or not user_preferences[message.chat.id]:
            await bot.send_message(message.chat.id, "⚠️ Сначала выберите хотя бы одну характеристику!")
            return
        df = load_data()
        if df.empty:
            await bot.send_message(message.chat.id, "❌ Нет данных о ноутбуках!")
            return
        filtered_df = df.copy()
        for spec, value in user_preferences[message.chat.id].items():
            if spec in df.columns:
                filtered_df = filtered_df[filtered_df[spec].astype(str).str.contains(str(value), case=False)]
        if filtered_df.empty:
            await bot.send_message(message.chat.id, "🔍 Не найдено ноутбуков, соответствующих вашим критериям!")
        else:
            await bot.send_message(message.chat.id, f"🔎 Найдено моделей: {len(filtered_df)}")
            column_rus_emoji = {
                'Model': 'Модель',
                'Screen Size': '📏 Размер экрана',
                'Refresh Rate': '🔄 Частота обновления',
                'Resolution': '🖥️ Разрешение экрана',
                'Processor': '💻 Процессор',
                'Graphics Card': '🎮 Видеокарта',
                'RAM': '💾 Объем оперативной памяти',
                'Storage': '💿 Объем постоянной памяти',
                'Price': '💰 Цена'
            }
            for _, laptop in filtered_df.iterrows():
                result = "💻 Найден ноутбук:\n"
                for column in df.columns:
                    if column not in ['Images', 'Link']:
                        value = laptop[column]
                        rus_emoji = column_rus_emoji.get(column, column)
                        if column == 'Refresh Rate':
                            result += f"{rus_emoji}: {value} Гц\n"
                        elif column == 'Price':
                            result += f"{rus_emoji}: {value}\n"
                        else:
                            result += f"{rus_emoji}: {value}\n"
                if 'Link' in df.columns and pd.notna(laptop['Link']) and str(laptop['Link']).strip():
                    result += f"🔗 [Ссылка на ноутбук]({laptop['Link']})\n"
                if 'Images' in df.columns and pd.notna(laptop['Images']):
                    images = [url.strip() for url in str(laptop['Images']).split(',') if url.strip()]
                    if len(images) == 1:
                        await bot.send_photo(message.chat.id, images[0], caption=result, parse_mode='Markdown')
                    elif len(images) > 1:
                        media = [types.InputMediaPhoto(url) for url in images]
                        media[0].caption = result
                        media[0].parse_mode = 'Markdown'
                        await bot.send_media_group(message.chat.id, media)
                    else:
                        await bot.send_message(message.chat.id, result, parse_mode='Markdown')
                else:
                    await bot.send_message(message.chat.id, result, parse_mode='Markdown')
    except Exception as e:
        user_log_name = get_user_log_name(message.from_user)
        logger.exception(f"Ошибка при поиске ноутбуков для пользователя {user_log_name} (id={message.chat.id})")
        await bot.send_message(message.chat.id, "❌ Произошла ошибка при поиске ноутбуков!")

@bot.message_handler(func=lambda message: message.text == 'Помощь ℹ️')
async def help_button(message):
    await help(message)

@bot.message_handler(func=lambda message: message.text == 'Очистить чат 🧹')
async def clear_chat(message):
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(message.chat.id, "⛔️ У вас нет прав для этой операции.")
        return
    cleaning_msg = await bot.send_message(message.chat.id, "🧹 Очищаю чат...")
    try:
        await bot.delete_message(message.chat.id, cleaning_msg.message_id)
    except Exception:
        pass
    try:
        for msg_id in range(message.message_id, message.message_id-100, -1):
            try:
                await bot.delete_message(message.chat.id, msg_id)
            except Exception:
                pass
    except Exception:
        pass

@bot.message_handler(func=lambda message: message.text == 'Перезагрузить бота 🔄')
async def reload_button(message):
    if message.from_user.id != ADMIN_ID:
        await bot.send_message(message.chat.id, "⛔️ У вас нет прав для перезагрузки бота.")
        return
    await bot.send_message(message.chat.id, "🔄 Перезагрузка бота...")
    with open(RELOAD_FLAG, 'w') as f:
        f.write(str(message.chat.id))
    python = sys.executable
    os.execl(python, python, *sys.argv)

if __name__ == '__main__':
    async def main():
        if os.path.exists(RELOAD_FLAG):
            with open(RELOAD_FLAG, 'r') as f:
                chat_id = int(f.read().strip())
            await bot.send_message(chat_id, "✅ Бот успешно перезагружен!")
            os.remove(RELOAD_FLAG)
        logger.info("🤖 Бот запущен...")
        await bot.polling(none_stop=True)
    asyncio.run(main())
