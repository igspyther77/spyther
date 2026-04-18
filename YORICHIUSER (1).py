import asyncio
import random
import json
import os
import time
import requests
import qrcode
from typing import Dict, Set, Optional

from telethon import TelegramClient, events, functions, types
from telethon.errors import FloodWaitError
from gtts import gTTS

# ────────────────────────────────────────────────
#                   CONFIG
# ────────────────────────────────────────────────
API_ID = 30761458
API_HASH = "b38c2a0564c880bba8efd971bcb7ffa4"
OWNER_ID = 8423621279
SESSION = "yorichi_userbot"

bot = TelegramClient(SESSION, API_ID, API_HASH)

# ────────────────────────────────────────────────
#                   STORAGE
# ────────────────────────────────────────────────
ADMINS_FILE = "admins.json"
NOTES_FILE = "notes.json"
BANNER_FILE = "banner_msg_id.txt"

admins: Set[int] = set()
notes: Dict[int, str] = {}
menu_banner_msg: Optional[int] = None
auto_react_emoji: Optional[str] = None
group_locked = False

muted_users: Set[int] = set()
global_muted: Set[int] = set()
reply_users: Set[int] = set()
rr_users: Set[int] = set()
flag_users: Set[int] = set()
hrr_users: Set[int] = set()
replygod_users: Set[int] = set()
replyyorichi_users: Dict[int, Dict] = {}
spray_tasks: Dict[int, asyncio.Task] = {}
RR_ACTIVE: Dict[int, int] = {}

# FastGC
gc_fast_active = False
gc_fast_template = None
gc_fast_task = None
GC_FAST_INTERVAL = 1
GC_FAST_EMOJIS = ["🔥","⚡","💥","✨","⚽","🚀","😎","❤️","👑","🎯","💣","⭐"]

# ────────────────────────────────────────────────
#                   HELPERS
# ────────────────────────────────────────────────
def load_admins():
    global admins
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE) as f:
            admins = set(json.load(f))

def save_admins():
    with open(ADMINS_FILE, "w") as f:
        json.dump(list(admins), f)

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID or uid in admins

async def safe_edit(event, text: str):
    try:
        await event.edit(text)
    except:
        try:
            await event.reply(text)
            await event.delete()
        except:
            pass

def load_notes():
    global notes
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            notes = {int(k): v for k, v in json.load(f).items()}

def save_notes():
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

def load_banner():
    global menu_banner_msg
    if os.path.exists(BANNER_FILE):
        with open(BANNER_FILE) as f:
            content = f.read().strip()
            menu_banner_msg = int(content) if content.isdigit() else None

def save_banner():
    with open(BANNER_FILE, "w") as f:
        f.write(str(menu_banner_msg) if menu_banner_msg else "")

load_admins()
load_notes()
load_banner()

