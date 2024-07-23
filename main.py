import logging
import io
import os
import mss
import subprocess
import pyaudio
import wave
import sounddevice as sd
import numpy as np
import cv2
import time
import warnings
import requests
import locale
import random
import json
import speedtest
import shutil
import pyautogui
import ctypes
import tkinter as tk
import threading
import webbrowser
import asyncio
import ast
import importlib
from playsound import playsound
from pynput.keyboard import Controller, Key
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto, Message, User, Chat, BotCommand
import config
from config import TGID, TOKEN, CITY_ID, API_KEY
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, filters, ConversationHandler
from threading import Timer
from PIL import ImageGrab
from PIL import Image
from moviepy.editor import *
from datetime import datetime

def gradient_color(start_color, end_color, lines):
    start_rgb = start_color
    end_rgb = end_color
    steps = len(lines)
    r_step = (end_rgb[0] - start_rgb[0]) / steps
    g_step = (end_rgb[1] - start_rgb[1]) / steps
    b_step = (end_rgb[2] - start_rgb[2]) / steps

    colored_lines = []
    for i, line in enumerate(lines):
        r = int(start_rgb[0] + i * r_step)
        g = int(start_rgb[1] + i * g_step)
        b = int(start_rgb[2] + i * b_step)
        colored_line = f"\033[38;2;{r};{g};{b}m{line}\033[0m"
        colored_lines.append(colored_line)
    return "\n".join(colored_lines)

ascii_art = """
██▓███    ▄████▄  ██▀███   ▓█████ ███▄ ▄███▓ ▒█████  ▄▄▄█████▓ ▓█████
▓██░  ██  ▒██▀ ▀█ ▓██ ▒ ██▒ ▓█   ▀▓██▒▀█▀ ██▒▒██▒  ██▒▓  ██▒ ▓▒ ▓█   ▀
▓██░ ██▓▒ ▒▓█    ▄▓██ ░▄█ ▒ ▒███  ▓██    ▓██░▒██░  ██▒▒ ▓██░ ▒░ ▒███  
▒██▄█▓▒ ▒▒▒▓▓▄ ▄██▒██▀▀█▄   ▒▓█  ▄▒██    ▒██ ▒██   ██░░ ▓██▓ ░  ▒▓█  ▄
▒██▒ ░  ░░▒ ▓███▀ ░██▓ ▒██▒▒░▒████▒██▒   ░██▒░ ████▓▒░  ▒██▒ ░ ▒░▒████
▒▓▒░ ░  ░░░ ░▒ ▒  ░ ▒▓ ░▒▓░░░░ ▒░ ░ ▒░   ░  ░░ ▒░▒░▒░   ▒ ░░   ░░░ ▒░ 
░▒ ░        ░  ▒    ░▒ ░ ▒ ░ ░ ░  ░  ░      ░  ░ ▒ ▒░     ░    ░ ░ ░  
░░        ░         ░░   ░     ░  ░      ░   ░ ░ ░ ▒    ░          ░  
        ░ ░        ░     ░   ░         ░       ░ ░           ░   ░  """

lines = ascii_art.split('\n')
transition_start = len(lines) - 3
colored_ascii_art = gradient_color((0, 0, 255), (255, 255, 255), lines[:transition_start])
colored_ascii_art += "\n" + "\n".join(f"\033[38;2;255;255;255m{line}\033[0m" for line in lines[transition_start:])
terminal_width = shutil.get_terminal_size().columns
max_line_width = max(len(line) for line in lines)
padding = (terminal_width - max_line_width) // 2
centered_ascii_art = "\n".join(f"{' ' * padding}{line}" for line in colored_ascii_art.split('\n'))

user_timers = {}
path_dict = {}
current_paths = {}
app_timers = {}

warnings.filterwarnings("ignore", category=UserWarning)
output_folder = "output"

keyboard_controller = Controller()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)
custom_actions_file = 'custom_actions.json'

locale.setlocale(locale.LC_TIME, 'ru_RU')

# Состояния для ConversationHandler
ENTER_URL, RECORD_MICROPHONE, RECORD_SCREEN = range(3)
ENTER_ACTION_NAME, ENTER_APP_PATH = range(2)
BROWSING, = range(1)
ASK_KEY = range(1)
ENTER_TEXT = 0

# Проверяем наличие файла с пользовательскими действиями при запуске бота
if os.path.exists(custom_actions_file):
    with open(custom_actions_file, 'r') as file:
        custom_actions = json.load(file)
else:
    custom_actions = {}

def translate_day_of_week(day):
    translations = {
        "Monday": "Понедельник",
        "Tuesday": "Вторник",
        "Wednesday": "Среда",
        "Thursday": "Четверг",
        "Friday": "Пятница",
        "Saturday": "Суббота",
        "Sunday": "Воскресенье",
        "Понедельник": "Понедельник",
        "Вторник": "Вторник",
        "Среда": "Среда",
        "Четверг": "Четверг",
        "Пятница": "Пятница",
        "Суббота": "Суббота",
        "Воскресенье": "Воскресенье"
    }
    return translations.get(day, day)

# Сохраняем последние данные в глобальных переменных
last_weather_data = {
    "temperature": "N/A",
    "humidity": "N/A",
    "weather_condition": "N/A",
    "emoji": "N/A"
}
last_currency_data = {
    "usd_rate": "N/A",
    "eur_rate": "N/A",
    "lira_rate": "N/A"
}

def play_startup_sound():
    if config.STARTUP_SOUND_ENABLED:
        resources_path = os.path.join(os.getcwd(), 'resources')
        sound_file_path = os.path.join(resources_path, 'startup.mp3')
        if os.path.exists(sound_file_path):
            playsound(sound_file_path)
        else:
            print("Звуковой файл не найден.")

async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in TGID:
        await send_start_message(update, context)
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этому боту.", parse_mode='MARKDOWN')

