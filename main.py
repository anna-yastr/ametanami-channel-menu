from aiogram import Bot, Dispatcher
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto, InputMediaAnimation, InputMediaVideo,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from keyboards import main_menu
from pathlib import Path
import asyncio
import json
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

open_menu_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✦ открыть меню")]],
    resize_keyboard=True,
)

PHOTOS_FILE = Path("photos.json")
POSTS_FILE = Path("posts.json")
SECTIONS = {"stickers", "comics", "art", "animation", "personal", "games", "socials"}

CAPTIONS = {
    "main":     "Приветы! Я Ame Tanami, и ты попал в библиотеку моего творчества ✦ Тут можно побродить по комиксам, арт-подборкам, анимациям, стикерам и даже играм ^^ А всё остальное продолжает жить в <a href=\"https://t.me/ame_tanami\">✦канале✦</a>",
    "stickers": "✦ Стикеры",
    "comics":   "✦ Мини-комиксы",
    "art":       "✦ Арт подборки",
    "animation": "✦ Анимации и видео",
    "personal":  "✦ Личное",
    "games":    "✦ Игры",
    "socials":  "✦ Другие соцсети",
}


def load_photos() -> dict:
    if PHOTOS_FILE.exists():
        return json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))
    return {"main": "", **{s: [] for s in SECTIONS}}


def save_photos(data: dict) -> None:
    PHOTOS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_posts() -> dict:
    if POSTS_FILE.exists():
        return json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    return {s: [] for s in SECTIONS}


def save_posts(data: dict) -> None:
    POSTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


photos = load_photos()
posts = load_posts()

_mg_buffer: dict[str, list] = {}
_mg_tasks: dict[str, asyncio.Task] = {}


def normalize(entry) -> dict:
    if isinstance(entry, str):
        return {"file_id": entry, "type": "photo"}
    return entry


def get_media(section: str, index: int = 0) -> dict | None:
    if section == "main":
        raw = photos.get("main", "")
        return normalize(raw) if raw else None
    imgs = photos.get(section, [])
    if imgs and 0 <= index < len(imgs):
        return normalize(imgs[index])
    return None


def make_input_media(entry: dict, caption: str):
    cap = entry.get("caption", caption)
    if entry["type"] == "animation":
        return InputMediaAnimation(media=entry["file_id"], caption=cap, parse_mode="HTML")
    if entry["type"] == "video":
        return InputMediaVideo(media=entry["file_id"], caption=cap, parse_mode="HTML")
    return InputMediaPhoto(media=entry["file_id"], caption=cap, parse_mode="HTML")


