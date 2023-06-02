import html
import os
import json
import importlib
import time
import re
import sys
import traceback
import EmikoRobot.modules.sql.users_sql as sql
from sys import argv
from typing import Optional
from telegram import __version__ as peler
from platform import python_version as memek
from EmikoRobot import (
    ALLOW_EXCL,
    CERT_PATH,
    IMG_BOT,
    DONATION_LINK,
    OWNER_USERNAME as uname,
    BOT_USERNAME as bu,
    LOGGER,
    OWNER_ID,
    PORT,
    SUPPORT_CHAT,
    TOKEN,
    URL,
    WEBHOOK,
    SUPPORT_CHAT,
    dispatcher,
    StartTime,
    telethn,
    pbot,
    updater,
)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from EmikoRobot.modules import ALL_MODULES
from EmikoRobot.modules.helper_funcs.chat_status import is_user_admin
from EmikoRobot.modules.helper_funcs.misc import paginate_modules
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.error import (
    BadRequest,
    ChatMigrated,
    NetworkError,
    TelegramError,
    TimedOut,
    Unauthorized,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
)
from telegram.ext.dispatcher import DispatcherHandlerStop, run_async
from telegram.utils.helpers import escape_markdown


def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time


PM_START_TEXT = """
*👋🏻 ʜᴇʟʟᴏ {} *
❍ Hakncock Robot is a bot manager + music to manage your group well.
❍ Press /help or /mhelp for Help.
❍ Managed By @azure_id.
────────────────────
🧸 Users ⋙ `` Users
📮 Groups ⋙ `` Groups
────────────────────
"""

buttons = [
        [
        InlineKeyboardButton(
            text="➕️ Tambahkan Saya Ke Grup ➕️", url="https://t.me/Hancock_Robot_bot?startgroup=true"
        ),
    ],
    [
        InlineKeyboardButton(text="Bantuan ❓", callback_data="emiko_support"
        ),
        InlineKeyboardButton(
            text="Support 📣", url="t.me/nakama_asl"
        ),
    ],
    [
        InlineKeyboardButton(text="Donasi ☕️", callback_data="emiko_own"
       ),
        InlineKeyboardButton(text="Jasa Bot 🚀", callback_data="emiko_jasa"
       ),
    ],
]


HELP_STRINGS = """
Klik tombol di bawah ini untuk mendapatkan deskripsi tentang fitur manage Amang Robot."""


DONATE_STRING = """Heya, glad to hear you want to donate!
 You can support the project by contacting  \
 Supporting isnt always financial! \
 Those who cannot provide monetary support are welcome to help us develop the bot act ."""

IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

for module_name in ALL_MODULES:
    imported_module = importlib.import_module("EmikoRobot.modules." + module_name)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if imported_module.__mod_name__.lower() not in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True,
        reply_markup=keyboard,
    )


def test(update: Update, context: CallbackContext):
    # pprint(eval(str(update)))
    # update.effective_message.reply_text("Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN)
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


def start(update: Update, context: CallbackContext):
    args = context.args
    uptime = get_readable_time((time.time() - StartTime))
    if update.effective_chat.type == "private":
        if len(args) >= 1:
            if args[0].lower() == "help":
                send_help(update.effective_chat.id, HELP_STRINGS)
            elif args[0].lower().startswith("ghelp_"):
                mod = args[0].lower().split("_", 1)[1]
                if not HELPABLE.get(mod, False):
                    return
                send_help(
                    update.effective_chat.id,
                    HELPABLE[mod].__help__,
                    InlineKeyboardMarkup(
                        [[InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="help_back")]]
                    ),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(match.group(1), update.effective_user.id, False)
                else:
                    send_settings(match.group(1), update.effective_user.id, True)

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            first_name = update.effective_user.first_name
            update.effective_message.reply_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),                 
                    sql.num_users(),
                    sql.num_chats()),                        
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
            )
    else:
        update.effective_message.reply_text(
            f"👋 Hi, I'm {dispatcher.bot.first_name}. Nice to meet You.",
            parse_mode=ParseMode.HTML
       )


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    LOGGER.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    message = (
        "An exception was raised while handling an update\n"
        "<pre>update = {}</pre>\n\n"
        "<pre>{}</pre>"
    ).format(
        html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False)),
        html.escape(tb),
    )

    if len(message) >= 4096:
        message = message[:4096]
    # Finally, send the message
    context.bot.send_message(chat_id=OWNER_ID, text=message, parse_mode=ParseMode.HTML)