# ────────────────────────────────────────────────
#                   TEXT LISTS
# ────────────────────────────────────────────────
reply_list = 
reply_texts = ["⋆｡ﾟ☁︎｡𝐂ʏᴜ 𝐑ᴇ मदरचोद 𝐘ᴏʀɪᴄʜɪ बाप के सामने 𝐅ʏᴛᴇʀ 𝐁ᴀɴᴇɢᴀ ⋆𓂃 ོ☼𓂃 😂🔥",
"नहीं नहीं तेरी मां को 𝐒ɪʀғ 𝐘ᴏʀɪᴄʜɪ बाप चोद सकता है ִֶָ𓂃 ࣪ ִֶָ👑་༘࿐ sᴀᴍᴊʜᴀ ʀᴀɴᴅɪᴋᴇ ???",
"तेरी मां का 𝐒ᴛʏʟɪsʜ भोसड़ा 😱",
"𝑻𝒆𝒓𝒚 𝒎𝒂𝒂 𝒓𝒂𝒏𝒅𝒂𝒍 𝒉 𝒃𝒂𝒔 𝒃𝒂𝒂𝒕 𝒌𝒉𝒂𝒕𝒂𝒎 😡🔥",
"सोच तेरी बहन को 𝐘ᴏʀɪᴄʜɪ बाप का गुलाम चोद रहा 😎🔥",
"Hello hello?? Oxygen aarahi है? रण्डी पुत्र 🧘🏻",
"Shut up रंडीके वरना दुनिया यही बोलेगी तेरी बहन 𝐘ᴏʀɪᴄʜɪ /~ 👑 बाप से सही chudi 🥵🔥",
"ᴛᴜ ᴏʀ ᴛᴇʀɪ ᴍᴀᴀ ᴅᴏɴᴏ 𝐘ᴏʀɪᴄʜɪ बाप के ʟɴᴅ sᴇ ᴋᴀʙʜɪ ᴜᴛʜ ɴʜɪ ᴘᴀʏᴇ 😂🔥",
"🇮🇳𝐵𝐻𝐴𝑅𝐴𝑇 𝐻𝐴𝑀𝐴𝑅𝐴 𝐷𝐸𝑆𝐻 𝐻 𝐴𝑈𝑅 𝑈𝑆 𝐷𝐸𝑆𝐻 𝑀𝐸 तेरी मां घर घर जाके MOAN करती है ! 🛐"]
fun_texts = ["तेरे मां के दूदू के बीच मेरा lund fas gaya oops 🤪（ ͜.🍆 ͜.）",

"𝐓ᴇʀʏ 𝐁ʜᴇ𝐍 𝐊ᴇ ( ͜. ㅅ ͜. )🥛 ʏᴜᴍᴍʏ ",

"𓂃☁︎ 𓂃𝐒ɪᴅᴇ 𝐇ᴀᴛ 𝐆ᴜʟᴀᴍ 𝐓ᴇʀʏ 𝐌ᴀᴀ 𝐊ᴏ 𝐂ʜᴏᴅɴᴇ  मेरी रेलगाड़ी आ रही .-‘🚂-‘.ᯓᡣ𐭩______ 𓂃☁︎ 𓂃",

"˙✧˖°📷༘ ⋆｡° 𝐓ᴇʀʏ 𝐌ᴀ  𝐊ᴀ 𝐂ʜɪʟᴅ 𝐏ᴏʀɴ 𝐑ᴇᴄᴏʀᴅ 𝐇ᴏɢʏᴀ 𝐀ʙ 𝐓ᴏ 𝐒ɪᴅʜᴀ 𝐕ɪʀᴀʟ 𝐇ᴏɢᴀ 𝐘ᴇ ˙✧˖°📷༘ ⋆｡°",

"𓂃✍︎ 𝑵ʏ 𝑵ʏ 𝑨ʙ 𝑲ᴜᴄʜ 𝑵ʏ 𝑯ᴏ 𝑺ᴋᴛᴀ 𝑻ᴇʀɪ  𝑪ᴜᴅᴀɪ 𝑲ɪ 𝑺ᴄʀɪᴘᴛ 𝑨ʙ 𝑳ᴇᴀᴋ 𝑯ᴏᴋᴇ 𝑯ʏ 𝑴ᴀɴᴇɢɪ 𓂃✍︎",

"⋆⭒˚.⋆🔭 𝐒ʜᴜᴛ 𝐔ᴘ 𝐑ᴀɴᴅɪᴋᴇ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ɪ 𝐂ʜᴜᴅᴀɪ 𝐄ɴᴊᴏʏ 𝐊ʀ 𝐑ᴀʜᴀ 𝐓ᴇʟᴇ𝐒ᴄᴏᴘᴇ 𝐒ᴇ⋆⭒˚.⋆🔭",
", "😈🔥 ]
flag_texts = [" ོ༘₊⁺🇮🇳 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ  𝐈ɴᴅɪᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇳 ₊⁺⋆.˚",
" ོ༘₊⁺🇯🇵 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐉ᴀᴘᴀɴ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇯🇵 ₊⁺⋆. " ,
" ₊⁺🇺🇸 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐒𝐀 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇺🇸 ₊⁺⋆.˚",
" ོ༘₊⁺🇬🇧 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐔𝐊 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇬🇧 ₊⁺⋆.˚", 
" ོ༘₊⁺🇰🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐊ᴏʀᴇᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇰🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇩🇪 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐆ᴇʀᴍᴀɴʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇩🇪 ₊⁺⋆.˚",
" ོ༘₊⁺🇫🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐅ʀᴀɴᴄᴇ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇫🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇮🇹 ₊⁺⋆.˚ 𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐈ᴛᴀʟʏ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇮🇹 ₊⁺⋆.˚",
" ོ༘₊⁺🇧🇷 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ   𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐁ʀᴀᴢɪʟ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇧🇷 ₊⁺⋆.˚",
" ོ༘₊⁺🇨🇦 ₊⁺⋆.˚𝐓ᴇʀɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐒ᴀᴛʜ  𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ᴜʀ 𝐂ᴀɴᴀᴅᴀ 𝐖ᴀʟᴇ 𝐁ʜɪ 𝐂ʜɪʟʟ 𝐊ᴀʀ 𝐑ʜᴇ ོ༘₊⁺🇨🇦 ₊⁺⋆.˚"]
heart_replies = ["𓂃˖˳·˖ ִֶָ ⋆❤️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🧡͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🧡 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💛͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💛 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💚͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💚 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💙͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💙 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💜͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💜 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🖤͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🖤 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤍͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤍 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆🤎͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚🤎 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💖͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💖 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💗͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💗 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💓͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💓 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💞͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💞 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💕͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💕 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💘͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💘 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💝͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💝 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆💟͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚💟 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❣️͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❣️ ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🔥͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🔥 ݁˖⭑.ᐟ",
"𓂃˖˳·˖ ִֶָ ⋆❤️‍🩹͙⋆ ִֶָ˖·˳˖𓂃 ִֶָ⁀➴༯ sꪶꪖꪜꫀ ִֶָ. ..𓂃 ࣪ ִֶָ🌈་༘࿐ 𝗟𝗡𝗗 𝗖𝗛𝗢𝗢𝗦 -/- ⋆˚❤️‍🩹 ݁˖⭑.ᐟ"]

