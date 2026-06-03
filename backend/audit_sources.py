import sqlite3
conn = sqlite3.connect('kyiv_events.db')
cur = conn.cursor()

print("=== ДУБЛІКАТИ Telegram джерел ===")
cur.execute("""
SELECT name, COUNT(*) as cnt 
FROM sources 
WHERE type = 'telegram' 
GROUP BY name 
HAVING COUNT(*) > 1 
ORDER BY cnt DESC
LIMIT 10
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  ДУБЛІКАТ: name={repr(row[0])} -> {row[1]} разів!")
else:
    print("  Дублікатів немає")

print()
print("=== Всі Telegram джерела (enabled=1, uniq) ===")
cur.execute("""
SELECT id, name, telegram_channel_username, enabled 
FROM sources 
WHERE type = 'telegram'
ORDER BY id
LIMIT 30
""")
for row in cur.fetchall():
    print(f"  [{row[0]}] name={repr(row[1])} | username={row[2]} | enabled={row[3]}")

print()
print("=== WEBSITE джерела ===")
cur.execute("SELECT id, name, url FROM sources WHERE type = 'website' AND enabled = 1")
for row in cur.fetchall():
    print(f"  [{row[0]}] {row[1]}")
    print(f"       {row[2]}")

print()
print("=== Всі події — city + title sample ===")
cur.execute("SELECT id, title, city, status, quality_score FROM events ORDER BY id DESC LIMIT 15")
for row in cur.fetchall():
    print(f"  [{row[0]}] title={repr(row[1][:40])} | city={repr(row[2])} | status={row[3]} | score={row[4]}")

conn.close()
