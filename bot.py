import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message
import sqlite3
from config import BOT_TOKEN, ADMIN_ID

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Підключення до бази
connection = sqlite3.connect("news.db")
cursor = connection.cursor()

# Функція для видалення HTML-тегів
def strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)

# /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Привіт, адмін! Ти маєш доступ до бота.")
    else:
        await message.answer("У тебе немає доступу до цього бота.")

# Основна логіка публікації
async def post_news_to_channel():
    cursor.execute("""
        SELECT n.id, n.title, n.image_url, nt.processed_text
        FROM news n
        JOIN news_texts nt ON n.id = nt.news_id
        WHERE nt.processed_text != ''
        AND n.id NOT IN (SELECT news_id FROM posted_news)
        AND n.id NOT IN (SELECT news_id FROM failed_news)
        ORDER BY n.id ASC
        LIMIT 1
    """)

    news = cursor.fetchone()

    if news:
        news_id, title, image_url, processed_text = news
        try:
            # Підрахунок реальної довжини тексту (без HTML)
            clean_title = strip_html_tags(title)
            clean_text = strip_html_tags(processed_text)
            total_length = len(clean_title) + len(clean_text) + 2  # за \n\n

            if not image_url or total_length > 1024:
                await bot.send_message(
                    chat_id="@my_test_cgannel",
                    text=f"<b>{title}</b>\n\n{processed_text}"
                )
            else:
                await bot.send_photo(
                    chat_id="@my_test_cgannel",
                    photo=image_url,
                    caption=f"<b>{title}</b>\n\n{processed_text}"
                )

            # Позначаємо як опубліковану
            cursor.execute("INSERT INTO posted_news (news_id) VALUES (?)", (news_id,))
            connection.commit()
        except Exception as e:
            logging.error(f"Не вдалося надіслати новину ID {news_id}: {e}")
            cursor.execute("INSERT OR IGNORE INTO failed_news (news_id, error_message) VALUES (?, ?)", (news_id, str(e)))
            connection.commit()
# Розклад
async def scheduled_posting():
    while True:
        await post_news_to_channel()
        await asyncio.sleep(300)  # 5 хвилин

# Запуск
async def main():
    asyncio.create_task(scheduled_posting())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