# ────────────────────────────────────────────────
#                   DECORATOR
# ────────────────────────────────────────────────
commands = []

def register_cmd(name: str, needs_reply: bool = False, group_only: bool = False):
    def decorator(func):
        commands.append((name.lower(), func, needs_reply, group_only))
        return func
    return decorator

# FastGC Helpers
async def fast_title_edit(chat_id, title):
    try:
        await bot(functions.channels.EditTitleRequest(channel=chat_id, title=title))
    except:
        try:
            await bot(functions.messages.EditChatTitleRequest(chat_id=chat_id, title=title))
        except:
            pass

async def gc_fast_loop(chat_id):
    global gc_fast_active, gc_fast_template
    try:
        while gc_fast_active and gc_fast_template:
            emoji = random.choice(GC_FAST_EMOJIS)
            new_title = gc_fast_template.replace("{emoji}", emoji)
            await fast_title_edit(chat_id, new_title)
            await asyncio.sleep(GC_FAST_INTERVAL)
    except asyncio.CancelledError:
        pass
        
# ────────────────────────────────────────────────
#                   MENU (STYLISH)
# ────────────────────────────────────────────────
@register_cmd("menu")
async def cmd_menu(event, _):
    menu = """🔥━━━〔 𝐘𝐎𝐑𝐈𝐂𝐇𝐈 𝐆𝐎𝐃 𝐔𝐒𝐄𝐑𝐁𝐎𝐓 〕━━━🔥
👑 𝐎𝐖𝐍𝐄𝐑 : 𝐘𝐎𝐑𝐈𝐂𝐇𝐈 👑

.admin / .admins          → Show admins
.addadmin (reply)         → Add admin
.deladmin (reply)         → Remove admin

.mute (reply)             → Local mute
.unmute (reply)           → Local unmute
.gmute (reply)            → Global mute
.gunmute (reply)          → Global unmute

.reply (reply)            → Abuse reply
.sreply                   → Stop reply
.rr (reply)               → RR + 🤣 react
.srr                      → Stop RR
.flag (reply)             → Flag raid
.sflag                    → Stop flag
.hrr (reply)              → Heart raid
.shrr                     → Stop heart
.replygod (reply)         → God reply
.sgod                     → Stop god
.replyyorichi <text> <count> (reply) → Limited raid
.syorichi (reply)         → Stop yorichi

.spray <text>             → Spray spam
.dspray                   → Stop spray

.lock                     → Lock group
.unlock                   → Unlock group
.purge <count>            → Delete last messages
.throw (reply)            → Kick user

.ar <emoji>               → Auto react your msgs
.sar                      → Stop auto react

.fastgc set <template {emoji}> → Fast title changer
.fastgc stop              → Stop fastgc

.tts <text>               → Hindi voice
.qrcode <text>            → QR code
.fancy <text>             → Fancy styles
.style <text>             → Bold/italic
.emoji <text>             → Random emojis
.calc <expr>              → Calculator
.weather <city>           → Weather
.ip <ip>                  → IP lookup
.short <url>              → Short link

.notesadd <text>          → Save note
.noteslist                → List notes
.notesdelete <id>         → Delete note

.ping  .status  .flip  .dice  .info (reply)

.banner (reply media)     → Set menu banner
.rembanner                → Remove banner

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
𝐏𝐎𝐖𝐄𝐑𝐄𝐃 𝐁𝐘 𝐘𝐎𝐑𝐈𝐂𝐇𝐈 𝐆𝐎𝐃 🔥"""

    if menu_banner_msg:
        try:
            await bot.send_file(event.chat_id, file=menu_banner_msg, caption=menu)
            await event.delete()
        except:
            await safe_edit(event, menu)
    else:
        await safe_edit(event, menu)

