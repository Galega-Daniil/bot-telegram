import random
import pyTelegramBotApi
from telebot import types

TOKEN = "******************"
bot = telebot.TeleBot(TOKEN)

WORDS = [
    "ПРОГРАММИСТ", "СЕРВЕР", "БРАУЗЕР", "АЛГОРИТМ", "ТЕРМИНАЛ",
    "КЛАВИАТУРА", "ИНТЕРНЕТ", "КОМПЬЮТЕР", "ПИТОН", "РЕПОЗИТОРИЙ"
]

HANGMAN_STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```"
]

BOARD_SIZE = 8
SHIPS_FLEET = [3, 2, 2, 1, 1, 1]

hangman_games = {}
battleship_games = {}


# ==================== ГЛАВНОЕ МЕНЮ ====================
def main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Виселица", "Морской бой")
    return markup


@bot.message_handler(commands=["start", "menu"])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "🎮 **Выбери игру в меню ниже:**\n"
        "• **Виселица** — угадай слово по буквам\n"
        "• **Морской бой** — потопи флот бота на поле 8×8",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


# ==================== ЛОГИКА «МОРСКОГО БОЯ» ====================
def create_empty_board():
    return [[0 for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def can_place_ship(board, r, c, length, horizontal):
    for i in range(length):
        nr = r + (0 if horizontal else i)
        nc = c + (i if horizontal else 0)
        if not (0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE):
            return False
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = nr + dr, nc + dc
                if 0 <= rr < BOARD_SIZE and 0 <= cc < BOARD_SIZE:
                    if board[rr][cc] == 1:
                        return False
    return True


def generate_fleet():
    board = create_empty_board()
    for length in SHIPS_FLEET:
        placed = False
        while not placed:
            horizontal = random.choice([True, False])
            r = random.randint(0, BOARD_SIZE - 1)
            c = random.randint(0, BOARD_SIZE - 1)
            if can_place_ship(board, r, c, length, horizontal):
                for i in range(length):
                    nr = r + (0 if horizontal else i)
                    nc = c + (i if horizontal else 0)
                    board[nr][nc] = 1
                placed = True
    return board


def render_player_board(board):
    symbols = {0: "🟦", 1: "🟩", 2: "⚪", 3: "🔥"}
    return "\n".join("".join(symbols[cell] for cell in row) for row in board)


def build_enemy_keyboard(enemy_board, reveal=False):
    markup = types.InlineKeyboardMarkup(row_width=BOARD_SIZE)
    for r in range(BOARD_SIZE):
        buttons = []
        for c in range(BOARD_SIZE):
            cell = enemy_board[r][c]
            if cell == 3:
                text = "🔥"
            elif cell == 2:
                text = "⚪"
            elif cell == 1 and reveal:
                text = "🚢"
            else:
                text = "🌊"
            buttons.append(types.InlineKeyboardButton(text, callback_data=f"bs_{r}_{c}"))
        markup.row(*buttons)
    return markup


def count_alive_decks(board):
    return sum(row.count(1) for row in board)


@bot.message_handler(commands=["battleship"])
@bot.message_handler(func=lambda m: m.text == "🚢 Морской бой")
def start_battleship(message):
    chat_id = message.chat.id
    hangman_games.pop(chat_id, None)

    player_board = generate_fleet()
    enemy_board = generate_fleet()
    available_shots = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)]
    random.shuffle(available_shots)

    battleship_games[chat_id] = {
        "player": player_board,
        "enemy": enemy_board,
        "bot_shots": available_shots
    }

    text = (
        "🚢 **Морской бой (8×8)!**\n"
        "Флот: 1×🚢🚢🚢, 2×🚢🚢, 3×🚢\n\n"
        f"**Твоё поле:**\n{render_player_board(player_board)}\n\n"
        "👇 **Нажимай на клетки поля противника, чтобы сделать выстрел:**"
    )
    bot.send_message(
        chat_id,
        text,
        reply_markup=build_enemy_keyboard(enemy_board),
        parse_mode="Markdown"
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("bs_"))
def handle_battleship_shot(call):
    chat_id = call.message.chat.id
    if chat_id not in battleship_games:
        bot.answer_callback_query(call.id, "Игра завершена. Нажми «🚢 Морской бой», чтобы начать новую!")
        return

    game = battleship_games[chat_id]
    _, r_str, c_str = call.data.split("_")
    r, c = int(r_str), int(c_str)
    enemy_board = game["enemy"]
    player_board = game["player"]

    if enemy_board[r][c] in (2, 3):
        bot.answer_callback_query(call.id, "Ты уже стрелял в эту клетку!")
        return

    if enemy_board[r][c] == 1:
        enemy_board[r][c] = 3
        player_status = f"Ты попал по координатам ({r+1}, {c+1})!"
    else:
        enemy_board[r][c] = 2
        player_status = f"Ты промахнулся ({r+1}, {c+1})."

    if count_alive_decks(enemy_board) == 0:
        del battleship_games[chat_id]
        bot.edit_message_text(
            f"🏆 **ПОБЕДА! Весь флот противника потоплен!**\n\n"
            f"**Твоё поле:**\n{render_player_board(player_board)}",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=build_enemy_keyboard(enemy_board, reveal=True),
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Победа!")
        return

    br, bc = game["bot_shots"].pop()
    if player_board[br][bc] == 1:
        player_board[br][bc] = 3
        bot_status = f"Бот попал в твой корабль ({br+1}, {bc+1})!"
    else:
        player_board[br][bc] = 2
        bot_status = f"Бот промахнулся ({br+1}, {bc+1})."

    if count_alive_decks(player_board) == 0:
        del battleship_games[chat_id]
        bot.edit_message_text(
            f"**ПОРАЖЕНИЕ! Бот уничтожил все твои корабли.**\n\n"
            f"**Твоё поле:**\n{render_player_board(player_board)}\n\n"
            "Корабли бота показаны на сетке ниже:",
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=build_enemy_keyboard(enemy_board, reveal=True),
            parse_mode="Markdown"
        )
        bot.answer_callback_query(call.id, "Игра окончена!")
        return

    updated_text = (
        f"{player_status}\n{bot_status}\n\n"
        f"**Твоё поле** (осталось палуб: {count_alive_decks(player_board)}):\n"
        f"{render_player_board(player_board)}\n\n"
        f"👇 **Поле противника** (осталось палуб: {count_alive_decks(enemy_board)}):"
    )
    bot.edit_message_text(
        updated_text,
        chat_id=chat_id,
        message_id=call.message.message_id,
        reply_markup=build_enemy_keyboard(enemy_board),
        parse_mode="Markdown"
    )
    bot.answer_callback_query(call.id)


def format_hangman_board(game):
    word = game["word"]
    guessed = game["guessed"]
    errors = game["errors"]

    masked_word = " ".join([letter if letter in guessed else "_" for letter in word])
    used_letters = ", ".join(sorted(guessed)) if guessed else "пока нет"

    return (
        f"{HANGMAN_STAGES[errors]}\n"
        f"Слово: `{masked_word}`\n"
        f"Ошибок: {errors} из 6\n"
        f"Использованные буквы: {used_letters}\n\n"
        f"Введи следующую букву (или слово целиком):"
    )


@bot.message_handler(commands=["hangman", "newgame"])
@bot.message_handler(func=lambda m: m.text == "🪢 Виселица")
def start_hangman(message):
    chat_id = message.chat.id
    battleship_games.pop(chat_id, None)

    hangman_games[chat_id] = {
        "word": random.choice(WORDS),
        "guessed": set(),
        "errors": 0
    }
    bot.send_message(
        chat_id,
        "**Новая игра «Виселица» началась!**\n" + format_hangman_board(hangman_games[chat_id]),
        parse_mode="Markdown"
    )


@bot.message_handler(content_types=["text"])
def handle_hangman_guess(message):
    chat_id = message.chat.id

    if chat_id not in hangman_games:
        bot.send_message(
            chat_id,
            "Выбери игру на клавиатуре ниже или отправь /start",
            reply_markup=main_menu_keyboard()
        )
        return

    game = hangman_games[chat_id]
    guess = message.text.strip().upper().replace("Ё", "Е")
    secret_word = game["word"]

    if len(guess) > 1:
        if guess == secret_word:
            del hangman_games[chat_id]
            bot.send_message(
                chat_id,
                f"🎉 **Победа!** Ты угадал слово целиком: `{secret_word}`!",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
        else:
            game["errors"] += 1
            if game["errors"] >= 6:
                del hangman_games[chat_id]
                bot.send_message(
                    chat_id,
                    f"{HANGMAN_STAGES[6]}\n💀 **Поражение!** Было загадано: `{secret_word}`.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(
                    chat_id,
                    "Неверное слово!\n" + format_hangman_board(game),
                    parse_mode="Markdown"
                )
        return

    if not guess.isalpha() or not ("А" <= guess <= "Я"):