# for test purposes
def error_callback(update: Update, context: CallbackContext):
    error = context.error
    try:
        raise error
    except Unauthorized:
        print("no nono1")
        print(error)
        # remove update.message.chat_id from conversation list
    except BadRequest:
        print("no nono2")
        print("BadRequest caught")
        print(error)

        # handle malformed requests - read more below!
    except TimedOut:
        print("no nono3")
        # handle slow connection problems
    except NetworkError:
        print("no nono4")
        # handle other connection problems
    except ChatMigrated as err:
        print("no nono5")
        print(err)
        # the chat_id of a group has changed, use e.new_chat_id instead
    except TelegramError:
        print(error)
        # handle all other telegram related errors


def help_button(update, context):
    query = update.callback_query
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)

    print(query.message.chat.id)

    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "Here is the help for the *{}* module:\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="help_back")]]
                ),
            )

        elif prev_match:
            curr_page = int(prev_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(curr_page - 1, HELPABLE, "help")
                ),
            )

        elif next_match:
            next_page = int(next_match.group(1))
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(next_page + 1, HELPABLE, "help")
                ),
            )

        elif back_match:
            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, HELPABLE, "help")
                ),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
        # query.message.delete()

    except BadRequest:
        pass


def emiko_about_callback(update, context):
    query = update.callback_query
    if query.data == "emiko_":
        query.message.edit_text(
            text="🎧 Bantuan Perintah Music."
            "\npilih menu di bawah ini untuk melihat bantuan Hancock Robot",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="ᴘᴇʀɪɴᴛᴀʜ ᴀᴅᴍɪɴ", callback_data="emiko_admin"),
                    InlineKeyboardButton(text="ᴘᴇʀɪɴᴛᴀʜ ʙᴏᴛ", callback_data="emiko_notes"),
                 ],
                 [
                    InlineKeyboardButton(text="ᴘᴇʀɪɴᴛᴀʜ ᴘʟᴀʏ", callback_data="source_"),
                    InlineKeyboardButton(text="ᴘᴇʀɪɴᴛᴀʜ ᴇxsᴛʀᴀ", callback_data="emiko_credit"),
                 ],
                 [
                    InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_support"),
                 ]
                ]
            ),
        )
    elif query.data == "emiko_back":
        first_name = update.effective_user.first_name
        uptime = get_readable_time((time.time() - StartTime))
        query.message.edit_text(
                PM_START_TEXT.format(                
                    escape_markdown(first_name),
                    sql.num_users(),
                    sql.num_chats()),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )

    elif query.data == "emiko_admin":
        query.message.edit_text(
            text=f"*👮 PERINTAH ADMIN."
            "\n\nc singkatan dari pemutaran Channel."
            "\n • /pause or /cpause - Jeda musik yang diputar."
            "\n • /resume or /cresume- Lanjutkan musik yang dijeda."
            "\n • /mute or /cmute- Matikan musik yang diputar."
            "\n •/unmute or /cunmute- Suarakan musik yang dibisukan."
            "\n • /skip or /cskip- Lewati musik yang sedang diputar."
            "\n • /musicstop or /cstop- Hentikan pemutaran musik."
            "\n • /shuffle or /cshuffle- Secara acak mengacak daftar putar yang antri."
            "\n • /seek or /cseek - Teruskan Cari musik sesuai durasi Anda."
            "\n • /seekback or /cseekback - Mundur Carilah musik sesuai durasi Anda."
            "\n\n✅Lewati."
            "\n • /skip or /cskip contoh 3 ."
            "\n • Melewati musik ke nomor antrian yang ditentukan. Contoh: /skip 3 akan melewatkan musik ke musik antrian ketiga dan akan mengabaikan musik 1 dan 2 dalam antrian."
            "\n\n✅Loop."
            "\n • /loop or /cloop [enable/disable] atau [Angka antara 1-10] ."
            "\n • Saat diaktifkan, bot memutar musik yang sedang diputar menjadi 1-10 kali pada obrolan suara. Default ke 10 kali."
            "\n\n✅Pengguna Auth."
            "\nPengguna Auth dapat menggunakan perintah admin tanpa hak admin di Group Anda."
            "\n • /auth [Username] - Tambahkan pengguna ke AUTH LIST dari grup."
            "\n • /unauth [Username] - Hapus pengguna dari AUTH LIST grup."
            "\n • /authusers - Periksa DAFTAR AUTH grup",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_")]]
            ),
        )
    elif query.data == "emiko_jasa":
        query.message.edit_text(
            text="*𝙅𝘼𝙎𝘼 𝘿𝙀𝙋𝙇𝙊𝙔 𝘽𝙊𝙏 𝙏𝙀𝙇𝙀𝙂𝙍𝘼𝙈*"
            "\n\n*➻ 𝙐𝙎𝙀𝙍𝘽𝙊𝙏 𝙂𝘾𝘼𝙎𝙏*"
            "\n├ *Rp. 20.000 [Ubot Premium ]*"
            "\n├ *Rp. 25.000 [Tede Ultra-Premium ]*"
            "\n└ *Sistem Terima Jadi*"
            "\n\n*➻ 𝘽𝙊𝙏 𝙈𝙐𝙎𝙄𝙆*"
            "\n├ *Rp. 100.000 [ Vps/bulan ]*"
            "\n├ *[ Awalan Pasang ]*"
            "\n└ *Sistem Terima Jadi*"
            "\n\n*➻ 𝘽𝙊𝙏 𝙈𝙐𝙎𝙄𝙆 & 𝙈𝘼𝙉𝘼𝙂𝙀*"
            "\n├ *Rp. 10.000 [ Clone GH ]*"
            "\n├ *Rp. 150.000 [ Deploy + Heroku + Vps ]*"
            "\n└ *Sistem Terima Jadi*"
            "\n\n*➻ 𝘽𝙊𝙏 𝙈𝘼𝙉𝘼𝙂𝙀*"
            "\n├ *Rp. 50.000 [ Heroku ]*"
            "\n└ *Sistem Terima Jadi*"
            "\n\n*➻ 𝘽𝙊𝙏 𝙈𝘼𝙉𝘼𝙂𝙀*"

            "\n├ *Rp. 50.000 [ Heroku ]*"

            "\n└ *Sistem Terima Jadi*"
            "\n\n*➻ Catatan*"
            "\n\n*➻ 𝘼𝙋𝘼𝘽𝙄𝙇𝘼 𝘽𝙊𝙏 𝙔𝘼𝙉𝙂 𝘼𝙉𝘿𝘼 𝙄𝙉𝙂𝙄𝙉𝙆𝘼𝙉 𝙏𝙞𝙙𝙖𝙠 𝙖𝙙𝙖 𝙨𝙞𝙡𝙖𝙝𝙠𝙖𝙣 𝙗𝙚𝙧𝙩𝙖𝙣𝙮𝙖 𝙠𝙚* [ᴀᴍᴀɴɢ](tg://openmessage?user_id=2073506739)"
            "\n\n*➻ ʜᴇʀᴏᴋᴜ ʀᴀᴡᴀɴ sᴜsᴘᴇɴ ᴊᴀᴅɪ sᴀʏᴀ ᴅᴇᴘʟᴏʏ ᴅɪ ᴠᴘs.*"
            "\n\n*➻ sɪʟᴀʜᴋᴀɴ ʜᴜʙᴜɴɢɪ* [ᴀᴍᴀɴɢ](tg://openmessage?user_id=2073506739) *ᴜɴᴛᴜᴋ ᴍᴇʟɪʜᴀᴛ/ᴍᴇɴᴀɴʏᴀᴋᴀɴ ᴄᴏɴᴛᴏʜ ʙᴏᴛ*"
            "\n\n*𝗦𝗘𝗞𝗜𝗔𝗡 𝗧𝗘𝗥𝗜𝗠𝗔 𝗞𝗔𝗦𝗜𝗛 🙏.*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                  [
                    InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_back"),
                  ]
                ]
            ),
        )
    elif query.data == "emiko_notes":
        query.message.edit_text(
            text="🤖 PERINTAH BOT"
            "\n\n • /stats - Dapatkan 10 Trek Global Stats Teratas, 10 Pengguna Bot Teratas, 10 Obrolan Teratas di bot, 10 Teratas Dimainkan dalam obrolan, dll."
            "\n\n • /sudolist - Periksa Sudo Pengguna Nnda Music Bot,"
            "\n\n • /lyrics [Nama Musik] mencari Lirik untuk Musik tertentu di web."
            "\n\n • /song [Nama Trek] atau [Tautan YT] - Unduh trek apa pun dari youtube dalam format mp3 atau mp4."
            "\n\n • /player -  Dapatkan Panel Bermain interaktif."
            "\n\n • c singkatan dari pemutaran saluran."
            "\n\n • /queue or /cqueue- Periksa Daftar Antrian Musik",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_")]]
            ),
        )
    elif query.data == "emiko_support":
        query.message.edit_text(
            text="*Bantuan Perintah AmangRobot*)"
            "\npilih tombol dibawah untuk melihat bantuan perintah AmangRobot",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="🎧ᴍᴜsɪᴄ", callback_data="emiko_"),
                    InlineKeyboardButton(text="🤖ᴍᴀɴᴀɢᴇ", callback_data="help_back"),
                 ],
                 [
                    InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_back"),
                 
                 ]
                ]
            ),
        )


    elif query.data == "emiko_own":
        query.message.edit_text(
            text="*ᴊɪᴋᴀ ᴋᴀʟɪᴀɴ ᴍᴇɴʏᴜᴋᴀɪ ᴀᴍᴀɴɢ ʀᴏʙᴏᴛ ᴅᴀɴ ɪɴɢɪɴ ʙᴇʀᴅᴏɴᴀsɪ ᴜɴᴛᴜᴋ ᴍᴇᴍʙᴀɴᴛᴜ ᴀɢᴀʀ ᴀᴍᴀɴɢ ʀᴏʙᴏᴛ ᴛᴇᴛᴀᴘ ᴀᴋᴛɪғ ᴛᴇʀᴜs.*"
            f"\n\n➻ *ᴋᴀʟɪᴀɴ ʙɪsᴀ ʙᴇʀᴅᴏɴᴀsɪ ᴅᴇɴɢᴀɴ ᴠɪᴀ ᴅᴀɴᴀ/ϙʀɪs ᴀᴛᴀᴜ ᴋᴀʟɪᴀɴ ʙɪsᴀ ʜᴜʙᴜɴɢɪ ᴏᴡɴᴇʀ ᴅɪʙᴀᴡᴀʜ ɪɴɪ*"
            f"\n\n➻ *ᴅᴀɴ ᴜɴᴛᴜᴋ ʏᴀɴɢ sᴜᴅᴀʜ ʙᴇʀᴅᴏɴᴀsɪ sᴀʏᴀ ᴜᴄᴀᴘᴋᴀɴ ᴛᴇʀɪᴍᴀᴋᴀsɪʜ ʙᴀɴʏᴀᴋ* 🙏",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="👨‍💻 ᴀᴍᴀɴɢ•", url="tg://openmessage?user_id=2073506739"),
                    InlineKeyboardButton(text="💳 ϙʀɪs", url="https://te.legra.ph/file/20897710ec3f3594d354d.jpg"),
                 ],
                 [
                    InlineKeyboardButton(text="ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_back"),                 
                 ],
                ]
            ),
        )
    elif query.data == "emiko_credit":
        query.message.edit_text(
            text="⚒️ PERINTAH EKSTRA"
            "\n\n✅Perintah Ekstra."
            "\n\n • /mstart - Mulai Bot Musik."
            "\n\n • /mhelp - Dapatkan Menu Pembantu Perintah dengan penjelasan rinci tentang perintah."
            "\n\n • /mping- Ping Bot dan periksa statistik Ram, Cpu, dll dari Bot."
            "\n\n✅Pengaturan Music."
            "\n • /msettings - Dapatkan pengaturan grup lengkap dengan tombol sebaris."
            "\n\n🔗 Opsi di Pengaturan."
            "\n\n1️⃣ Kamu Bisa set ingin Kualitas Audio Anda streaming di obrolan suara."
            "\n\n2️⃣ You can set Kualitas Video Anda ingin streaming di obrolan suara."
            "\n\n3️⃣ Auth Users:- Anda dapat mengubah mode perintah admin dari sini ke semua orang atau hanya admin. Jika semua orang, siapa pun yang ada di grup Anda dapat menggunakan perintah admin (seperti /skip, /stop dll)."
            "\n\n4️⃣ Clean Mode: Saat diaktifkan, hapus pesan bot setelah 5 menit dari grup Anda untuk memastikan obrolan Anda tetap bersih dan baik."
            "\n\n5️⃣ Command Clean : Saat diaktifkan, Bot akan menghapus perintah yang dieksekusi (/play, /pause, /shuffle, /stop etc) langsung."
            "\n\n6️⃣ Play Settings."
            "\n\n • /playmode - Dapatkan panel pengaturan pemutaran lengkap dengan tombol tempat Anda dapat mengatur pengaturan pemutaran grup Anda."
            "\n\nOpsi dalam mode putar."
            "\n\n1️⃣ Mode Pencarian [Langsung atau Inline] - Mengubah mode pencarian Anda saat Anda memberikan mode /play."
            "\n\n2️⃣ Perintah Admin [Semua orang atau Admin] - Jika semua orang, siapa pun yang ada di grup Anda akan dapat menggunakan perintah admin (seperti /skip, /stop dll)."
            "\n\n3️⃣ Jenis Bermain [Everyone or Admins] - Jika admin, hanya admin yang ada di grup yang dapat memutar musik di obrolan suara",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_")
                 ]
                ]
            ),
        )