# Banner
@register_cmd("banner", needs_reply=True)
async def cmd_banner(event, _):
    global menu_banner_msg
    r = await event.get_reply_message()
    if not r or not r.media:
        await safe_edit(event, "𝐑ᴇᴘʟʏ 𝐭𝐨 𝐩𝐡𝐨𝐭𝐨/𝐯𝐢𝐝𝐞𝐨")
        return
    saved = await bot.forward_messages("me", r)
    menu_banner_msg = saved.id
    save_banner()
    await safe_edit(event, "✅ 𝐁𝐚𝐧𝐧𝐞𝐫 𝐒𝐞𝐭  ")

@register_cmd("rembanner")
async def cmd_rembanner(event, _):
    global menu_banner_msg
    if menu_banner_msg is None:
        await safe_edit(event, "𝐍ᴏ 𝐛𝐚𝐧𝐧𝐞𝐫")
        return
    await bot.delete_messages("me", menu_banner_msg)
    menu_banner_msg = None
    save_banner()
    await safe_edit(event, "✅ 𝐁𝐚𝐧𝐧𝐞𝐫 𝐑𝐞𝐦𝐨𝐯𝐞𝐝   ")

# Admin Commands
@register_cmd("addadmin", needs_reply=True)
async def cmd_addadmin(event, _):
    uid = (await event.get_reply_message()).sender_id
    admins.add(uid)
    save_admins()
    await safe_edit(event, f"✅ 𝐄ᴋ 𝐀ᴜʀ 𝐘ᴏʀɪᴄʜɪ 𝐊ᴀ 𝐁ᴇᴛᴀ 𝐀ɢʏᴀ {uid}")

@register_cmd("deladmin", needs_reply=True)
async def cmd_deladmin(event, _):
    uid = (await event.get_reply_message()).sender_id
    admins.discard(uid)
    save_admins()
    await safe_edit(event, f"{uid} 𝐁ʜᴇᴇᴋʜ 𝐌ᴀɴɢ 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐒ᴇ 𝐀ʙ 😂")

@register_cmd("admins")
async def cmd_admins(event, _):
    txt = f"👑 𝐘ᴏʀɪᴄʜɪ 𝐀ᴅᴍɪɴ𝐬\n━━━━━━━━━━━━━━━\n𝐎ᴡɴᴇʀ: `{OWNER_ID}`\n\n"
    txt += "\n".join(f"• `{a}`" for a in sorted(admins)) if admins else "No extra admins"
    await safe_edit(event, txt)

# Basic
@register_cmd("ping")
async def cmd_ping(event, _):
    start = time.time()
    await safe_edit(event, "𝐏ɪɴɢɪɴɢ...")
    ms = round((time.time() - start) * 1000)
    await event.edit(f"🏓 𝐏ᴏɴɢ! {ms}ᴍs    𝐘ᴏʀɪᴄʜɪ")

@register_cmd("status")
async def cmd_status(event, _):
    await safe_edit(event, "✅ 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀ𝐏  𝐔sᴇʀʙᴏᴛ 𝐀ᴄᴛɪᴠᴇ 🔥")

@register_cmd("flip")
async def cmd_flip(event, _):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await safe_edit(event, f"🪙 Coin Flip: {result}  ")

@register_cmd("dice")
async def cmd_dice(event, _):
    num = random.randint(1, 6)
    await safe_edit(event, f"🎲 Dice: {num}    ")
    
# Raid Commands
@register_cmd("reply", needs_reply=True)
async def cmd_reply(event, _):
    uid = (await event.get_reply_message()).sender_id
    reply_users.add(uid)
    await safe_edit(event, "🔥 𝐑ᴇᴘʟʏ 𝐑ᴀɪᴅ 𝐄ɴᴀʙʟᴇᴅ  𝐀ʙ 𝐇ᴏɢɪ 𝐂ʜᴜᴅᴀɪ 😂")

@register_cmd("sreply")
async def cmd_sreply(event, _):
    reply_users.clear()
    await safe_edit(event, "𝐑ᴀɪᴅ 𝐒ᴛᴏᴘᴘᴇᴅ 🔴 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀ𝐏 𝐊ᴏ 𝐓ᴀʀᴀs 𝐀ɢʏᴀ")

