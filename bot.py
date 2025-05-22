import telebot
import pandas as pd
import os
import sys
from telebot import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize bot with token from .env
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in .env file")

bot = telebot.TeleBot(TOKEN)

# Load laptop data
def load_data():
    try:
        return pd.read_csv('data.csv')
    except FileNotFoundError:
        return pd.DataFrame()

def get_available_options(df, column):
    return sorted(df[column].unique().tolist())

# Create keyboard for specifications
def create_spec_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Screen Size 📏', 'Refresh Rate 🔄', 'Resolution 🖥️')
    keyboard.row('Processor 💻', 'Graphics Card 🎮', 'RAM 💾')
    keyboard.row('Storage 💿', 'Find Laptops 🔍', 'Back to Main ↩️')
    return keyboard

# Create keyboard for main menu
def create_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row('Start Selection 🚀', 'Help ℹ️')
    return keyboard

# Store user preferences
user_preferences = {}

# Map display names to CSV column names
SPEC_MAPPING = {
    'Screen Size': 'Screen Size',
    'Refresh Rate': 'Refresh Rate',
    'Resolution': 'Resolution',
    'Processor': 'Processor',
    'Graphics Card': 'Graphics Card',
    'RAM': 'RAM',
    'Storage': 'Storage'
}

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
    bot.send_message(message.chat.id, 
                     "👋 Welcome to Laptop Selector Bot! 🖥️\n"
                     "I'll help you find the perfect laptop based on your preferences.\n"
                     "Use /help to see available commands.",
                     reply_markup=create_main_keyboard())

@bot.message_handler(commands=['help'])
def help(message):
    help_text = (
        "📋 Available commands:\n"
        "/start - Start the bot 🚀\n"
        "/help - Show this help message ℹ️\n"
        "/reload - Reload the bot 🔄\n"
        "/reset - Reset your preferences 🔁\n\n"
        "To select a laptop, click 'Start Selection 🚀' and follow the prompts."
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['reload'])
def reload(message):
    bot.send_message(message.chat.id, "🔄 Reloading bot...")
    python = sys.executable
    os.execl(python, python, *sys.argv)
    bot.send_message(message.chat.id, "✅ Bot successfully reloaded!")

@bot.message_handler(commands=['reset'])
def reset(message):
    user_preferences[message.chat.id] = {}
    bot.send_message(message.chat.id, "🔄 Your preferences have been reset!", 
                     reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Start Selection 🚀')
def start_selection(message):
    bot.send_message(message.chat.id, 
                     "🔍 Please select the specification you want to set:",
                     reply_markup=create_spec_keyboard())

@bot.message_handler(func=lambda message: message.text == 'Back to Main ↩️')
def back_to_main(message):
    bot.send_message(message.chat.id, 
                     "🏠 Main menu:",
                     reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda message: message.text in ['Screen Size 📏', 'Refresh Rate 🔄', 'Resolution 🖥️', 
                                                         'Processor 💻', 'Graphics Card 🎮', 'RAM 💾', 'Storage 💿'])
def handle_spec_selection(message):
    # Extract the specification name without emoji
    display_spec = ' '.join(message.text.split()[:-1])  # Remove the last word (emoji)
    spec = SPEC_MAPPING[display_spec]  # Get the correct column name
    df = load_data()
    
    if df.empty:
        bot.send_message(message.chat.id, "❌ No laptop data available!")
        return

    # Get filtered options based on current preferences
    filtered_df = get_filtered_options(df, user_preferences.get(message.chat.id, {}))
    available_options = get_available_options(filtered_df, spec)
    
    if not available_options:
        bot.send_message(message.chat.id, "❌ No available options for this specification with current filters!")
        return

    options_text = f"Available {display_spec} options:\n" + "\n".join([f"• {option}" for option in available_options])
    bot.send_message(message.chat.id, 
                     f"Select {display_spec}:\n\n{options_text}",
                     reply_markup=create_options_keyboard(available_options, spec))

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    spec, value = call.data.split(':')
    if call.message.chat.id not in user_preferences:
        user_preferences[call.message.chat.id] = {}
    
    user_preferences[call.message.chat.id][spec] = value
    bot.answer_callback_query(call.id, f"✅ {spec} set to: {value}")
    
    # Update the message to show current selection
    bot.edit_message_text(
        f"✅ {spec} set to: {value}\n\nCurrent preferences:\n" + 
        "\n".join([f"• {k}: {v}" for k, v in user_preferences[call.message.chat.id].items()]),
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda message: message.text == 'Find Laptops 🔍')
def find_laptops(message):
    if message.chat.id not in user_preferences or not user_preferences[message.chat.id]:
        bot.send_message(message.chat.id, "⚠️ Please set at least one specification first!")
        return

    df = load_data()
    if df.empty:
        bot.send_message(message.chat.id, "❌ No laptop data available!")
        return

    # Filter laptops based on user preferences
    filtered_df = df.copy()
    for spec, value in user_preferences[message.chat.id].items():
        if spec in df.columns:
            filtered_df = filtered_df[filtered_df[spec].astype(str).str.contains(str(value), case=False)]

    if filtered_df.empty:
        bot.send_message(message.chat.id, "🔍 No laptops found matching your criteria!")
    else:
        # Format and send results
        for _, laptop in filtered_df.iterrows():
            result = "💻 Laptop Found:\n"
            for column in df.columns:
                result += f"{column}: {laptop[column]}\n"
            bot.send_message(message.chat.id, result)

if __name__ == '__main__':
    print("🤖 Bot started...")
    bot.polling(none_stop=True)