def Source_about_callback(update, context):
    query = update.callback_query
    if query.data == "source_":
        query.message.edit_text(
            text="🎵 PERINTAH PLAY."
            "\n\n✅Perintah Play."
            "\n\nPerintah yang tersedia = play , vplay , cplay."
            "\n\nPerintah ForcePlay = playforce , vplayforce , cplayforce."
            "\n\nc singkatan dari pemutaran Channel."
            "\nv singkatan dari pemutaran video."
            "\nforce singkatan dari force play."
            "\n\n • /play atau /vplay atau /cplay  - Bot akan mulai memainkan kueri yang Anda berikan di obrolan suara atau Streaming tautan langsung di obrolan suara."
            "\n\n • /playforce atau /vplayforce atau /cplayforce -  Force Play menghentikan trek yang sedang diputar pada obrolan suara dan mulai memutar trek yang dicari secara instan tanpa mengganggu/mengosongkan antrean."
            "\n\n • /channelplay [Nama pengguna atau id obrolan] atau [Disable] - Hubungkan saluran ke grup dan streaming musik di obrolan suara saluran dari grup Anda."
            "\n\n✅Daftar Putar Server Bot."
            "\n • /playlist  - Periksa Daftar Putar Tersimpan Anda Di Server."
            "\n • /deleteplaylist - Hapus semua musik yang disimpan di daftar putar Anda."
            "\n • /play  - Mulai mainkan Daftar Putar Tersimpan Anda dari Server",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                 [
                    InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_")
                 ]
                ]
            ),
        )
    elif query.data == "source_back":
        first_name = update.effective_user.first_name
        query.message.edit_text(
                PM_START_TEXT.format(
                    escape_markdown(first_name),
                    sql.num_users(),
                    sql.num_chats()),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
                disable_web_page_preview=False,
        )

