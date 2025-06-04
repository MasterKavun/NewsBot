import mechanicalsoup
import sqlite3
import httpx
import asyncio
import json
import re
from config import API_KEY, AGENT_ID, API_URL

headers = {
   "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json" 
}

connection = sqlite3.connect("news.db")
cursor = connection.cursor()

# Створення таблиць
cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        url TEXT UNIQUE,
        image_url TEXT        
    )
""")

cursor.execute("""
  CREATE TABLE IF NOT EXISTS news_texts (
    news_id INTEGER PRIMARY KEY,
    full_text TEXT,
    processed_text TEXT,
    FOREIGN KEY(news_id) REFERENCES news(id)
  )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS posted_news (
        news_id INTEGER PRIMARY KEY,
        FOREIGN KEY(news_id) REFERENCES news(id)    
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS failed_news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        news_id INTEGER UNIQUE,
        error_message TEXT,
        failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

def get_all_image_urls(article_page):
    image_urls = []

    # Основне зображення
    main_img_tag = article_page.select_one("figure.article-body__figure img")
    if main_img_tag and main_img_tag.get("src"):
        src = main_img_tag["src"]
        high_res = re.sub(r"w=\\d+", "w=1280", src)
        image_urls.append(high_res)

    # Додаткові зображення — <a href=...>
    extra_figures = article_page.select("figure.article__figure a")
    for a_tag in extra_figures:
        href = a_tag.get("href")
        if href and href.startswith("http"):
            image_urls.append(href) 

    return image_urls

# Парсинг сайту
url = "https://news.liga.net/ua"
browser = mechanicalsoup.StatefulBrowser()
browser.open(url)
page = browser.get_current_page()
articles = page.find_all("a", {"class":"news-card__title"})

for article in articles:
    title = article.text.strip()
    url = article["href"]

    browser.open(url)
    article_page = browser.get_current_page()

    # Збір усіх зображень через функцію
    image_urls = get_all_image_urls(article_page)
    image_urls_json = json.dumps(image_urls)

    if url.startswith("https://news.liga.net/"):
        try:
            cursor.execute("INSERT INTO news (title, url, image_url) VALUES (?,?,?)",
                        (title, url, image_urls_json))
            connection.commit()
        except sqlite3.IntegrityError:
            print(f"Новина вже є в базі: {title}")

connection.commit()
print("✅ Базу оновлено")

cursor.execute("""
    SELECT id, url FROM news
    WHERE id NOT IN (SELECT news_id FROM news_texts)
""")

rows = cursor.fetchall()

for news_id, url in rows:
    try:
        browser.open(url)
        page = browser.get_current_page()
        article_text = page.find_all("p")
        full_text = '\n\n'.join([p.get_text().strip() for p in article_text if p.get_text().strip()])

        cursor.execute("""
            INSERT INTO news_texts (news_id, full_text, processed_text)
            VALUES (?,?, NULL)
        """, (news_id, full_text))
        connection.commit()
        print(f"Збережено текст новини ID {news_id}")
    except Exception as e:
        print(f"❌ Помилка при обробці новини ID {news_id}: {e}")

print("📥 Парсинг текстів завершено")

# Обробка через Mistral
cursor.execute("""
    SELECT news_id, full_text FROM news_texts
    WHERE processed_text IS NULL
""")

news_to_process = cursor.fetchall()
connection.commit()

async def process_news(session, news_id, full_text):
    try:
        data = {
            "agent_id": AGENT_ID,
            "max_tokens": 850,
            "messages": [
                {"role": "user", "content": full_text}
            ]
        }

        response = await session.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()

        try:
            result = response.json()
            processed_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            print(f"⚠️ Помилка розбору JSON для новини ID {news_id}")
            return

        if processed_text:
            cursor.execute("""
                UPDATE news_texts
                SET processed_text = ?
                WHERE news_id = ?
            """, (processed_text, news_id))
            connection.commit()
            print(f"✅ Новина ID {news_id} оброблена")
        else:
            print(f"⚠️ Відсутній результат для новини ID {news_id}")
    except Exception as e:
        print(f"⚠️ Помилка при обробці новини ID {news_id}: {e}")

async def main():
    async with httpx.AsyncClient() as session:
        for news_id, full_text in news_to_process:
            await process_news(session, news_id, full_text)
            await asyncio.sleep(2)

asyncio.run(main())
connection.close()
print("🎉 Усі новини оброблено та збережено")