async def send_start_message(update: Update, context: CallbackContext) -> None:
    global last_weather_data, last_currency_data

    # Получаем текущую дату и время
    now = datetime.now()
    day_of_week = now.strftime("%A")
    month_names = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    date = f"{now.day} {month_names[now.month - 1]}"
    time = now.strftime("%H:%M")
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?id={CITY_ID}&appid={API_KEY}&units=metric&lang=ru"

    try:
        response = requests.get(weather_url)
        response.raise_for_status()
        weather_data = response.json()

        if "main" in weather_data:
            temperature = weather_data["main"]["temp"]
            humidity = weather_data["main"]["humidity"]
            weather_condition = weather_data["weather"][0]["description"]
            emoji = "☀️"
            wind_speed = weather_data["wind"]["speed"]

            if "дождь" in weather_condition:
                emoji = "🌧️"
            elif "облачно" in weather_condition:
                emoji = "☁️"
            elif "снег" in weather_condition:
                emoji = "❄️"
            
            last_weather_data = {
                "temperature": temperature,
                "humidity": humidity,
                "weather_condition": weather_condition,
                "emoji": emoji,
                "wind_speed": wind_speed
            }
        else:
            raise ValueError("Invalid weather data")
    except (requests.RequestException, ValueError):
        # Используем последние известные данные, если возникла ошибка
        temperature = last_weather_data.get("temperature", "N/A")
        humidity = last_weather_data.get("humidity", "N/A")
        weather_condition = last_weather_data.get("weather_condition", "N/A")
        emoji = last_weather_data.get("emoji", "❓")
        wind_speed = last_weather_data.get("wind_speed", "N/A")

    # Получаем курсы валют
    currency_url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        currency_response = requests.get(currency_url)
        currency_response.raise_for_status()
        currency_data = currency_response.json()

        if "Valute" in currency_data:
            try:
                usd_rate = currency_data["Valute"]["USD"]["Value"]
                usd_rate = "{:.2f}".format(usd_rate)
            except KeyError:
                usd_rate = "N/A"

            try:
                eur_rate = currency_data["Valute"]["EUR"]["Value"]
                eur_rate = "{:.2f}".format(eur_rate)
            except KeyError:
                eur_rate = "N/A"

            try:
                lira_rate = currency_data["Valute"]["TRY"]["Value"] / 10
                lira_rate = "{:.2f}".format(lira_rate)
            except KeyError:
                lira_rate = "N/A"
            
            last_currency_data = {
                "usd_rate": usd_rate,
                "eur_rate": eur_rate,
                "lira_rate": lira_rate
            }
        else:
            raise ValueError("Invalid currency data")
    except (requests.RequestException, ValueError):
        # Используем последние известные данные, если возникла ошибка
        usd_rate = last_currency_data.get("usd_rate", "N/A")
        eur_rate = last_currency_data.get("eur_rate", "N/A")
        lira_rate = last_currency_data.get("lira_rate", "N/A")

    # Путь к папке с изображениями погоды
    weather_images_path = "resources/weather"
    weather_images = [f for f in os.listdir(weather_images_path) if f.endswith('.jpg')]
    random_image = random.choice(weather_images)
    image_path = os.path.join(weather_images_path, random_image)

    # Составляем стартовое сообщение
    start_message = (
        f"<b>🖥️ Мы подключены и готовы, сэр!</b>\n\n"
        f"•  Сегодня <b>{day_of_week}, {date}</b>.\n"
        f"•  Время <b>{time}</b>\n"
        f"•  За окном <b>{humidity}%</b> 💦, <b>{temperature}°C</b>, {emoji} <b>{weather_condition}</b>\n\n"
    )
    start_message += (
        f"<b>💵 Курс доллара:</b> {usd_rate} руб.\n"
        f"<b>💶 Курс евро:</b> {eur_rate} руб.\n"
        f"<b>💴 Курс лиры:</b> {lira_rate} руб."
    )

    # Определяем кнопки клавиатуры
    keyboard = [
        [
            InlineKeyboardButton("⚠️ Выключить", callback_data='shutdown'),
            InlineKeyboardButton("🔄 Перезагрузить", callback_data='reboot'),
        ],
        [
            InlineKeyboardButton("💤 Спящий режим", callback_data='sleep_computer'),
            InlineKeyboardButton("🔒 Заблокировать", callback_data='lock'),
        ],
        [
            InlineKeyboardButton("📸 Скриншот", callback_data='screenshot'),
            InlineKeyboardButton("✍️ Ввести текст", callback_data='input_text'),
        ],
        [
            InlineKeyboardButton("🌐 Скорость интернета", callback_data='check_speed'),
            InlineKeyboardButton("🔗 Открыть ссылку", callback_data='open_url'),
        ],
        [
            InlineKeyboardButton("🔊 Повысить громкость", callback_data='volume_up'),
            InlineKeyboardButton("🔉 Понизить громкость", callback_data='volume_down'),
        ],
        [
            InlineKeyboardButton("🎙️ Запись микрофона", callback_data='record_microphone'),
            InlineKeyboardButton("📹 Запись экрана", callback_data='record_screen'),
        ],
        [
            InlineKeyboardButton("⌨️ Нажать клавишу", callback_data='ask_key'),
            InlineKeyboardButton("🗑️ Очистить корзину", callback_data='clear_cart'),
        ],
        [
            InlineKeyboardButton("✨ Мои действия", callback_data='custom_actions'),
            InlineKeyboardButton("📂 Просмотр файлов", callback_data='start_browsing')
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
        ],
    ]

    # Создаем клавиатуру с указанием кнопок
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query and update.callback_query.message:
        message_id = update.callback_query.message.message_id
        chat_id = update.callback_query.message.chat_id

        if update.callback_query.message.photo:
            await context.bot.edit_message_media(
                media=InputMediaPhoto(media=open(image_path, 'rb')),
                chat_id=chat_id,
                message_id=message_id,
                caption=start_message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return

    sent_message = await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(image_path, 'rb'),
        caption=start_message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    context.user_data['start_message_id'] = sent_message.message_id

def update_config_value(file_path, variable_name, new_value):
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=file_path)

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == variable_name:
                node.value = ast.parse(repr(new_value)).body[0].value

    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(ast.unparse(tree))

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    action = query.data
    user_data = context.user_data

    if action == 'custom_actions':
        custom_action_names = list(custom_actions.keys())
        keyboard = []
        for i in range(0, len(custom_action_names), 2):
            row = [
                InlineKeyboardButton(custom_action_names[i], callback_data=f'run_custom_action:{custom_action_names[i]}')
            ]
            if i + 1 < len(custom_action_names):
                row.append(InlineKeyboardButton(custom_action_names[i + 1], callback_data=f'run_custom_action:{custom_action_names[i + 1]}'))
            keyboard.append(row)
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query.message and query.message.photo:
            # Удаляем старую фотографию
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
            # Отправляем новое сообщение с фотографией и клавиатурой
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text='*✨ Выберите действие:*',
                reply_markup=reply_markup,
                parse_mode='MARKDOWN'
            )
        else:
            if query.message and query.message.text:
                await query.message.edit_text('*✨ Выберите действие:*', reply_markup=reply_markup, parse_mode='MARKDOWN')
            elif query.message and query.message.caption:
                await query.message.edit_caption('*✨ Выберите действие:*', reply_markup=reply_markup, parse_mode='MARKDOWN')
            else:
                await query.edit_message_text('*✨ Выберите действие:*', reply_markup=reply_markup, parse_mode='MARKDOWN')

    elif action == 'settings':
        importlib.reload(config)
        soundon_keyboard = [
            [InlineKeyboardButton("❌ Отключить звук запуска", callback_data='disable_startup_sound')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')]
        ]
        sound_on = InlineKeyboardMarkup(soundon_keyboard) 

        soundoff_keyboard = [
            [InlineKeyboardButton("✅ Включить звук запуска", callback_data='enable_startup_sound')],
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')]
        ]
        sound_off = InlineKeyboardMarkup(soundoff_keyboard) 

        # Выбор правильной клавиатуры
        current_markup = sound_on if config.STARTUP_SOUND_ENABLED else sound_off

        if query.message and query.message.photo:
            # Удаляем старую фотографию
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
            # Отправляем новое сообщение с фотографией и клавиатурой
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text='*✨ Выберите действие:*',
                reply_markup=current_markup,
                parse_mode='MARKDOWN'
            )
        else:
            if query.message and query.message.text:
                await query.message.edit_text('*✨ Выберите действие:*', reply_markup=current_markup, parse_mode='MARKDOWN')
            elif query.message and query.message.caption:
                await query.message.edit_caption('*✨ Выберите действие:*', reply_markup=current_markup, parse_mode='MARKDOWN')
            else:
                await query.edit_message_text('*✨ Выберите действие:*', reply_markup=current_markup, parse_mode='MARKDOWN')

    elif action == 'disable_startup_sound':
        # Логика для отключения звука запуска

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard) 


        update_config_value('config.py', 'STARTUP_SOUND_ENABLED', False)
        await query.edit_message_text(text="🔇 *Звук запуска отключен.*", parse_mode='MARKDOWN', reply_markup=reply_markup)

    elif action == 'enable_startup_sound':
        # Логика для отключения звука запуска

        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_start')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update_config_value('config.py', 'STARTUP_SOUND_ENABLED', True)
        await query.edit_message_text(text="🔇 *Звук запуска включен.*", parse_mode='MARKDOWN', reply_markup=reply_markup)

    elif action.startswith('run_custom_action:'):
        action_name = action.split(':')[1]
        app_path = custom_actions.get(action_name)
        
        if app_path:
            subprocess.Popen(app_path, shell=True)
            # Добавляем кнопку "Вернуться назад" после выполнения действия
            keyboard = [[InlineKeyboardButton("⬅️ Вернуться назад", callback_data='custom_actions')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if query.message and query.message.text:
                await query.message.edit_text(f"*🚀 Выполняю действие: {action_name}*", reply_markup=reply_markup, parse_mode='MARKDOWN')
            else:
                await query.message.reply_text(f"*🚀 Выполняю действие: {action_name}*", reply_markup=reply_markup, parse_mode='MARKDOWN')
        else:
            await query.message.reply_text("❌ *Ошибка:* Не удалось найти путь для пользовательского действия.", parse_mode='MARKDOWN')

    elif action == 'back_to_start':
        await send_start_message(update, context)
        # Удаляем текущее сообщение "Выберите папку или файл:", если оно есть
        if query.message.text:
            await query.message.delete()
        elif query.message.caption:
            await query.message.delete_caption()
        else:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)

    # Остальная логика кнопок
    elif action == 'shutdown':
        await query.message.reply_text(text="*💤 Выключаю компьютер...*", parse_mode='MARKDOWN')
        subprocess.run(["shutdown", "/s", "/t", "0"])

    elif action == 'reboot':
        await query.message.reply_text(text="*🔄 Перезагружаю компьютер...*", parse_mode='MARKDOWN')
        subprocess.run(["shutdown", "/r", "/t", "0"])

    elif action == 'lock':
        await query.message.reply_text(text="*🔒 Блокирую экран...*", parse_mode='MARKDOWN')
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])

    elif action == 'screenshot':
        await query.message.reply_text(text="*📸 Создаю скриншот...*", parse_mode='MARKDOWN')
        await screenshot(update, context)

    elif action == 'open_url':
        await query.message.reply_text(text="*⛓️ Введите ссылку для открытия:*", parse_mode='MARKDOWN')
        return ENTER_URL
    
    elif action == 'record_microphone':
        await query.message.reply_text("*🎤 Запись с микрофона (ожидайте 15с)*", parse_mode='MARKDOWN')
        await record_microphone(update, context)
        return RECORD_MICROPHONE
    
    elif action == 'record_screen':
        await query.message.reply_text(text="*🎥 Запись с экрана (ожидайте 15с)*", parse_mode='MARKDOWN')
        await record_screen(update, context)
        return RECORD_SCREEN
    
    elif action == 'check_speed':
        await query.message.reply_text(text="*✨ Проверка скорости вашего интернет-соединения займёт 20 секунд...*", parse_mode='MARKDOWN')
        speed_result = check_speed()
        await query.message.reply_text(text=speed_result, parse_mode='MARKDOWN')

    elif action == 'clear_cart':
        await query.message.reply_text(text="*🗑️ Очистка корзины...*", parse_mode='MARKDOWN')
        await clear_cart(update, context)

    elif action == 'input_text':
        msg = await query.message.reply_text("*🖋️ Введите текст для отображения на экране компьютера:*", parse_mode='MARKDOWN')
        save_message_id(context, msg.message_id)
        return ENTER_TEXT
    
    elif action == 'ask_key':
        msg = await query.message.reply_text("*✨ Введите клавишу, которую нужно нажать:*", parse_mode='MARKDOWN')
        context.user_data['ask_key_msg_id'] = msg.message_id
        context.user_data['ask_key_chat_id'] = msg.chat_id
        return ASK_KEY
    
    elif action == 'volume_up':
        await volume_up(update, context)

    elif action == 'volume_down':
        await volume_down(update, context)

    elif action == 'sleep_computer':
        sleep_computer(update, context)

    elif action.startswith('open_folder:'):
        folder_id = action.split(':')[1]
        new_path = path_dict.get(folder_id)
        if new_path:
            parent_path = os.path.dirname(new_path)
            current_paths[update.effective_user.id] = (new_path, parent_path)
            reply_markup = list_directory(new_path, user_data)
            await query.edit_message_text(text=f"👀 *Вы просматриваете:* `{new_path}`", reply_markup=reply_markup, parse_mode='MARKDOWN')
        else:
            await query.message.reply_text("❌ *Ошибка:* Путь не найден.", parse_mode='MARKDOWN')

    elif action.startswith('open_file:'):
        file_id = action.split(':')[1]
        file_path = path_dict.get(file_id)
        if file_path:
            await query.message.reply_document(document=open(file_path, 'rb'))
        else:
            await query.message.reply_text("❌ *Ошибка:* Файл не найден.", parse_mode='MARKDOWN')

    elif action == 'access_denied':
        await query.message.reply_text("*⛔ Доступ запрещен к этому каталогу.*", parse_mode='MARKDOWN')
        
    elif action == 'folder_not_found':
        await query.message.reply_text("*⛔ Папка не найдена.*", parse_mode='MARKDOWN')

    elif action == 'start_browsing':
        # Начало просмотра файловой системы
        await start_browsing(update, context)

    elif action == 'go_up':
        current_path, parent_path = current_paths.get(update.effective_user.id, (None, None))
        if parent_path:
            reply_markup = list_directory(parent_path, user_data)
            await query.edit_message_text(text=f"👀 *Вы просматриваете:* `{parent_path}`", reply_markup=reply_markup, parse_mode='MARKDOWN')
            current_paths[update.effective_user.id] = (parent_path, os.path.dirname(parent_path))
        else:
            await query.message.reply_text("❌ *Ошибка:* Невозможно вернуться на уровень выше.", parse_mode='MARKDOWN')

    else:
        print(f"Неизвестное действие: {action}")  # Добавляем отладочный вывод
        await query.message.reply_text("❌ *Ошибка:* Неизвестное действие.", parse_mode='MARKDOWN')

    return ConversationHandler.END