def build_section_keyboard(section: str, img_idx: int = 0) -> InlineKeyboardMarkup:
    imgs = photos.get(section, [])
    section_posts = posts.get(section, [])
    rows = []

    if len(imgs) > 1:
        prev_i = (img_idx - 1) % len(imgs)
        next_i = (img_idx + 1) % len(imgs)
        rows.append([
            InlineKeyboardButton(text="◁", callback_data=f"nav_{section}_{prev_i}"),
            InlineKeyboardButton(text=f"{img_idx + 1} / {len(imgs)}", callback_data="noop"),
            InlineKeyboardButton(text="▷", callback_data=f"nav_{section}_{next_i}"),
        ])

    for i, p in enumerate(section_posts):
        if p.get("url"):
            rows.append([InlineKeyboardButton(text=f"✦ {p['title']}", url=p["url"])])
        else:
            rows.append([InlineKeyboardButton(text=f"✦ {p['title']}", callback_data=f"showpost_{section}_{i}")])

    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_post_keyboard(section: str, post_idx: int, img_idx: int) -> InlineKeyboardMarkup:
    images = posts[section][post_idx].get("images", [])
    rows = []
    if len(images) > 1:
        prev_i = (img_idx - 1) % len(images)
        next_i = (img_idx + 1) % len(images)
        rows.append([
            InlineKeyboardButton(text="◁", callback_data=f"postview_{section}_{post_idx}_{prev_i}"),
            InlineKeyboardButton(text=f"{img_idx + 1} / {len(images)}", callback_data="noop"),
            InlineKeyboardButton(text="▷", callback_data=f"postview_{section}_{post_idx}_{next_i}"),
        ])
    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data=section)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_submenu_keyboard(section: str, post_idx: int) -> InlineKeyboardMarkup:
    children = posts[section][post_idx].get("children", [])
    rows = []
    for i, child in enumerate(children):
        if child.get("url"):
            rows.append([InlineKeyboardButton(text=f"✦ {child['title']}", url=child["url"])])
        else:
            rows.append([InlineKeyboardButton(text=f"✦ {child['title']}", callback_data=f"subpost_{section}_{post_idx}_{i}")])
    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data=section)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subsubmenu_keyboard(section: str, post_idx: int, child_idx: int) -> InlineKeyboardMarkup:
    grandchildren = posts[section][post_idx]["children"][child_idx].get("children", [])
    rows = []
    for i, gc in enumerate(grandchildren):
        if gc.get("url"):
            rows.append([InlineKeyboardButton(text=f"✦ {gc['title']}", url=gc["url"])])
        else:
            rows.append([InlineKeyboardButton(text=f"✦ {gc['title']}", callback_data=f"subsubpost_{section}_{post_idx}_{child_idx}_{i}")])
    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data=f"submenu_{section}_{post_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subsubpost_keyboard(section: str, post_idx: int, child_idx: int, grandchild_idx: int, img_idx: int) -> InlineKeyboardMarkup:
    gc = posts[section][post_idx]["children"][child_idx]["children"][grandchild_idx]
    images = gc.get("images", [])
    rows = []
    if len(images) > 1:
        prev_i = (img_idx - 1) % len(images)
        next_i = (img_idx + 1) % len(images)
        rows.append([
            InlineKeyboardButton(text="◁", callback_data=f"subsubpostview_{section}_{post_idx}_{child_idx}_{grandchild_idx}_{prev_i}"),
            InlineKeyboardButton(text=f"{img_idx + 1} / {len(images)}", callback_data="noop"),
            InlineKeyboardButton(text="▷", callback_data=f"subsubpostview_{section}_{post_idx}_{child_idx}_{grandchild_idx}_{next_i}"),
        ])
    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data=f"subsubmenu_{section}_{post_idx}_{child_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_subpost_keyboard(section: str, post_idx: int, child_idx: int, img_idx: int) -> InlineKeyboardMarkup:
    child = posts[section][post_idx]["children"][child_idx]
    images = child.get("images", [])
    rows = []
    if len(images) > 1:
        prev_i = (img_idx - 1) % len(images)
        next_i = (img_idx + 1) % len(images)
        rows.append([
            InlineKeyboardButton(text="◁", callback_data=f"subpostview_{section}_{post_idx}_{child_idx}_{prev_i}"),
            InlineKeyboardButton(text=f"{img_idx + 1} / {len(images)}", callback_data="noop"),
            InlineKeyboardButton(text="▷", callback_data=f"subpostview_{section}_{post_idx}_{child_idx}_{next_i}"),
        ])
    rows.append([InlineKeyboardButton(text="✦ ← назад", callback_data=f"submenu_{section}_{post_idx}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def has_media(msg: Message) -> bool:
    return bool(msg.photo or msg.animation or msg.video)


# ── Разбор подписи ────────────────────────────────────────────────────────
#
# "stickers"         → обложка раздела, заменить
# "stickers +"       → обложка раздела, добавить
# "stickers 1"       → картинки поста №1, заменить
# "stickers 1 +"     → картинки поста №1, добавить
# "personal 1 2"     → картинки подпункта №2 поста №1, заменить
# "personal 1 2 +"   → картинки подпункта №2 поста №1, добавить

def _parse_caption(caption: str) -> tuple:
    """(section | None, post_idx | None, child_idx | None, action)"""
    parts = caption.strip().lower().split()
    valid = {"main"} | SECTIONS
    if not parts or parts[0] not in valid:
        return None, None, None, "replace"
    section = parts[0]
    if section == "main":
        return section, None, None, "replace"
    if len(parts) > 1 and parts[1].isdigit():
        post_idx = int(parts[1]) - 1
        if len(parts) > 2 and parts[2].isdigit():
            child_idx = int(parts[2]) - 1
            action = parts[3] if len(parts) > 3 else "replace"
            return section, post_idx, child_idx, action
        action = parts[2] if len(parts) > 2 else "replace"
        return section, post_idx, None, action
    action = parts[1] if len(parts) > 1 else "replace"
    return section, None, None, action


async def _apply_entries(entries: list, section: str, post_idx, child_idx, action: str, reply_to: Message):
    if section == "main":
        photos["main"] = entries[0]
        save_photos(photos)
        await reply_to.reply("✓ главное медиа обновлено")
        return

    if post_idx is not None:
        section_posts = posts.get(section, [])
        if post_idx < 0 or post_idx >= len(section_posts):
            await reply_to.reply(f"нет поста #{post_idx + 1} в «{CAPTIONS[section]}»")
            return
        p = section_posts[post_idx]

        if child_idx is not None:
            children = p.get("children", [])
            if child_idx < 0 or child_idx >= len(children):
                await reply_to.reply(f"нет подпункта #{child_idx + 1} в посте «{p['title']}»")
                return
            child = children[child_idx]
            if action == "+":
                child.setdefault("images", []).extend(entries)
            else:
                child["images"] = entries
            save_posts(posts)
            await reply_to.reply(f"✓ «{child['title']}» — {len(child['images'])} картинок")
        else:
            if action == "+":
                p.setdefault("images", []).extend(entries)
            else:
                p["images"] = entries
            save_posts(posts)
            await reply_to.reply(f"✓ «{p['title']}» — {len(p['images'])} картинок")
    else:
        if action == "+":
            photos[section].extend(entries)
        else:
            photos[section] = entries
        save_photos(photos)
        await reply_to.reply(f"✓ обложка «{CAPTIONS[section]}»: {len(photos[section])} шт.")


# ── Админ: загрузка медиа ─────────────────────────────────────────────────

def _msg_to_entry(message: Message) -> dict | None:
    if message.animation:
        return {"file_id": message.animation.file_id, "type": "animation"}
    if message.video:
        return {"file_id": message.video.file_id, "type": "video"}
    if message.photo:
        return {"file_id": message.photo[-1].file_id, "type": "photo"}
    return None


async def _flush_media_group(group_id: str):
    await asyncio.sleep(0.3)
    messages = _mg_buffer.pop(group_id, [])
    _mg_tasks.pop(group_id, None)
    if not messages:
        return

    caption = next((m.caption for m in messages if m.caption), "")
    section, post_idx, child_idx, action = _parse_caption(caption)

    if section is None:
        await messages[0].reply(
            "укажи в подписи первого фото:\n"
            "обложка раздела: <code>stickers</code>\n"
            "картинки поста №1: <code>stickers 1</code>\n"
            "картинки подпункта №2 поста №1: <code>personal 1 2</code>",
            parse_mode="HTML",
        )
        return

    entries = [e for m in messages if (e := _msg_to_entry(m))]
    await _apply_entries(entries, section, post_idx, child_idx, action, messages[0])


@dp.message(lambda m: m.from_user.id == ADMIN_ID and (m.photo is not None or m.animation is not None or m.video is not None))
async def set_media(message: Message):
    if message.media_group_id:
        gid = message.media_group_id
        _mg_buffer.setdefault(gid, []).append(message)
        if gid in _mg_tasks:
            _mg_tasks[gid].cancel()
        _mg_tasks[gid] = asyncio.create_task(_flush_media_group(gid))
        return

    section, post_idx, child_idx, action = _parse_caption(message.caption or "")

    if section is None:
        await message.reply(
            "укажи раздел в подписи:\n"
            "обложка раздела: <code>stickers</code>\n"
            "картинки поста №1: <code>stickers 1</code>\n"
            "картинки подпункта №2 поста №1: <code>personal 1 2</code>",
            parse_mode="HTML",
        )
        return

    entry = _msg_to_entry(message)
    await _apply_entries([entry], section, post_idx, child_idx, action, message)


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/clear_post "))
async def clear_post(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("формат: <code>/clear_post раздел номер</code>", parse_mode="HTML")
        return
    section, num = parts[1], parts[2]
    if section not in SECTIONS:
        await message.reply("неизвестный раздел")
        return
    try:
        idx = int(num) - 1
    except ValueError:
        await message.reply("номер должен быть числом")
        return
    if idx < 0 or idx >= len(posts.get(section, [])):
        await message.reply(f"нет поста #{idx + 1}")
        return
    posts[section][idx]["images"] = []
    save_posts(posts)
    await message.reply(f"✓ картинки поста «{posts[section][idx]['title']}» очищены")


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/clear_"))
async def clear_section(message: Message):
    section = message.text.removeprefix("/clear_").strip()
    if section not in SECTIONS:
        await message.reply("неизвестный раздел")
        return
    photos[section] = []
    save_photos(photos)
    await message.reply(f"✓ обложки «{CAPTIONS[section]}» очищены")


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/add_post "))
async def add_post(message: Message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply(
            "формат: <code>/add_post раздел название</code>\n"
            "пример: <code>/add_post comics Новый комикс</code>",
            parse_mode="HTML",
        )
        return
    _, section, title = parts
    if section not in SECTIONS:
        await message.reply(f"неизвестный раздел. доступные: {', '.join(sorted(SECTIONS))}")
        return
    posts[section].append({"title": title, "images": []})
    save_posts(posts)
    idx = len(posts[section])
    await message.reply(
        f"✓ пост #{idx} добавлен в «{CAPTIONS[section]}»: «{title}»\n"
        f"добавить картинки: отправь фото с подписью <code>{section} {idx}</code>",
        parse_mode="HTML",
    )


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/add_link "))
async def add_link(message: Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.reply(
            "формат: <code>/add_link раздел ссылка название</code>\n"
            "пример: <code>/add_link comics https://t.me/mychannel/42 Внутри</code>",
            parse_mode="HTML",
        )
        return
    _, section, url, title = parts
    if section not in SECTIONS:
        await message.reply(f"неизвестный раздел. доступные: {', '.join(sorted(SECTIONS))}")
        return
    posts[section].append({"title": title, "url": url})
    save_posts(posts)
    await message.reply(f"✓ ссылка добавлена в «{CAPTIONS[section]}»: «{title}»")


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/add_copy "))
async def add_copy(message: Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.reply(
            "формат: <code>/add_copy раздел айди_канала номера_через_запятую название</code>\n"
            "пример: <code>/add_copy stickers 4472109036 3 Пак стикеров</code>\n"
            "альбом: <code>/add_copy comics 4472109036 4,5,6,7,8 Внутри</code>",
            parse_mode="HTML",
        )
        return
    _, section, channel_id, rest = parts
    if section not in SECTIONS:
        await message.reply(f"неизвестный раздел. доступные: {', '.join(sorted(SECTIONS))}")
        return
    # rest = "4,5,6 Название" или "4 Название"
    rest_parts = rest.split(maxsplit=1)
    if len(rest_parts) < 2:
        await message.reply("укажи номера постов и название через пробел")
        return
    ids_str, title = rest_parts
    try:
        ids = [int(x) for x in ids_str.split(",")]
    except ValueError:
        await message.reply("номера постов — числа через запятую без пробелов: <code>4,5,6</code>", parse_mode="HTML")
        return
    posts[section].append({"title": title, "channel": channel_id, "ids": ids})
    save_posts(posts)
    await message.reply(f"✓ пост #{len(posts[section])} добавлен в «{CAPTIONS[section]}»: «{title}»")


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/add_subpost "))
async def add_subpost(message: Message):
    parts = message.text.split(maxsplit=3)
    if len(parts) < 4:
        await message.reply(
            "формат: <code>/add_subpost раздел номер_поста название</code>\n"
            "пример: <code>/add_subpost personal 1 Питер 2024</code>",
            parse_mode="HTML",
        )
        return
    _, section, num, title = parts
    if section not in SECTIONS:
        await message.reply("неизвестный раздел")
        return
    try:
        idx = int(num) - 1
    except ValueError:
        await message.reply("номер должен быть числом")
        return
    if idx < 0 or idx >= len(posts.get(section, [])):
        await message.reply(f"нет поста #{idx + 1}")
        return
    children = posts[section][idx].setdefault("children", [])
    children.append({"title": title, "images": []})
    save_posts(posts)
    child_num = len(children)
    await message.reply(
        f"✓ подпункт #{child_num} добавлен в «{posts[section][idx]['title']}»: «{title}»\n"
        f"картинки: фото с подписью <code>{section} {idx + 1} {child_num}</code>",
        parse_mode="HTML",
    )


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/remove_post "))
async def remove_post(message: Message):
    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("формат: <code>/remove_post раздел номер</code>", parse_mode="HTML")
        return
    section = parts[1]
    if section not in SECTIONS:
        await message.reply("неизвестный раздел")
        return
    try:
        idx = int(parts[2]) - 1
    except ValueError:
        await message.reply("номер должен быть числом")
        return
    if idx < 0 or idx >= len(posts.get(section, [])):
        await message.reply(f"нет поста #{idx + 1}")
        return
    removed = posts[section].pop(idx)
    save_posts(posts)
    await message.reply(f"✓ удалён: «{removed['title']}»")


@dp.message(lambda m: m.from_user.id == ADMIN_ID and m.text and m.text.startswith("/list_posts"))
async def list_posts_cmd(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or parts[1] not in SECTIONS:
        await message.reply(
            "формат: <code>/list_posts раздел</code>\n"
            f"разделы: {', '.join(sorted(SECTIONS))}",
            parse_mode="HTML",
        )
        return
    section = parts[1]
    section_posts = posts.get(section, [])
    if not section_posts:
        await message.reply(f"«{CAPTIONS[section]}» — постов нет")
        return
    lines = [f"<b>«{CAPTIONS[section]}»</b>:"]
    for i, p in enumerate(section_posts):
        count = len(p.get("images", []))
        lines.append(f"{i + 1}. {p['title']} — {count} картинок")
    await message.reply("\n".join(lines), parse_mode="HTML")


# ── Пользователь ─────────────────────────────────────────────────────────

async def show_main_menu(message: Message) -> None:
    entry = get_media("main")
    if entry:
        if entry["type"] == "animation":
            await message.answer_animation(
                animation=entry["file_id"], caption=CAPTIONS["main"], reply_markup=main_menu, parse_mode="HTML",
            )
        elif entry["type"] == "video":
            await message.answer_video(
                video=entry["file_id"], caption=CAPTIONS["main"], reply_markup=main_menu, parse_mode="HTML",
            )
        else:
            await message.answer_photo(
                photo=entry["file_id"], caption=CAPTIONS["main"], reply_markup=main_menu, parse_mode="HTML",
            )
    else:
        if message.from_user.id == ADMIN_ID:
            await message.answer(
                "⚠ главное медиа не задано — отправь фото/гиф с подписью <code>main</code>",
                parse_mode="HTML",
            )
        else:
            await message.answer(CAPTIONS["main"], reply_markup=main_menu, parse_mode="HTML")


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("✦", reply_markup=open_menu_kb)
    await show_main_menu(message)


@dp.message(lambda m: m.text == "✦ открыть меню")
async def open_menu(message: Message):
    await show_main_menu(message)


async def show_section_new(message: Message, section: str) -> None:
    entry = get_media(section, 0)
    keyboard = build_section_keyboard(section, 0)
    if entry:
        if entry["type"] == "animation":
            await message.answer_animation(entry["file_id"], caption=CAPTIONS[section], reply_markup=keyboard)
        elif entry["type"] == "video":
            await message.answer_video(entry["file_id"], caption=CAPTIONS[section], reply_markup=keyboard)
        else:
            await message.answer_photo(entry["file_id"], caption=CAPTIONS[section], reply_markup=keyboard)
    else:
        await message.answer(CAPTIONS[section], reply_markup=keyboard)


# ── Callback ──────────────────────────────────────────────────────────────

@dp.callback_query()
async def menu_handler(callback: CallbackQuery):
    await callback.answer()
    key = callback.data

    if key == "noop":
        return

    if key == "back":
        entry = get_media("main")
        if entry and has_media(callback.message):
            await callback.message.edit_media(
                media=make_input_media(entry, CAPTIONS["main"]),
                reply_markup=main_menu,
            )
        else:
            await callback.message.edit_caption(caption=CAPTIONS["main"], reply_markup=main_menu, parse_mode="HTML")
        return

    if key in SECTIONS:
        entry = get_media(key, 0)
        keyboard = build_section_keyboard(key, 0)
        if entry and has_media(callback.message):
            await callback.message.edit_media(
                media=make_input_media(entry, CAPTIONS[key]),
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_caption(caption=CAPTIONS[key], reply_markup=keyboard)
        return

    if key.startswith("backpost_"):
        section = key.split("_", 1)[1]
        try:
            await callback.message.delete()
        except Exception:
            pass
        await show_section_new(callback.message, section)
        return

    if key.startswith("nav_"):
        _, section, idx_str = key.split("_", 2)
        img_idx = int(idx_str)
        entry = get_media(section, img_idx)
        keyboard = build_section_keyboard(section, img_idx)
        if entry:
            await callback.message.edit_media(
                media=make_input_media(entry, CAPTIONS[section]),
                reply_markup=keyboard,
            )
        return

    if key.startswith("showpost_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        section_posts = posts.get(section, [])
        if post_idx >= len(section_posts):
            return
        post = section_posts[post_idx]

        # Тип 0: подменю с подпунктами
        if "children" in post:
            keyboard = build_submenu_keyboard(section, post_idx)
            if has_media(callback.message):
                await callback.message.edit_caption(caption=post["title"], reply_markup=keyboard)
            else:
                await callback.message.edit_text(text=post["title"], reply_markup=keyboard)
            return

        # Тип 1: скопировать из приватного канала
        if post.get("channel") and post.get("ids"):
            full_id = int(f"-100{post['channel']}")
            ids = post["ids"]
            try:
                if len(ids) == 1:
                    await bot.copy_message(
                        chat_id=callback.message.chat.id,
                        from_chat_id=full_id,
                        message_id=ids[0],
                    )
                else:
                    await bot.copy_messages(
                        chat_id=callback.message.chat.id,
                        from_chat_id=full_id,
                        message_ids=ids,
                    )
                nav_kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✦ ← назад", callback_data=f"backpost_{section}")
                ]])
                await callback.message.answer(post["title"], reply_markup=nav_kb)
            except Exception as e:
                print(f"showpost copy error: {e}")
                await callback.message.answer("контент временно недоступен")
            return

        # Тип 2: карусель картинок
        images = post.get("images", [])
        if not images:
            await callback.answer("картинок пока нет", show_alert=True)
            return
        entry = normalize(images[0])
        keyboard = build_post_keyboard(section, post_idx, 0)
        if has_media(callback.message):
            await callback.message.edit_media(
                media=make_input_media(entry, post["title"]),
                reply_markup=keyboard,
            )
        else:
            await callback.message.edit_caption(caption=post["title"], reply_markup=keyboard)
        return

    if key.startswith("postview_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        img_idx = int(parts[3])
        post = posts[section][post_idx]
        images = post.get("images", [])
        if not images or img_idx >= len(images):
            return
        entry = normalize(images[img_idx])
        keyboard = build_post_keyboard(section, post_idx, img_idx)
        await callback.message.edit_media(
            media=make_input_media(entry, post["title"]),
            reply_markup=keyboard,
        )
        return

    if key.startswith("submenu_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        post = posts[section][post_idx]
        keyboard = build_submenu_keyboard(section, post_idx)
        if has_media(callback.message):
            await callback.message.edit_caption(caption=post["title"], reply_markup=keyboard)
        else:
            await callback.message.edit_text(text=post["title"], reply_markup=keyboard)
        return

    if key.startswith("subpost_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        child_idx = int(parts[3])
        child = posts[section][post_idx]["children"][child_idx]

        if child.get("children"):
            keyboard = build_subsubmenu_keyboard(section, post_idx, child_idx)
            if has_media(callback.message):
                await callback.message.edit_caption(caption=child["title"], reply_markup=keyboard)
            else:
                await callback.message.edit_text(text=child["title"], reply_markup=keyboard)
            return

        if child.get("channel") and child.get("ids"):
            full_id = int(f"-100{child['channel']}")
            ids = child["ids"]
            try:
                if len(ids) == 1:
                    await bot.copy_message(chat_id=callback.message.chat.id, from_chat_id=full_id, message_id=ids[0])
                else:
                    await bot.copy_messages(chat_id=callback.message.chat.id, from_chat_id=full_id, message_ids=ids)
            except Exception as e:
                print(f"subpost copy error: {e}")
                await callback.message.answer("контент временно недоступен")
            return

        images = child.get("images", [])
        if not images:
            await callback.answer("картинок пока нет", show_alert=True)
            return
        entry = normalize(images[0])
        keyboard = build_subpost_keyboard(section, post_idx, child_idx, 0)
        if has_media(callback.message):
            await callback.message.edit_media(media=make_input_media(entry, child["title"]), reply_markup=keyboard)
        else:
            await callback.message.edit_caption(caption=child["title"], reply_markup=keyboard)
        return

    if key.startswith("subpostview_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        child_idx = int(parts[3])
        img_idx = int(parts[4])
        child = posts[section][post_idx]["children"][child_idx]
        images = child.get("images", [])
        if not images or img_idx >= len(images):
            return
        entry = normalize(images[img_idx])
        keyboard = build_subpost_keyboard(section, post_idx, child_idx, img_idx)
        await callback.message.edit_media(media=make_input_media(entry, child["title"]), reply_markup=keyboard)
        return

    if key.startswith("subsubmenu_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        child_idx = int(parts[3])
        child = posts[section][post_idx]["children"][child_idx]
        keyboard = build_subsubmenu_keyboard(section, post_idx, child_idx)
        if has_media(callback.message):
            await callback.message.edit_caption(caption=child["title"], reply_markup=keyboard)
        else:
            await callback.message.edit_text(text=child["title"], reply_markup=keyboard)
        return

    if key.startswith("subsubpost_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        child_idx = int(parts[3])
        grandchild_idx = int(parts[4])
        gc = posts[section][post_idx]["children"][child_idx]["children"][grandchild_idx]
        images = gc.get("images", [])
        if not images:
            await callback.answer("картинок пока нет", show_alert=True)
            return
        entry = normalize(images[0])
        keyboard = build_subsubpost_keyboard(section, post_idx, child_idx, grandchild_idx, 0)
        if has_media(callback.message):
            await callback.message.edit_media(media=make_input_media(entry, gc["title"]), reply_markup=keyboard)
        else:
            await callback.message.edit_caption(caption=gc["title"], reply_markup=keyboard)
        return

    if key.startswith("subsubpostview_"):
        parts = key.split("_")
        section = parts[1]
        post_idx = int(parts[2])
        child_idx = int(parts[3])
        grandchild_idx = int(parts[4])
        img_idx = int(parts[5])
        gc = posts[section][post_idx]["children"][child_idx]["children"][grandchild_idx]
        images = gc.get("images", [])
        if not images or img_idx >= len(images):
            return
        entry = normalize(images[img_idx])
        keyboard = build_subsubpost_keyboard(section, post_idx, child_idx, grandchild_idx, img_idx)
        await callback.message.edit_media(media=make_input_media(entry, gc["title"]), reply_markup=keyboard)
        return


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
