"""
Модуль для работы с PostgreSQL.
Содержит функции инициализации БД, регистрации пользователей,
получения слов для карточек, добавления и удаления персональных слов.
"""

import random

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    "dbname": "englishcard_db",
    "user": "postgres",
    "password": "1234",          # ← замените на свой пароль
    "host": "localhost",
    "port": 5432,
}


def get_conn():
    """Возвращает соединение с БД."""
    return psycopg2.connect(**DB_CONFIG)


def init_db():
    """Создаёт таблицы, если их ещё нет."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     BIGINT PRIMARY KEY,
                    username    VARCHAR(255),
                    first_name  VARCHAR(255),
                    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS dictionary (
                    id          SERIAL PRIMARY KEY,
                    word        VARCHAR(100) NOT NULL UNIQUE,
                    translation VARCHAR(255) NOT NULL,
                    category    VARCHAR(50)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    id          SERIAL PRIMARY KEY,
                    user_id     BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    word        VARCHAR(100) NOT NULL,
                    translation VARCHAR(255) NOT NULL,
                    added_at    TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, word)
                );
            """)
        conn.commit()


def fill_dictionary():
    """Заполняет общий словарь 10 стартовыми словами (если пусто)."""
    words = [
        ("Red", "Красный", "colors"),
        ("Green", "Зелёный", "colors"),
        ("Blue", "Синий", "colors"),
        ("White", "Белый", "colors"),
        ("Black", "Чёрный", "colors"),
        ("I", "Я", "pronouns"),
        ("You", "Ты", "pronouns"),
        ("He", "Он", "pronouns"),
        ("She", "Она", "pronouns"),
        ("We", "Мы", "pronouns"),
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM dictionary;")
            count = cur.fetchone()[0]
            if count == 0:
                cur.executemany(
                    """
                    INSERT INTO dictionary (word, translation, category)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (word) DO NOTHING;
                    """,
                    words,
                )
        conn.commit()


def ensure_user(user_id, username, first_name):
    """Регистрирует пользователя в БД (или обновляет данные)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, username, first_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    username   = EXCLUDED.username,
                    first_name = EXCLUDED.first_name;
                """,
                (user_id, username, first_name),
            )
        conn.commit()


def get_words_for_user(user_id):
    """Возвращает список кортежей (word, translation) — общие + персональные."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT word, translation FROM dictionary;")
            global_words = cur.fetchall()

            cur.execute(
                "SELECT word, translation FROM user_words WHERE user_id = %s;",
                (user_id,),
            )
            personal_words = cur.fetchall()

    return global_words + personal_words


def pick_card_data(user_id):
    """Выбирает случайное слово для карточки и 3 варианта ответа."""
    words = get_words_for_user(user_id)
    if not words:
        return {
            "target_word": "Peace",
            "translate_word": "Мир",
            "other_words": ["Green", "White", "Hello"],
        }

    target = random.choice(words)
    target_word, target_translation = target

    others = [w for w in words if w[0] != target_word]
    random.shuffle(others)
    other_words = [w[0] for w in others[:3]]

    fallback = ["Dog", "Cat", "Tree", "Sky", "House", "Book", "Water", "Fire"]
    while len(other_words) < 3:
        extra = random.choice(fallback)
        if extra != target_word and extra not in other_words:
            other_words.append(extra)

    return {
        "target_word": target_word,
        "translate_word": target_translation,
        "other_words": other_words,
    }


def add_user_word(user_id, word, translation):
    """Добавляет персональное слово пользователя.
    Возвращает (True, None) при успехе или (False, msg) при ошибке.
    """
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_words (user_id, word, translation)
                    VALUES (%s, %s, %s);
                    """,
                    (user_id, word, translation),
                )
            conn.commit()
        return True, None
    except psycopg2.errors.UniqueViolation:
        return False, "Это слово уже есть в твоём словаре."


def delete_user_word(user_id, word):
    """Удаляет персональное слово пользователя.
    Возвращает True, если слово было удалено, иначе False.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_words WHERE user_id = %s AND word = %s;",
                (user_id, word),
            )
            deleted = cur.rowcount
        conn.commit()
    return deleted > 0


def count_user_words(user_id):
    """Возвращает количество персональных слов пользователя."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_words WHERE user_id = %s;",
                (user_id,),
            )
            return cur.fetchone()[0]
