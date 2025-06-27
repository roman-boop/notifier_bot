import requests
import telebot
import time
import threading

# Telegram Bot API ключ
TELEGRAM_BOT_TOKEN = 'TGTOKEN'
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# API для получения цен
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/simple/price"

# Словарь: ключ — chat_id пользователя, значение — список отслеживаемых кошельков
user_wallets = {}

# Словарь: ключ — chat_id, значение — список запросов на уведомления о ценах
user_notifications = {}

# Хранение последних обработанных транзакций
last_transactions = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id not in user_wallets:
        user_wallets[chat_id] = []  # Инициализируем пустой список кошельков
    if chat_id not in user_notifications:
        user_notifications[chat_id] = []  # Инициализируем пустой список уведомлений
    bot.reply_to(message, "Добро пожаловать! Используйте /addwallet, /removewallet, /listwallets и /notify для управления.")

# Обработчик команды /notify
@bot.message_handler(commands=['notify'])
def set_price_notification(message):
    chat_id = message.chat.id
    try:
        _, ticker, price = message.text.split()
        price = float(price)
        user_notifications.setdefault(chat_id, []).append({"ticker": ticker.lower(), "price": price})
        bot.reply_to(message, f"Уведомление установлено: {ticker.upper()} достигнет {price}.")
    except ValueError:
        bot.reply_to(message, "Неверный формат. Используйте: /notify {ticker} {price}")

# Обработчик команды /addwallet
@bot.message_handler(commands=['addwallet'])
def add_wallet(message):
    chat_id = message.chat.id
    wallet = message.text.split(maxsplit=1)[-1].strip()
    if wallet:
        if wallet not in user_wallets[chat_id]:
            user_wallets[chat_id].append(wallet)
            bot.reply_to(message, f"Кошелек {wallet} добавлен для отслеживания.")
        else:
            bot.reply_to(message, "Кошелек уже добавлен в список отслеживания.")
    else:
        bot.reply_to(message, "Команда некорректна. Используйте /addwallet <адрес кошелька>.")

# Обработчик команды /removewallet
@bot.message_handler(commands=['removewallet'])
def remove_wallet(message):
    chat_id = message.chat.id
    wallet = message.text.split(maxsplit=1)[-1].strip()
    if wallet in user_wallets.get(chat_id, []):
        user_wallets[chat_id].remove(wallet)
        bot.reply_to(message, f"Кошелек {wallet} удален из списка отслеживания.")
    else:
        bot.reply_to(message, "Кошелек не найден в вашем списке отслеживания.")

# Обработчик команды /listwallets
@bot.message_handler(commands=['listwallets'])
def list_wallets(message):
    chat_id = message.chat.id
    wallets = user_wallets.get(chat_id, [])
    if wallets:
        wallets_list = "\n".join(wallets)
        bot.reply_to(message, f"Ваши отслеживаемые кошельки:\n{wallets_list}")
    else:
        bot.reply_to(message, "Ваш список отслеживаемых кошельков пуст.")

# Проверка цен монет
def check_prices():
    while True:
        try:
            for chat_id, notifications in user_notifications.items():
                for notification in notifications[:]:  # Используем копию списка, чтобы безопасно изменять его
                    ticker = notification["ticker"]
                    target_price = notification["price"]

                    # Получаем текущую цену монеты
                    response = requests.get(COINGECKO_API_URL, params={"ids": ticker, "vs_currencies": "usd"})
                    if response.status_code == 200:
                        current_price = response.json().get(ticker, {}).get("usd")
                        if current_price is not None and current_price == target_price:
                            # Отправляем уведомление
                            bot.send_message(chat_id, f"Монета {ticker.upper()} достигла цены {target_price} USD!")
                            notifications.remove(notification)
        except Exception as e:
            print(f"Ошибка при проверке цен: {e}")
        time.sleep(60)

# Основной поток для бота
def start_bot():
    bot.polling()

if __name__ == "__main__":
    # Поток для бота
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.daemon = True
    bot_thread.start()

    # Поток для проверки цен монет
    price_check_thread = threading.Thread(target=check_prices)
    price_check_thread.daemon = True
    price_check_thread.start()

    # Ожидание завершения потоков
    bot_thread.join()
    price_check_thread.join()
