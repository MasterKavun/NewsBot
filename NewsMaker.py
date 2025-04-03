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


    try:
        cursor.execute("INSERT INTO news (title, url, content) VALUES (?,?,?)",
                       (title, url, "Текст статті"))
        connection.commit()
    except sqlite3.IntegrityError:
        print(f"Новина вже є в базі: {title}")

connection.close()
print("Базу оновлено")