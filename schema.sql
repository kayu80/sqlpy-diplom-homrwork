-- ──────────────────────────────────────────
-- Схема БД «EnglishCard»
-- ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    user_id     BIGINT PRIMARY KEY,
    username    VARCHAR(255),
    first_name  VARCHAR(255),
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dictionary (
    id          SERIAL PRIMARY KEY,
    word        VARCHAR(100) NOT NULL UNIQUE,
    translation VARCHAR(255) NOT NULL,
    category    VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS user_words (
    id          SERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    word        VARCHAR(100) NOT NULL,
    translation VARCHAR(255) NOT NULL,
    added_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, word)
);

-- ── Начальное наполнение общего словаря ──
INSERT INTO dictionary (word, translation, category) VALUES
    ('Red',   'Красный', 'colors'),
    ('Green', 'Зелёный', 'colors'),
    ('Blue',  'Синий',   'colors'),
    ('White', 'Белый',   'colors'),
    ('Black', 'Чёрный',  'colors'),
    ('I',     'Я',       'pronouns'),
    ('You',   'Ты',      'pronouns'),
    ('He',    'Он',      'pronouns'),
    ('She',   'Она',     'pronouns'),
    ('We',    'Мы',      'pronouns')
ON CONFLICT (word) DO NOTHING;
