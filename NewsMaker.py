import mechanicalsoup
import sqlite3

connection = sqlite3.connect("news.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        url TEXT UNIQUE,
        content TEXT
    )

""")

url = "https://news.liga.net/ua"

browser = mechanicalsoup.StatefulBrowser()
browser.open(url)
page = browser.get_current_page()

articles = page.find_all("a", {"class":"news-card__title"})

for article in articles:
    title = article.text.strip()
    url = article["href"]

    if url.startswith("https://news.liga.net/"):
        try:
            cursor.execute("INSERT INTO news (title, url, content) VALUES (?,?,?)",
                        (title, url, "Текст статті"))
            connection.commit()
        except sqlite3.IntegrityError:
            print(f"Новина вже є в базі: {title}")

connection.commit()
print("Базу оновлено")

cursor.execute("""
  CREATE TABLE IF NOT EXISTS news_texts (
    news_id INTEGER PRIMARY KEY,
    full_text TEXT,
    processed_text TEXT,
    FOREIGN KEY(news_id) REFERENCES news(id)
  )
""")

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
        print(f"Помилка при обробці новини ID {news_id}: {e}")

connection.close()
print("Парсинг текстів завершено")