@register_cmd("rr", needs_reply=True)
async def cmd_rr(event, _):
    uid = (await event.get_reply_message()).sender_id
    rr_users.add(uid)
    RR_ACTIVE[event.chat_id] = uid
    await safe_edit(event, "⚡ 𝐑𝐑 𝐑ᴀɪᴅ 𝐄ɴᴀʙʟᴇᴅ + 🤣  ")

@register_cmd("srr")
async def cmd_srr(event, _):
    rr_users.clear()
    RR_ACTIVE.pop(event.chat_id, None)
    await safe_edit(event, "🛑 𝐑𝐑 𝐒ᴛᴏᴘᴘᴇᴅ   ")

@register_cmd("flag", needs_reply=True)
async def cmd_flag(event, _):
    uid = (await event.get_reply_message()).sender_id
    flag_users.add(uid)
    await safe_edit(event, "𝐖ᴏʀʟᴅᴡɪᴅᴇ 𝐂ʜᴜᴅᴀɪ 𝐁ʏ 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀ𝐏 ")

@register_cmd("sflag")
async def cmd_sflag(event, _):
    flag_users.clear()
    await safe_edit(event, "🛑 𝐖ᴏʀʟᴅᴡɪᴅᴇ 𝐂ʜᴜᴅᴀɪ 𝐑ᴏᴋ 𝐃ɪ ")

@register_cmd("hrr", needs_reply=True)
async def cmd_hrr(event, _):
    uid = (await event.get_reply_message()).sender_id
    hrr_users.add(uid)
    await safe_edit(event, "💜 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐀ʙ 𝐃ɪʟ 𝐒ᴇ 𝐏ᴇʟᴇɴɢᴇ ")

@register_cmd("shrr")
async def cmd_shrr(event, _):
    hrr_users.clear()
    await safe_edit(event, "⛔ 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐊ᴀ 𝐈ɴᴛᴇʀᴇsᴛ 𝐊ʜᴀᴛᴀᴍ 𝐇ᴏɢʏᴀ ")

@register_cmd("replygod", needs_reply=True)
async def cmd_replygod(event, _):
    uid = (await event.get_reply_message()).sender_id
    replygod_users.add(uid)
    await safe_edit(event, "💥 𝐑ᴇᴘʟ𝐲𝐆ᴏᴅ 𝐄ɴᴀʙʟᴇᴅ  ")

@register_cmd("sgod")
async def cmd_sgod(event, _):
    replygod_users.clear()
    await safe_edit(event, "🛑 𝐑ᴇᴘʟ𝐲𝐆ᴏᴅ 𝐒ᴛᴏᴘᴘᴇᴅ    ")

@register_cmd("replyyorichi", needs_reply=True)
async def cmd_replyyorichi(event, arg):
    if not arg or len(arg.split()) < 2:
        await safe_edit(event, "𝐔sᴀɢᴇ: .replyyorichi <text> <count>")
        return
    text, count = arg.rsplit(" ", 1)
    uid = (await event.get_reply_message()).sender_id
    replyyorichi_users[uid] = {"text": text, "count": int(count)}
    await safe_edit(event, f"☄️ 𝐑ᴇᴘʟʏ𝐘ᴏʀɪᴄʜɪ ({count} times)   ")

@register_cmd("syorichi", needs_reply=True)
async def cmd_syorichi(event, _):
    uid = (await event.get_reply_message()).sender_id
    replyyorichi_users.pop(uid, None)
    await safe_edit(event, "🛑 𝐑ᴇᴘʟʏ𝐘ᴏʀɪᴄʜɪ 𝐒ᴛᴏᴘᴘᴇᴅ  ")

@register_cmd("spray")
async def cmd_spray(event, arg):
    if not arg:
        await safe_edit(event, "𝐔sᴀɢᴇ: .spray <text>")
        return
    chat = event.chat_id
    if chat in spray_tasks:
        await safe_edit(event, "⚠️ Already spraying")
        return
    async def loop():
        while chat in spray_tasks:
            await bot.send_message(chat, arg)
            await asyncio.sleep(5)
    task = asyncio.create_task(loop())
    spray_tasks[chat] = task
    await safe_edit(event, "💣 𝐒ᴘʀᴀʏ 𝐒ᴛᴀʀᴛᴇᴅ  ")

