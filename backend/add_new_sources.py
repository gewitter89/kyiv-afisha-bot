"""
Adds new sources to DB: cinema (Multiplex), sports (Dynamo, Sport.ua),
deals (GoToShop, Pokupon) and Facebook pages.
Run: python -X utf8 add_new_sources.py
"""
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('kyiv_events.db')
cur = conn.cursor()

NEW_SOURCES = [
    # ── CINEMA ──────────────────────────────────────────────────────────────────
    {
        "name": "Multiplex Kyiv — Cinema",
        "type": "website",
        "url": "https://multiplex.ua/ua/city/kyiv/movies",
        "enabled": 1,
        "category": "cinema",
    },
    {
        "name": "Planeta Kino — Cinema",
        "type": "website",
        "url": "https://planetakino.ua/ua/kyiv/",
        "enabled": 1,
        "category": "cinema",
    },

    # ── SPORTS ──────────────────────────────────────────────────────────────────
    {
        "name": "Sport.ua — Kyiv Events",
        "type": "rss",
        "url": "https://www.sport.ua/rss/football.xml",
        "enabled": 1,
        "category": "sport",
    },
    {
        "name": "Dynamo Kyiv Official",
        "type": "website",
        "url": "https://www.fcdynamo.kyiv.ua/uk/matches/calendar/",
        "enabled": 1,
        "category": "sport",
    },
    {
        "name": "Boxing in Kyiv — Palats Sportu",
        "type": "website",
        "url": "https://palats-sportu.com.ua/events/",
        "enabled": 1,
        "category": "sport",
    },

    # ── DEALS & DISCOUNTS ────────────────────────────────────────────────────────
    {
        "name": "Pokupon — Kyiv Deals",
        "type": "website",
        "url": "https://pokupon.ua/kyiv/",
        "enabled": 1,
        "category": "deal",
    },
    {
        "name": "GoToShop — Supermarket Deals",
        "type": "website",
        "url": "https://gotoshop.ua/kyiv/",
        "enabled": 1,
        "category": "deal",
    },
    {
        "name": "Superdeal — Kyiv",
        "type": "website",
        "url": "https://superdeal.ua/kyiv/",
        "enabled": 1,
        "category": "deal",
    },

    # ── FACEBOOK PAGES ────────────────────────────────────────────────────────────
    {
        "name": "Палац Україна — FB",
        "type": "facebook",
        "url": "https://facebook.com/PalatsUkrainy",
        "telegram_channel_username": "PalatsUkrainy",
        "enabled": 1,
        "category": "concert",
    },
    {
        "name": "Атлас Kyiv — FB",
        "type": "facebook",
        "url": "https://facebook.com/AtlasKyiv",
        "telegram_channel_username": "AtlasKyiv",
        "enabled": 1,
        "category": "concert",
    },
    {
        "name": "RePublic Kyiv — FB",
        "type": "facebook",
        "url": "https://facebook.com/RePublicKyiv",
        "telegram_channel_username": "RePublicKyiv",
        "enabled": 1,
        "category": "concert",
    },
    {
        "name": "Concert.ua — FB",
        "type": "facebook",
        "url": "https://facebook.com/ConcertUaOfficial",
        "telegram_channel_username": "ConcertUaOfficial",
        "enabled": 1,
        "category": "concert",
    },
    {
        "name": "Kyiv Today Events — FB",
        "type": "facebook",
        "url": "https://facebook.com/kyivtoday",
        "telegram_channel_username": "kyivtoday",
        "enabled": 1,
        "category": "other",
    },

    # ── RESTAURANTS & FOOD ────────────────────────────────────────────────────────
    {
        "name": "The Village Ukraine — Events",
        "type": "rss",
        "url": "https://www.the-village.com.ua/feed",
        "enabled": 1,
        "category": "food",
    },
    {
        "name": "Eda.ua — Kyiv Restaurant Deals",
        "type": "website",
        "url": "https://eda.ua/kyiv/restaurants/",
        "enabled": 1,
        "category": "restaurant",
    },
]

# Check existing sources to avoid duplicates
cur.execute("SELECT url FROM sources")
existing_urls = {row[0] for row in cur.fetchall()}

# Check table columns
cur.execute("PRAGMA table_info(sources)")
cols = {row[1] for row in cur.fetchall()}
print(f"Source table columns: {sorted(cols)}")

added = 0
skipped = 0
for src in NEW_SOURCES:
    if src["url"] in existing_urls:
        print(f"  SKIP (exists): {src['name']}")
        skipped += 1
        continue

    # Build insert statement based on available columns
    now = "datetime('now')"
    insert_data = {
        "name": src["name"],
        "type": src["type"],
        "url": src["url"],
        "enabled": src.get("enabled", 1),
        "crawl_interval_minutes": 60,
    }
    if "telegram_channel_username" in cols and "telegram_channel_username" in src:
        insert_data["telegram_channel_username"] = src["telegram_channel_username"]

    columns = ", ".join(list(insert_data.keys()) + ["created_at", "updated_at"])
    placeholders = ", ".join([f":{k}" for k in insert_data.keys()] + ["datetime('now')", "datetime('now')"])

    cur.execute(f"INSERT INTO sources ({columns}) VALUES ({placeholders})", insert_data)
    print(f"  ADDED: [{src['type'].upper()}] {src['name']}")
    added += 1

conn.commit()
conn.close()

print(f"\nDone! Added: {added}, Skipped (duplicates): {skipped}")
print("Total new sources ready!")
