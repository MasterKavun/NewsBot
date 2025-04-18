import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message
import sqlite3
import time
from config import BOT_TOKEN, ADMIN_ID

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота з правильним default
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

connection = sqlite3.connect("news.db")
cursor = connection.cursor()

# Обробка команди /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Привіт, адмін! Ти маєш доступ до бота.")
    else:
        await message.answer("У тебе немає доступу до цього бота.")

async def post_news_to_channel():
    cursor.execute("""
        SELECT n.id, n.title, n.image_url, nt.processed_text
        FROM news n
        JOIN news_texts nt ON n.id = nt.news_id
        WHERE nt.processed_text != ''
        AND n.id NOT IN (SELECT news_id FROM posted_news)
        ORDER BY n.id ASC
        LIMIT 1
    """)

    news = cursor.fetchone()

    if news:
        news_id, title, image_url, processed_text = news
        try:
            if not image_url or len(processed_text) > 1024:
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


async def scheduled_posting():
    while True:
        await post_news_to_channel()
        await asyncio.sleep(300)  # Інтервал 5 хвилин між публікаціями

# Запуск бота
async def main():
    # Запуск публікацій новин
    asyncio.create_task(scheduled_posting())
    # Запуск адмінки
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())