@register_cmd("dspray")
async def cmd_dspray(event, _):
    chat = event.chat_id
    if chat in spray_tasks:
        spray_tasks[chat].cancel()
        del spray_tasks[chat]
        await safe_edit(event, "🛑 𝐒ᴘʀᴀʏ 𝐒ᴛᴏᴘᴘᴇᴅ  ")

# Mute
@register_cmd("mute", needs_reply=True)
async def cmd_mute(event, _):
    uid = (await event.get_reply_message()).sender_id
    muted_users.add(uid)
    await safe_edit(event, "🔇 𝐂ʜᴜᴘ 𝐑ɴᴅʏᴋ 𝐁ʜᴏᴛ 𝐋ᴀᴍᴇ 𝐄ʏ 𝐓ᴜ ")

@register_cmd("unmute", needs_reply=True)
async def cmd_unmute(event, _):
    muted_users.discard((await event.get_reply_message()).sender_id)
    await safe_edit(event, "🗣️𝐄ɴᴊᴏʏ 𝐘ᴏᴜʀ 𝐂ʜᴀᴛs ")

@register_cmd("gmute", needs_reply=True)
async def cmd_gmute(event, _):
    global_muted.add((await event.get_reply_message()).sender_id)
    await safe_edit(event, "🔕 𝐖ᴏʀʟᴅ𝐖ɪᴅᴇ 𝐂ʜᴜᴅᴀɪ 𝐊ʜᴀ 𝐑ɴᴅʏ𝐊")

@register_cmd("gunmute", needs_reply=True)
async def cmd_gunmute(event, _):
    global_muted.discard((await event.get_reply_message()).sender_id)
    await safe_edit(event, "🔊 𝐘ᴏʀɪᴄʜɪ 𝐁ᴀᴀᴘ 𝐍ᴇ 𝐀ᴢᴀᴅɪ 𝐃ᴇᴅɪ ")

# Purge + Throw
@register_cmd("purge", group_only=True)
async def cmd_purge(event, arg):
    try:
        count = min(int(arg or 50), 100)
    except:
        count = 50
    msgs = [m.id async for m in bot.iter_messages(event.chat_id, limit=count+1)]
    if msgs:
        await bot.delete_messages(event.chat_id, msgs)
        await safe_edit(event, f"🧹 𝐏ᴜʀɢᴇᴅ {len(msgs)-1} ᴍsɢs  ")

@register_cmd("throw", needs_reply=True, group_only=True)
async def cmd_throw(event, _):
    user = (await event.get_reply_message()).sender_id
    perms = await bot.get_permissions(event.chat_id, 'me')
    if not perms.is_admin:
        await safe_edit(event, "❌ No admin rights")
        return
    await bot.kick_participant(event.chat_id, user)
    await safe_edit(event, "👞 𝐋ᴇ 𝐌ᴀᴅᴇʀᴄʜᴏᴅ 𝐆ᴀɴᴅ 𝐏ᴇ 𝐋ᴀᴛ 𝐊ʜᴀ ")

# Auto Handler
@bot.on(events.NewMessage)
async def auto_handler(event):
    if event.out: return
    sender = event.sender_id

    if sender in global_muted or sender in muted_users:
        try: await event.delete()
        except: pass
        return
    if group_locked and not is_admin(sender):
        try: await event.delete()
        except: pass
        return

    try:
        if sender in reply_users: await event.reply(random.choice(reply_list))
        elif sender in replygod_users: await event.reply(random.choice(reply_texts))
        elif sender in rr_users: await event.reply(random.choice(fun_texts))
        elif sender in flag_users: await event.reply(random.choice(flag_texts))
        elif sender in hrr_users: await event.reply(random.choice(heart_replies))
        elif sender in replyyorichi_users:
            data = replyyorichi_users[sender]
            if data["count"] > 0:
                await event.reply(data["text"])
                data["count"] -= 1
            else:
                replyyorichi_users.pop(sender, None)
    except: pass

    # RR Reaction
    try:
        if event.chat_id in RR_ACTIVE and event.sender_id == RR_ACTIVE[event.chat_id]:
            bot_msg = await event.reply(random.choice(fun_texts))
            await bot(functions.messages.SendReactionRequest(
                peer=event.chat_id, msg_id=bot_msg.id,
                reaction=[types.ReactionEmoji(emoticon="🤣")]
            ))
    except: pass

