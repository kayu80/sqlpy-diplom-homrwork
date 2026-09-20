"""
Telegram-бот «EnglishCard» — изучение английского языка.
Бот предлагает карточки с переводом, позволяет добавлять
и удалять персональные слова для каждого пользователя.
"""

import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

import db

# ── Инициализация БД ──────────────────────────
db.init_db()
db.fill_dictionary()

print("Start telegram bot...")

TOKEN = ""  # ← вставьте токен вашего бота
state_storage = StateMemoryStorage()
bot = TeleBot(TOKEN, state_storage=state_storage)

known_users = []
user_step = {}


class Command:
    ADD_WORD = "Добавить слово ➕"
    DELETE_WORD = "Удалить слово 🔙"
    NEXT = "Дальше ⏭"


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    add_word_state = State()


def show_hint(*lines):
    return "\n".join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


@bot.message_handler(commands=["cards", "start"])
def create_cards(message):
    """Главный обработчик: показывает карточку с переводом и кнопками."""
    cid = message.chat.id
    uid = message.from_user.id

    # Регистрируем пользователя в БД
    db.ensure_user(uid, message.from_user.username, message.from_user.first_name)

    if cid not in known_users:
        known_users.append(cid)
        user_step[cid] = 0
        bot.send_message(cid, "Привет! Давай учить английский 🇬🇧")

    card = db.pick_card_data(uid)
    target_word = card["target_word"]
    translate = card["translate_word"]
    others = card["other_words"]

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = []

    buttons.append(types.KeyboardButton(target_word))
    buttons.extend(types.KeyboardButton(word) for word in others)
    random.shuffle(buttons)

    buttons.extend([
        types.KeyboardButton(Command.NEXT),
        types.KeyboardButton(Command.ADD_WORD),
        types.KeyboardButton(Command.DELETE_WORD),
    ])
    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(cid, greeting, reply_markup=markup)
    bot.set_state(uid, MyStates.target_word, cid)

    with bot.retrieve_data(uid, cid) as data:
        data["target_word"] = target_word
        data["translate_word"] = translate
        data["other_words"] = others

    user_step[cid] = 0


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    """Удаляет текущее слово из персонального словаря пользователя."""
    cid = message.chat.id
    uid = message.from_user.id

    with bot.retrieve_data(uid, cid) as data:
        target_word = data.get("target_word")

    if not target_word:
        bot.send_message(cid, "Сейчас нет активного слова для удаления.")
        return

    deleted = db.delete_user_word(uid, target_word)
    if deleted:
        bot.send_message(cid, f"🗑 Слово «{target_word}» удалено из твоего словаря.")
    else:
        bot.send_message(
            cid,
            f"Слово «{target_word}» — из общего словаря, его нельзя удалить.",
        )
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_start(message):
    """Начинает процесс добавления слова."""
    cid = message.chat.id
    uid = message.from_user.id

    user_step[cid] = 1
    bot.set_state(uid, MyStates.add_word_state, cid)
    bot.send_message(
        cid,
        "Напиши слово и перевод через вертикальную черту.\n"
        "Пример:  Apple | Яблоко",
    )


@bot.message_handler(state=MyStates.add_word_state, func=lambda m: True)
def add_word_finish(message):
    """Принимает и сохраняет новое слово пользователя."""
    cid = message.chat.id
    uid = message.from_user.id

    text = message.text.strip()
    parts = [p.strip() for p in text.split("|")]

    if len(parts) != 2 or not parts[0] or not parts[1]:
        bot.send_message(
            cid,
            "Формат:  Слово | Перевод\nПример:  Apple | Яблоко",
        )
        return

    word, translation = parts
    success, err = db.add_user_word(uid, word, translation)

    if success:
        total = db.count_user_words(uid)
        bot.send_message(
            cid,
            f"✅ Слово «{word}» добавлено!\n"
            f"В твоём словаре теперь {total} персональных слов.",
        )
    else:
        bot.send_message(cid, f"⚠ {err}")

    user_step[cid] = 0
    create_cards(message)


@bot.message_handler(state=MyStates.target_word, func=lambda m: True, content_types=["text"])
def message_reply(message):
    """Проверяет ответ пользователя на карточку."""
    text = message.text
    cid = message.chat.id

    markup = types.ReplyKeyboardMarkup(row_width=2)

    with bot.retrieve_data(message.from_user.id, cid) as data:
        target_word = data["target_word"]

        if text == target_word:
            hint = show_hint("Отлично! ❤", show_target(data))
            markup.add(
                types.KeyboardButton(Command.NEXT),
                types.KeyboardButton(Command.ADD_WORD),
                types.KeyboardButton(Command.DELETE_WORD),
            )
        else:
            # Собираем кнопки заново, помечая ошибку
            other_words = data["other_words"]
            all_words = [target_word] + other_words
            buttons = [types.KeyboardButton(w) for w in all_words]
            random.shuffle(buttons)
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + " ❌"
                    break
            buttons.extend([
                types.KeyboardButton(Command.NEXT),
                types.KeyboardButton(Command.ADD_WORD),
                types.KeyboardButton(Command.DELETE_WORD),
            ])
            markup.add(*buttons)
            hint = show_hint(
                "Допущена ошибка!",
                f"Попробуй ещё раз вспомнить слово 🇷🇺 {data['translate_word']}",
            )

    bot.send_message(cid, hint, reply_markup=markup)


# ── Запуск бота ───────────────────────────────
bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