def get_help(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:
        if len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
            module = args[1].lower()
            update.effective_message.reply_text(
                f"Hubungi saya di PM untuk mendapatkan bantuan {module.capitalize()}",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="👨‍💼 Bantuan",
                                url="t.me/{}?start=ghelp_{}".format(
                                    context.bot.username, module
                                ),
                            )
                        ]
                    ]
                ),
            )
            return
        update.effective_message.reply_text(
            "Hubungi saya di PM untuk mendapatkan daftar perintah.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="ʙᴀɴᴛᴜᴀɴ ᴘᴇʀɪɴᴛᴀʜ ↗️",
                            url="t.me/{}?start=help".format(context.bot.username),
                        )
                    ]
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = (
            "Here is the available help for the *{}* module:\n".format(
                HELPABLE[module].__mod_name__
            )
            + HELPABLE[module].__help__
        )
        send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [[InlineKeyboardButton(text="⭅ ᴋᴇᴍʙᴀʟɪ", callback_data="emiko_support")]]
            ),
        )

    else:
        send_help(chat.id, HELP_STRINGS)


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(mod.__mod_name__, mod.__user_settings__(user_id))
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "These are your current settings:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any user specific settings available :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="Which module would you like to check {}'s settings for?".format(
                    chat_name
                ),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Seems like there aren't any chat settings available :'(\nSend this "
                "in a group chat you're admin in to find its current settings!",
                parse_mode=ParseMode.MARKDOWN,
            )