def list_directory(path, user_data):
    """Возвращает список инлайн-кнопок для файлов и папок в заданном каталоге"""
    keyboard = []
    folders = []
    files = []

    try:

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            item_id = len(path_dict)  # Используем простой числовой идентификатор
            path_dict[str(item_id)] = item_path
            if os.path.isdir(item_path):
                folders.append(InlineKeyboardButton(f"📁 {item}", callback_data=f'open_folder:{item_id}'))
            else:
                files.append(InlineKeyboardButton(f"📄 {item}", callback_data=f'open_file:{item_id}'))
    except PermissionError:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⛔ Доступ запрещен", callback_data='access_denied')]])
    except FileNotFoundError:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⛔ Папка не найдена", callback_data='folder_not_found')]])

    for i in range(0, len(folders), 2):
        keyboard.append(folders[i:i + 2])
    for i in range(0, len(files), 2):
        keyboard.append(files[i:i + 2])

    if path != '/':
        parent_folder_id = len(path_dict)  # Используем новый идентификатор для кнопки "Назад"
        path_dict[str(parent_folder_id)] = os.path.dirname(path)  # Сохраняем путь к родительской папке
        keyboard.append([InlineKeyboardButton("⬆️ Назад", callback_data=f'open_folder:{parent_folder_id}')])

    # Кнопка для возврата в начало
    keyboard.append([InlineKeyboardButton("⬅️ Вернуться в начало", callback_data='back_to_start')])

    return InlineKeyboardMarkup(keyboard)

