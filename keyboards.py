from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="✦ Стикеры", callback_data="stickers")],
        [InlineKeyboardButton(text="✦ Комиксы", callback_data="comics")],
        [InlineKeyboardButton(text="✦ Арт подборки", callback_data="art")],
        [InlineKeyboardButton(text="✦ Анимации и видео", callback_data="animation")],
        [InlineKeyboardButton(text="✦ Личное", callback_data="personal")],
        [InlineKeyboardButton(text="✦ Игры", callback_data="games")],
        [InlineKeyboardButton(text="✦ Другие соцсети", callback_data="socials")],
        [InlineKeyboardButton(text="✦ вернуться в канал", url="https://t.me/ame_tanami")],
    ]
)
