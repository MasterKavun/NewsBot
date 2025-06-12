import logging
import asyncio
import re
import json
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import InputMediaPhoto
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
        news_id, title, image_url_json, processed_text = news

        try:
            clean_title = strip_html_tags(title)
            clean_text = strip_html_tags(processed_text)
            total_length = len(clean_title) + len(clean_text) + 2

            # Парсимо список зображень
            if image_url_json:
                try:
                    parsed = json.loads(image_url_json)
                    if isinstance(parsed, list):
                        # Фільтруємо валідні URL
                        filtered = [url for url in parsed if url.startswith("http")]

                        # Якщо є додаткові зображення — прибираємо головне (перше)
                        if len(filtered) > 1:
                            image_urls = filtered[1:11]  # максимум 10, без першого
                        else:
                            image_urls = filtered
                except json.JSONDecodeError:
                    pass


            # Якщо є зображення і текст влізає
            if image_urls and total_length <= 1024:
                media = []

                for i, url in enumerate(image_urls):
                    if i == len(image_urls) - 1:
                        # caption тільки для останнього фото
                        media.append(InputMediaPhoto(media=url, caption=f"<b>{title}</b>\n\n{processed_text}", parse_mode="HTML"))
                    else:
                        media.append(InputMediaPhoto(media=url))

                await bot.send_media_group(
                    chat_id="@my_test_cgannel",
                    media=media
                )
            else:
                # Якщо немає зображень або текст завеликий — просто текст
                await bot.send_message(
                    chat_id="@my_test_cgannel",
                    text=f"<b>{title}</b>\n\n{processed_text}"
                )

            # Позначаємо як опубліковану
            cursor.execute("INSERT INTO posted_news (news_id) VALUES (?)", (news_id,))
            connection.commit()

        except Exception as e:
            logging.error(f"Не вдалося надіслати новину ID {news_id}: {e}")
            cursor.execute(
                "INSERT OR IGNORE INTO failed_news (news_id, error_message) VALUES (?, ?)",
                (news_id, str(e))
            )
            connection.commit()
# Розклад
async def scheduled_posting():
    while True:
        await post_news_to_channel()
        await asyncio.sleep(60)  # 5 хвилин

# Запуск
async def main():
    asyncio.create_task(scheduled_posting())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