async def start_browsing(update: Update, context: CallbackContext) -> None:
    """Начинает просмотр файловой системы с корневого каталога"""
    query = update.callback_query
    await query.answer()
    
    root_path = 'C:\\'
    reply_markup = list_directory(root_path, context.user_data)
    
    sent_message = await query.message.reply_text(
        text="✨ *Выберите папку или файл:*",
        reply_markup=reply_markup,
        parse_mode='MARKDOWN'
    )

    if 'start_message_id' in context.user_data:
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=context.user_data['start_message_id']
        )

    context.user_data['last_sent_message_id'] = sent_message.message_id

    return BROWSING

def save_message_id(context: CallbackContext, message_id: int) -> None:
    if 'last_message_id' in context.user_data:
        context.user_data['previous_message_id'] = context.user_data['last_message_id']
    context.user_data['last_message_id'] = message_id

async def delete_last_two_messages(context: CallbackContext, chat_id: int) -> None:
    if 'last_message_id' in context.user_data:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['last_message_id'])
        context.user_data.pop('last_message_id')
    if 'user_message_id' in context.user_data:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data['user_message_id'])
        context.user_data.pop('user_message_id')

def show_text_on_screen(text: str) -> None:
    try:
        # Создаем основное окно tkinter
        root = tk.Tk()
        root.attributes("-fullscreen", True)  # устанавливаем полноэкранный режим
        root.attributes("-topmost", True)  # окно всегда на первом плане

        # Создаем черный фон на всю площадь окна
        canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg="black")
        canvas.pack()

        # Размещаем текст по центру окна
        text_label = tk.Label(canvas, text=text, fg="white", bg="black", font=("Helvetica", 24))
        text_label.place(relx=0.5, rely=0.5, anchor="center")

        # Закрываем окно через 5 секунд
        root.after(5000, root.destroy)

        root.mainloop()

    except Exception as e:
        print(f"Ошибка при отображении текста на экране: {str(e)}")

