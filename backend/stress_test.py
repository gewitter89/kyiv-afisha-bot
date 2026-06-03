import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

# Add current folder to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 1. Initialize SQLite database & Patch database module BEFORE importing other app parts
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
import app.core.database

sqlite_engine = create_async_engine(
    "sqlite+aiosqlite:///test_kyiv_events.db",
    echo=False,
    future=True
)
sqlite_sessionmaker = async_sessionmaker(
    bind=sqlite_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Patch globally in sys.modules
app.core.database.engine = sqlite_engine
app.core.database.AsyncSessionLocal = sqlite_sessionmaker

# Import configuration and patch settings
from app.core.config import settings
from app.services.ai_processor import ai_processor
settings.AI_PROVIDER = "mock"
ai_processor.provider = "mock"

# Patch publisher to avoid calling Telegram API during stress test
import app.services.publisher
async def mock_publish_single_event(event, db):
    event.status = "published"
    event.published_to_telegram_at = datetime.utcnow()
    await db.commit()
    return True, None
app.services.publisher.publish_single_event = mock_publish_single_event

# 2. Now import app parts which will import the patched versions
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.models import Source, RawItem, Event, EventSource, Post
from app.tasks.jobs import process_raw_item_job
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError

def safe_print(text: str):
    """
    Safely prints text on Windows console by encoding to terminal's stdout encoding or ignoring emojis.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            enc = sys.stdout.encoding or 'utf-8'
            print(text.encode(enc, errors='ignore').decode(enc))
        except Exception:
            print(text.encode('ascii', errors='ignore').decode('ascii'))

async def setup_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Ensure stress test source exists in DB
    async with AsyncSessionLocal() as session:
        q = await session.execute(select(Source).where(Source.id == 888))
        source = q.scalar_one_or_none()
        if not source:
            source = Source(
                id=888,
                name="Stress Test Mock Crawler",
                type="website",
                url="https://stresstest.kyiv.ua",
                enabled=True,
                crawl_interval_minutes=30
            )
            session.add(source)
            await session.commit()
    safe_print("[OK] SQLite Database tables initialized & stress test source loaded.")

def generate_stress_data():
    unique_events = [
        ("Концерт Океан Ельзи", "Палац Спорту", "12 червня о 19:00", "Великий концерт гурту Океан Ельзи у Палаці Спорту в Києві. Всі хіти наживо. Ціна від 500 грн."),
        ("Вистава Ромео і Джульєтта", "Національна опера", "15 червня о 18:00", "Класична вистава Ромео і Джульєтта в Національній опері України. Вартість квитків 300 грн."),
        ("Стендап Вечір", "Urban Space", "20 червня о 20:00", "Сольний стендап вечір кращих коміків столиці в Urban Space. Вхід 250 грн."),
        ("Виставка квітів", "Співоче поле", "10 червня о 10:00", "Щорічна виставка квітів на Співочому полі. Неймовірні інсталяції та фотозони. Квитки 150 грн."),
        ("Вечірка на Даху", "ЦУМ", "18 червня о 21:00", "Електронна вечірка на даху ЦУМу. Лайнап з кращих діджеїв. Вхід 400 грн."),
        ("Гастрономічний фестиваль", "ВДНГ", "25 червня о 12:00", "Великий фестиваль їжі на ВДНГ. Фудкорти з усієї України. Вхід вільний."),
        ("Лекція з Історії Києва", "Будинок вчителя", "14 червня о 15:00", "Цікава лекція про таємниці стародавнього Києва в Будинку вчителя. Безкоштовно."),
        ("Майстер-клас з живопису", "Арт-студія Світло", "22 червня о 14:00", "Майстер-клас з олійного живопису для початківців. Ціна 600 грн."),
        ("Дитячий квест", "Парк Шевченка", "11 червня о 11:00", "Пригодницький квест для дітей в парку Шевченка. Вік 6-12 років. Ціна 200 грн."),
        ("Йога в парку", "Наталка", "13 червня о 08:00", "Ранкова йога на свіжому повітрі в парку Наталка. Вхід за донат."),
        ("Кіно під відкритим небом", "Unit City", "17 червня о 21:30", "Показ фільму під відкритим небом в Unit City. Вхід 100 грн."),
        ("Джаз на Дніпрі", "Причал 14", "19 червня о 19:30", "Вечір джазової музики на теплоході. Старт від причалу 14. Квитки 450 грн."),
        ("Виставка сучасного мистецтва", "PinchukArtCentre", "16 червня о 12:00", "Нова виставка молодих українських художників у PinchukArtCentre. Вхід безкоштовний."),
        ("Тур подвір'ями Подолу", "метро Контрактова", "21 червня о 16:00", "Екскурсія таємними двориками Подолу. Початок біля метро Контрактова. Вартість 250 грн."),
        ("Поетичний вечір", "Книгарня Є", "23 червня о 18:30", "Читання віршів сучасних поетів у Книгарні Є. Вхід вільний за реєстрацією."),
        ("Благодійний забіг", "Труханів острів", "24 червня о 09:00", "Марафон на підтримку ЗСУ на Трухановому острові. Реєстрація 300 грн."),
        ("Балет Лебедине Озеро", "Жовтневий палац", "26 червня о 19:00", "Балет Лебедине Озеро у виконанні української трупи в Жовтневому палаці. Квитки від 400 грн."),
        ("Дегустація вин", "WineTime", "27 червня о 19:00", "Дегустація італійських вин із сомельє у WineTime. Вартість участі 800 грн."),
        ("Психологічний воркшоп", "Hub 4.0", "28 червня о 13:00", "Воркшоп з керування стресом та емоціями у Hub 4.0. Ціна 350 грн."),
        ("Концерт органної музики", "Костел Святого Миколая", "29 червня о 18:00", "Вечір класичної органної музики в Костелі Святого Миколая. Ціна квитків від 200 грн.")
    ]

    duplicates = [
        ("Виступ Океан Ельзи", "Палац Спорту", "12 червня о 19:00", "Купуйте квитки на концерт Океан Ельзи у Києві! Палац Спорту, 12 червня о 19:00. Ціна 500 грн."),
        ("Спектакль Ромео і Джульєтта", "Національна опера", "15 червня о 18:00", "Спектакль Ромео і Джульєтта в Оперному театрі. 15.06 о 18:00. Вартість квитків від 300 грн."),
        ("Стендап в Києві", "Urban Space", "20 червня о 20:00", "Вечір стендапу в Urban Space. Найкращі жарти від коміків. Початок о 20:00, ціна 250 грн."),
        ("Квіти на Співочому полі", "Співоче поле", "10 червня о 10:00", "Виставка квітів Співоче поле Київ. Початок 10 червня о 10:00. Квитки 150 грн."),
        ("Party на Даху ЦУМу", "Дах ЦУМу", "18 червня о 21:00", "Вечірка Rooftop Party в ЦУМі. 18 червня о 21:00. Вхід 400 грн."),
        ("Street Food Festival", "ВДНГ", "25 червня о 12:00", "Фестиваль вуличної їжі на ВДНГ. 25 червня з 12:00. Вхід безкоштовний."),
        ("Історія Києва: лекція", "Будинок вчителя", "14 червня о 15:00", "Безкоштовна лекція про історію Києва в Будинку вчителя. Початок о 15:00."),
        ("Малюємо олією", "Арт-студія Світло", "22 червня о 14:00", "Майстер-клас з малювання олією в Арт-студії Світло. Ціна 600 грн. Запис відкритий."),
        ("Пригоди в парку: квест", "Парк Шевченка", "11 червня о 11:00", "Дитячий пригодницький квест у парку Шевченка. 11 червня об 11:00. Ціна 200 грн."),
        ("Ранкова йога", "Парк Наталка", "13 червня о 08:00", "Заняття йогою в парку Наталка вранці. 13 червня о 08:00. Вхід вільний донат."),
        ("Кіно просто неба", "Unit.City", "17 червня о 21:30", "Показ фільму в Unit City просто неба. 17.06 о 21:30. Ціна квитків 100 грн."),
        ("Jazz на теплоході", "Причал 14", "19 червня о 19:30", "Джаз на Дніпрі на кораблі. Відправлення від причалу 14 о 19:30. Ціна 450 грн."),
        ("Мистецтво в PinchukArtCentre", "PinchukArtCentre", "16 червня о 12:00", "Безкоштовна виставка сучасного мистецтва в PinchukArtCentre. 16 червня, 12:00."),
        ("Екскурсія Подолом", "метро Контрактова", "21 червня о 16:00", "Пішохідна екскурсія двориками Подолу. Зустріч біля метро Контрактова о 16:00. Ціна 250 грн."),
        ("Поезія в Книгарні Є", "Книгарня Є", "23 червня о 18:30", "Поетичний вечір у Книгарні Є на Лисенка. 23 червня о 18:30. Вхід безкоштовно."),
        ("Run for ZSU", "Труханів острів", "24 червня о 09:00", "Марафон на Трухановому острові на підтримку ЗСУ. 24 червня о 09:00. Реєстрація 300 грн."),
        ("Балет Лебедине Озеро", "Жовтневий палац", "26 червня о 19:00", "Класичний балет Лебедине Озеро в Жовтневому палаці. 26.06 о 19:00. Квитки від 400 грн."),
        ("Wine Tasting", "WineTime", "27 червня о 19:00", "Дегустація вин Італії в WineTime. 27 червня о 19:00. Вартість 800 грн."),
        ("Управління стресом", "Hub 4.0", "28 червня о 13:00", "Воркшоп з психології Hub 4.0. 28 червня о 13:00. Вартість 350 грн."),
        ("Органний концерт", "Костел Святого Миколая", "29 червня о 18:00", "Класична органна музика в Костелі Миколая. 29.06 о 18:00. Ціна квитків від 200 грн.")
    ]

    non_events = [
        "Ремонтні роботи на тепломережі по вул. Хрещатик. Можливі тимчасові обмеження гарячого водопостачання в навколишніх будинках.",
        "Нові правила реєстрації домашніх тварин у Києві. Всі власники мають зареєструвати своїх улюбленців у системі КМДА.",
        "Рейтинг кращих парків Києва для прогулянок цього літа за версією туристичного порталу.",
        "Київпастранс запустив новий маршрут автобуса №118 з Позняків до центру міста.",
        "Погода на тиждень: синоптики обіцяють спеку до +30 градусів і локальні зливи з градом у столиці.",
        "Відкриття нової бібліотеки на Оболоні. Книжковий фонд налічує понад 10 тисяч сучасних видань українською мовою.",
        "Кияни пропонують облаштувати велодоріжки на проспекті Перемоги. Відповідна петиція набрала необхідні голоси.",
        "Зниження тарифів на проїзд у міській електричці для студентів та школярів столиці.",
        "КМДА закликає мешканців бути обережними під час грози та не паркувати автомобілі під деревами.",
        "Історія створення Золотих воріт: цікаві історичні факти про головну браму стародавнього Києва."
    ]

    raw_items_data = []
    
    # 1. Unique events (1 to 20)
    for i, (title, venue, date_str, desc) in enumerate(unique_events):
        raw_items_data.append({
            "external_id": f"stress_unique_{i}",
            "url": f"https://stresstest.kyiv.ua/event/{i}",
            "title": title,
            "raw_text": f"⭐️ {title} ⭐️\n\nКоли: {date_str}\nДе: {venue}\n\n{desc}",
            "is_event": True
        })
        
    # 2. Duplicate events (21 to 40)
    for i, (title, venue, date_str, desc) in enumerate(duplicates):
        raw_items_data.append({
            "external_id": f"stress_dup_{i}",
            "url": f"https://stresstest.kyiv.ua/duplicate/{i}",
            "title": title,
            "raw_text": f"🔥 Увага! {title} 🔥\n\nМісце проведення: {venue}\nДата: {date_str}\n\n{desc}",
            "is_event": True
        })
        
    # 3. Non-events (41 to 50)
    for i, text in enumerate(non_events):
        raw_items_data.append({
            "external_id": f"stress_nonevent_{i}",
            "url": f"https://stresstest.kyiv.ua/news/{i}",
            "title": f"Міська новина №{i}",
            "raw_text": text,
            "is_event": False
        })
        
    return raw_items_data

async def seed_stress_raw_items(raw_items_data) -> list:
    from app.core.security import compute_raw_item_hash
    item_ids = []
    async with AsyncSessionLocal() as session:
        for data in raw_items_data:
            item_hash = compute_raw_item_hash(data["raw_text"], data["url"])
            
            # Check if exists
            q = await session.execute(select(RawItem).where(RawItem.hash == item_hash))
            raw_item = q.scalar_one_or_none()
            if not raw_item:
                raw_item = RawItem(
                    source_id=888,
                    external_id=data["external_id"],
                    url=data["url"],
                    title=data["title"],
                    raw_text=data["raw_text"],
                    published_at=datetime.utcnow(),
                    fetched_at=datetime.utcnow(),
                    hash=item_hash,
                    processing_status="new"
                )
                session.add(raw_item)
                await session.flush()
                item_ids.append(raw_item.id)
            else:
                raw_item.processing_status = "new"
                raw_item.error_message = None
                item_ids.append(raw_item.id)
        await session.commit()
    return item_ids

async def run_concurrent_stress_test(item_ids):
    safe_print(f"\n[STARTING TEST] Launching {len(item_ids)} concurrent raw item tasks in parallel...")
    start_time = time.time()
    
    # Run all process jobs concurrently using asyncio.gather
    tasks = [process_raw_item_job(item_id) for item_id in item_ids]
    
    # We will gather results and handle any exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    elapsed_time = time.time() - start_time
    safe_print(f"[COMPLETED] Concurrent tasks completed in {elapsed_time:.3f} seconds.")
    
    # Check for exceptions
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        safe_print(f"[WARNING] {len(errors)} tasks raised exceptions during concurrent execution!")
        for i, err in enumerate(errors[:3]):
            safe_print(f"   Exception {i+1}: {type(err).__name__} - {err}")
    else:
        safe_print("[OK] All tasks completed without raising script-level exceptions.")
        
    return elapsed_time, errors

async def print_stress_report(elapsed_time, errors, unique_items_count):
    safe_print("\n" + "=" * 60)
    safe_print("           STRESS TEST CONCURRENCY METRICS REPORT           ")
    safe_print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # 1. Raw Items Status
        processed_q = await session.execute(
            select(RawItem.processing_status, func.count(RawItem.id))
            .where(RawItem.source_id == 888)
            .group_by(RawItem.processing_status)
        )
        raw_status = dict(processed_q.all())
        
        # 2. Events count created
        events_q = await session.execute(
            select(func.count(Event.id))
            .where(Event.source_url.like("https://stresstest.kyiv.ua/%"))
        )
        events_created = events_q.scalar()
        
        # 3. Duplicate groups
        dup_groups_q = await session.execute(
            select(Event.duplicate_group_id, func.count(Event.id))
            .where(Event.source_url.like("https://stresstest.kyiv.ua/%"))
            .group_by(Event.duplicate_group_id)
        )
        dup_groups = dup_groups_q.all()
        
    safe_print(f"Total processing time: {elapsed_time:.3f} seconds")
    safe_print(f"Average processing speed: {unique_items_count / elapsed_time:.2f} items/sec")
    safe_print(f"Tasks raising exceptions: {len(errors)}")
    
    safe_print("\n--- Raw Items DB Status ---")
    for status, count in raw_status.items():
        safe_print(f"   - {status}: {count}")
        
    safe_print(f"\nEvents created in DB: {events_created}")
    
    safe_print("\n--- Duplicate Resolution Groups ---")
    grouped_events_count = 0
    unique_groups_count = 0
    for group_id, count in dup_groups:
        if group_id is not None:
            safe_print(f"   - Group ID {group_id}: contains {count} duplicate events")
            grouped_events_count += count
            unique_groups_count += 1
            
    safe_print(f"   - Total duplicate groups detected: {unique_groups_count}")
    safe_print(f"   - Total items resolved as duplicates: {grouped_events_count}")
    safe_print("=" * 60)
    
    if raw_status.get("error", 0) > 0:
        safe_print("[FAIL] Database lock or concurrency errors detected in DB!")
    else:
        safe_print("[SUCCESS] SQLite database handled concurrent writes and AI calls perfectly!")

async def clear_previous_stress_data():
    async with AsyncSessionLocal() as session:
        # Delete previous test events
        await session.execute(
            Event.__table__.delete().where(Event.source_url.like("https://stresstest.kyiv.ua/%"))
        )
        # Delete previous test raw items
        await session.execute(
            RawItem.__table__.delete().where(RawItem.source_id == 888)
        )
        await session.commit()
    safe_print("[INFO] Cleared previous stress test records from DB.")

if __name__ == "__main__":
    async def main():
        safe_print("=" * 75)
        safe_print("[START] RUNNING KYIV EVENT GUIDE STRESS TEST [START]")
        safe_print("=" * 75)
        
        await setup_db_tables()
        await clear_previous_stress_data()
        
        # 1. Generate 50 items
        data = generate_stress_data()
        safe_print(f"[INFO] Generated {len(data)} test items (20 Unique events, 20 Duplicates, 10 Non-events).")
        
        # 2. Insert as NEW in database
        unique_items_ids = await seed_stress_raw_items(data)
        safe_print(f"[OK] Seeded {len(unique_items_ids)} raw items as 'new' in DB.")
        
        # 3. Run concurrently
        elapsed_time, errors = await run_concurrent_stress_test(unique_items_ids)
        
        # 4. Print results
        await print_stress_report(elapsed_time, errors, len(unique_items_ids))
        
        safe_print("\n" + "=" * 75)
        safe_print("[END] STRESS TEST RUN COMPLETED [END]")
        safe_print("=" * 75)

    asyncio.run(main())
