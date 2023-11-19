import os
import re
import json
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from settings import TOKEN, SCAN_CHANNEL_ID, NOTIFICATION_CHAT_ID
print("Текущая рабочая директория:", os.getcwd())

# Пути к файлам для сохранения словарей
ALERTS_FILE_PATH = "alerts.json"
ADDRESSES_FILE_PATH = "addresses.json"

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка данных
def load_data(file_path):
    """Загрузка данных из файла."""
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return {k: set(v) for k, v in data.items()}
    except (json.JSONDecodeError, FileNotFoundError):
        logger.warning(f"Ошибка при чтении {file_path}. Используется пустой словарь.")
        return {}

def save_data(data, file_path):
    """Сохранение данных в файл."""
    with open(file_path, 'w') as file:
        json.dump({k: list(v) for k, v in data.items()}, file)

# Загрузка словарей при запуске
alerts_dict = load_data(ALERTS_FILE_PATH)
addresses_dict = load_data(ADDRESSES_FILE_PATH)

def check_args_length(update, expected_length):
    """Проверяет количество аргументов в команде."""
    if len(update.message.text.split()) < expected_length:
        update.message.reply_text("Недостаточно аргументов для этой команды.")
        return False
    return True

def unknown_command(update, context):
    """Обработчик неизвестных команд."""
    update.message.reply_text("Неизвестная команда. Введите /help для просмотра доступных команд.")



# Команды бота-
def start(update, context):
    commands = [
        "/add_v <alrt/addr> <ключ> <значение1> ... - Добавить значения",
        "/edit_v <alrt/addr> <ключ> <значение1> ... - Редактировать значения",
        "/rm_v <alrt/addr> <ключ> <значение1> ... - Удалить значения",
        "/rm_k <alrt/addr> <ключ> - Удалить ключ",
        "/help - Подробный хелп"
    ]
    update.message.reply_text("\n".join(commands))

def add_value(update, context):
    """Добавление значений к существующему ключу в выбранном словаре."""
    if not context.args or context.args[0] not in ["alrt", "addr"]:
        update.message.reply_text("Неверный аргумент. Используйте 'alrt' или 'addr'.")
        return

    dictionary_type = context.args[0]
    key = context.args[1]
    values = context.args[2:]

    if dictionary_type == "alrt":
        target_dict = alerts_dict
        file_path = ALERTS_FILE_PATH
    else:
        target_dict = addresses_dict
        file_path = ADDRESSES_FILE_PATH

    if key not in target_dict:
        target_dict[key] = set()
    target_dict[key].update(values)
    save_data(target_dict, file_path)
    update.message.reply_text(f"Ключ '{key}' обновлен с значениями: {', '.join(values)}.")


def edit_value(update, context):
    dictionary, key, *new_values = update.message.text.split()[1:]
    target_dict = alerts_dict if dictionary == "alrt" else addresses_dict
    target_dict[key] = set(new_values)
    save_data(target_dict, ALERTS_FILE_PATH if dictionary == "alrt" else ADDRESSES_FILE_PATH)
    update.message.reply_text(f"Значения для ключа '{key}' обновлены.")

def remove_value(update, context):
    if not check_args_length(update, 3):  # Минимальное количество аргументов: /rm_v alrt ключ
        return

    dictionary, key, *values_to_remove = update.message.text.split()[1:]
    target_dict = alerts_dict if dictionary == "alrt" else addresses_dict
    if key not in target_dict:
        update.message.reply_text(f"Ключ '{key}' не найден.")
        return
    removed_values = target_dict[key].intersection(values_to_remove)
    if not removed_values:
        update.message.reply_text(f"Значения {', '.join(values_to_remove)} не найдены для ключа '{key}'.")
        return
    target_dict[key] -= removed_values
    save_data(target_dict, ALERTS_FILE_PATH if dictionary == "alrt" else ADDRESSES_FILE_PATH)
    update.message.reply_text(f"Значения {', '.join(removed_values)} удалены из ключа '{key}'.")

def remove_key(update, context):
    if not check_args_length(update, 3):  # Минимальное количество аргументов: /rm_k alrt ключ
        return
    dictionary, key = update.message.text.split()[1:3]
    target_dict = alerts_dict if dictionary == "alrt" else addresses_dict
    if key not in target_dict:
        update.message.reply_text(f"Ключ '{key}' не найден.")
        return
    target_dict.pop(key, None)
    save_data(target_dict, ALERTS_FILE_PATH if dictionary == "alrt" else ADDRESSES_FILE_PATH)
    update.message.reply_text(f"Ключ '{key}' удален.")

def view_dictionaries(update, context):
    """Вывод содержимого выбранного словаря или обоих словарей."""
    response = []
    args = update.message.text.split()

    if len(args) > 1:
        dictionary = args[1]
        if dictionary == "alrt":
            if not alerts_dict:
                response.append("Словарь alerts пуст.")
            else:
                for key, values in alerts_dict.items():
                    response.append(f"{key}: {', '.join(values)}")
        elif dictionary == "addr":
            if not addresses_dict:
                response.append("Словарь addresses пуст.")
            else:
                for key, values in addresses_dict.items():
                    response.append(f"{key}: {', '.join(values)}")
        else:
            response.append("Неизвестный аргумент. Используйте 'alrt' или 'addr'.")
    else:
        # Вывод содержимого обоих словарей, если аргументы не указаны
        response.append("Alerts:")
        if not alerts_dict:
            response.append("Словарь alerts пуст.")
        else:
            for key, values in alerts_dict.items():
                response.append(f"{key}: {', '.join(values)}")

        response.append("\nAddresses:")
        if not addresses_dict:
            response.append("Словарь addresses пуст.")
        else:
            for key, values in addresses_dict.items():
                response.append(f"{key}: {', '.join(values)}")

    update.message.reply_text("\n".join(response))




def handle_message(update, context):
    if update.channel_post:
        message = update.channel_post
        found_alerts = [key for key, values in alerts_dict.items() if any(value in message.text for value in values)]
        found_addresses = [key for key, values in addresses_dict.items() if any(value in message.text for value in values)]

        # Находим все 6-значные числовые последовательности, ограниченные символами или пробелами
        six_digit_sequences = re.findall(r'\b\d{6}\b', message.text)

        # Исключаем последовательности из одинаковых цифр
        six_digit_sequences = [seq for seq in six_digit_sequences if len(set(seq)) > 1]

        # Извлекаем контекст для каждой найденной последовательности
        context_sequences = []
        for sequence in six_digit_sequences:
            start_index = max(message.text.find(sequence) - 0, 0)
            end_index = min(message.text.find(sequence) + 6, len(message.text))
            context_sequences.append("`" + message.text[start_index:end_index] + "`")  # Оборачиваем в обратные апострофы

        # Формируем ответ
        response = "account ➧ " + " ".join(found_addresses) + "\n" + " ".join(found_alerts)
        if context_sequences:
            response += " ❒ OTP▐ " + "\n".join(context_sequences) + "\n"
        response += "\n" + message.link

        context.bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=response, parse_mode='Markdown')




def help_command(update, context):
    """Отправляет инструкции по использованию бота."""
    with open("readme.txt", "r",encoding="utf-8") as file:
        instructions = file.read()
    update.message.reply_text(instructions)
    
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command)) 
    dp.add_handler(CommandHandler("add_v", add_value))
    dp.add_handler(CommandHandler("edit_v", edit_value))
    dp.add_handler(CommandHandler("rm_v", remove_value))
    dp.add_handler(CommandHandler("rm_k", remove_key))
    dp.add_handler(CommandHandler("view", view_dictionaries))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