async def receive_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    context.user_data['user_message_id'] = update.message.message_id
    show_text_on_screen(text)
    await delete_last_two_messages(context, update.message.chat_id)
    await context.bot.send_message(chat_id=update.message.chat_id, text="✅ *Текст был успешно отображен*", parse_mode='MARKDOWN')
    return ConversationHandler.END

def is_russian(text):
    return any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in text)

def get_key(key_str):
    key_str = key_str.strip().upper()
    if key_str == 'ENTER':
        return Key.enter
    elif key_str == 'ESC':
        return Key.esc
    elif key_str == 'SPACE':
        return Key.space
    elif key_str == 'BACKSPACE':
        return Key.backspace
    elif key_str == 'TAB':
        return Key.tab
    elif key_str == 'CAPSLOCK':
        return Key.caps_lock
    elif key_str == 'NUMLOCK':
        return Key.num_lock
    elif key_str == 'SCROLLLOCK':
        return Key.scroll_lock
    elif key_str == 'SHIFT':
        return Key.shift
    elif key_str == 'CTRL':
        return Key.ctrl
    elif key_str == 'ALT':
        return Key.alt
    elif key_str == 'PAUSE':
        return Key.pause
    elif key_str == 'INSERT':
        return Key.insert
    elif key_str == 'DELETE':
        return Key.delete
    elif key_str == 'HOME':
        return Key.home
    elif key_str == 'END':
        return Key.end
    elif key_str == 'PAGEUP':
        return Key.page_up
    elif key_str == 'PAGEDOWN':
        return Key.page_down
    elif key_str == 'LEFT':
        return Key.left
    elif key_str == 'RIGHT':
        return Key.right
    elif key_str == 'UP':
        return Key.up
    elif key_str == 'DOWN':
        return Key.down
    elif key_str.startswith('F') and key_str[1:].isdigit():
        try:
            return getattr(Key, key_str.lower())
        except AttributeError:
            return None
    elif len(key_str) == 1 and key_str.isalpha():
        return key_str
    else:
        return None

async def ask_key(update: Update, context: CallbackContext) -> int:
    key_input = update.message.text

    # Проверяем, есть ли русские буквы в клавише
    if is_russian(key_input):
        await update.message.reply_text("❌ *Ошибка:* Введена недопустимая клавиша. Пожалуйста, введите корректную клавишу на латинице.", parse_mode='MARKDOWN')
        return ASK_KEY

    try:
        if '*' in key_input:
            key, times = key_input.split('*', 1)
            key = key.strip().upper()
            times = times.strip()

            # Проверяем, что times является числом
            try:
                times = int(times)
                if times < 1:
                    raise ValueError("Количество нажатий должно быть положительным числом.")
            except ValueError as e:
                await update.message.reply_text(f"❌ *Ошибка:* {str(e)}", parse_mode='MARKDOWN')
                return ASK_KEY

            # Получаем клавишу
            key = get_key(key)
            if key is None:
                await update.message.reply_text("❌ *Ошибка:* Введена недопустимая клавиша. Пожалуйста, введите корректную клавишу.", parse_mode='MARKDOWN')
                return ASK_KEY

            # Обрабатываем множественные нажатия
            for _ in range(times):
                if isinstance(key, Key):
                    keyboard_controller.press(key)
                    keyboard_controller.release(key)
                else:
                    keyboard_controller.press(key)
                    keyboard_controller.release(key)
        
        elif '+' in key_input:
            keys = key_input.split('+')
            keys = [key.strip().upper() for key in keys]

            pressed_keys = []
            for key in keys:
                key_obj = get_key(key)
                if key_obj is None:
                    await update.message.reply_text("❌ *Ошибка:* Введена недопустимая клавиша. Пожалуйста, введите корректную клавишу.", parse_mode='MARKDOWN')
                    return ASK_KEY
                else:
                    pressed_keys.append(key_obj)
                    keyboard_controller.press(key_obj)

            # Отпускаем все клавиши в обратном порядке
            for key in reversed(pressed_keys):
                keyboard_controller.release(key)

        else:
            key = get_key(key_input)
            if key is None:
                await update.message.reply_text("❌ *Ошибка:* Введена недопустимая клавиша. Пожалуйста, введите корректную клавишу.", parse_mode='MARKDOWN')
                return ASK_KEY
            
            if isinstance(key, Key):
                keyboard_controller.press(key)
                keyboard_controller.release(key)
            else:
                keyboard_controller.press(key)
                keyboard_controller.release(key)

        # Удаление сообщений
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        await context.bot.delete_message(chat_id=context.user_data['ask_key_chat_id'], message_id=context.user_data['ask_key_msg_id'])

        await update.message.reply_text(f"✅ *Клавиша *`{key_input}`* была нажата.*", parse_mode='MARKDOWN')
    except Exception as e:
        print(f"Ошибка при нажатии клавиши {key_input}: {e}")
        await update.message.reply_text(f"❌ *Ошибка при нажатии клавиши '{key_input}'.* Попробуйте еще раз.", parse_mode='MARKDOWN')
        return ASK_KEY

    return ConversationHandler.END
