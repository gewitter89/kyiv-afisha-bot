import sqlite3
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('kyiv_events.db')
cur = conn.cursor()

# Fix 1: Remove duplicate Telegram sources
print("=== Fix 1: Vydalyaemo duplikaty Telegram dzherel ===")
cur.execute("""
    SELECT telegram_channel_username, MIN(id) as keep_id, COUNT(*) as cnt
    FROM sources
    WHERE type = 'telegram' AND telegram_channel_username IS NOT NULL
    GROUP BY telegram_channel_username
    HAVING COUNT(*) > 1
""")
dupes = cur.fetchall()
total_deleted = 0
for username, keep_id, cnt in dupes:
    cur.execute("""
        DELETE FROM sources
        WHERE type = 'telegram' 
        AND telegram_channel_username = ? 
        AND id != ?
    """, (username, keep_id))
    deleted = cur.rowcount
    total_deleted += deleted
    print(f"  @{username}: zalyshaemo id={keep_id}, vydaleno {deleted} duplikativ")

print(f"  Vsogo vydaleno duplikativ: {total_deleted}")

# Fix 2: Update non-Kyiv website URLs to Kyiv-specific
print()
print("=== Fix 2: Onovlyuemo URL saytiv na Kyiv-spetsyfichni ===")

kyiv_url_fixes = [
    (14, "https://pokupon.ua/kyiv/",      "Pokupon - kyiv filter"),
    (15, "https://kontramarka.ua/kyiv/",  "Kontramarka - kyiv"),
    (18, "https://superdeal.ua/kyiv/",    "Superdeal - kyiv"),
    (20, "https://parter.ua/kyiv/",       "Parter.ua - kyiv"),
    (22, "https://kasa.in.ua/uk/kyiv",    "Kasa.in.ua - kyiv"),
]

for src_id, new_url, desc in kyiv_url_fixes:
    cur.execute("SELECT name, url FROM sources WHERE id = ?", (src_id,))
    row = cur.fetchone()
    if row:
        old_url = row[1]
        if old_url != new_url:
            cur.execute("UPDATE sources SET url = ? WHERE id = ?", (new_url, src_id))
            print(f"  [{src_id}] {desc}")
            print(f"       OLD: {old_url}")
            print(f"       NEW: {new_url}")
        else:
            print(f"  [{src_id}] {desc} - vzhe aktualno")

# Fix 3: Check events city distribution
print()
print("=== Perevirka cities v events ===")
cur.execute("SELECT city, COUNT(*) FROM events GROUP BY city ORDER BY COUNT(*) DESC")
for row in cur.fetchall():
    print(f"  city={repr(row[0])} -> {row[1]} podiy")

# Summary
print()
print("=== Pidsumok dzherel pislya vypravlen ===")
cur.execute("SELECT type, enabled, COUNT(*) FROM sources GROUP BY type, enabled ORDER BY type, enabled")
for row in cur.fetchall():
    status = "ENABLED" if row[1] else "DISABLED"
    print(f"  {row[0]} | {status}: {row[2]} dzherel")

conn.commit()
conn.close()
print()
print("=== DONE: Vsi vypravlennya zastosovano! ===")