@bot.on(events.NewMessage(outgoing=True))
async def auto_react(event):
    if auto_react_emoji:
        try:
            await bot(functions.messages.SendReactionRequest(
                peer=event.chat_id, msg_id=event.id,
                reaction=[types.ReactionEmoji(emoticon=auto_react_emoji)]
            ))
        except: pass
        
# Lock / Unlock
@register_cmd("lock", group_only=True)
async def cmd_lock(event, _):
    global group_locked
    group_locked = True
    await safe_edit(event, "🔒 𝐇ɪᴊᴅᴏ 𝐊ᴀ 𝐁ᴏʟɴᴀ 𝐌ᴀɴᴀ 𝐄ʏ")

@register_cmd("unlock", group_only=True)
async def cmd_unlock(event, _):
    global group_locked
    group_locked = False
    await safe_edit(event, "🔓 𝐆ʀᴏᴜᴘ 𝐔ɴʟᴏᴄᴋᴇᴅ 𝐅ᴏʀ 𝐄ᴠᴇʀʏᴏɴᴇ ")

# AR / SAR
@register_cmd("ar")
async def cmd_ar(event, arg):
    global auto_react_emoji
    if not arg:
        await safe_edit(event, "𝐔sᴀɢᴇ: .ar <emoji>")
        return
    auto_react_emoji = arg
    await safe_edit(event, f"✅ 𝐀ᴜᴛᴏ 𝐑ᴇᴀᴄᴛ {arg}  ")

@register_cmd("sar")
async def cmd_sar(event, _):
    global auto_react_emoji
    auto_react_emoji = None
    await safe_edit(event, "🛑 𝐀ᴜᴛᴏ 𝐑ᴇᴀᴄᴛ 𝐒ᴛᴏᴘᴘᴇᴅ   ")

# FastGC
@register_cmd("fastgc")
async def cmd_fastgc(event, arg):
    global gc_fast_active, gc_fast_template, gc_fast_task
    if arg.startswith("set "):
        template = arg[4:].strip()
        if "{emoji}" not in template:
            await safe_edit(event, "❌ Use `{emoji}` in template")
            return
        gc_fast_template = template
        gc_fast_active = True
        if gc_fast_task: gc_fast_task.cancel()
        gc_fast_task = asyncio.create_task(gc_fast_loop(event.chat_id))
        await safe_edit(event, f"⚡ 𝐅ᴀsᴛ𝐆𝐂 𝐒ᴛᴀʀᴛᴇᴅ!\nTemplate: `{template}`")
    elif arg == "stop":
        gc_fast_active = False
        gc_fast_template = None
        if gc_fast_task: gc_fast_task.cancel()
        gc_fast_task = None
        await safe_edit(event, "🛑 𝐅ᴀsᴛ𝐆𝐂 𝐒ᴛᴏᴘᴘᴇᴅ   ")
    else:
        await safe_edit(event, "𝐔sᴀɢᴇ: .fastgc set <template {emoji}> or .fastgc stop")

# Notes
@register_cmd("notesadd")
async def notes_add(event, arg):
    if not arg: return
    nid = len(notes) + 1
    notes[nid] = arg
    save_notes()
    await safe_edit(event, f"📝 𝐍ᴏᴛᴇ {nid} 𝐒ᴀᴠᴇᴅ ")

@register_cmd("noteslist")
async def notes_list(event, _):
    if not notes:
        await safe_edit(event, "No notes")
        return
    msg = "**Your Notes:**\n"
    for i, t in notes.items():
        msg += f"{i}. {t}\n"
    await safe_edit(event, msg)

@register_cmd("notesdelete")
async def notes_delete(event, arg):
    try:
        nid = int(arg)
        if nid in notes:
            del notes[nid]
            save_notes()
            await safe_edit(event, "🗑️ 𝐃ᴇʟᴇᴛᴇᴅ!")
        else:
            await safe_edit(event, "Not found")
    except:
        await safe_edit(event, "𝐔sᴀɢᴇ: .notesdelete <id>")

# Utilities
@register_cmd("tts")
async def cmd_tts(event, arg):
    if not arg: return
    try:
        fname = f"tts_{int(time.time())}.mp3"
        gTTS(text=arg, lang="hi", slow=False).save(fname)
        await event.reply(file=fname)
        os.remove(fname)
    except Exception as e:
        await safe_edit(event, f"❌ TTS Error: {str(e)[:80]}")

@register_cmd("qrcode")
async def cmd_qrcode(event, arg):
    if not arg: return
    file = "qr.png"
    qrcode.make(arg).save(file)
    await event.reply("QR Code:", file=file)
    os.remove(file)