async def sleep_computer(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("*💤 Перевожу компьютер в спящий режим...*", parse_mode='MARKDOWN')
    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])

def check_speed():
    try:
        st = speedtest.Speedtest()
        best_server = st.get_best_server()  # Получение лучшего сервера
        st.download()
        st.upload()
        res = st.results.dict()
        download_speed = res['download'] / 1_000_000  # конвертируем в Mbps
        upload_speed = res['upload'] / 1_000_000  # конвертируем в Mbps
        ping = res['ping']
        server_name = best_server['sponsor']
        server_location = best_server['name']
        server_country = best_server['country']
        return (f"💫 *Результаты спидтеста:* \n\n"
                f"⬇️ Скорость скачивания: *{download_speed:.2f} Mbps*\n"
                f"⬆️ Скорость загрузки: *{upload_speed:.2f} Mbps*\n"
                f"🛜 Пинг: *{ping} ms*\n"
                f"📍 Сервер: *{server_name}, {server_location}, {server_country}*")
    except speedtest.ConfigRetrievalError as e:
        return f"❌ *Ошибка:* Не удалось получить конфигурацию для проверки скорости. Попробуйте позже. {e}"
    except speedtest.NoMatchedServers:
        return "❌ *Ошибка:* Не удалось найти подходящий сервер для проверки скорости. Попробуйте позже."
    except speedtest.SpeedtestBestServerFailure:
        return "❌ *Ошибка:* Не удалось найти лучший сервер для проверки скорости. Попробуйте позже."
    except speedtest.SpeedtestException as e:
        return f"❌ *Ошибка:* Произошла ошибка при проверке скорости: {e}"
    except Exception as e:
        return f"❌ *Ошибка:* Произошла непредвиденная ошибка при проверке скорости: {e}"

async def volume_up(update, context):
    # Нажимаем горячую клавишу для увеличения громкости
    pyautogui.press('volumeup', presses=5)
    await update.callback_query.message.reply_text("*🔊 Громкость увеличена на 10%.*", parse_mode='MARKDOWN')

async def volume_down(update, context):
    # Нажимаем горячую клавишу для увеличения громкости
    pyautogui.press('volumedown', presses=5)
    await update.callback_query.message.reply_text("*🔊 Громкость уменьшена на 10%.*", parse_mode='MARKDOWN')

async def screenshot(update: Update, context: CallbackContext) -> None:
    with mss.mss() as sct:
        # Получаем список всех экранов
        monitors = sct.monitors[1:]  # sct.monitors[0] - это все мониторы вместе, остальные - индивидуальные экраны
        
        media_group = []
        
        for i, monitor in enumerate(monitors):
            # Захватываем скриншот текущего экрана
            screenshot = sct.grab(monitor)
            
            # Конвертируем в PIL Image
            img = Image.frombytes('RGB', (screenshot.width, screenshot.height), screenshot.rgb)
            
            # Сохраняем скриншот в байтовый поток
            bio = io.BytesIO()
            bio.name = f'screenshot_{i+1}.png'
            img.save(bio, 'PNG')
            bio.seek(0)
            
            # Добавляем байтовый поток в список медиа
            media_group.append(InputMediaPhoto(bio))
        
        # Отправляем все скриншоты в одном сообщении
        await context.bot.send_media_group(chat_id=update.callback_query.message.chat_id, media=media_group)

# Функция для получения ссылки от пользователя и её открытия в браузере
async def receive_url(update: Update, context: CallbackContext) -> int:
    url = update.message.text
    # Открытие URL в браузере по умолчанию
    webbrowser.open(url)
    await update.message.reply_text(f'*✅ Ссылка {url} открыта в браузере.*', parse_mode='MARKDOWN', disable_web_page_preview=True)

    return ConversationHandler.END

# Функция для записи звука с микрофона
async def record_microphone(update: Update, context: CallbackContext) -> None:
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 15
    WAVE_OUTPUT_FILENAME = os.path.join(output_folder, "output_microphone.wav")

    # Проверяем, существует ли папка для сохранения файла, если нет, создаём её
    os.makedirs(output_folder, exist_ok=True)

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []

    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

    # Отправка аудиофайла в Telegram в виде голосового сообщения
    with open(WAVE_OUTPUT_FILENAME, 'rb') as audio:
        await context.bot.send_voice(chat_id=update.callback_query.message.chat_id, voice=audio)

    # Удаление временного файла
    os.remove(WAVE_OUTPUT_FILENAME)