def settings_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user = update.effective_user
    bot = context.bot
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = bot.get_chat(chat_id)
            text = "*{}* has the following settings for the *{}* module:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[module].__chat_settings__(chat_id, user.id)
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Go Back",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                "Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = bot.get_chat(chat_id)
            query.message.reply_text(
                text="Hi there! There are quite a few settings for {} - go ahead and pick what "
                "you're interested in.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        bot.answer_callback_query(query.id)
        query.message.delete()
    except BadRequest as excp:
        if excp.message not in [
            "Message is not modified",
            "Query_id_invalid",
            "Message can't be deleted",
        ]:
            LOGGER.exception("Exception in settings buttons. %s", str(query.data))


def get_settings(update: Update, context: CallbackContext):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Click here to get this chat's settings, as well as yours."
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Settings",
                                url="t.me/{}?start=stngs_{}".format(
                                    context.bot.username, chat.id
                                ),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Click here to check your settings."

    else:
        send_settings(chat.id, user.id, True)


def donate(update: Update, context: CallbackContext):
    user = update.effective_message.from_user
    chat = update.effective_chat  # type: Optional[Chat]
    bot = context.bot
    if chat.type == "private":
        update.effective_message.reply_text(
            DONATE_STRING, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True
        )

        if OWNER_ID != 1252482197:
            update.effective_message.reply_text(
                "I'm free for everyone ❤️ If you wanna make me smile, just join"
                "[My Channel]({})".format(DONATION_LINK),
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        try:
            bot.send_message(
                user.id,
                DONATE_STRING,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )

            update.effective_message.reply_text(
                "I've PM'ed you about donating to my creator!"
            )
        except Unauthorized:
            update.effective_message.reply_text(
                "Contact me in PM first to get donation information."
            )


def migrate_chats(update: Update, context: CallbackContext):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def main():

    if SUPPORT_CHAT is not None and isinstance(SUPPORT_CHAT, str):
        try:
            dispatcher.bot.sendMessage(
                f"@{SUPPORT_CHAT}", 
                "👋 Hi, i'm alive.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Unauthorized:
            LOGGER.warning(
                "Bot isnt able to send message to support_chat, go and check!"
            )
        except BadRequest as e:
            LOGGER.warning(e.message)

    test_handler = CommandHandler("test", test, run_async=True)
    start_handler = CommandHandler("start", start, run_async=True)

    help_handler = CommandHandler("help", get_help, run_async=True)
    help_callback_handler = CallbackQueryHandler(
        help_button, pattern=r"help_.*", run_async=True
    )

    settings_handler = CommandHandler("settings", get_settings, run_async=True)
    settings_callback_handler = CallbackQueryHandler(
        settings_button, pattern=r"stngs_", run_async=True
    )

    about_callback_handler = CallbackQueryHandler(
        emiko_about_callback, pattern=r"emiko_", run_async=True
    )

    source_callback_handler = CallbackQueryHandler(
        Source_about_callback, pattern=r"source_", run_async=True
    )

    donate_handler = CommandHandler("donate", donate, run_async=True)
    migrate_handler = MessageHandler(
        Filters.status_update.migrate, migrate_chats, run_async=True
    )

    dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(about_callback_handler)
    dispatcher.add_handler(source_callback_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(donate_handler)

    dispatcher.add_error_handler(error_callback)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(url=URL + TOKEN, certificate=open(CERT_PATH, "rb"))
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=4, drop_pending_updates=True)

    if len(argv) not in (1, 3, 4):
        telethn.disconnect()
    else:
        telethn.run_until_disconnected()

    updater.idle()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    telethn.start(bot_token=TOKEN)
    pbot.start()
    main()