@register_cmd("fancy")
async def cmd_fancy(event, arg):
    if not arg: return
    styles = [arg.upper(), arg.lower(), f"★彡 {arg} 彡★", f"『 {arg} 』", f"✦ {arg} ✦"]
    msg = "**Fancy:**\n\n" + "\n".join(styles)
    await safe_edit(event, msg)

@register_cmd("style")
async def cmd_style(event, arg):
    if not arg: return
    await safe_edit(event, f"**Styled:**\n\n𝒇𝒂𝒏𝒄𝒚: {arg.replace('a','𝒶').replace('b','𝒷')}\n**Bold**: **{arg}**\n__Italic__: __{arg}__\n`Mono`: `{arg}`")

@register_cmd("emoji")
async def cmd_emoji(event, arg):
    if not arg: return
    emojis = "".join(random.choice(["🔥","❤️","✨","⚡","💥"]) for _ in range(5))
    await safe_edit(event, f"{arg} {emojis}")

@register_cmd("calc")
async def cmd_calc(event, arg):
    if not arg: return
    try:
        res = eval(arg, {"__builtins__": {}})
        await safe_edit(event, f"🧮 Result: `{res}`  ")
    except:
        await safe_edit(event, "❌ Invalid expression")

@register_cmd("weather")
async def cmd_weather(event, arg):
    if not arg: return
    # Put your OPENWEATHER key in code if you want
    await safe_edit(event, "Weather needs API key (add OPENWEATHER_API_KEY)")

@register_cmd("ip")
async def cmd_ip(event, arg):
    if not arg: return
    try:
        data = requests.get(f"http://ip-api.com/json/{arg}").json()
        await safe_edit(event, f"🌍 IP Info:\n```{json.dumps(data, indent=2)}```")
    except:
        await safe_edit(event, "❌ Error")

@register_cmd("short")
async def cmd_short(event, arg):
    if not arg: return
    try:
        r = requests.get(f'http://tinyurl.com/api-create.php?url={requests.utils.requote_uri(arg)}').text
        await safe_edit(event, f"🔗 Short: {r}    ")
    except:
        await safe_edit(event, "❌ Error")

@register_cmd("info", needs_reply=True)
async def cmd_info(event, _):
    reply = await event.get_reply_message()
    user = await bot.get_entity(reply.sender_id)
    full = await bot(functions.users.GetFullUserRequest(reply.sender_id))
    bio = full.full_user.about or "No bio"
    txt = f"""👤 𝐔𝐒𝐄𝐑 𝐈𝐍𝐅𝐎
🆔 `{user.id}`
📛 {user.first_name or ''} {user.last_name or ''}
🔗 @{user.username or 'None'}
📝 Bio: {bio}"""
    await safe_edit(event, txt)

# ────────────────────────────────────────────────
#                   START
# ────────────────────────────────────────────────
@bot.on(events.NewMessage(outgoing=True))
async def command_handler(event):
    text = event.raw_text.strip()
    if not text.startswith("."): return
    if not is_admin(event.sender_id):
        await safe_edit(event, "𝐘ᴏʀɪᴄʜɪ 𝐊ᴏ 𝐁ᴀᴀᴘ 𝐁ᴀɴᴀ 𝐑ᴀɴᴅɪ 𝐌ᴀᴀ 𝐊ᴇ 𝐋ᴀᴅᴋᴇ 🤩🖕🏻")
        return

    parts = text.split(maxsplit=1)
    cmd = parts[0][1:].lower()
    arg = parts[1] if len(parts) > 1 else ""

    for name, func, need_reply, grp_only in commands:
        if cmd == name:
            if grp_only and not event.is_group:
                await safe_edit(event, "𝐆ʀᴏᴜᴘ 𝐎ɴʟʏ")
                return
            if need_reply and not event.is_reply:
                await safe_edit(event, "𝐑ᴇᴘʟʏ 𝐏ᴇʜʟᴇ")
                return
            try:
                await func(event, arg)
            except FloodWaitError as e:
                await safe_edit(event, f"𝐅ʟᴏᴏᴅ 𝐖ᴀɪᴛ: {e.seconds}s")
            except Exception as e:
                await safe_edit(event, f"𝐄ʀʀᴏʀ: {str(e)[:100]}")
            return

async def main():
    await bot.start()
    me = await bot.get_me()
    print(f"🔥 YORICHI GOD USERBOT RUNNING 🔥\nLogged as: {me.first_name} (@{me.username})")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())