async def record_screen(update: Update, context: CallbackContext) -> None:
    # Установите время записи в секундах
    RECORD_SECONDS = 15

    # Проверяем, существует ли папка output, и если нет, создаем её
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Задайте имя временного файла
    TEMP_VIDEO_FILENAME = os.path.join(output_folder, "temp_screen_record.mp4").replace('\\', '/')

    # Получите размер экрана
    screen_width, screen_height = ImageGrab.grab().size
    # Установите разрешение видео
    resolution = (screen_width, screen_height)

    # Создайте объект VideoWriter для записи видео
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Изменено для сохранения в формате MP4
    out = cv2.VideoWriter(TEMP_VIDEO_FILENAME, fourcc, 15.0, resolution)

    start_time = time.time()

    while (time.time() - start_time) < RECORD_SECONDS:
        # Захватите изображение экрана
        img = ImageGrab.grab()
        # Преобразуйте изображение в массив numpy
        frame = np.array(img)
        # Конвертируйте BGR в RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Запишите кадр
        out.write(frame)

    # Освободите объект VideoWriter
    out.release()

    # Отправьте видео в Telegram как видеозапись
    try:
        with open(TEMP_VIDEO_FILENAME, 'rb') as video:
            await context.bot.send_video(chat_id=update.callback_query.message.chat_id, video=video, supports_streaming=True)
    except Exception as e:
        print("Ошибка при отправке видео в Telegram:", e)

    # Проверяем, существует ли файл перед его удалением
    if os.path.exists(TEMP_VIDEO_FILENAME):
        os.remove(TEMP_VIDEO_FILENAME)
    else:
        print("Временный файл не был удалён.")

async def clear_cart(update: Update, context: CallbackContext) -> None:
    try:
        # Определение констант
        SHERB_NOCONFIRMATION = 0x00000001
        SHERB_NOPROGRESSUI = 0x00000002
        SHERB_NOSOUND = 0x00000004

        # Вызов функции SHEmptyRecycleBin
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND)

        if result == 0:
            message = await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text='✅ *Корзина очищена*', parse_mode='MARKDOWN')
        elif result == -2147418113:
            message = await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text='🤖 *Корзина пуста*', parse_mode='MARKDOWN')
        else:
            message = await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=f'❌ *Ошибка*: код ошибки {result}', parse_mode='MARKDOWN')

        # Сохраняем message_id в user_data
        context.user_data['clear_cart_message_id'] = message.message_id
        
    except Exception as e:
        await context.bot.send_message(chat_id=update.callback_query.message.chat_id, text=f'❌ *Ошибка*: {str(e)}')

# Функция для отмены ввода ссылки
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text('*❌ Отмена операции.*', parse_mode='MARKDOWN')
    return ConversationHandler.END

# Обработчик команды /reboot
async def reboot(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in TGID:
        time_args = context.args
        if len(time_args) != 3:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /reboot 1h 59m 59s", parse_mode='MARKDOWN')
            return

        try:
            hours = int(time_args[0].replace('h', '')) * 3600
            minutes = int(time_args[1].replace('m', '')) * 60
            seconds = int(time_args[2].replace('s', ''))
            total_seconds = hours + minutes + seconds
        except ValueError:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /reboot 1h 59m 59s", parse_mode='MARKDOWN')
            return

        new_timer = Timer(total_seconds, os.system, ["shutdown -r -t 1"])
        new_timer.start()

        if user_id not in user_timers:
            user_timers[user_id] = []
        user_timers[user_id].append(new_timer)

        await update.message.reply_text(f"*✅ Перезапуск компьютера запланирован через {total_seconds} секунд*", parse_mode='MARKDOWN')
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этой команде.", parse_mode='MARKDOWN')

# Обработчик команды /stop
async def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in TGID:
        time_args = context.args
        if len(time_args) != 3:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /stop 1h 59m 59s", parse_mode='MARKDOWN')
            return

        try:
            hours = int(time_args[0].replace('h', '')) * 3600
            minutes = int(time_args[1].replace('m', '')) * 60
            seconds = int(time_args[2].replace('s', ''))
            total_seconds = hours + minutes + seconds
        except ValueError:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /stop 1h 59m 59s", parse_mode='MARKDOWN')
            return

        new_timer = Timer(total_seconds, os.system, ["shutdown -s -t 1"])
        new_timer.start()

        if user_id not in user_timers:
            user_timers[user_id] = []
        user_timers[user_id].append(new_timer)

        await update.message.reply_text(f"*✅ Выключение компьютера запланировано через {total_seconds} секунд*", parse_mode='MARKDOWN')
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этой команде.", parse_mode='MARKDOWN')

async def add_custom_action(update, context):
    await update.message.reply_text("*✨ Введите название вашего действия:*", parse_mode='MARKDOWN')
    return ENTER_ACTION_NAME

async def receive_action_name(update, context):
    action_name = update.message.text
    context.user_data['action_name'] = action_name
    await update.message.reply_text("*✨ Теперь отправьте путь к ярлыку приложения (.lnk):*", parse_mode='MARKDOWN')
    return ENTER_APP_PATH

async def receive_app_path(update, context):
    action_name = context.user_data['action_name']
    app_path = update.message.text
    custom_actions[action_name] = app_path
    save_custom_actions()
    await update.message.reply_text(f"*✅ Пользовательское действие '{action_name}' успешно добавлено.*", parse_mode='MARKDOWN')
    return ConversationHandler.END

async def undo(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in TGID:
        os.system("shutdown /a")  # Отменяем все запланированные действия
        if user_id in user_timers:
            for timer in user_timers[user_id]:
                timer.cancel()  # Отменяем каждый таймер
            user_timers[user_id] = []  # Очищаем список таймеров
        await update.message.reply_text("*✅ Все запланированные действия отменены*", parse_mode='MARKDOWN')
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этой команде.", parse_mode='MARKDOWN')

async def sleep(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in TGID:
        time_args = context.args
        if len(time_args) != 3:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /sleep 1h 59m 59s", parse_mode='MARKDOWN')
            return

        if time_args[0] != '/t':
            await update.message.reply_text("❌ *Ошибка:* Не указан параметр для времени спящего режима.", parse_mode='MARKDOWN')
            return

        try:
            hours = int(time_args[1].replace('h', '')) * 3600
            minutes = int(time_args[2].replace('m', '')) * 60
            seconds = int(time_args[3].replace('s', ''))
            total_seconds = hours + minutes + seconds
        except ValueError:
            await update.message.reply_text("❌ *Ошибка:* Неверный формат времени. Используйте /sleep 1h 59m 59s", parse_mode='MARKDOWN')
            return

        new_timer = Timer(total_seconds, os.system, [f"shutdown /h /t {total_seconds}"])
        new_timer.start()

        if user_id not in user_timers:
            user_timers[user_id] = []
        user_timers[user_id].append(new_timer)

        await update.message.reply_text(f"*✅ Перевод компьютера в спящий режим запланирован через {total_seconds} секунд*", parse_mode='MARKDOWN')
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этой команде.", parse_mode='MARKDOWN')

def save_custom_actions():
    with open(custom_actions_file, 'w') as file:
        json.dump(custom_actions, file)

async def schedule_app(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in TGID:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text(
                "❌ *Ошибка:* Неверный формат команды. Используйте /timer <app\_path> <hours>h <minutes>m <seconds>s",
                parse_mode='Markdown'
            )
            return

        # Объединяем все аргументы до последних трех в путь к приложению
        app_path = ' '.join(args[:-3])
        time_args = args[-3:]

        try:
            hours = int(time_args[0].replace('h', '')) * 3600
            minutes = int(time_args[1].replace('m', '')) * 60
            seconds = int(time_args[2].replace('s', ''))
            total_seconds = hours + minutes + seconds
        except ValueError:
            await update.message.reply_text(
                "❌ *Ошибка:* Неверный формат времени. Используйте /timer <app\_path> <hours>h <minutes>m <seconds>s",
                parse_mode='Markdown'
            )
            return

        async def run_app():
            try:
                if os.path.exists(app_path):
                    if app_path.endswith('.exe'):
                        subprocess.Popen(app_path)
                    else:
                        os.startfile(app_path)
                else:
                    await update.message.reply_text(
                        f"❌ *Ошибка:* Файл `{app_path}` не найден.",
                        parse_mode='Markdown'
                    )
            except Exception as e:
                await update.message.reply_text(
                    f"❌ *Ошибка:* Не удалось запустить файл `{app_path}`. Подробности: {str(e)}",
                    parse_mode='Markdown'
                )

        def run_coroutine():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_app())
            loop.close()

        new_timer = threading.Timer(total_seconds, run_coroutine)
        new_timer.start()

        if user_id not in app_timers:
            app_timers[user_id] = []
        app_timers[user_id].append(new_timer)

        await update.message.reply_text(
            f"*✅ Приложение* `{app_path}` *запланировано к запуску через* `{total_seconds}` *секунд*",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ *Ошибка:* У вас нет доступа к этой команде.", parse_mode='Markdown')

def startup():
    logging.debug("Запуск бота")
    print(centered_ascii_art)
    play_startup_sound()

startup()

async def send_start_to_all(app: Application) -> None:
    for user_id in TGID:
        try:
            # Создаем "фейковый" объект Message
            fake_message = Message(
                message_id=0,
                date=datetime.now,
                chat=Chat(id=user_id, type='private'),
                from_user=User(id=user_id, is_bot=False, first_name='User'),
                text='/start'
            )

            # Создаем "фейковый" объект Update
            fake_update = Update(
                update_id=0,
                message=fake_message
            )

            # Вызываем функцию start с "фейковым" объектом Update
            await start(fake_update, CallbackContext(app))
        except Exception as e:
            logging.info(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

async def commands(app:Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start", "🐬 Меню"),
        BotCommand("addaction", "✨ Добавить новое действие"),
        BotCommand("timer", "⏳ Запланировать запуск приложения"),
        BotCommand("stop", "⏳ Запланировать отключение "),
        BotCommand("reboot", "⏳ Запланировать перезапуск"),
        BotCommand("sleep", "⏳ Запланировать спящий режим"),
        BotCommand("undo", "❌ Отменить запланированные действия")
    ])

def main() -> None:
    try:

        app = Application.builder().token(TOKEN).build()

        # Добавить обработчик команды /start для всех пользователей
        app.add_handler(CommandHandler('start', start))

        app.job_queue.run_once(send_start_to_all, 0)
        app.job_queue.run_once(commands, 0)

        # Обработчик для ввода ссылки или записи микрофона
        conv_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button, pattern='^open_url$')],
            states={
                ENTER_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_url)],
                RECORD_MICROPHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, record_microphone)]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        # Добавляем ConversationHandler для добавления пользовательских действий
        add_custom_action_handler = ConversationHandler(
            entry_points=[CommandHandler('addaction', add_custom_action)],
            states={
                ENTER_ACTION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_action_name)],
                ENTER_APP_PATH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_app_path)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        keyboard_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button)],
            states={
                ASK_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_key)],
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )

        text_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(button, pattern='^input_text$')],
            states={
                ENTER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )

        files_handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(start_browsing, pattern='^browse$')],
            states={
                BROWSING: [CallbackQueryHandler(button)]
            },
            fallbacks=[]
        )

        app.add_handler(files_handler)
        app.add_handler(text_handler)
        app.add_handler(add_custom_action_handler)
        app.add_handler(conv_handler)
        app.add_handler(keyboard_handler)
        app.add_handler(CallbackQueryHandler(button))
        app.add_handler(CommandHandler('timer', schedule_app))

        # Добавить обработчики команд /reboot, /stop и /undo
        reboot_handler = CommandHandler('reboot', reboot)
        app.add_handler(reboot_handler)

        stop_handler = CommandHandler('stop', stop)
        app.add_handler(stop_handler)

        sleep_handler = CommandHandler('sleep', sleep)
        app.add_handler(sleep_handler)

        undo_handler = CommandHandler('undo', undo)
        app.add_handler(undo_handler)

    except Exception as e:
        logging.error(f"Произошла ошибка при запуске бота (def main): {e}")

    app.run_polling()

if __name__ == '__main__':
    main()