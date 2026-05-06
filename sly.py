import logging
import asyncio
import os
import io
import json
import random
import time
from typing import Set, Dict, List, Any, Optional
from telegram import Update
from telegram.error import RetryAfter, TimedOut, NetworkError, BadRequest, Forbidden
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from gtts import gTTS

from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ================= TELETHON USER CLIENT =================
try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.functions.channels import (
        CreateChannelRequest, InviteToChannelRequest,
        EditAdminRequest, ExportInviteRequest
    )
    from telethon.tl.functions.messages import (
        CreateChatRequest, ExportChatInviteRequest,
        AddChatUserRequest
    )
    from telethon.tl.functions.messages import EditChatAdminRequest as TeleEditChatAdminRequest
    from telethon.tl.types import (
        ChatAdminRights, InputPeerEmpty, ChannelAdminRights,
        Channel as TeleChannel, Chat as TeleChat
    )
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

TELE_API_ID   = int(os.environ.get("TELEGRAM_API_ID", "38948897"))
TELE_API_HASH = os.environ.get("TELEGRAM_API_HASH", "59337e57e49184ac6a75998060b226cd")
TELE_SESSION  = os.environ.get("TELEGRAM_SESSION", "")
_SESSION_FILE = ".telegram_session"

def _load_session_from_file() -> str:
    try:
        if os.path.exists(_SESSION_FILE):
            with open(_SESSION_FILE, "r") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""

if not TELE_SESSION:
    TELE_SESSION = _load_session_from_file()

_user_client: Any = None
_session_gen_state: Dict[int, Dict] = {}

async def get_user_client():
    global _user_client, TELE_SESSION
    if not TELETHON_AVAILABLE:
        return None
    if not TELE_API_ID or not TELE_API_HASH or not TELE_SESSION:
        return None
    if _user_client is None:
        _user_client = TelegramClient(
            StringSession(TELE_SESSION), TELE_API_ID, TELE_API_HASH
        )
    if not _user_client.is_connected():
        await _user_client.connect()
    return _user_client

# ================= HEALTH CHECK =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        return

def run_health_check_server():
    server = HTTPServer(('0.0.0.0', 5000), HealthCheckHandler)
    server.serve_forever()

# ================= LOGGING =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.CRITICAL
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("telegram").setLevel(logging.CRITICAL)
logging.getLogger("http.server").setLevel(logging.CRITICAL)

# ================= CONFIGURATION =================
TOKENS_FILE = "tokens.json"
GROUPS_FILE = "groups.json"
MEMORY_FILE = "memory.json"

def get_base_tokens():
    tokens_env = os.environ.get("BOT_TOKENS")
    if tokens_env:
        return [t.strip() for t in tokens_env.split(",") if t.strip()]
    return [
        
"8678337928:AAFB2kjr49cFBQycd6cVusaBqKutFtQESy4",

"8421829560:AAEJsMLvePart6tvLg0FhkonSsvmr_jqDA8",

"8737554703:AAGkVgcMUtGAncWpTW1R7odXJGWAkskcYmE",

"8258722308:AAHQuRQlh3NV2f-wl3d1VskQJORU5t1-b1E",

"8796497143:AAECWD3eFZrJ-J5JISM-QP7a7T_u4iIemkk",

"8643097990:AAGygCCklEFDAyCOGkgIzeqBaVMbn6YXT7M",

"8741545966:AAFr2vWql-L-y90iP3gZaBLZPpzJglVijec",

"8730600002:AAF76WIMWLWoOM6YYk0JYkSNDqrAGMk6IG4",

"8638467347:AAEWCAYPpv8D-iF8tmzQPkBkOwy9IeCT4II",

"8333463144:AAGaOiMVG_DDUb6Bs5GW8RYLw-pLS8TwCqw"
]

def load_extra_tokens() -> List[str]:
    try:
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return []

def save_extra_tokens(tokens: List[str]):
    try:
        with open(TOKENS_FILE, "w") as f:
            json.dump(tokens, f)
    except:
        pass

def load_groups() -> Set[int]:
    try:
        if os.path.exists(GROUPS_FILE):
            with open(GROUPS_FILE, "r") as f:
                return set(json.load(f))
    except:
        pass
    return set()

def save_groups(groups: Set[int]):
    try:
        with open(GROUPS_FILE, "w") as f:
            json.dump(list(groups), f)
    except:
        pass

def load_memory() -> Dict:
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_memory(mem: Dict):
    try:
        with open(MEMORY_FILE, "w") as f:
            json.dump(mem, f)
    except:
        pass

OWNER_ID = int(os.environ.get("6803396897"))
MASTER_CHAT_ID = int(os.environ.get("6803396897"))

# ================= GLOBAL SETTINGS =================
MIN_DELAY = 0.02
DEFAULT_SPEED = 0.1
MAX_CONCURRENT_TASKS = 1000
MAX_TASKS_PER_CHAT = 5
REQUEST_QUEUE_SIZE = 5000
CLEANUP_INTERVAL = 60
MAX_CHAT_STATS_AGE = 600
BATCH_SIZE = 10
STUCK_TASK_TIMEOUT = 0  # disabled — tasks run until /stop is called

# ================= STEADYNC V2 SPEED MODES =================
# STEADYNC V2 PIPELINE ENGINE — per-bot delays (each of 10 bots has its own loop)
# With pipelined workers: effective rate ≈ N_bots × (1 / (delay + api_latency))
# Setting delay=0 gives maximum throughput bounded only by Telegram's server rate
NC_SPEED_STEADY = 0.0   # All bots fire continuously — 10× pipeline
NC_SPEED_FAST   = 0.0   # Same — pipeline handles it
NC_SPEED_ULTRA  = 0.0   # Same
NC_SPEED_BURST  = 0.0   # NO sleep — maximum throughput

# Per-chat NC mode: "steady" | "fast" | "ultra" | "burst"
nc_mode: Dict[int, str] = {}

def get_nc_delay(chat_id: int) -> float:
    mode = nc_mode.get(chat_id, "steady")
    if mode == "fast":
        return NC_SPEED_FAST
    if mode == "ultra":
        return NC_SPEED_ULTRA
    if mode == "burst":
        return NC_SPEED_BURST
    return NC_SPEED_STEADY

# ================= TEXT TEMPLATES =================
NC_TEXTS = [
    "{text}┕━☽【🇦🇨】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇦🇫】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇦🇷】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇦🇩】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇧🇷】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇨🇦】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇨🇿】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇩🇪】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇫🇷】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇳🇱】☾━┙𝐂𝐇𝐔𝐃",
    "{text}┕━☽【🇳🇮】☾━┙𝐂𝐇𝐔𝐃",
]

GOD_TEXT = [
    "⭅╡𝗧𝗠𝗞𝗖╞⭆",
    "⭅╡𝗧𝗕𝗞𝗖╞⭆",
    "⭅╡𝗖𝗛𝗨𝗗╞⭆",
    "⭅╡𝗧𝗕𝗥╞⭆",
    "⭅╡𝗞𝗜𝗗𝗘╞⭆",
    "⭅╡𝗛𝗜𝗝𝗗𝗘╞⭆",
    "⭅╡𝗖𝗛𝗔𝗞𝗞𝗘╞⭆",
    "⭅╡𝗠𝗢𝗧𝗛𝗘𝗥𝗙𝗨𝗖𝗞𝗘𝗥╞⭆",
    "⭅╡𝗕𝗜𝗧𝗖𝗛╞⭆",
    "⭅╡𝗠𝗢𝗠𝗟𝗘𝗦𝗦╞⭆",
    "⭅╡𝗛𝗢𝗠𝗘𝗟𝗘𝗦𝗦╞⭆",
    "⭅╡𝗞𝗔𝗟𝗪𝗘╞⭆",
    "⭅╡𝗪𝗛𝗢𝗥𝗘╞⭆",
    "⭅╡𝗞𝗨𝗧𝗜𝗬𝗔╞⭆",
    "⭅╡𝐊𝐑𝐈𝐒𝐇 𝐃𝐀𝐃𝐃𝐘 𝗛𝗔𝗜╞⭆",
]

GODTAMP = [
    "⊱❄️⊰{text}⊱❄️⊰", "⊱🌹⊰{text}⊱🌹⊰", "𐙚🧸ྀི{text}𐙚🧸ྀི",
    "⊱⚡⊰{text}⊱⚡⊰", "⊱🪷⊰{text}⊱🪷⊰", "𓍢ִ໋🌷͙֒{text}𓍢ִ໋🌷͙֒",
    "💋ྀིྀི{text}💋ྀིྀི", "˚.🎀༘⋆{text}˚.🎀༘⋆", "ִֶཐི༏ཋྀ{text}ཐི༏ཋྀ",
    "⊱🕶️⊰{text}⊱🕶️⊰", "⊱💮⊰{text}⊱💮⊰", "⊱🌸⊰{text}⊱🌸⊰",
]

CUSTOMNC_TEXTS = [
    "×~🌷×~", "~×🌼×~", "~×🌻×~", "~×🌺×~", "~×🌹×~",
    "~×🏵️×~️", "~×🪷×~", "~×💮×~", "~×🌸×~", "~×🌷×~",
    "~×🌼×~", "~×🌻×~", "~×🌺×~", "~×🏵️×~", "~×❄️×~", "~×⚡×~",
]

NC_TEMPLATES = [
    "🔥 {text} 🔥", "⚡ {text} ⚡", "👑 {text} 👑", "💀 {text} 💀", "✨ {text} ✨",
    "💥 {text} 💥", "❄️ {text} ❄️", "🍀 {text} 🍀", "🍄 {text} 🍄", "🌹 {text} 🌹",
    "☄️ {text} ☄️", "☀️ {text} ☀️", "🌙 {text} 🌙", "🌀 {text} 🌀", "🔱 {text} 🔱",
    "💎 {text} 💎", "🔮 {text} 🔮", "🧿 {text} 🧿",
]

SPAM_TEXTS = [
    "𝑰𝑫𝑯𝑨𝑹 𝑺𝑬 𝑪𝑯𝑶𝑫𝑼 𝒀𝑨 𝑼𝑫𝑯𝑹 𝑺𝑬 /~💱🌺♥",
    "𝐀𝐈𝐒𝐄 𝐂𝐇𝐎𝐃𝐔 𝐘𝐀 𝐅𝐈𝐑 𝐖𝐀𝐈𝐒𝐄 /~💱🌺♥",
    "ḶÖḊЁ ṖṚ ÄÄĠЁ ḄÖḶ T͓̽M͓̽K͓̽C͓̽ /~💤🧞‍♀️",
]

MSG_EMOJIS = ["🔥", "⚡", "💀", "👑", "🌹", "❄️", "💎", "🧿", "🌸", "⭐"]
MSG_SPACERS = ["", " ", "  ", "   "]

_SASUKENC_EMOJIS = [
    "🔥","💥","⚡","🌙","🌟","✨","💫","🌈","🎯","👑","🏆","💎","🗡️","⚔️",
    "🐉","🦋","🌺","🌸","🍀","🌊","❄️","🔮","🎭","🎪","🎨","🎬","🎤","🎸",
    "🚀","🛸","💀","🦅","🐺","🦁","🐯","🦊","🐍","🦂","🌑","🌕","☄️","🌠",
    "💣","🧨","🎆","🎇","🪄","🏴‍☠️","🔴","🟠","🟡","🟢","🔵","🟣","🖤","🤍",
    "🧿","🔑","🗝️","⛓️","🪬","🧲","🪖","🛡️","🏹","🔱","⚜️","🌀","🌪️","🌩️",
]

_SASNC_SYMBOLS = [
    "𖤍", "✦", "⚡", "☠", "♛", "𓆩𓆪", "꧁", "✧", "🔥", "💫",
    "⚜️", "🌀", "🌪️", "🌩️", "💥", "🌟", "🌠", "🌌", "🌍",
    "❦", "۩", "꩜", "𓂀", "༒", "ꜰ", "ꕤ", "᯾", "꙰", "⛧",
    "🦋", "🌸", "💠", "🔮", "🌙", "☽", "⭐", "✴️", "🔱", "⚔️",
    "🏴", "💎", "🪬", "🧿", "🌊", "🔯", "☯️", "🕉️", "⚙️", "🎯",
]

# ================= SUDO PERSISTENCE =================
_SUDO_FILE = "sudo_users.json"

def _load_sudo() -> Set[int]:
    try:
        with open(_SUDO_FILE, "r") as f:
            data = json.load(f)
        return set(int(x) for x in data)
    except Exception:
        return set()

def _save_sudo(s: Set[int]) -> None:
    try:
        with open(_SUDO_FILE, "w") as f:
            json.dump(list(s), f)
    except Exception:
        pass


# ================= GLOBAL STATE =================
running_tasks: Dict[str, asyncio.Task] = {}
stop_events: Dict[str, asyncio.Event] = {}
known_chats: Set[int] = load_groups()
SUDO_USERS: Set[int] = _load_sudo() | {OWNER_ID}
slide_reply_targets: Dict[int, str] = {}
speed_settings: Dict[int, float] = {}
global_mode: bool = False
bot_start_time = time.time()
all_bot_instances: List[Any] = []
all_apps: List[Any] = []
extra_tokens: List[str] = load_extra_tokens()
max_threads: int = 5
spam_templates: List[str] = list(SPAM_TEXTS)
target_names: Dict[int, str] = {}
nc_speeds: Dict[int, float] = {}
task_start_times: Dict[str, float] = {}
messages_sent: int = 0
memory: Dict = load_memory()

_seen_updates: Set[int] = set()


def _is_primary_bot(context) -> bool:
    """Returns True only for the first/primary bot instance.
    Prevents all secondary bots from sending duplicate replies."""
    if not all_bot_instances:
        return True
    return context.bot.id == all_bot_instances[0].id

_OWNER_GATE_MSG = (
    "┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅\n"
    "⚡️𝑫𝑼𝑹 𝑹𝑬𝑯 𝑹𝑵𝑫𝒀𝑪𝑬⚡️\n"
    "𝑻𝑼 𝑲𝑹𝑰𝑺𝑯 𝑲𝑬𝑵𝑮 \n"
    "𝑲𝑨𝑩𝑯𝑰 𝑵𝑯𝑰 𝑩𝑨𝑵 𝑺𝑨𝑲𝑻𝑨\n"
    "┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅┅"
)

def _dedup(handler):
    """Wrap a handler so:
    1. Only ONE bot per unique update_id executes it (deduplication).
    2. Only the PRIMARY bot instance sends replies (prevents N-bot spam).
    3. Non-owner /commands get the taunt reply (from primary bot only).

    Root cause of multi-bot replies:
      Each bot receives a DIFFERENT update_id for the same group message,
      so update_id deduplication alone cannot deduplicate across bots.
      The primary-bot gate is the correct cross-bot filter.
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.update_id
        if uid in _seen_updates:
            return
        _seen_updates.add(uid)
        if len(_seen_updates) > 10000:
            oldest = sorted(_seen_updates)[:5000]
            for u in oldest:
                _seen_updates.discard(u)

        # PRIMARY BOT GATE — only the first bot in all_bot_instances replies.
        # All other bots silently drop the command to prevent duplicate messages.
        if all_bot_instances and context.bot.id != all_bot_instances[0].id:
            return

        msg = update.message or update.edited_message
        if msg and msg.text and msg.text.startswith("/"):
            user = update.effective_user
            if not user or user.id != OWNER_ID:
                try:
                    await msg.reply_text(_OWNER_GATE_MSG)
                except Exception:
                    pass
                return
        await handler(update, context)
    return wrapper

perf_stats = {
    "msgs_sent": 0,
    "msgs_failed": 0,
    "rate_limit_hits": 0,
    "tasks_completed": 0,
    "start_time": time.time(),
}

# ================= SMART RATE LIMITER =================
class SmartRateLimiter:
    def __init__(self):
        self.chat_stats: Dict[int, Dict[str, Any]] = {}
        self.consecutive_failures: Dict[int, int] = {}
        self.success_streak: Dict[int, int] = {}
        self.action_cooldowns: Dict[str, float] = {}
        self.last_cleanup = time.time()
        self.per_chat_cooldown: Dict[int, float] = {}
        self.base_delays: Dict[str, float] = {
            "message": 0.03, "title": 0.3, "photo": 0.8, "default": 0.05
        }

    def get_chat_stats(self, chat_id: int) -> Dict[str, Any]:
        if chat_id not in self.chat_stats:
            self.chat_stats[chat_id] = {
                "total_requests": 0, "success_count": 0,
                "rate_limit_hits": 0, "last_rate_limit": 0,
                "adaptive_delay": 0.05, "last_success": time.time()
            }
        return self.chat_stats[chat_id]

    def calculate_adaptive_delay(self, chat_id: int, action_type: str = "default") -> float:
        base = self.base_delays.get(action_type, self.base_delays["default"])
        failures = self.consecutive_failures.get(chat_id, 0)
        if failures > 0:
            delay = base * (1.5 ** min(failures, 8))
            return delay + random.uniform(0, delay * 0.3)
        success = self.success_streak.get(chat_id, 0)
        if success > 5:
            reduction = min(0.8, 0.05 * (success - 5))
            return max(0.02, base * (1 - reduction))
        return max(0.02, base + random.uniform(0, base * 0.1))

    def record_success(self, chat_id: int):
        stats = self.get_chat_stats(chat_id)
        stats["total_requests"] += 1
        stats["success_count"] += 1
        stats["last_success"] = time.time()
        stats["adaptive_delay"] = max(0.02, stats["adaptive_delay"] * 0.95)
        self.consecutive_failures[chat_id] = 0
        self.success_streak[chat_id] = self.success_streak.get(chat_id, 0) + 1
        self.per_chat_cooldown.pop(chat_id, None)

    def record_rate_limit(self, chat_id: int, wait_time: float):
        stats = self.get_chat_stats(chat_id)
        stats["total_requests"] += 1
        stats["rate_limit_hits"] += 1
        stats["last_rate_limit"] = time.time()
        stats["adaptive_delay"] = min(30.0, stats["adaptive_delay"] * 2)
        self.consecutive_failures[chat_id] = self.consecutive_failures.get(chat_id, 0) + 1
        self.success_streak[chat_id] = 0
        self.per_chat_cooldown[chat_id] = time.time() + wait_time
        self.action_cooldowns[f"{chat_id}_all"] = time.time() + wait_time
        perf_stats["rate_limit_hits"] += 1

    def record_failure(self, chat_id: int):
        stats = self.get_chat_stats(chat_id)
        stats["total_requests"] += 1
        self.consecutive_failures[chat_id] = self.consecutive_failures.get(chat_id, 0) + 1
        self.success_streak[chat_id] = 0

    def should_throttle(self, chat_id: int) -> bool:
        cooldown_key = f"{chat_id}_all"
        if cooldown_key in self.action_cooldowns:
            if time.time() < self.action_cooldowns[cooldown_key]:
                return True
            del self.action_cooldowns[cooldown_key]
        return False

    def get_throttle_time(self, chat_id: int) -> float:
        cooldown_key = f"{chat_id}_all"
        if cooldown_key in self.action_cooldowns:
            remaining = self.action_cooldowns[cooldown_key] - time.time()
            return max(0, remaining)
        return 0

    def get_smart_wait_time(self, retry_after: float) -> float:
        return retry_after + random.uniform(0.1, 0.5)

    def get_stats_summary(self, chat_id: int) -> str:
        stats = self.get_chat_stats(chat_id)
        success_rate = (stats["success_count"] / max(1, stats["total_requests"])) * 100
        return (f"📊 Reqs: {stats['total_requests']} | "
                f"Success: {success_rate:.1f}% | "
                f"RL Hits: {stats['rate_limit_hits']} | "
                f"Delay: {stats['adaptive_delay']:.3f}s")

    def get_global_stats(self) -> Dict[str, Any]:
        total_reqs = sum(s.get("total_requests", 0) for s in self.chat_stats.values())
        total_success = sum(s.get("success_count", 0) for s in self.chat_stats.values())
        total_rl = sum(s.get("rate_limit_hits", 0) for s in self.chat_stats.values())
        return {
            "tracked_chats": len(self.chat_stats),
            "total_requests": total_reqs,
            "total_success": total_success,
            "total_rate_limits": total_rl,
            "success_rate": (total_success / max(1, total_reqs)) * 100
        }

    async def cleanup_old_stats(self):
        now = time.time()
        if now - self.last_cleanup < CLEANUP_INTERVAL:
            return
        self.last_cleanup = now
        stale_chats = [c for c, s in self.chat_stats.items()
                       if now - s.get("last_success", 0) > MAX_CHAT_STATS_AGE]
        for chat_id in stale_chats:
            del self.chat_stats[chat_id]
            self.consecutive_failures.pop(chat_id, None)
            self.success_streak.pop(chat_id, None)
        stale_cooldowns = [k for k, v in self.action_cooldowns.items() if v < now]
        for k in stale_cooldowns:
            del self.action_cooldowns[k]


rate_limiter = SmartRateLimiter()


# ================= TASK CONTROLLER =================
class TaskController:
    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.events: Dict[str, asyncio.Event] = {}
        self.task_times: Dict[str, float] = {}
        self.last_cleanup = time.time()

    def make_key(self, chat_id: int, task_type: str) -> str:
        return f"{chat_id}_{task_type}"

    async def start_task(self, chat_id: int, task_type: str, coro_factory) -> bool:
        await self.stop_task(chat_id, task_type)
        key = self.make_key(chat_id, task_type)
        stop_event = asyncio.Event()
        self.events[key] = stop_event
        self.task_times[key] = time.time()

        async def wrapped():
            try:
                await coro_factory(stop_event)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Task {key} error: {e}")
            finally:
                self.tasks.pop(key, None)
                self.events.pop(key, None)
                self.task_times.pop(key, None)
                perf_stats["tasks_completed"] += 1

        self.tasks[key] = asyncio.create_task(wrapped())
        return True

    async def stop_task(self, chat_id: int, task_type: str) -> bool:
        key = self.make_key(chat_id, task_type)
        stopped = False
        if key in self.events:
            self.events[key].set()
            stopped = True
        if key in self.tasks:
            task = self.tasks.pop(key)
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError, Exception):
                    pass
            stopped = True
        self.events.pop(key, None)
        self.task_times.pop(key, None)
        return stopped

    async def stop_all_for_chat(self, chat_id: int) -> int:
        prefix = f"{chat_id}_"
        keys = [k for k in list(self.tasks.keys()) + list(self.events.keys()) if k.startswith(prefix)]
        task_types = set(k.split("_", 1)[1] for k in keys)
        count = 0
        for t in task_types:
            if await self.stop_task(chat_id, t):
                count += 1
        return count

    async def stop_all(self) -> int:
        for event in list(self.events.values()):
            event.set()
        tasks_to_cancel = list(self.tasks.values())
        count = len(tasks_to_cancel)
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()
        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
        self.tasks.clear()
        self.events.clear()
        self.task_times.clear()
        return count

    def is_running(self, chat_id: int, task_type: str) -> bool:
        key = self.make_key(chat_id, task_type)
        return key in self.tasks and not self.tasks[key].done()

    def get_event(self, chat_id: int, task_type: str) -> Optional[asyncio.Event]:
        return self.events.get(self.make_key(chat_id, task_type))

    def get_active_count(self) -> int:
        return len([t for t in self.tasks.values() if not t.done()])

    async def detect_and_restart_stuck(self):
        # STUCK_TASK_TIMEOUT = 0 means disabled — tasks run until /stop
        if not STUCK_TASK_TIMEOUT:
            return
        now = time.time()
        for key, start_time in list(self.task_times.items()):
            if now - start_time > STUCK_TASK_TIMEOUT:
                task = self.tasks.get(key)
                if task and not task.done():
                    logger.warning(f"Stuck task detected: {key}, cancelling")
                    task.cancel()

    async def cleanup(self):
        now = time.time()
        if now - self.last_cleanup < CLEANUP_INTERVAL:
            return
        self.last_cleanup = now
        done_keys = [k for k, t in self.tasks.items() if t.done()]
        for k in done_keys:
            self.tasks.pop(k, None)
            self.events.pop(k, None)
            self.task_times.pop(k, None)


task_controller = TaskController()


# ================= BOT MANAGER =================
class BotManager:
    def __init__(self):
        self._bots_info: Dict[str, Dict] = {}

    def add_bot_info(self, token: str, app: Any, bot: Any, username: str, bot_id: int):
        self._bots_info[token] = {
            "app": app, "bot": bot, "username": username,
            "bot_id": bot_id, "active": True
        }

    def get_all_bots(self) -> List[Any]:
        return [info["bot"] for info in self._bots_info.values() if info.get("active")]

    def get_bot_count(self) -> int:
        return len([i for i in self._bots_info.values() if i.get("active")])

    def get_bot_list_text(self) -> str:
        lines = []
        for token, info in self._bots_info.items():
            status = "✅" if info.get("active") else "❌"
            lines.append(f"{status} @{info['username']} (ID: {info['bot_id']})")
        return "\n".join(lines) if lines else "No bots registered"

    async def remove_bot(self, bot_id: int) -> bool:
        for token, info in list(self._bots_info.items()):
            if info["bot_id"] == bot_id:
                info["active"] = False
                try:
                    await info["app"].stop()
                    await info["app"].shutdown()
                except:
                    pass
                if token in extra_tokens:
                    extra_tokens.remove(token)
                    save_extra_tokens(extra_tokens)
                return True
        return False


bot_manager = BotManager()


# ================= HELPERS =================
def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in SUDO_USERS

def is_master_chat(chat_id: int) -> bool:
    if MASTER_CHAT_ID == 0:
        return True
    return chat_id == MASTER_CHAT_ID

def get_delay(chat_id: int) -> float:
    return max(MIN_DELAY, speed_settings.get(chat_id, DEFAULT_SPEED))

def get_task_key(chat_id: int, action: str) -> str:
    return f"{chat_id}_{action}"

def vary_message(text: str) -> str:
    emoji = random.choice(MSG_EMOJIS)
    spacer = random.choice(MSG_SPACERS)
    patterns = [
        f"{text}{spacer}{emoji}",
        f"{emoji}{spacer}{text}",
        f"{text}",
    ]
    return random.choice(patterns)

async def safe_api_request(func, *args, chat_id=None, action_type="default", **kwargs):
    global messages_sent
    if chat_id and rate_limiter.should_throttle(chat_id):
        throttle_time = rate_limiter.get_throttle_time(chat_id)
        if throttle_time > 0:
            await asyncio.sleep(min(throttle_time, 5.0))
    for attempt in range(3):
        try:
            result = await func(*args, **kwargs)
            if chat_id:
                rate_limiter.record_success(chat_id)
            messages_sent += 1
            perf_stats["msgs_sent"] += 1
            return True
        except RetryAfter as e:
            wait_time = e.retry_after
            smart_wait = rate_limiter.get_smart_wait_time(wait_time)
            if chat_id:
                rate_limiter.record_rate_limit(chat_id, wait_time)
            if wait_time > 60:
                await asyncio.sleep(min(smart_wait, 30.0))
            elif wait_time > 10:
                await asyncio.sleep(smart_wait * 0.7)
            else:
                await asyncio.sleep(smart_wait * 0.5 + random.uniform(0.1, 0.5))
            if attempt < 2:
                continue
            return False
        except BadRequest as e:
            err_msg = str(e)
            if any(x in err_msg for x in ["Chat not found", "Have no rights", "not a member"]):
                return True
            if "Too Many Requests" in err_msg or "retry" in err_msg.lower():
                if chat_id:
                    rate_limiter.record_rate_limit(chat_id, 5.0)
                await asyncio.sleep(random.uniform(0.5, 2.0))
                if attempt < 2:
                    continue
            if chat_id:
                rate_limiter.record_failure(chat_id)
            perf_stats["msgs_failed"] += 1
            return False
        except Forbidden:
            return True
        except (TimedOut, NetworkError):
            if chat_id:
                rate_limiter.record_failure(chat_id)
            await asyncio.sleep(random.uniform(0.01, 0.1))
            if attempt < 2:
                continue
            perf_stats["msgs_failed"] += 1
            return False
        except Exception as e:
            err_msg = str(e)
            if "Chat not found" in err_msg:
                return True
            if "Flood control" in err_msg or "429" in err_msg:
                if chat_id:
                    rate_limiter.record_rate_limit(chat_id, 3.0)
                await asyncio.sleep(rate_limiter.calculate_adaptive_delay(chat_id, action_type) if chat_id else 0.5)
                if attempt < 2:
                    continue
            if chat_id:
                rate_limiter.record_failure(chat_id)
            perf_stats["msgs_failed"] += 1
            return False
    return False


# ================= BACKGROUND TASKS =================
async def periodic_cleanup():
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL)
            await rate_limiter.cleanup_old_stats()
            await task_controller.cleanup()
            await task_controller.detect_and_restart_stuck()
            save_groups(known_chats)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# ===================================================================
# STEADYNC ENGINE — THE SINGLE BASE ENGINE FOR ALL NC COMMANDS
# ===================================================================
# Design:
#   • ONE loop per command (no asyncio.create_task / pipeline)
#   • Each round: build tasks list → gather(*tasks) → wait delay
#   • Stop event checked every round AND inside wait_for
#   • BURST mode: no sleep at all — just back-to-back gathers
#   • Instant stop: stop_event.set() → current gather finishes → loop exits
# ===================================================================

# ================= FLOOD BYPASS TRACKER =================
class BotFloodTracker:
    """
    Per-bot RetryAfter bypass — zero global pauses.

    When bot X hits FloodWait(N):
      • Mark ONLY bot X as unavailable for N seconds
      • ALL other bots continue firing at full speed
      • Bot X resumes automatically when N seconds expire
      • If ALL bots flood simultaneously, wait only for the SHORTEST remaining cooldown

    With 10 bots this means one flooded bot = 9 bots still at 100% throughput.
    The NC pipeline effectively never stops — just rotates the flooded bot out temporarily.
    """
    def __init__(self):
        self._flood_until: Dict[int, float] = {}

    def is_flooded(self, bot_id: int) -> bool:
        exp = self._flood_until.get(bot_id, 0.0)
        if time.monotonic() < exp:
            return True
        self._flood_until.pop(bot_id, None)
        return False

    def mark_flooded(self, bot_id: int, seconds: float) -> None:
        self._flood_until[bot_id] = time.monotonic() + max(float(seconds), 0.05)
        logger.debug(f"[FloodBypass] Bot {bot_id} → cooling {seconds:.1f}s")

    def remaining(self, bot_id: int) -> float:
        return max(0.0, self._flood_until.get(bot_id, 0.0) - time.monotonic())

    def min_wait(self, bots: list) -> float:
        """Minimum seconds until at least ONE bot is available again."""
        if not bots:
            return 0.0
        return min(self.remaining(getattr(b, "id", id(b))) for b in bots)


# Module-level singleton shared across all NC engines and sessions
_flood_tracker = BotFloodTracker()


# ================= HYPER RATE LIMIT BYPASS =================
class HyperRateLimiter:
    """
    Adaptive token-bucket rate limiter — proactively prevents RetryAfter.

    ┌─────────────────────────────────────────────────────────────────┐
    │  The problem with dumb burst NC:                                │
    │    Fire as fast as possible → hit RetryAfter → sleep N seconds  │
    │    → burst again → looks jittery and gets throttled hard        │
    │                                                                 │
    │  HyperRateLimiter solution:                                     │
    │    Each bot fires at its OWN regulated interval (token bucket)  │
    │    On RetryAfter  → double this bot's interval (back off)       │
    │    On clean call  → slowly reduce interval back to BASE         │
    │    Result: near-zero RetryAfter, perfectly constant NC rhythm   │
    │                                                                 │
    │  With 10 bots staggered at BASE_INTERVAL=0.30s:                │
    │    → 10/0.30 = ~33 renames/sec  (smooth, never spiky)           │
    └─────────────────────────────────────────────────────────────────┘

    Stagger formula: bot[i] starts after  i × (interval / n_bots)  seconds.
    This spreads all 10 bots evenly across the interval window so renames
    arrive at Telegram's servers in a perfectly uniform stream.
    """
    BASE_INTERVAL    = 2.0    # seconds between calls per bot → ~5 renames/sec with 10 bots
    MIN_INTERVAL     = 1.5    # never go faster than this per bot
    MAX_INTERVAL     = 6.0    # ceiling after flooding (won't crawl for ages)
    BACKOFF_FACTOR   = 1.3    # only 30% slower after flood (2.0 → 2.6 s)
    RECOVERY_FACTOR  = 0.80   # recover 20% per success → ~3 clean fires back to BASE

    def __init__(self):
        # Per-bot current interval (seconds)
        self._intervals:  Dict[int, float] = {}
        # Per-bot last-fire timestamp (monotonic)
        self._last_fire:  Dict[int, float] = {}
        # Per-bot consecutive-success counter (for faster recovery after calm period)
        self._successes:  Dict[int, int]   = {}

    # ── public API ────────────────────────────────────────────────────

    def interval(self, bot_id: int) -> float:
        return self._intervals.get(bot_id, self.BASE_INTERVAL)

    def time_until_ready(self, bot_id: int) -> float:
        """Seconds until this bot is allowed to fire its next rename."""
        last     = self._last_fire.get(bot_id, 0.0)
        interval = self.interval(bot_id)
        return max(0.0, (last + interval) - time.monotonic())

    def is_ready(self, bot_id: int) -> bool:
        return self.time_until_ready(bot_id) <= 0.0

    def mark_fired(self, bot_id: int) -> None:
        self._last_fire[bot_id] = time.monotonic()

    def on_success(self, bot_id: int) -> None:
        """Called after every clean set_chat_title — gradually recovers rate."""
        cnt = self._successes.get(bot_id, 0) + 1
        self._successes[bot_id] = cnt
        current = self.interval(bot_id)
        if current > self.BASE_INTERVAL:
            new = max(current * self.RECOVERY_FACTOR, self.BASE_INTERVAL)
            self._intervals[bot_id] = new

    def on_flood(self, bot_id: int, retry_after: float) -> None:
        """
        Called on RetryAfter — back off this bot's interval AND mark it flooded.
        Doubling the interval means the bot fires half as often after recovery,
        preventing an immediate re-hit of the rate limit.
        """
        self._successes[bot_id] = 0
        current = self.interval(bot_id)
        # Gentle 30% backoff only — BotFloodTracker already handles the full
        # Telegram-mandated wait, so we must NOT amplify off retry_after here.
        # Otherwise one 30 s RetryAfter turns into a 15 s per-fire interval.
        new = min(current * self.BACKOFF_FACTOR, self.MAX_INTERVAL)
        self._intervals[bot_id] = new
        _flood_tracker.mark_flooded(bot_id, retry_after)
        logger.debug(f"[HyperRL] Bot {bot_id} flooded {retry_after:.1f}s — interval → {new:.2f}s")

    def stagger_delay(self, bot_index: int, n_bots: int, bot_id: int) -> float:
        """
        Even startup stagger for a fleet of bots.
        Spreads them across one full interval window so they never
        all fire at the same millisecond.
        """
        interval = self.interval(bot_id)
        if n_bots <= 1:
            return 0.0
        return (bot_index / n_bots) * interval


# Module-level singleton — shared across all smooth/sasnc NC engines
_hyper_rl = HyperRateLimiter()


async def _steadync_engine(
    chat_id: int,
    bots: List[Any],
    stop_event: asyncio.Event,
    name_factory,       # callable() → str  (generates next name)
    delay: float = NC_SPEED_STEADY
):
    """
    STEADYNC V2 PIPELINE ENGINE  +  FLOOD BYPASS
    =============================================
    Each bot runs its OWN independent asyncio loop — pipelined for maximum throughput.
    With N bots we get ~N× the rename rate vs old gather model.

    FLOOD BYPASS:
      • RetryAfter → mark ONLY this bot flooded; bot waits its own cooldown
      • ALL other bots keep firing — no global pause EVER
      • Bot resumes automatically when cooldown expires
      • If all bots flood at once → wait for shortest remaining cooldown only
    """
    if not bots:
        return

    async def _bot_worker(bot):
        bot_id = getattr(bot, "id", id(bot))
        while not stop_event.is_set():

            # ── FLOOD CHECK: if this bot is cooling down, wait for it ──
            if _flood_tracker.is_flooded(bot_id):
                wait = _flood_tracker.remaining(bot_id)
                if wait > 0:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=min(wait, 0.25))
                    except asyncio.TimeoutError:
                        pass
                continue  # re-check flood state before firing

            try:
                name = name_factory()[:255]
                await bot.set_chat_title(chat_id, name)

            except RetryAfter as e:
                # ── FLOOD BYPASS: mark this bot, don't sleep globally ──
                _flood_tracker.mark_flooded(bot_id, e.retry_after)
                continue  # loop immediately; flood check handles the wait

            except (BadRequest, Forbidden):
                if stop_event.is_set():
                    break
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=0.3)
                except asyncio.TimeoutError:
                    pass
                continue

            except (TimedOut, NetworkError):
                if stop_event.is_set():
                    break
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
                continue

            except Exception:
                if stop_event.is_set():
                    break
                await asyncio.sleep(0.1)
                continue

            if stop_event.is_set():
                break

            # ── optional inter-round delay for this bot only ──
            if delay > 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=delay)
                except asyncio.TimeoutError:
                    continue
                else:
                    break
            else:
                # Burst: yield control so other bots get event-loop time
                await asyncio.sleep(0)

    workers = [asyncio.create_task(_bot_worker(bot)) for bot in bots]
    try:
        await asyncio.gather(*workers, return_exceptions=True)
    finally:
        for w in workers:
            if not w.done():
                w.cancel()


async def _hyperfire_engine(
    chat_id: int,
    bots: List[Any],
    stop_event: asyncio.Event,
    name_factory,       # callable() → str
):
    """
    HYPERFIRE ENGINE  +  FLOOD BYPASS
    ===================================
    Fire-and-forget: each bot queues rename tasks WITHOUT awaiting them.
    API responses are handled in the background — maximum rename throughput.

    FLOOD BYPASS:
      • RetryAfter in any pending task → marks ONLY that bot flooded
      • Bot worker sees the flood flag → pauses ONLY that bot's queue
      • Other 9 bots keep firing — ZERO global pauses
      • Pending tasks for flooded bot are NOT queued until cooldown expires
    """
    if not bots:
        return

    pending_tasks: set = set()

    def _on_task_done(t):
        pending_tasks.discard(t)

    async def _safe_rename(bot, name: str, bot_id: int):
        try:
            await bot.set_chat_title(chat_id, name)
        except RetryAfter as e:
            # Mark bot flooded — worker will pause until it clears
            _flood_tracker.mark_flooded(bot_id, e.retry_after)
        except (TimedOut, NetworkError):
            pass  # transient — next task will retry automatically
        except (BadRequest, Forbidden):
            pass  # title unchanged / no admin — silent skip
        except Exception:
            pass

    async def _bot_worker(bot):
        bot_id = getattr(bot, "id", id(bot))
        while not stop_event.is_set():

            # ── FLOOD CHECK: pause only this bot while it's cooling ──
            if _flood_tracker.is_flooded(bot_id):
                wait = _flood_tracker.remaining(bot_id)
                if wait > 0:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=min(wait, 0.25))
                    except asyncio.TimeoutError:
                        pass
                continue  # re-check before queuing next task

            name = name_factory()[:255]
            t = asyncio.create_task(_safe_rename(bot, name, bot_id))
            pending_tasks.add(t)
            t.add_done_callback(_on_task_done)
            # Yield to event loop — lets other bots queue their tasks too
            await asyncio.sleep(0)

    workers = [asyncio.create_task(_bot_worker(bot)) for bot in bots]
    try:
        await asyncio.gather(*workers, return_exceptions=True)
    finally:
        for w in workers:
            if not w.done():
                w.cancel()
        for t in list(pending_tasks):
            t.cancel()


async def _smoothsas_engine(
    chat_id: int,
    bots: List[Any],
    stop_event: asyncio.Event,
    name_factory,       # callable() → str
):
    """
    SMOOTH SAS ENGINE  —  constant · jitter-free · flood-proof
    ===========================================================
    Designed for `+smoothsas`: looks like the group is renaming itself
    at a perfectly steady, natural-feeling pace with zero stoppage.

    Principles:
      1. HyperRateLimiter paces each bot at BASE_INTERVAL (0.30 s).
         → 10 bots × 0.30 s = one rename every ~30 ms globally.
      2. Startup stagger evenly spreads all bots across one full interval
         window — renames arrive at Telegram as a perfectly uniform stream,
         never in clusters that trigger rate-limit detection.
      3. On RetryAfter → back off THIS bot only (double interval), others
         keep running. That bot recovers gradually over the next N successes.
      4. No burst-then-stop pattern — the system self-regulates continuously.

    Visual result: group name changes smoothly and constantly, at a rate
    that looks deliberate and limitless — no visible pauses or jitter.
    """
    if not bots:
        return

    n = len(bots)

    async def _bot_worker(bot, bot_index: int):
        bot_id = getattr(bot, "id", id(bot))

        # ── Stagger startup: spread bots evenly across one interval ──
        stagger = _hyper_rl.stagger_delay(bot_index, n, bot_id)
        if stagger > 0:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=stagger)
            except asyncio.TimeoutError:
                pass
        if stop_event.is_set():
            return

        while not stop_event.is_set():

            # ── 1. Flood gate: wait out any active flood on this bot ──
            if _flood_tracker.is_flooded(bot_id):
                wait = _flood_tracker.remaining(bot_id)
                if wait > 0:
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=min(wait, 0.25))
                    except asyncio.TimeoutError:
                        pass
                continue

            # ── 2. Rate limiter gate: wait until this bot's token refills ──
            wait = _hyper_rl.time_until_ready(bot_id)
            if wait > 0:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=wait)
                except asyncio.TimeoutError:
                    pass
                if stop_event.is_set():
                    break
                continue

            # ── 3. Fire rename ──
            name = name_factory()[:255]
            _hyper_rl.mark_fired(bot_id)

            try:
                await bot.set_chat_title(chat_id, name)
                _hyper_rl.on_success(bot_id)    # gradually recover interval

            except RetryAfter as e:
                _hyper_rl.on_flood(bot_id, e.retry_after)   # back off + mark flooded

            except (BadRequest, Forbidden):
                pass  # title unchanged or no rights — silent, keep going

            except (TimedOut, NetworkError):
                pass  # transient — next tick will retry

            except Exception:
                pass

    workers = [asyncio.create_task(_bot_worker(bot, i)) for i, bot in enumerate(bots)]
    try:
        await asyncio.gather(*workers, return_exceptions=True)
    finally:
        for w in workers:
            if not w.done():
                w.cancel()


# ================= COMMAND HANDLERS =================

_SUSANOO_PHOTO = "susanoo.jpg"
_CAPTION_LIMIT  = 1024   # Telegram hard cap for photo captions

async def _send_with_photo(message, text: str, short_header: str = "𖤍 𝑲𝑹𝑰𝑺𝑯 𝑹𝑼𝑳𝑬𝑹  𖤍") -> None:
    """
    Send text with the Susanoo photo header.
    • text ≤ 1024 chars  → single reply_photo with text as caption
    • text > 1024 chars  → reply_photo with short_header, then reply_text with full text
    • photo missing/error → falls back to plain reply_text
    """
    if not os.path.exists(_SUSANOO_PHOTO):
        await message.reply_text(text)
        return
    try:
        if len(text) <= _CAPTION_LIMIT:
            with open(_SUSANOO_PHOTO, "rb") as f:
                await message.reply_photo(f, caption=text)
        else:
            with open(_SUSANOO_PHOTO, "rb") as f:
                await message.reply_photo(f, caption=short_header)
            await message.reply_text(text)
    except Exception as e:
        logger.warning(f"[_send_with_photo] photo send failed ({e}), falling back to text")
        await message.reply_text(text)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    known_chats.add(chat_id)
    save_groups(known_chats)
    if update.message:
        await _send_with_photo(
            update.message,
            "✅ रूलर 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 𝐁𝐎𝐓 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃\n\n"
            "☠ All bots online and ready\n"
            "⚡ Use /menu for full control panel\n"
            "📋 Use /cmds for command list",
        )

async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n\n"
        "𖤍 𝑹𝑼𝑳𝑰𝑵𝑮 𝑴𝑶𝑫𝑬 𝑨𝑪𝑻𝑰𝑽𝑨𝑻𝑬𝑫 𖤍\n\n"
        "۞ The soul of the gods has awakened\n"
        "۞ My eyes see through your secrets\n"
        "۞ You are now the chosen controller\n\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n\n"
        "⚡ 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 भगवान 𝐁𝐎𝐓  ⚡\n\n"
        "☠ Control all bots\n"
        "☠ Global domination\n\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n\n"
        "💬 𝐒𝐏𝐀𝐌: /spam /raidspam /imagespam /gspam +slide\n"
        "🏷️ 𝐍𝐂: +nc +fastnc +ultranc +burstnc +sasnc +sasmaxnc +smoothsas\n"
        "⚡ 𝐒𝐏𝐄𝐄𝐃: /ncsteady /ncfast /ncultra /ncburst\n"
        "📸 𝐏𝐅𝐏: /changepfp /gpfp\n"
        "🔁 𝐂𝐎𝐌𝐁𝐎: /spnc /ncpfp /all\n"
        "⚡ 𝐒𝐓𝐎𝐏: /stop /gstop /dynstop\n"
        "🌐 𝐆𝐋𝐎𝐁𝐀𝐋: /g /gspam /gnc /gpfp /gstop\n"
        "🤖 𝐁𝐎𝐓𝐒: /addtoken /bots /removebot /gaddbot\n"
        "📊 𝐒𝐓𝐀𝐓𝐒: /dashboard /status /perf\n\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤"
    )
    if update.message:
        await _send_with_photo(update.message, caption)


async def plus_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n\n"
        "𖤍 भगवान बोट — 𝐅𝐔𝐋𝐋 𝐂𝐌𝐃 𝐋𝐈𝐒𝐓 𖤍\n\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n\n"
        "💬 𝐒𝐏𝐀𝐌\n"
        "├ /spam <text> — Spam loop\n"
        "├ /raidspam — Raid spam\n"
        "├ /imagespam — Image spam (reply photo)\n"
        "├ /gspam <text> — Global spam ALL groups\n"
        "├ +slide <text> — ⚡ Reply-bomb (all bots · modern symbols)\n"
        "└ /Stopspm — Stop spam\n\n"
        "🏷️ 𝐍𝐀𝐌𝐄 𝐂𝐇𝐀𝐍𝐆𝐄𝐑 (STEADYNC V2 ENGINE)\n"
        "├ +nc <text> — Steady NC (pipeline, 10× throughput)\n"
        "├ +fastnc <text> — Fast NC (pipeline)\n"
        "├ +ultranc <text> — Ultra NC ⚡ HYPERFIRE (fire-and-forget)\n"
        "├ +burstnc <text> — Burst NC (pipeline, no delay)\n"
        "├ +sasnc <text> — SASNC styled ultra smooth\n"
        "├ +sasmaxnc <text> — SASMAXNC 💀 HYPERFIRE + 50-symbol pool\n"
        "├ +smoothsas <text> — 🌊 Smooth SAS (constant · no jitter · no flood pauses)\n"
        "├ +sasukenc <text> — SasukeNC\n"
        "├ /nc <text> — NC loop (uses current mode)\n"
        "├ /gcnc <name> — GCNC loop\n"
        "├ /godspeed <text> — Ultra fast NC\n"
        "├ /ncbaap <name> — Speed NC burst\n"
        "├ /customnc <name> — Custom template NC\n"
        "├ /gnc <text> — Global NC ALL groups\n"
        "├ /g nc|fastnc|ultranc|burstnc|sasnc <text> — Global any mode\n"
        "├ /delaync <sec> — Set NC delay\n"
        "├ /ncsteady — STEADY mode (50ms)\n"
        "├ /ncfast — FAST mode (40ms)\n"
        "├ /ncultra — ULTRA mode (30ms)\n"
        "├ /ncburst — BURST mode (no delay)\n"
        "└ /stopnc — Stop NC\n\n"
        "📸 𝐏𝐅𝐏\n"
        "├ /changepfp — PFP loop (reply photo)\n"
        "├ /gpfp — Global PFP ALL groups (reply photo)\n"
        "└ /Stoppfp — Stop PFP\n\n"
        "🔁 𝐂𝐎𝐌𝐁𝐎𝐒\n"
        "├ /spnc <text> — Spam + NC together\n"
        "├ /ncpfp <text> — NC + PFP together (reply photo)\n"
        "└ /all <text> — Spam + NC + PFP all at once 💀\n\n"
        "⚡ 𝐒𝐓𝐎𝐏\n"
        "├ /stop — Stop ALL tasks in THIS chat\n"
        "├ /gstop — Stop ALL tasks GLOBALLY\n"
        "└ /dynstop — Nuclear stop (owner only)\n\n"
        "🌐 𝐆𝐋𝐎𝐁𝐀𝐋 𝐂𝐎𝐍𝐓𝐑𝐎𝐋\n"
        "├ /g <cmd> <text> — Run cmd in ALL groups\n"
        "├ /gspam <text> — Spam in ALL groups\n"
        "├ /gnc <text> — NC in ALL groups\n"
        "├ /gpfp — PFP in ALL groups\n"
        "└ /gstop — Stop everything globally\n\n"
        "🤖 𝐁𝐎𝐓 𝐌𝐀𝐍𝐀𝐆𝐄𝐑\n"
        "├ /addtoken <token> — Add new bot live\n"
        "├ /bots — List all active bots\n"
        "├ /removebot <id> — Remove a bot\n"
        "├ /addbot — Promote bots admin (this GC)\n"
        "└ /gaddbot — Promote bots in ALL groups\n\n"
        "🏠 𝐆𝐑𝐎𝐔𝐏 𝐒𝐄𝐓𝐔𝐏\n"
        "├ /joinlink <link> — All bots join via link\n"
        "├ /setupgc — Setup this GC (promote bots)\n"
        "├ /setname <name> — Set name for ALL bots\n"
        "├ /setpfp — Set group photo in ALL chats (reply photo)\n"
        "└ /setbotpfp — Set profile photo for ALL bots (reply photo)\n\n"
        "🛠️ 𝐓𝐄𝐋𝐄𝐓𝐇𝐎𝐍 𝐔𝐒𝐄𝐑 𝐀𝐂𝐂𝐎𝐔𝐍𝐓\n"
        "├ /login — Login user account (BotFather features)\n"
        "├ /gensession — Same as /login\n"
        "├ /userstatus — Check user account status\n"
        "├ /creategc <name> — Create GC + add bots + promote\n"
        "├ /addpromote — Add & promote bots to current GC\n"
        "└ /gclink — Get invite link\n\n"
        "📊 𝐒𝐓𝐀𝐓𝐒\n"
        "├ /status — Bot status\n"
        "├ /dashboard — Live dashboard\n"
        "├ /perf — Performance stats\n"
        "└ /rlstats — Rate limit stats\n\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤\n"
        "⚡ भगवान कृष | /menu for main panel\n"
        "¤═══¤۩❦۩═══════۩❦۩¤═══¤"
    )
    if update.message:
        await _send_with_photo(
            update.message, text,
            short_header="𖤍 𝐒𝐀𝐒𝐔𝐊𝐄 𝐕30 — 𝐅𝐔𝐋𝐋 𝐂𝐌𝐃 𝐋𝐈𝐒𝐓 𖤍"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🚀 रूलर बोट 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 🚀

💬 𝐒𝐏𝐀𝐌
/spam <text> — Spam loop
/imagespam — Image spam (reply photo)
/raidspam — Raid spam
/gspam <text> — Global spam
+slide <text> — Reply-bomb with all bots + modern symbols (reply to a message)
/Stopspm — Stop spam

🏷️ 𝐍𝐀𝐌𝐄 𝐂𝐇𝐀𝐍𝐆𝐄𝐑 (STEADYNC)
/nc <text> — NC loop
/gcnc <name> — GCNC loop
/godspeed <text> — Ultra fast NC
/ncbaap <name> — Speed NC
/customnc <name> — Custom NC
+sasukenc <text> — SasukeNC
+sasnc <text> — SASNC ultra smooth
+sasmaxnc <text> — SASMAXNC 💀 HYPERFIRE + 50-symbol pool
+smoothsas <text> — 🌊 Smooth SAS (constant · zero jitter · no flood pauses)
+ultranc <text> — HYPERFIRE ultra (fire-and-forget)
/gnc <text> — Global NC
/ncsteady | /ncfast | /ncburst — Speed modes
/stopnc — Stop NC

📸 𝐏𝐅𝐏
/changepfp — PFP loop (reply photo)
/gpfp — Global PFP (reply photo)
/Stoppfp — Stop PFP

🔁 𝐂𝐎𝐌𝐁𝐎𝐒
/spnc <text> — Spam + NC
/ncpfp <text> — NC + PFP
/all <text> — SP+NC+PFP 💀

⚡ 𝐒𝐓𝐎𝐏
/stop — Stop ALL in THIS chat
/gstop — Stop ALL globally
/dynstop — Nuclear stop

📊 𝐒𝐓𝐀𝐓𝐒
/status /dashboard /perf /rlstats
"""
    if update.message:
        await _send_with_photo(
            update.message, text.strip(),
            short_header="🚀 Rᴜʟᴇʀ ~ 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄 🚀"
        )


# ================= SPAM =================
async def spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /spam <text>")
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    message = " ".join(context.args) if context.args else ""

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            text_to_send = vary_message(message)
            await safe_api_request(context.bot.send_message, chat_id, text_to_send, chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id)))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "spam", worker)
    await update.message.reply_text("𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🐖")


async def raidspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            msg = vary_message(random.choice(SPAM_TEXTS))
            await safe_api_request(context.bot.send_message, chat_id, msg, chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id)))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "spam", worker)
    await update.message.reply_text("🚀 𝐑𝐀𝐈𝐃 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🚀")


async def stop_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if await task_controller.stop_task(update.effective_chat.id, "spam"):
        await update.message.reply_text("🛑 𝐒𝐏𝐀𝐌 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


async def imagespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        if update.message:
            return await update.message.reply_text("Reply to a photo!")
        return
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    photo = update.message.reply_to_message.photo[-1].file_id

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            await safe_api_request(context.bot.send_photo, chat_id, photo=photo, chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id)))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "imagespam", worker)
    await update.message.reply_text("🖼️ 𝐈𝐌𝐀𝐆𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃")


# ================= STEADYNC NAME CHANGE COMMANDS =================
# ALL NC commands use the same _steadync_engine — zero jitter, instant stop,
# no background task leaks, no create_task pipeline.

async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /nc <text>")
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    base = " ".join(context.args) if context.args else ""
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = get_nc_delay(chat_id)

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    mode = nc_mode.get(chat_id, "steady").upper()
    await update.message.reply_text(
        f"🚀 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐖𝐈𝐓𝐇 {len(bots)} 𝐁𝐎𝐓𝐒 🚀\n"
        f"Mode: {mode} | Delay: {delay}s"
    )


async def stop_nc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if await task_controller.stop_task(update.effective_chat.id, "nc"):
        await update.message.reply_text("🛑 𝐍𝐂 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


async def gcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /gcnc <name>")
    if not update.effective_chat or not update.message:
        return
    base = " ".join(context.args)
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = get_nc_delay(chat_id)

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    mode = nc_mode.get(chat_id, "steady").upper()
    await update.message.reply_text(
        f"𝐆𝐂𝐍𝐂 𝐋𝐎𝐎𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 💀 ({len(bots)} BOTS)\n"
        f"Mode: {mode} | Delay: {delay}s"
    )


async def sasukenc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+sasukenc"):
        base = raw_text[len("+sasukenc"):].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +sasukenc TEXT")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = get_nc_delay(chat_id)

    def make_name():
        emoji = "".join(random.choices(_SASUKENC_EMOJIS, k=random.randint(3, 5)))
        return f"{base}═══¤۩❦۩¤═══{emoji}"

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    preview = "".join(random.choices(_SASUKENC_EMOJIS, k=4))
    mode = nc_mode.get(chat_id, "steady").upper()
    await update.message.reply_text(
        f"⚡Rᴜʟᴇʀ 𝐍𝐂 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃⚡\n"
        f"Template: {base}═══¤۩❦۩¤═══{preview}\n"
        f"Bots: {len(bots)} | Mode: {mode} ✅"
    )


async def ncbaap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /ncbaap <name>")
    if not update.effective_chat or not update.message:
        return
    base = " ".join(context.args)
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = get_nc_delay(chat_id)

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    mode = nc_mode.get(chat_id, "steady").upper()
    await update.message.reply_text(
        f"💀🔥 NCBAAP ACTIVATED ({len(bots)} BOTS)\n"
        f"Mode: {mode} | Delay: {delay}s"
    )


async def godspeed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /godspeed <text>")
    if not update.effective_chat or not update.message:
        return
    base = " ".join(context.args)
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    # godspeed always uses fast delay
    delay = NC_SPEED_FAST

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def godspeed_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", godspeed_loop)
    await update.message.reply_text(
        f"⚡️💀 𝐆𝐎𝐃𝐒𝐏𝐄𝐄𝐃 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃 💀⚡️\n"
        f"Bots: {len(bots)} | Mode: FAST | Delay: {delay}s\n"
        f"Stop: /stopnc or /stop"
    )


async def customnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /customnc <name>")
    if not update.effective_chat or not update.message:
        return
    base = " ".join(context.args)
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = get_nc_delay(chat_id)
    _idx = [0]

    def make_name():
        nc_text_template = NC_TEXTS[_idx[0] % len(NC_TEXTS)]
        _idx[0] += 1
        return nc_text_template.format(text=base)

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    mode = nc_mode.get(chat_id, "steady").upper()
    await update.message.reply_text(
        f"✨ 𝐂𝐔𝐒𝐓𝐎𝐌 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 ({len(bots)} bots)\n"
        f"Mode: {mode} | Delay: {delay}s"
    )


async def sasnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+sasnc"):
        base = raw_text[len("+sasnc"):].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +sasnc TEXT")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    # SASNC always runs at BURST speed (zero delay) — maximum smoothness
    delay = NC_SPEED_BURST

    # Never repeat the same symbol twice — Telegram ignores duplicate name changes
    _last = [None]
    def make_name():
        available = [s for s in _SASNC_SYMBOLS if s != _last[0]]
        symbol = random.choice(available) if available else _SASNC_SYMBOLS[0]
        _last[0] = symbol
        return f"{base} {symbol}"

    async def sasnc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", sasnc_loop)
    prev = random.choice(_SASNC_SYMBOLS)
    await update.message.reply_text(
        f"⚡ Rᴜʟᴇ 𝐍𝐂 𝐕𝟐 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃 ⚡\n"
        f"Text: {base} {prev}\n"
        f"Bots: {len(bots)} | Mode: BURST | No lag ✅\n"
        f"Stop: /stop"
    )


# ================= NC SPEED MODE COMMANDS =================
async def nc_set_steady(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    nc_mode[update.effective_chat.id] = "steady"
    await update.message.reply_text(
        f"🌊 NC Mode: STEADY — Pipeline V2 active\n10 bots firing independently — max throughput"
    )


async def nc_set_fast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    nc_mode[update.effective_chat.id] = "fast"
    await update.message.reply_text(
        f"⚡ NC Mode: FAST — Pipeline V2 active\n10 bots firing independently — max throughput"
    )


async def nc_set_ultra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    nc_mode[update.effective_chat.id] = "ultra"
    await update.message.reply_text(
        f"🔥 NC Mode: ULTRA — Pipeline V2 active\n10 bots firing independently — max throughput"
    )


async def nc_set_burst(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    nc_mode[update.effective_chat.id] = "burst"
    await update.message.reply_text(
        "💥 NC Mode: BURST — Pipeline V2\n10 bots firing simultaneously — MAXIMUM SPEED ☠️"
    )


# ================= STEADYNC V2 PLUS-PREFIX COMMANDS =================
# +nc       → steady mode NC
# +fastnc   → fast mode NC
# +ultranc  → ultra mode NC
# +burstnc  → burst mode NC (no delay)
# +sasnc    → styled ultra mode NC (already defined above, handles "+sasnc" prefix)

async def plus_nc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +nc <text> — Start STEADY NC (50ms delay, smooth)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+nc"):
        base = raw_text[3:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +nc <text>")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = NC_SPEED_STEADY

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"🌊 𝐒𝐓𝐄𝐀𝐃𝐘 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 ({len(bots)} bots)\n"
        f"Delay: {delay}s | Stop: /stop"
    )


async def plus_fastnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +fastnc <text> — Start FAST NC (40ms delay)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+fastnc"):
        base = raw_text[7:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +fastnc <text>")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = NC_SPEED_FAST

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"⚡ 𝐅𝐀𝐒𝐓 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 ({len(bots)} bots)\n"
        f"Delay: {delay}s | Stop: /stop"
    )


async def plus_ultranc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +ultranc <text> — HYPERFIRE ultra NC (fire-and-forget, absolute max speed)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+ultranc"):
        base = raw_text[8:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +ultranc <text>")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        # HYPERFIRE: fire-and-forget — all bots barrage without awaiting responses
        await _hyperfire_engine(chat_id, bots, stop_event, make_name)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"⚡ 𝐔𝐋𝐓𝐑𝐀 𝐍𝐂 𝐇𝐘𝐏𝐄𝐑𝐅𝐈𝐑𝐄 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 ({len(bots)} bots)\n"
        f"🔥 Fire-and-forget — absolute max speed | Stop: /stop"
    )


async def plus_burstnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +burstnc <text> — Start BURST NC (no delay, maximum speed, proper stop)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+burstnc"):
        base = raw_text[8:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +burstnc <text>")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]
    delay = NC_SPEED_BURST

    def make_name():
        template = random.choice(GODTAMP)
        nc_text = random.choice(GOD_TEXT)
        return template.format(text=f"{base} {nc_text}")

    async def nc_loop(stop_event: asyncio.Event):
        await _steadync_engine(chat_id, bots, stop_event, make_name, delay)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"💥 𝐁𝐔𝐑𝐒𝐓 𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 ({len(bots)} bots)\n"
        f"No delay — max speed | Stop: /stop"
    )


async def plus_sasmaxnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +sasmaxnc <text> — SASNC symbols + HYPERFIRE engine = absolute maximum NC.
    Combines rotating 50-symbol SASNC pool (no-repeat guard) with fire-and-forget
    parallel barrage across all bots.  Fastest possible rename rate.
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+sasmaxnc"):
        base = raw_text[9:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +sasmaxnc <text>")
    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]

    # No-repeat tracker shared across all bot workers
    _last = [""]
    _sym_pool = list(_SASNC_SYMBOLS)  # 50 symbols

    def make_name():
        for _ in range(len(_sym_pool)):
            sym = random.choice(_sym_pool)
            candidate = f"{sym} {base} {sym}"[:255]
            if candidate != _last[0]:
                _last[0] = candidate
                return candidate
        # Fallback: force-unique with random suffix
        sym = random.choice(_sym_pool)
        name = f"{sym} {base} {sym} {random.randint(0,9)}"[:255]
        _last[0] = name
        return name

    async def nc_loop(stop_event: asyncio.Event):
        await _hyperfire_engine(chat_id, bots, stop_event, make_name)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"💀 Rᴜʟᴇʀ 𝐌𝐀𝐗𝐍𝐂 𝐇𝐘𝐏𝐄𝐑𝐅𝐈𝐑𝐄 𝐀𝐂𝐓𝐈𝐕𝐄 ({len(bots)} bots)\n"
        f"⚡ 50-symbol pool · fire-and-forget · absolute max | Stop: /stop"
    )


async def plus_smoothsas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +smoothsas <text>
    ─────────────────────────────────────────────────────────
    SMOOTH SAS NC — constant, jitter-free, flood-proof.

    Uses the HyperRateLimiter + staggered startup to maintain
    a perfectly even rename stream. Looks like the group title
    changes naturally with zero stoppiness or burst-pause cycles.

    Speed feel: moderate-fast (not as violent as +ultranc)
    but 100% CONTINUOUS — no rate limit pauses visible.

    Symbol pool: 50 SASNC symbols, no-repeat guard.
    Rate: ~33 renames/sec across 10 bots (self-tuning).
    ─────────────────────────────────────────────────────────
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    if not _is_primary_bot(context):
        return
    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+smoothsas"):
        base = raw_text[10:].strip()
    elif context.args:
        base = " ".join(context.args)
    else:
        base = ""
    if not base:
        return await update.message.reply_text("Usage: +smoothsas <text>")

    chat_id = update.effective_chat.id
    bots = [b for b in all_bot_instances if b is not None] or [context.bot]

    # No-repeat tracker — prevents Telegram "message not modified" rejections
    _last = [""]
    _sym_pool = list(_SASNC_SYMBOLS)  # 50 symbols

    def make_name():
        for _ in range(len(_sym_pool)):
            sym = random.choice(_sym_pool)
            candidate = f"{sym} {base} {sym}"[:255]
            if candidate != _last[0]:
                _last[0] = candidate
                return candidate
        # Absolute fallback: append tiny rotating suffix
        sym = random.choice(_sym_pool)
        name = f"{sym} {base} {sym} ·"[:255]
        _last[0] = name
        return name

    async def nc_loop(stop_event: asyncio.Event):
        await _smoothsas_engine(chat_id, bots, stop_event, make_name)

    await task_controller.start_task(chat_id, "nc", nc_loop)
    await update.message.reply_text(
        f"🌊 𝐒𝐌𝐎𝐎𝐓𝐇 𝙍𝙐𝙇𝙀 𝐀𝐂𝐓𝐈𝐕𝐄 ({len(bots)} bots)\n"
        f"✨ Smooth · constant · zero jitter · no flood pauses\n"
        f"⚡ ~5 renames/sec · self-healing after any flood | Stop: /stop"
    )


# ================= PFP =================
async def change_pfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        if update.message:
            return await update.message.reply_text("Reply to a photo!")
        return
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    try:
        f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        b = await f.download_as_bytearray()
    except:
        if update.message:
            await update.message.reply_text("Failed to download photo.")
        return

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            await safe_api_request(context.bot.set_chat_photo, chat_id, photo=bytes(b), chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 2.5))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "pfp", worker)
    await update.message.reply_text("📸 𝐏𝐅𝐏 𝐋𝐎𝐎𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃")


# ================= COMBOS =================
async def spnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /spnc <text>")
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    base = " ".join(context.args) if context.args else ""

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            spam_msg = vary_message(random.choice(SPAM_TEXTS))
            template = random.choice(GODTAMP)
            nc_text = random.choice(GOD_TEXT)
            name = template.format(text=f"{base} {nc_text}")[:252]
            tasks = [
                safe_api_request(context.bot.send_message, chat_id, f"{base}\n{spam_msg}", chat_id=chat_id),
                safe_api_request(context.bot.set_chat_title, chat_id, name, chat_id=chat_id),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 1.5))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "spnc", worker)
    await update.message.reply_text("🔁 SPNC 𝐒𝐏𝐀𝐌+𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🌻")


async def stop_spnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if await task_controller.stop_task(update.effective_chat.id, "spnc"):
        await update.message.reply_text("🛑 𝐒𝐏𝐍𝐂 𝐒𝐓𝐎𝐏𝐏𝐄𝐃 🌷")


async def all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    base = " ".join(context.args) if context.args else ""
    b = None
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        try:
            f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
            b = await f.download_as_bytearray()
        except:
            pass

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            template = random.choice(GODTAMP)
            nc_text = random.choice(GOD_TEXT)
            name = template.format(text=f"{base} {nc_text}")[:252]
            spam_msg = vary_message(random.choice(SPAM_TEXTS))
            tasks = [
                safe_api_request(context.bot.send_message, chat_id, f"{base}\n{spam_msg}" if base else spam_msg, chat_id=chat_id),
                safe_api_request(context.bot.set_chat_title, chat_id, name, chat_id=chat_id),
            ]
            if b:
                tasks.append(safe_api_request(context.bot.set_chat_photo, chat_id, photo=bytes(b), chat_id=chat_id))
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 1.5))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "all", worker)
    await update.message.reply_text("💀 ALL 𝐍𝐂+𝐒𝐏𝐀𝐌+𝐏𝐅𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🚀")


async def ncpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        if update.message:
            return await update.message.reply_text("Reply to a photo for PFP loop!")
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    base = " ".join(context.args) if context.args else ""
    try:
        f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        b = await f.download_as_bytearray()
    except:
        if update.message:
            await update.message.reply_text("Failed to download photo.")
        return

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            template = random.choice(GODTAMP)
            nc_text = random.choice(GOD_TEXT)
            name = template.format(text=f"{base} {nc_text}")[:252]
            tasks = [
                safe_api_request(context.bot.set_chat_title, chat_id, name, chat_id=chat_id),
                safe_api_request(context.bot.set_chat_photo, chat_id, photo=bytes(b), chat_id=chat_id),
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 2.0))
            except asyncio.TimeoutError:
                continue
            else:
                break

    await task_controller.start_task(chat_id, "ncpfp", worker)
    await update.message.reply_text("📸🏷️ NCPFP 𝐍𝐂+𝐏𝐅𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🚀")


async def stop_ncpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.message:
        return
    if await task_controller.stop_task(update.effective_chat.id, "ncpfp"):
        await update.message.reply_text("🛑 𝐍𝐂𝐏𝐅𝐏 𝐒𝐓𝐎𝐏𝐏𝐄𝐃")


# ================= STOP COMMANDS =================
async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    # All bots stop tasks — only primary bot replies to avoid spam
    count = await task_controller.stop_all_for_chat(chat_id)
    if chat_id in slide_reply_targets:
        del slide_reply_targets[chat_id]
    if not _is_primary_bot(context):
        return
    await update.message.reply_text(
        f"🛑 **𝐒𝐓𝐎𝐏𝐏𝐄𝐃 {count} 𝐓𝐀𝐒𝐊𝐒 𝐈𝐍 𝐓𝐇𝐈𝐒 𝐂𝐇𝐀𝐓**"
        if count else "🛑 **𝐒𝐓𝐎𝐏 𝐒𝐄𝐍𝐓 — 𝐀𝐋𝐋 𝐁𝐎𝐓𝐒 𝐇𝐀𝐋𝐓𝐄𝐃**",
        parse_mode="Markdown"
    )


async def dynstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    if not update.message:
        return
    count = await task_controller.stop_all()
    slide_reply_targets.clear()
    try:
        await update.message.reply_text(
            f"🛑 **DYNSTOP: ALL {count} TASKS STOPPED GLOBALLY.**",
            parse_mode="Markdown"
        )
    except:
        pass


async def stop_all_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    count = await task_controller.stop_all_for_chat(chat_id)
    if not _is_primary_bot(context):
        return
    try:
        await update.message.reply_text(
            f"🛑 **𝐕30 𝐒𝐓𝐎𝐏𝐏𝐄𝐃 {count} 𝐓𝐀𝐒𝐊𝐒**",
            parse_mode="Markdown"
        )
    except:
        pass


# ================= GLOBAL COMMANDS =================
async def gstop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    count = await task_controller.stop_all()
    slide_reply_targets.clear()
    if not _is_primary_bot(context):
        return
    try:
        await update.message.reply_text(
            f"🛑 **𝐆𝐒𝐓𝐎𝐏: ALL {count} TASKS STOPPED GLOBALLY ☠️**",
            parse_mode="Markdown"
        )
    except:
        pass


async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    prefix = f"{chat_id}_"
    keys_before = [k for k in list(task_controller.tasks.keys()) + list(task_controller.events.keys()) if k.startswith(prefix)]
    task_types = sorted(set(k.split("_", 1)[1] for k in keys_before))
    for key in list(task_controller.events.keys()):
        if key.startswith(prefix):
            task_controller.events[key].set()
    for key in list(task_controller.tasks.keys()):
        if key.startswith(prefix):
            t = task_controller.tasks[key]
            if not t.done():
                t.cancel()
    for key in list(task_controller.tasks.keys()):
        if key.startswith(prefix):
            task_controller.tasks.pop(key, None)
            task_controller.events.pop(key, None)
            task_controller.task_times.pop(key, None)
    slide_reply_targets.pop(chat_id, None)
    count = len(task_types)
    if count:
        killed_list = "\n".join(f"  ☠️ `{t}`" for t in task_types)
        msg = f"💀 **𝐊𝐈𝐋𝐋𝐄𝐃 {count} 𝐓𝐀𝐒𝐊𝐒 𝐈𝐍 𝐓𝐇𝐈𝐒 𝐂𝐇𝐀𝐓**\n{killed_list}"
    else:
        msg = "❌ **𝐍𝐎 𝐀𝐂𝐓𝐈𝐕𝐄 𝐓𝐀𝐒𝐊𝐒 𝐓𝐎 𝐊𝐈𝐋𝐋**"
    try:
        await update.message.reply_text(msg, parse_mode="Markdown")
    except:
        pass


async def gkill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    task_types_snapshot = sorted(set(k.split("_", 1)[1] for k in task_controller.tasks.keys()))
    chats_hit = sorted(set(k.split("_", 1)[0] for k in task_controller.tasks.keys()))
    count = len([t for t in task_controller.tasks.values() if not t.done()])
    for event in list(task_controller.events.values()):
        event.set()
    for task in list(task_controller.tasks.values()):
        if not task.done():
            task.cancel()
    task_controller.tasks.clear()
    task_controller.events.clear()
    task_controller.task_times.clear()
    slide_reply_targets.clear()
    if count:
        types_str = "  " + "  |  ".join(task_types_snapshot) if task_types_snapshot else "unknown"
        msg = (
            f"☠️ **𝐆𝐋𝐎𝐁𝐀𝐋 𝐊𝐈𝐋𝐋 𝐄𝐗𝐄𝐂𝐔𝐓𝐄𝐃** ☠️\n"
            f"💀 Killed: **{count} tasks** across **{len(chats_hit)} chats**\n"
            f"📋 Types: `{types_str}`"
        )
    else:
        msg = "❌ **𝐍𝐎 𝐓𝐀𝐒𝐊𝐒 𝐑𝐔𝐍𝐍𝐈𝐍𝐆 𝐆𝐋𝐎𝐁𝐀𝐋𝐋𝐘**"
    try:
        await update.message.reply_text(msg, parse_mode="Markdown")
    except:
        pass


async def gspam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /gspam <text>")
    text = " ".join(context.args)
    chats = list(known_chats)
    if not chats:
        if update.message:
            await update.message.reply_text("❌ No known groups!")
        return
    bots = all_bot_instances or [context.bot]
    num_bots = len(bots)

    async def worker_for_chat(stop_event: asyncio.Event, chat_id: int, bot):
        while not stop_event.is_set():
            await safe_api_request(bot.send_message, chat_id, vary_message(text), chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id)))
            except asyncio.TimeoutError:
                continue
            else:
                break

    async def global_coordinator(stop_event: asyncio.Event):
        tasks = []
        for idx, chat_id in enumerate(chats):
            bot = bots[idx % num_bots]
            tasks.append(asyncio.create_task(worker_for_chat(stop_event, chat_id, bot)))
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            await asyncio.gather(*batch, return_exceptions=True)

    global_chat_id = update.effective_chat.id if update.effective_chat else 0
    await task_controller.start_task(global_chat_id, "gspam", global_coordinator)
    if update.message:
        await update.message.reply_text(f"🌐 𝐆𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐈𝐍 {len(chats)} 𝐆𝐑𝐎𝐔𝐏𝐒 ⚡")


async def gnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /gnc <text>")
    base = " ".join(context.args)
    chats = list(known_chats)
    if not chats:
        if update.message:
            await update.message.reply_text("❌ No known groups!")
        return
    bots = all_bot_instances or [context.bot]
    num_bots = len(bots)

    async def nc_in_chat(stop_event: asyncio.Event, chat_id: int, bot):
        while not stop_event.is_set():
            template = random.choice(GODTAMP)
            nc_text = random.choice(GOD_TEXT)
            name = template.format(text=f"{base} {nc_text}")[:255]
            await safe_api_request(bot.set_chat_title, chat_id, name, chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 1.0))
            except asyncio.TimeoutError:
                continue
            else:
                break

    async def global_coordinator(stop_event: asyncio.Event):
        tasks = []
        for idx, chat_id in enumerate(chats):
            bot = bots[idx % num_bots]
            tasks.append(asyncio.create_task(nc_in_chat(stop_event, chat_id, bot)))
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            await asyncio.gather(*batch, return_exceptions=True)

    global_chat_id = update.effective_chat.id if update.effective_chat else 0
    await task_controller.start_task(global_chat_id, "gnc", global_coordinator)
    if update.message:
        await update.message.reply_text(f"🌐 𝐆𝐍𝐂 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐈𝐍 {len(chats)} 𝐆𝐑𝐎𝐔𝐏𝐒 ⚡")


async def gpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.reply_to_message or not update.message.reply_to_message.photo:
        if update.message:
            return await update.message.reply_text("Reply to a photo!")
        return
    chats = list(known_chats)
    if not chats:
        if update.message:
            await update.message.reply_text("❌ No known groups!")
        return
    try:
        f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        b = await f.download_as_bytearray()
    except:
        if update.message:
            await update.message.reply_text("Failed to download photo.")
        return
    bots = all_bot_instances or [context.bot]
    num_bots = len(bots)

    async def pfp_in_chat(stop_event: asyncio.Event, chat_id: int, bot):
        while not stop_event.is_set():
            await safe_api_request(bot.set_chat_photo, chat_id, photo=bytes(b), chat_id=chat_id)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id) + 2.5))
            except asyncio.TimeoutError:
                continue
            else:
                break

    async def global_coordinator(stop_event: asyncio.Event):
        tasks = []
        for idx, chat_id in enumerate(chats):
            bot = bots[idx % num_bots]
            tasks.append(asyncio.create_task(pfp_in_chat(stop_event, chat_id, bot)))
        for i in range(0, len(tasks), BATCH_SIZE):
            batch = tasks[i:i + BATCH_SIZE]
            await asyncio.gather(*batch, return_exceptions=True)

    global_chat_id = update.effective_chat.id if update.effective_chat else 0
    await task_controller.start_task(global_chat_id, "gpfp", global_coordinator)
    if update.message:
        await update.message.reply_text(f"📸 𝐆𝐏𝐅𝐏 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐈𝐍 {len(chats)} 𝐆𝐑𝐎𝐔𝐏𝐒 ⚡")


async def execute_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "Usage: /g <command> [args]\n"
                "NC: /g nc <text> | /g fastnc <text> | /g ultranc <text> | /g burstnc <text> | /g sasnc <text>\n"
                "Spam: /g spam <text>\n"
                "Stop: /g stop"
            )
        return
    cmd = context.args[0].lower()
    args = context.args[1:]
    chats = list(known_chats)
    if not chats:
        if update.message:
            await update.message.reply_text("❌ No known groups!")
        return
    bots = all_bot_instances or [context.bot]
    num_bots = len(bots)
    global_chat_id = update.effective_chat.id if update.effective_chat else 0

    if cmd == "stop":
        count = await task_controller.stop_all()
        if update.message:
            await update.message.reply_text(f"🛑 Global stop: {count} tasks cancelled.")
        return

    if cmd == "spam" and args:
        text = " ".join(args)

        async def global_spam(stop_event: asyncio.Event):
            inner_tasks = []
            for idx, chat_id in enumerate(chats):
                bot = bots[idx % num_bots]
                async def _spam(sid=chat_id, b=bot):
                    while not stop_event.is_set():
                        await safe_api_request(b.send_message, sid, vary_message(text), chat_id=sid)
                        try:
                            await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(sid)))
                        except asyncio.TimeoutError:
                            continue
                        else:
                            break
                inner_tasks.append(asyncio.create_task(_spam()))
            for i in range(0, len(inner_tasks), BATCH_SIZE):
                await asyncio.gather(*inner_tasks[i:i + BATCH_SIZE], return_exceptions=True)

        await task_controller.start_task(global_chat_id, "gspam", global_spam)
        if update.message:
            await update.message.reply_text(f"🌐 Global spam started in {len(chats)} groups.")
        return

    # STEADYNC V2 — Global NC commands
    _nc_delay_map = {
        "nc": NC_SPEED_STEADY,
        "fastnc": NC_SPEED_FAST,
        "ultranc": NC_SPEED_ULTRA,
        "burstnc": NC_SPEED_BURST,
        "sasnc": NC_SPEED_ULTRA,  # sasnc uses ultra delay
        "sasmaxnc": NC_SPEED_BURST,  # sasmaxnc = max speed
    }
    if cmd in _nc_delay_map and args:
        base = " ".join(args)
        g_delay = _nc_delay_map[cmd]

        def _make_global_name_factory(text, mode):
            _last_sym = [""]
            def make_name():
                if mode in ("sasnc", "sasmaxnc"):
                    for _ in range(len(_SASNC_SYMBOLS)):
                        symbol = random.choice(_SASNC_SYMBOLS)
                        candidate = f"{symbol} {text} {symbol}"
                        if candidate != _last_sym[0]:
                            _last_sym[0] = candidate
                            return candidate
                    return f"{random.choice(_SASNC_SYMBOLS)} {text} {random.randint(0,9)}"
                template = random.choice(GODTAMP)
                nc_text = random.choice(GOD_TEXT)
                return template.format(text=f"{text} {nc_text}")
            return make_name

        async def global_nc(stop_event: asyncio.Event, _base=base, _delay=g_delay, _cmd=cmd):
            name_factory = _make_global_name_factory(_base, _cmd)
            # Each chat gets its own per-bot pipeline with flood bypass
            # Uses _steadync_engine so flood bypass is automatic for every group
            chat_tasks = []
            for cid in chats:
                chat_bots = [b for b in bots if b is not None] or [context.bot]
                async def _nc_for_chat(chat_id=cid, cbots=chat_bots):
                    # Independent per-bot workers for this chat — flood bypass built-in
                    async def _per_bot(bot):
                        bot_id = getattr(bot, "id", id(bot))
                        while not stop_event.is_set():
                            if _flood_tracker.is_flooded(bot_id):
                                wait = _flood_tracker.remaining(bot_id)
                                try:
                                    await asyncio.wait_for(stop_event.wait(),
                                                           timeout=min(wait, 0.25))
                                except asyncio.TimeoutError:
                                    pass
                                continue
                            try:
                                name = name_factory()[:255]
                                await bot.set_chat_title(chat_id, name)
                            except RetryAfter as e:
                                _flood_tracker.mark_flooded(bot_id, e.retry_after)
                                continue
                            except (BadRequest, Forbidden):
                                if stop_event.is_set():
                                    break
                                await asyncio.sleep(0.3)
                                continue
                            except (TimedOut, NetworkError):
                                if stop_event.is_set():
                                    break
                                await asyncio.sleep(0.5)
                                continue
                            except Exception:
                                if stop_event.is_set():
                                    break
                                await asyncio.sleep(0.1)
                                continue
                            if stop_event.is_set():
                                break
                            if _delay > 0:
                                try:
                                    await asyncio.wait_for(stop_event.wait(), timeout=_delay)
                                except asyncio.TimeoutError:
                                    continue
                                else:
                                    break
                            else:
                                await asyncio.sleep(0)
                    bot_workers = [asyncio.create_task(_per_bot(b)) for b in cbots]
                    try:
                        await asyncio.gather(*bot_workers, return_exceptions=True)
                    finally:
                        for w in bot_workers:
                            if not w.done():
                                w.cancel()
                chat_tasks.append(asyncio.create_task(_nc_for_chat()))
            await asyncio.gather(*chat_tasks, return_exceptions=True)

        await task_controller.start_task(global_chat_id, "gnc", global_nc)
        mode_label = cmd.upper()
        if update.message:
            await update.message.reply_text(
                f"🌐 𝐆𝐋𝐎𝐁𝐀𝐋 {mode_label} 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 𝐈𝐍 {len(chats)} 𝐆𝐑𝐎𝐔𝐏𝐒 ⚡\n"
                f"Delay: {g_delay}s | Stop: /gstop"
            )
        return

    if update.message:
        await update.message.reply_text(
            f"Usage: /g <command> [args]\n"
            f"NC: /g nc | /g fastnc | /g ultranc | /g burstnc | /g sasnc | /g sasmaxnc <text>\n"
            f"Spam: /g spam <text> | Stop: /g stop"
        )


# ================= BOT MANAGER COMMANDS =================
async def addtoken_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /addtoken <bot_token>")
    token = context.args[0].strip()
    if update.message:
        await update.message.reply_text("🔄 Validating and adding bot...")
    try:
        from telegram.request import HTTPXRequest
        req = HTTPXRequest(connection_pool_size=10, read_timeout=10, write_timeout=10, connect_timeout=10)
        new_app = Application.builder().token(token).request(req).build()
        await new_app.initialize()
        await new_app.start()
        me = await new_app.bot.get_me()
        _register_handlers(new_app)
        if new_app.updater:
            await new_app.updater.start_polling(drop_pending_updates=True)
        all_bot_instances.append(new_app.bot)
        all_apps.append(new_app)
        bot_manager.add_bot_info(token, new_app, new_app.bot, me.username, me.id)
        if token not in extra_tokens:
            extra_tokens.append(token)
            save_extra_tokens(extra_tokens)
        if update.message:
            await update.message.reply_text(f"✅ Bot @{me.username} (ID: {me.id}) added successfully!")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Failed to add bot: {e}")


async def bots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    total = len(all_bot_instances)
    bot_list = bot_manager.get_bot_list_text()
    if update.message:
        await update.message.reply_text(
            f"🤖 **ACTIVE BOTS: {total}**\n\n{bot_list}",
            parse_mode="Markdown"
        )


async def removebot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /removebot <bot_id>")
    try:
        bot_id = int(context.args[0])
        if await bot_manager.remove_bot(bot_id):
            all_bot_instances[:] = [b for b in all_bot_instances if b.id != bot_id]
            if update.message:
                await update.message.reply_text(f"✅ Bot {bot_id} removed.")
        else:
            if update.message:
                await update.message.reply_text(f"❌ Bot {bot_id} not found.")
    except Exception as e:
        if update.message:
            await update.message.reply_text(f"❌ Error: {e}")


# ================= UTILITY COMMANDS =================
async def vn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /vn <text>")
    if not update.message:
        return
    try:
        tts = gTTS(" ".join(context.args), lang='en')
        f = io.BytesIO()
        tts.write_to_fp(f)
        f.seek(0)
        await update.message.reply_voice(f, caption="🎤 Voice")
    except:
        if update.message:
            await update.message.reply_text("Error generating voice.")


async def slidespam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message or not update.message.reply_to_message:
        if update.message:
            await update.message.reply_text("Reply to a user.")
        return
    user = update.message.reply_to_message.from_user
    if not user:
        return
    target = user.id
    slide_reply_targets[target] = " ".join(context.args) if context.args else ""
    await update.message.reply_text(f"🎯 Target set: {target}")


async def slidestop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    slide_reply_targets.clear()
    if update.message:
        await update.message.reply_text("🎯 Targets cleared.")


# Modern symbol pool for +slide
_SLIDE_SYMS = [
    "꧁", "꧂", "⟡", "✦", "◈", "✧", "⊹", "✶", "⋆", "꩜",
    "⌬", "◉", "⧖", "⬡", "⬢", "⍟", "⎔", "⏣", "☽", "☾",
    "⚡", "🔥", "💫", "⚜", "🌟", "💠", "🔮", "🌀", "👑", "💎",
    "⚔", "🛡", "🎯", "🎭", "🎨", "🌸", "🦋", "🌊", "🎪", "🎬",
    "꫁", "ꫂ", "⟣", "⟢", "⟤", "⟥", "⊛", "⊜", "⍣", "⍤",
]

async def plus_slide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    +slide <text>
    ─────────────────────────────────────────────────────────
    SLIDE SPAM — reply-bomb with all bots + modern symbols.

    • Reply to any message → all bots reply to THAT message
    • Each bot picks a random modern symbol pair each time
    • Fires as fast as possible across all 10 bots in parallel
    • /stop stops it like any other task

    Example:
      +slide gn         (while replying to a user's message)
    ─────────────────────────────────────────────────────────
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not _is_primary_bot(context):
        return
    if not update.effective_chat or not update.message:
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text(
            "↩️ Reply to a message, then use +slide <text>"
        )

    raw_text = (update.message.text or "").strip()
    if raw_text.lower().startswith("+slide"):
        base = raw_text[6:].strip()
    else:
        base = " ".join(context.args) if context.args else ""
    if not base:
        return await update.message.reply_text("Usage: +slide <text>")

    chat_id      = update.effective_chat.id
    target_msg_id = update.message.reply_to_message.message_id
    bots         = [b for b in all_bot_instances if b is not None] or [context.bot]

    async def _bot_slide_worker(bot, stop_event: asyncio.Event):
        while not stop_event.is_set():
            sym1 = random.choice(_SLIDE_SYMS)
            sym2 = random.choice(_SLIDE_SYMS)
            text = f"{sym1} {base} {sym2}"
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_to_message_id=target_msg_id,
                )
            except RetryAfter as e:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=float(e.retry_after))
                except asyncio.TimeoutError:
                    pass
            except (BadRequest, Forbidden, TimedOut, NetworkError):
                pass
            except Exception:
                pass
            # Tiny pacing — readable speed, not pure fire-and-forget
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=0.05)
            except asyncio.TimeoutError:
                pass

    async def slide_loop(stop_event: asyncio.Event):
        workers = [
            asyncio.create_task(_bot_slide_worker(bot, stop_event))
            for bot in bots
        ]
        try:
            await asyncio.gather(*workers, return_exceptions=True)
        finally:
            for w in workers:
                if not w.done():
                    w.cancel()

    await task_controller.start_task(chat_id, "spam", slide_loop)
    await update.message.reply_text(
        f"⚡ 𝐒𝐋𝐈𝐃𝐄 𝐀𝐂𝐓𝐈𝐕𝐄 ({len(bots)} bots)\n"
        f"💬 Replying with modern symbols at max speed | Stop: /stop"
    )


async def speed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    if not context.args:
        return await update.message.reply_text(f"Speed: {get_delay(chat_id)}s")
    try:
        speed_settings[chat_id] = float(context.args[0])
        await update.message.reply_text(f"⚡ 𝐒𝐏𝐄𝐄𝐃 𝐒𝐄𝐓 𝐓𝐎 {context.args[0]}s")
    except:
        pass


async def delaync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /delaync <sec>")
    try:
        sec = float(context.args[0])
        nc_speeds[update.effective_chat.id] = sec
        await update.message.reply_text(f"⏱️ NC Speed set to {sec}s")
    except:
        await update.message.reply_text("Invalid value.")


async def set_godspeed_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args and update.message:
        return await update.message.reply_text("Usage: /setgodspeed <sec>")
    try:
        sec = float(context.args[0])
        nc_speeds[update.effective_chat.id] = sec
        await update.message.reply_text(f"⚡️ Godspeed delay: {sec}s")
    except:
        await update.message.reply_text("Invalid value.")


async def set_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /threads <val>")
    try:
        global max_threads
        max_threads = int(context.args[0])
        await update.message.reply_text(f"🧵 𝐓𝐇𝐑𝐄𝐀𝐃𝐒 𝐒𝐄𝐓 𝐓𝐎 {max_threads}")
    except:
        await update.message.reply_text("Invalid value.")


async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /target <name>")
    target_names[update.effective_chat.id] = " ".join(context.args)
    await update.message.reply_text(f"🎯 Target: {target_names[update.effective_chat.id]}")


async def set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if len(context.args) < 2:
        return await update.message.reply_text("Usage: /settemplate <1-N> <text>")
    try:
        idx = int(context.args[0])
        text = " ".join(context.args[1:])
        while len(spam_templates) <= idx:
            spam_templates.append("")
        spam_templates[idx] = text
        await update.message.reply_text(f"✅ Template {idx} updated.")
    except:
        await update.message.reply_text("Invalid template ID.")


async def show_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    res = "\n".join([f"{i}: {v[:50]}..." if len(v) > 50 else f"{i}: {v}" for i, v in enumerate(spam_templates)])
    await update.message.reply_text(f"📋 **SPAM TEMPLATES:**\n{res}", parse_mode="Markdown")


async def spam_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    chat_id = update.effective_chat.id
    target = target_names.get(chat_id, "Target")

    async def worker(stop_event: asyncio.Event):
        while not stop_event.is_set():
            for tmpl in spam_templates:
                if stop_event.is_set():
                    break
                msg = tmpl.replace("{text}", target)
                await safe_api_request(context.bot.send_message, chat_id, msg, chat_id=chat_id)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=max(0.02, get_delay(chat_id)))
                except asyncio.TimeoutError:
                    pass
                else:
                    break

    await task_controller.start_task(chat_id, "spam", worker)
    await update.message.reply_text("🚀 𝐒𝐄𝐐𝐔𝐄𝐍𝐂𝐄 𝐒𝐏𝐀𝐌 𝐒𝐓𝐀𝐑𝐓𝐄𝐃 🚀")


async def stop_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await task_controller.stop_task(update.effective_chat.id, "spam"):
        await update.message.reply_text("🛑 Target spam stopped.")


# ================= ADMIN =================
async def global_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    global global_mode
    global_mode = True
    await update.message.reply_text("🌐 𝐆𝐋𝐎𝐁𝐀𝐋 𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃")


async def off_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    global global_mode
    global_mode = False
    await update.message.reply_text("🌐 𝐆𝐋𝐎𝐁𝐀𝐋 𝐃𝐄𝐀𝐂𝐓𝐈𝐕𝐀𝐓𝐄𝐃")


async def activategbl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    global global_mode
    global_mode = True
    if update.message:
        await update.message.reply_text("🌍 **Global Mode ACTIVATED**", parse_mode="Markdown")


async def offgbl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    global global_mode
    global_mode = False
    if update.message:
        await update.message.reply_text("🔒 **Global Mode DEACTIVATED**", parse_mode="Markdown")


async def leave_gc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    await update.message.reply_text("𝐒𝐀𝐒𝐔𝐊𝐄 𝐏𝐀𝐏𝐀'𝐒 𝐎𝐑𝐃𝐄𝐑 𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃 🐱🚀 𝐁𝐘𝐄𝐄𝐄𝐄𝐄...🚀")
    await context.bot.leave_chat(update.effective_chat.id)


async def leave_gbl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    current = update.effective_chat.id
    count = 0
    await update.message.reply_text("𝐒𝐀𝐒𝐔𝐊𝐄 𝐏𝐀𝐏𝐀'𝐒 𝐎𝐑 𝐀𝐂𝐂𝐄𝐏𝐓𝐄𝐃 🐱🚀 𝐁𝐘𝐄𝐄𝐄𝐄𝐄...🚀")
    for cid in list(known_chats):
        if cid == current:
            continue
        try:
            await context.bot.leave_chat(cid)
            known_chats.remove(cid)
            count += 1
        except:
            pass
    save_groups(known_chats)
    await update.message.reply_text(f"✅ Left {count} other chats.")


async def leave_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    for chat_id in list(known_chats):
        asyncio.create_task(safe_api_request(context.bot.leave_chat, chat_id, chat_id=chat_id))
    known_chats.clear()
    save_groups(known_chats)
    if update.message:
        try:
            await update.message.reply_text("👋 Left all groups.")
        except:
            pass


async def show_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(f"📊 Total groups: {len(known_chats)}\nIDs: {list(known_chats)[:20]}")


async def add_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Grant sudo (admin-level bot access) to another user.

    Usage:
      /sudo           — reply to that user's message
      /sudo <user_id> — type their ID directly

    Sudo users can use ALL bot commands exactly like the owner.
    Survives bot restarts (saved to sudo_users.json).
    """
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    if not update.message:
        return

    # ── Priority 1: reply-based grant ────────────────────────────────
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        uid  = target_user.id
        name = target_user.full_name or str(uid)
        if uid == OWNER_ID:
            return await update.message.reply_text("👑 That's already the owner.")
        SUDO_USERS.add(uid)
        _save_sudo(SUDO_USERS)
        return await update.message.reply_text(
            f"✅ 𝐒𝐔𝐃𝐎 𝐆𝐑𝐀𝐍𝐓𝐄𝐃\n"
            f"👤 {name}\n"
            f"🆔 `{uid}`\n"
            f"⚡ Can now command all {len(all_bot_instances)} bots",
            parse_mode="Markdown",
        )

    # ── Priority 2: typed ID ──────────────────────────────────────────
    if context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid ID. Provide a numeric user ID.")
        if uid == OWNER_ID:
            return await update.message.reply_text("👑 That's already the owner.")
        SUDO_USERS.add(uid)
        _save_sudo(SUDO_USERS)
        return await update.message.reply_text(
            f"✅ 𝐒𝐔𝐃𝐎 𝐆𝐑𝐀𝐍𝐓𝐄𝐃 → `{uid}`",
            parse_mode="Markdown",
        )

    await update.message.reply_text(
        "↩️ Reply to a user's message with /sudo  — or use /sudo <user_id>"
    )


async def del_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Revoke sudo from a user.

    Usage:
      /delsudo           — reply to that user's message
      /delsudo <user_id> — type their ID directly
    """
    if not update.effective_user or update.effective_user.id != OWNER_ID:
        return
    if not update.message:
        return

    # ── Priority 1: reply-based revoke ───────────────────────────────
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        target_user = update.message.reply_to_message.from_user
        uid  = target_user.id
        name = target_user.full_name or str(uid)
        if uid == OWNER_ID:
            return await update.message.reply_text("👑 Can't remove the owner.")
        SUDO_USERS.discard(uid)
        _save_sudo(SUDO_USERS)
        return await update.message.reply_text(
            f"🗑️ 𝐒𝐔𝐃𝐎 𝐑𝐄𝐕𝐎𝐊𝐄𝐃\n"
            f"👤 {name}\n"
            f"🆔 `{uid}`",
            parse_mode="Markdown",
        )

    # ── Priority 2: typed ID ──────────────────────────────────────────
    if context.args:
        try:
            uid = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("❌ Invalid ID.")
        if uid == OWNER_ID:
            return await update.message.reply_text("👑 Can't remove the owner.")
        SUDO_USERS.discard(uid)
        _save_sudo(SUDO_USERS)
        return await update.message.reply_text(
            f"🗑️ Sudo revoked → `{uid}`",
            parse_mode="Markdown",
        )

    await update.message.reply_text(
        "↩️ Reply to a user's message with /delsudo  — or use /delsudo <user_id>"
    )


async def list_sudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        sudos_str = "\n".join(str(u) for u in SUDO_USERS)
        await update.message.reply_text(f"👑 **Sudos:**\n{sudos_str}", parse_mode="Markdown")


async def owner_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(f"👑 **Owner ID:** `{OWNER_ID}`", parse_mode="Markdown")


async def get_all_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(f"🤖 **Bot Count:** {len(all_bot_instances)}", parse_mode="Markdown")


async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("🟢 **𝙍𝙐𝙇𝙀𝙍 𝘽𝙊𝙏**\n⚡ Online | Ping: ~12ms", parse_mode="Markdown")


async def announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not context.args:
        return
    msg = " ".join(context.args)
    n = 0
    for cid in known_chats:
        try:
            await context.bot.send_message(cid, msg)
            n += 1
        except:
            pass
    if update.message:
        await update.message.reply_text(f"📢 Sent to {n} chats.")


# ================= STATS / DASHBOARD =================
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = int(time.time() - bot_start_time)
    chat_id = update.effective_chat.id if update.effective_chat else 0
    rl_stats = rate_limiter.get_stats_summary(chat_id) if chat_id else "N/A"
    active = task_controller.get_active_count()
    text = f"""
📊 **रूलर बोट 𝐔𝐋𝐓𝐈𝐌𝐀𝐓𝐄**
⏱️ 𝐔𝐏𝐓𝐈𝐌𝐄: {uptime}s
🤖 𝐀𝐂𝐓𝐈𝐕𝐄 𝐁𝐎𝐓𝐒: {len(all_bot_instances)}
🏃 𝐀𝐂𝐓𝐈𝐕𝐄 𝐓𝐀𝐒𝐊𝐒: {active}
🌍 𝐆𝐋𝐎𝐁𝐀𝐋 𝐌𝐎𝐃𝐄: {'ON' if global_mode else 'OFF'}
👥 Known Chats: {len(known_chats)}
📨 Msgs Sent: {perf_stats['msgs_sent']}

🛡️ **Rate Limit Bypass:**
{rl_stats}
"""
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")


async def dashboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    uptime = int(time.time() - bot_start_time)
    h, m = divmod(uptime, 3600)
    m, s = divmod(m, 60)
    active = task_controller.get_active_count()
    elapsed = time.time() - perf_stats["start_time"]
    msgs_per_sec = perf_stats["msgs_sent"] / max(1, elapsed)
    spam_tasks = len([k for k in task_controller.tasks if "spam" in k and not task_controller.tasks[k].done()])
    nc_tasks = len([k for k in task_controller.tasks if "_nc" in k and not task_controller.tasks[k].done()])
    pfp_tasks = len([k for k in task_controller.tasks if "pfp" in k and not task_controller.tasks[k].done()])
    total_msgs = perf_stats["msgs_sent"]
    failed_msgs = perf_stats["msgs_failed"]
    error_rate = (failed_msgs / max(1, total_msgs + failed_msgs)) * 100
    text = f"""
🏥 **रूलर बोट 𝐋𝐈𝐕𝐄 𝐃𝐀𝐒𝐇𝐁𝐎𝐀𝐑𝐃**

⏱️ **Uptime:** `{h:02d}h {m:02d}m {s:02d}s`
🤖 **Active Bots:** `{len(all_bot_instances)}`
👥 **Known Chats:** `{len(known_chats)}`
👑 **Admins:** `{len(SUDO_USERS)}`

📊 **LIVE ACTIVITY**
🏃 **Total Tasks:** `{active}`
💬 **Spam Loops:** `{spam_tasks}`
🏷️ **NC Loops:** `{nc_tasks}`
📸 **PFP Loops:** `{pfp_tasks}`

⚡ **PERFORMANCE**
📨 **Msgs/sec:** `{msgs_per_sec:.2f}`
✅ **Total Sent:** `{total_msgs}`
❌ **Error Rate:** `{error_rate:.1f}%`
🚦 **RL Hits:** `{perf_stats['rate_limit_hits']}`
🌍 **Global Mode:** `{'ON' if global_mode else 'OFF'}`
"""
    if update.message:
        await update.message.reply_text(text, parse_mode='Markdown')


async def ratelimit_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    stats = rate_limiter.get_chat_stats(chat_id)
    success_rate = (stats["success_count"] / max(1, stats["total_requests"])) * 100
    failures = rate_limiter.consecutive_failures.get(chat_id, 0)
    streak = rate_limiter.success_streak.get(chat_id, 0)
    text = f"""
🛡️ **𝐑𝐀𝐓𝐄 𝐋𝐈𝐌𝐈𝐓 𝐁𝐘𝐏𝐀𝐒𝐒 𝐒𝐓𝐀𝐓𝐒**

📊 **This Chat:**
├ Total Requests: {stats['total_requests']}
├ Successful: {stats['success_count']}
├ Rate Limit Hits: {stats['rate_limit_hits']}
└ Success Rate: {success_rate:.1f}%

⚡ **Performance:**
├ Adaptive Delay: {stats['adaptive_delay']:.3f}s
├ Consecutive Failures: {failures}
├ Success Streak: {streak}
└ Throttle Active: {'Yes' if rate_limiter.should_throttle(chat_id) else 'No'}
"""
    await update.message.reply_text(text, parse_mode="Markdown")


async def reset_ratelimit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    rate_limiter.chat_stats.pop(chat_id, None)
    rate_limiter.consecutive_failures[chat_id] = 0
    rate_limiter.success_streak[chat_id] = 0
    await update.message.reply_text("🔄 Rate limit stats reset!")


async def performance_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    rl_stats = rate_limiter.get_global_stats()
    uptime = int(time.time() - bot_start_time)
    h, m = divmod(uptime, 3600)
    m, s = divmod(m, 60)
    active = task_controller.get_active_count()
    text = f"""
⚡ **𝐏𝐄𝐑𝐅𝐎𝐑𝐌𝐀𝐍𝐂𝐄 𝐒𝐓𝐀𝐓𝐒**

⏱️ Uptime: {h:02d}h {m:02d}m {s:02d}s

📊 **Rate Limiter:**
├ Tracked Chats: {rl_stats['tracked_chats']}
├ Total Requests: {rl_stats['total_requests']}
├ Success Rate: {rl_stats['success_rate']:.1f}%
└ Rate Limit Hits: {rl_stats['total_rate_limits']}

🏃 **Task Engine:**
├ Active Tasks: {active}
└ Tasks Completed: {perf_stats['tasks_completed']}
"""
    await update.message.reply_text(text, parse_mode="Markdown")


# ================= USER ACCOUNT (TELETHON) =================

async def _check_user_client(update: Update) -> Any:
    client = await get_user_client()
    if client is None:
        if update.message:
            await update.message.reply_text(
                "⚠️ **User account not logged in!**\n\n"
                "Use /login to connect your Telegram account.\n"
                "This enables: create groups, change bot names & PFPs via BotFather.",
                parse_mode="Markdown"
            )
        return None
    return client


async def _botfather_set_name(client, bot_username: str, new_name: str) -> str:
    """
    Automate BotFather to change a bot's display name.
    Flow: /setname → select bot (inline btn or @username) → send new name
    Returns BotFather's confirmation text.
    """
    uname = bot_username.lstrip("@").strip()
    bf = await client.get_entity("@BotFather")
    async with client.conversation(bf, timeout=30) as conv:
        await conv.send_message("/setname")
        resp = await conv.get_response()
        # Try clicking the inline button whose text contains our bot username
        clicked = False
        if getattr(resp, "reply_markup", None) and hasattr(resp.reply_markup, "rows"):
            for row in resp.reply_markup.rows:
                for btn in row.buttons:
                    if uname.lower() in getattr(btn, "text", "").lower():
                        try:
                            await resp.click(text=btn.text)
                            clicked = True
                        except Exception:
                            pass
                        break
                if clicked:
                    break
        if not clicked:
            # Fallback: send @username as text (some BotFather versions accept this)
            await conv.send_message(f"@{uname}")
        resp2 = await conv.get_response()
        # BotFather now asks for the new name
        await conv.send_message(new_name[:64])
        resp3 = await conv.get_response()
        return resp3.text or "Done"


async def _botfather_set_pfp(client, bot_username: str, photo_bytes: bytes) -> str:
    """
    Automate BotFather to change a bot's profile photo.
    Flow: /setuserpic → select bot → send photo
    Returns BotFather's confirmation text.
    """
    import io as _io
    uname = bot_username.lstrip("@").strip()
    bf = await client.get_entity("@BotFather")
    async with client.conversation(bf, timeout=60) as conv:
        await conv.send_message("/setuserpic")
        resp = await conv.get_response()
        # Try clicking the inline button for this bot
        clicked = False
        if getattr(resp, "reply_markup", None) and hasattr(resp.reply_markup, "rows"):
            for row in resp.reply_markup.rows:
                for btn in row.buttons:
                    if uname.lower() in getattr(btn, "text", "").lower():
                        try:
                            await resp.click(text=btn.text)
                            clicked = True
                        except Exception:
                            pass
                        break
                if clicked:
                    break
        if not clicked:
            await conv.send_message(f"@{uname}")
        resp2 = await conv.get_response()
        # Send the photo
        await client.send_file(bf, _io.BytesIO(photo_bytes), force_document=False)
        resp3 = await conv.get_response()
        return resp3.text or "Done"


async def _tele_add_bot(client, entity, bot_username: str) -> bool:
    try:
        await client(InviteToChannelRequest(entity, [bot_username]))
        return True
    except Exception as e:
        err = str(e)
        if "USER_ALREADY_PARTICIPANT" in err or "already" in err.lower():
            return True
        try:
            await client(AddChatUserRequest(entity.id, bot_username, fwd_limit=50))
            return True
        except Exception as e2:
            err2 = str(e2)
            if "USER_ALREADY_PARTICIPANT" in err2 or "already" in err2.lower():
                return True
            logger.error(f"Add bot error — channel: {err[:60]} | chat: {err2[:60]}")
            raise Exception(f"channel: {err[:40]} | chat: {err2[:40]}")


async def _tele_promote_bot(client, entity, bot_username: str) -> bool:
    admin_rights = ChatAdminRights(
        change_info=True,
        delete_messages=True,
        ban_users=False,
        invite_users=True,
        pin_messages=True,
        add_admins=False,
        anonymous=False,
        manage_call=True,
        other=True,
        manage_topics=False,
    )
    try:
        await client(EditAdminRequest(
            channel=entity,
            user_id=bot_username,
            admin_rights=admin_rights,
            rank="⚡ BOT"
        ))
        return True
    except Exception as e:
        err = str(e)
        try:
            await client(TeleEditChatAdminRequest(
                chat_id=entity.id,
                user_id=bot_username,
                is_admin=True
            ))
            return True
        except Exception as e2:
            logger.error(f"Promote bot error — channel: {err[:60]} | chat: {str(e2)[:60]}")
            raise Exception(f"channel: {err[:40]} | chat: {str(e2)[:40]}")


async def userstatus_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not TELETHON_AVAILABLE:
        return await update.message.reply_text("❌ Telethon not installed.")
    missing = []
    if not TELE_API_ID:   missing.append("`TELEGRAM_API_ID`")
    if not TELE_API_HASH: missing.append("`TELEGRAM_API_HASH`")
    if not TELE_SESSION:  missing.append("`TELEGRAM_SESSION`")
    if missing:
        return await update.message.reply_text(
            f"⚠️ **User account NOT configured.**\n\nMissing:\n" +
            "\n".join(f"• {m}" for m in missing) +
            "\n\nUse /gensession for help.",
            parse_mode="Markdown"
        )
    try:
        client = await get_user_client()
        me = await client.get_me()
        await update.message.reply_text(
            f"✅ **User Account Connected**\n\n"
            f"👤 Name: {me.first_name or ''} {me.last_name or ''}\n"
            f"📱 Phone: +{me.phone}\n"
            f"🆔 ID: `{me.id}`\n"
            f"👤 Username: @{me.username or 'none'}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Connection error: {e}")


async def gensession_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not TELETHON_AVAILABLE:
        await update.message.reply_text("❌ Telethon not installed. Run: pip install telethon")
        return
    uid = update.effective_user.id
    old = _session_gen_state.pop(uid, None)
    if old and old.get("client"):
        try:
            await old["client"].disconnect()
        except Exception:
            pass
    _session_gen_state[uid] = {"state": "phone"}
    await update.message.reply_text(
        "🔑 **Login — Step 1 of 2**\n\n"
        "Send your Telegram phone number (with country code):\n"
        "Example: `+1234567890`\n\n"
        "✨ After login you can:\n"
        "• `/creategc` — Create groups\n"
        "• `/setname` — Change ALL bot names via BotFather\n"
        "• `/setbotpfp` — Set ALL bot PFPs via BotFather\n"
        "• `/addpromote` — Add & admin-promote bots\n\n"
        "_(Send /cancel to abort)_",
        parse_mode="Markdown"
    )


async def _handle_session_gen(update: Update, text: str, uid: int) -> bool:
    global TELE_SESSION, _user_client
    if uid not in _session_gen_state:
        return False
    state_data = _session_gen_state[uid]
    state = state_data["state"]
    if text.strip().lower() == "/cancel":
        client = state_data.get("client")
        if client:
            try:
                await client.disconnect()
            except Exception:
                pass
        _session_gen_state.pop(uid, None)
        await update.message.reply_text("❌ Session generation cancelled.")
        return True
    if state == "phone":
        phone = text.strip()
        await update.message.reply_text("⏳ Sending OTP to your Telegram…")
        try:
            client = TelegramClient(StringSession(), TELE_API_ID, TELE_API_HASH)
            await client.connect()
            sent = await client.send_code_request(phone)
            state_data.update({
                "state":       "code",
                "phone":       phone,
                "client":      client,
                "phone_hash":  sent.phone_code_hash,
            })
            await update.message.reply_text(
                "✅ OTP sent!\n\n"
                "**Step 2/2** — Enter the code Telegram sent you:\n"
                "Example: `12345`\n\n"
                "_(2FA password will be asked if enabled)_",
                parse_mode="Markdown"
            )
        except Exception as e:
            _session_gen_state.pop(uid, None)
            await update.message.reply_text(f"❌ Error sending OTP: {e}\n\nTry /gensession again.")
        return True
    if state == "code":
        code = text.strip().replace(" ", "")
        phone  = state_data["phone"]
        client = state_data["client"]
        try:
            await client.sign_in(phone, code, phone_code_hash=state_data["phone_hash"])
            await _save_session(update, uid, client)
        except Exception as e:
            err = str(e).lower()
            if "two-steps" in err or "password" in err or "2fa" in err or "sessionpasswordneeded" in err:
                state_data["state"] = "2fa"
                await update.message.reply_text(
                    "🔒 2FA enabled on your account.\n\nSend your **2FA password** now:",
                    parse_mode="Markdown"
                )
            else:
                _session_gen_state.pop(uid, None)
                try:
                    await client.disconnect()
                except Exception:
                    pass
                await update.message.reply_text(f"❌ Login failed: {e}\n\nTry /gensession again.")
        return True
    if state == "2fa":
        password = text.strip()
        client   = state_data["client"]
        try:
            await client.sign_in(password=password)
            await _save_session(update, uid, client)
        except Exception as e:
            _session_gen_state.pop(uid, None)
            try:
                await client.disconnect()
            except Exception:
                pass
            await update.message.reply_text(f"❌ 2FA failed: {e}\n\nTry /gensession again.")
        return True
    return False


async def _save_session(update, uid: int, client) -> None:
    global TELE_SESSION, _user_client
    session_str = client.session.save()
    _session_gen_state.pop(uid, None)
    try:
        with open(_SESSION_FILE, "w") as f:
            f.write(session_str)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not save session file: {e}")
        return
    TELE_SESSION = session_str
    if _user_client:
        try:
            await _user_client.disconnect()
        except Exception:
            pass
    _user_client = client
    me = await client.get_me()
    await update.message.reply_text(
        f"✅ **User Account Logged In & Saved!**\n\n"
        f"👤 **Name:** {me.first_name} {me.last_name or ''}".strip() + "\n"
        f"🔗 **Username:** @{me.username or 'no username'}\n"
        f"📱 **Phone:** `+{me.phone}`\n\n"
        f"💾 Session saved to disk — survives restarts.\n\n"
        f"✨ **Now enabled:**\n"
        f"• `/creategc` — Create groups with your account\n"
        f"• `/addpromote` — Add & promote bots via your account\n"
        f"• `/setname` — Change ALL bot names via BotFather\n"
        f"• `/setbotpfp` — Set ALL bot profile photos via BotFather\n"
        f"• `/gclink` — Export group invite links",
        parse_mode="Markdown"
    )


# ================= ADDBOT + GC (FIXED WITH FULL LOGGING) =================
async def addbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addbot — Promotes all bots to admin in the current chat using Bot API.
    Checks admin permission before action, logs all errors.
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    bots = all_bot_instances if all_bot_instances else [context.bot]
    if not bots:
        return await update.message.reply_text("❌ No bots loaded.")

    # Check if the bot calling has admin rights first
    try:
        chat_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        if chat_member.status not in ("administrator", "creator"):
            return await update.message.reply_text(
                "❌ This bot is not an admin in this chat.\n"
                "Make it admin first, then use /addbot again.\n"
                "Or use /addpromote with your user account."
            )
    except Exception as e:
        logger.error(f"addbot permission check error: {e}")
        await update.message.reply_text(f"⚠️ Could not check admin status: {e}")

    status_msg = await update.message.reply_text(
        f"⚙️ Promoting {len(bots)} bots to admin..."
    )

    bot_ids: list = []
    for b in bots:
        try:
            me = await b.get_me()
            bot_ids.append((b, me.id, me.username))
        except Exception as e:
            logger.error(f"addbot get_me error: {e}")

    promoted_ids: set = set()
    errors: list = []

    for promoter_bot, promoter_id, promoter_uname in bot_ids:
        for target_bot, target_id, target_uname in bot_ids:
            if target_id == promoter_id or target_id in promoted_ids:
                continue
            try:
                await promoter_bot.promote_chat_member(
                    chat_id, target_id,
                    can_manage_chat=True,
                    can_delete_messages=True,
                    can_invite_users=True,
                    can_change_info=True,
                    can_pin_messages=True,
                    can_manage_video_chats=True,
                )
                promoted_ids.add(target_id)
                await asyncio.sleep(random.uniform(0.5, 1.0))
            except Exception as e:
                err = str(e)
                if "not enough rights" in err.lower() or "CHAT_ADMIN_REQUIRED" in err:
                    pass
                elif "participant" in err.lower():
                    errors.append(f"@{target_uname}: not in chat")
                else:
                    logger.error(f"addbot promote error @{target_uname}: {err}")
                    errors.append(f"@{target_uname}: {err[:60]}")

    total = len(bot_ids)
    promoted = len(promoted_ids)
    summary = f"✅ **Promote done!**\n👑 Bots promoted: `{promoted}/{total}`"
    if promoted == 0:
        summary = (
            "⚠️ **No bots could be promoted.**\n\n"
            "None of the bots have admin rights yet.\n"
            "Use /addpromote to add and promote via your user account."
        )
    if errors:
        summary += f"\n\n⚠️ Issues:\n" + "\n".join(errors[:5])
    await status_msg.edit_text(summary, parse_mode="Markdown")


async def gaddbot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /gaddbot — Promotes ALL bots to admin in ALL known groups.
    Checks admin permission per chat before acting.
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    bots = all_bot_instances if all_bot_instances else [context.bot]
    if not bots:
        return await update.message.reply_text("❌ No bots loaded.")
    chats = list(known_chats)
    if not chats:
        return await update.message.reply_text("❌ No known groups.")

    status_msg = await update.message.reply_text(
        f"⚙️ Promoting {len(bots)} bots in {len(chats)} groups...\nThis may take a while."
    )

    bot_ids: list = []
    for b in bots:
        try:
            me = await b.get_me()
            bot_ids.append((b, me.id, me.username))
        except Exception as e:
            logger.error(f"gaddbot get_me error: {e}")

    total_promoted = 0
    total_errors = 0
    skipped_chats = 0

    for chat_id in chats:
        # Check admin permission in this chat before trying
        has_admin = False
        for promoter_bot, promoter_id, promoter_uname in bot_ids:
            try:
                member = await promoter_bot.get_chat_member(chat_id, promoter_id)
                if member.status in ("administrator", "creator"):
                    has_admin = True
                    break
            except Exception as e:
                logger.error(f"gaddbot admin check error in {chat_id}: {e}")

        if not has_admin:
            skipped_chats += 1
            continue

        promoted_in_chat: set = set()
        for promoter_bot, promoter_id, _ in bot_ids:
            for target_bot, target_id, target_uname in bot_ids:
                if target_id == promoter_id or target_id in promoted_in_chat:
                    continue
                try:
                    await promoter_bot.promote_chat_member(
                        chat_id, target_id,
                        can_manage_chat=True,
                        can_delete_messages=True,
                        can_invite_users=True,
                        can_change_info=True,
                        can_pin_messages=True,
                        can_manage_video_chats=True,
                    )
                    promoted_in_chat.add(target_id)
                    total_promoted += 1
                    await asyncio.sleep(random.uniform(0.4, 0.9))
                except Exception as e:
                    err = str(e)
                    if "not enough rights" in err.lower() or "CHAT_ADMIN_REQUIRED" in err:
                        pass
                    elif "participant" not in err.lower():
                        total_errors += 1
                        logger.error(f"gaddbot promote error in {chat_id} for @{target_uname}: {err}")

    await status_msg.edit_text(
        f"✅ **Global promote done!**\n"
        f"👑 Promoted: `{total_promoted}` bot-chat pairs\n"
        f"⏭️ Skipped (no admin): `{skipped_chats}` chats\n"
        f"⚠️ Errors: `{total_errors}`",
        parse_mode="Markdown"
    )


async def setupgc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await addpromote_cmd(update, context)


async def joinlink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not context.args:
        return await update.message.reply_text(
            "Usage: /joinlink <invite_link>\nExample: /joinlink https://t.me/+xxxxxxxxxx"
        )
    invite_link = context.args[0].strip()
    bots = all_bot_instances
    if not bots:
        return await update.message.reply_text("❌ No bots loaded.")
    status_msg = await update.message.reply_text(f"⚙️ Joining {len(bots)} bots via link...")
    joined = 0
    errors = []
    for bot_instance in bots:
        try:
            await bot_instance.join_chat(invite_link)
            joined += 1
            await asyncio.sleep(random.uniform(1.0, 2.5))
        except Exception as e:
            err = str(e)
            if "already" in err.lower() or "USER_ALREADY_PARTICIPANT" in err:
                joined += 1
            else:
                logger.error(f"joinlink error: {err}")
                errors.append(f"Bot error: {err[:60]}")
    summary = f"✅ **Done!**\n🤖 Bots joined: `{joined}/{len(bots)}`"
    if errors:
        summary += f"\n\n⚠️ Errors:\n" + "\n".join(errors[:3])
    await status_msg.edit_text(summary, parse_mode="Markdown")


async def setname_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setname <name> — Change display name on ALL bots.
    Strategy (in order):
      1. Telethon user client → BotFather /setname automation (most reliable)
      2. Bot API set_my_name() direct call (fallback — no Telethon needed)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not context.args:
        return await update.message.reply_text(
            "Usage: /setname <name>\nExample: `/setname 𝐒𝐔𝐒𝐀𝐍𝐎𝐎`",
            parse_mode="Markdown"
        )
    name = " ".join(context.args)[:64]
    bots = all_bot_instances
    if not bots:
        return await update.message.reply_text("❌ No bots loaded.")

    user_client = await get_user_client()
    use_botfather = (user_client is not None and TELETHON_AVAILABLE)

    if use_botfather:
        status_msg = await update.message.reply_text(
            f"⚙️ Setting name **{name}** on {len(bots)} bots via BotFather...",
            parse_mode="Markdown"
        )
    else:
        status_msg = await update.message.reply_text(
            f"⚙️ Setting name **{name}** on {len(bots)} bots via Bot API...\n"
            f"_(Tip: /login for faster BotFather method)_",
            parse_mode="Markdown"
        )

    success = 0
    errors = []
    for bot_instance in bots:
        try:
            uname = None
            try:
                me = await bot_instance.get_me()
                uname = me.username
            except Exception:
                pass

            if use_botfather and uname:
                # Method 1: Telethon BotFather automation
                try:
                    result = await _botfather_set_name(user_client, uname, name)
                    if result and ("success" in result.lower() or "done" in result.lower()
                                   or "name" in result.lower()):
                        success += 1
                        await asyncio.sleep(random.uniform(1.5, 3.0))
                        continue
                except Exception as bf_err:
                    logger.warning(f"BotFather setname failed for @{uname}: {bf_err}")
                    # Fall through to API method

            # Method 2: Bot API set_my_name (direct)
            await bot_instance.set_my_name(name=name)
            success += 1
            await asyncio.sleep(random.uniform(0.3, 0.8))

        except Exception as e:
            logger.error(f"setname error: {e}")
            errors.append(str(e)[:60])

    method = "BotFather" if use_botfather else "Bot API"
    summary = f"✅ **Name set to:** `{name}`\n🤖 Success: `{success}/{len(bots)}` ({method})"
    if errors:
        summary += f"\n\n⚠️ Errors:\n" + "\n".join(errors[:3])
    await status_msg.edit_text(summary, parse_mode="Markdown")


async def setpfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text(
            "Reply to a photo with /setpfp to set it as the group photo in ALL known chats."
        )
    chats = list(known_chats)
    bots = all_bot_instances if all_bot_instances else [context.bot]
    if not chats:
        return await update.message.reply_text("❌ No known groups.")
    try:
        f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        photo_bytes = bytes(await f.download_as_bytearray())
    except Exception as e:
        return await update.message.reply_text(f"❌ Could not download photo: {e}")
    status_msg = await update.message.reply_text(f"⚙️ Setting group photo in {len(chats)} chats...")
    success = 0
    num_bots = len(bots)
    for idx, chat_id in enumerate(chats):
        bot_instance = bots[idx % num_bots]
        try:
            await bot_instance.set_chat_photo(chat_id, photo=photo_bytes)
            success += 1
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"setpfp error in {chat_id}: {e}")
            for fallback_bot in bots:
                if fallback_bot is bot_instance:
                    continue
                try:
                    await fallback_bot.set_chat_photo(chat_id, photo=photo_bytes)
                    success += 1
                    break
                except Exception as e2:
                    logger.error(f"setpfp fallback error in {chat_id}: {e2}")
    await status_msg.edit_text(
        f"✅ **Group photo set!**\n📸 Updated: `{success}/{len(chats)}` chats",
        parse_mode="Markdown"
    )


async def setbotpfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /setbotpfp — Set profile photo on ALL bots. Reply to a photo.
    Strategy (in order):
      1. Telethon user client → BotFather /setuserpic automation (most reliable)
      2. PTB native set_my_photo() (if available in this PTB version)
      3. Raw HTTP multipart POST to Telegram setMyPhoto API (always available)
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text(
            "📸 Reply to a photo with /setbotpfp to set it as the profile photo for ALL bots.\n"
            "_(Login with /login first for best results via BotFather)_",
            parse_mode="Markdown"
        )
    bots = all_bot_instances if all_bot_instances else [context.bot]
    try:
        f = await context.bot.get_file(update.message.reply_to_message.photo[-1].file_id)
        photo_bytes = bytes(await f.download_as_bytearray())
    except Exception as e:
        return await update.message.reply_text(f"❌ Could not download photo: {e}")

    user_client = await get_user_client()
    use_botfather = (user_client is not None and TELETHON_AVAILABLE)
    method_label = "BotFather" if use_botfather else "Bot API"
    status_msg = await update.message.reply_text(
        f"⚙️ Setting PFP on {len(bots)} bots via {method_label}..."
    )
    success = 0
    errors = []

    async def _set_one_bot_photo(bot_instance, photo_data: bytes) -> bool:
        """
        3-tier PFP setter:
        1. Telethon BotFather /setuserpic automation
        2. PTB native set_my_photo
        3. Raw HTTP multipart POST
        """
        import io as _io

        uname = None
        try:
            me = await bot_instance.get_me()
            uname = me.username
        except Exception:
            pass

        # Tier 1: BotFather via Telethon user account
        if use_botfather and uname:
            try:
                result = await _botfather_set_pfp(user_client, uname, photo_data)
                if result and any(w in result.lower() for w in
                                  ("success", "done", "updated", "photo", "changed")):
                    return True
                # If BotFather responded but without expected keywords, still treat as success
                if result and "sorry" not in result.lower():
                    return True
            except Exception as bf_err:
                logger.warning(f"BotFather setpfp failed for @{uname}: {bf_err}")
                # Fall through to next tier

        # Tier 2: PTB native set_my_photo (only exists in PTB >= 21.6)
        native = getattr(bot_instance, "set_my_photo", None)
        if native:
            try:
                await native(photo=_io.BytesIO(photo_data))
                return True
            except Exception:
                pass

        # Tier 3: Raw Telegram Bot API HTTP call (works regardless of PTB version)
        import urllib.request, ssl, json as _json
        token = bot_instance.token
        url = f"https://api.telegram.org/bot{token}/setMyPhoto"
        boundary = "----BotPhotoUpload"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="photo.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode() + photo_data + f"\r\n--{boundary}--\r\n".encode()
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        }
        loop = asyncio.get_event_loop()
        def _do_request():
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
                return r.read()
        result = await loop.run_in_executor(None, _do_request)
        res_json = _json.loads(result)
        if not res_json.get("ok", False):
            raise RuntimeError(f"API error: {res_json.get('description', 'unknown')}")
        return True

    for bot_instance in bots:
        try:
            ok = await _set_one_bot_photo(bot_instance, photo_bytes)
            if ok:
                success += 1
            await asyncio.sleep(random.uniform(1.0, 2.5) if use_botfather else random.uniform(0.4, 0.9))
        except Exception as e:
            errors.append(str(e)[:60])

    summary = f"✅ **Bot PFP updated!**\n🤖 Success: `{success}/{len(bots)}` ({method_label})"
    if errors:
        summary += "\n\n⚠️ Errors:\n" + "\n".join(errors[:3])
    await status_msg.edit_text(summary, parse_mode="Markdown")


# ================= TELETHON GC COMMANDS =================

async def creategc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /creategc <group name>
    Creates a supergroup via user account, adds all bots,
    promotes them to admin (with change_info=True), then sends invite link.
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.message:
        return
    if not context.args:
        return await update.message.reply_text(
            "Usage: /creategc <group name>\nExample: /creategc SUSANOO RAID GC"
        )
    client = await _check_user_client(update)
    if not client:
        return
    gc_name = " ".join(context.args)
    status_msg = await update.message.reply_text(f"⚙️ Creating group **{gc_name}**...", parse_mode="Markdown")
    try:
        result = await client(CreateChannelRequest(
            title=gc_name,
            about="Created by SUSANOO V30",
            megagroup=True
        ))
        channel = result.chats[0]
        chat_id_tele = channel.id
        ptb_chat_id = int(f"-100{chat_id_tele}")
        known_chats.add(ptb_chat_id)
        save_groups(known_chats)

        await status_msg.edit_text(
            f"✅ Group created!\n⚙️ Adding and promoting {len(all_bot_instances)} bots...",
            parse_mode="Markdown"
        )

        bots_added = 0
        bots_promoted = 0
        bot_errors = []

        for bot_instance in all_bot_instances:
            bot_username = None
            try:
                bot_info = await bot_instance.get_me()
                bot_username = bot_info.username
                try:
                    await _tele_add_bot(client, channel, bot_username)
                    bots_added += 1
                    await asyncio.sleep(random.uniform(1.5, 2.5))
                except Exception as e:
                    bot_errors.append(f"Add @{bot_username}: {str(e)[:60]}")
                    logger.error(f"creategc add bot error @{bot_username}: {e}")
                try:
                    await _tele_promote_bot(client, channel, bot_username)
                    bots_promoted += 1
                    await asyncio.sleep(random.uniform(1.0, 2.0))
                except Exception as e:
                    bot_errors.append(f"Promote @{bot_username}: {str(e)[:60]}")
                    logger.error(f"creategc promote bot error @{bot_username}: {e}")
            except Exception as e:
                bot_errors.append(f"GetMe: {str(e)[:60]}")
                logger.error(f"creategc get_me error: {e}")

        try:
            link_result = await client(ExportInviteRequest(channel))
            invite_link = link_result.link
        except Exception as e:
            invite_link = f"(could not get link: {e})"
            logger.error(f"creategc invite link error: {e}")

        summary = (
            f"🏠 **GROUP CREATED!**\n\n"
            f"📛 Name: `{gc_name}`\n"
            f"🆔 ID: `{ptb_chat_id}`\n"
            f"🔗 Link: {invite_link}\n\n"
            f"🤖 Bots added: {bots_added}/{len(all_bot_instances)}\n"
            f"👑 Bots promoted: {bots_promoted}\n"
        )
        if bot_errors:
            summary += f"\n⚠️ Errors ({len(bot_errors)}):\n" + "\n".join(bot_errors[:5])
        await status_msg.edit_text(summary, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"creategc failed: {e}")
        await status_msg.edit_text(f"❌ Failed to create group: {e}")


async def addpromote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addpromote — Adds ALL bots to the current chat and promotes each one to admin.
    Uses user account (Telethon). Full error logging.
    """
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    client = await _check_user_client(update)
    if not client:
        return
    chat_id = update.effective_chat.id
    bots = all_bot_instances
    if not bots:
        return await update.message.reply_text("❌ No bots loaded.")
    status_msg = await update.message.reply_text(
        f"⚙️ Adding & promoting {len(bots)} bots to this chat...",
        parse_mode="Markdown"
    )
    bots_added = 0
    bots_promoted = 0
    errors = []
    try:
        entity = await client.get_entity(chat_id)
    except Exception as e:
        logger.error(f"addpromote get entity error: {e}")
        return await status_msg.edit_text(f"❌ Could not get chat entity: {e}")
    for bot_instance in bots:
        bot_username = None
        try:
            bot_info = await bot_instance.get_me()
            bot_username = bot_info.username
            try:
                await _tele_add_bot(client, entity, bot_username)
                bots_added += 1
                await asyncio.sleep(random.uniform(1.5, 2.5))
            except Exception as e:
                errors.append(f"Add @{bot_username}: {str(e)[:70]}")
                logger.error(f"addpromote add error @{bot_username}: {e}")
            try:
                await _tele_promote_bot(client, entity, bot_username)
                bots_promoted += 1
                await asyncio.sleep(random.uniform(1.0, 2.0))
            except Exception as e:
                errors.append(f"Promote @{bot_username}: {str(e)[:70]}")
                logger.error(f"addpromote promote error @{bot_username}: {e}")
        except Exception as e:
            errors.append(f"GetMe @{bot_username or '?'}: {str(e)[:60]}")
            logger.error(f"addpromote get_me error: {e}")
    invite_link = ""
    try:
        link_result = await client(ExportInviteRequest(entity))
        invite_link = f"\n🔗 Link: {link_result.link}"
    except Exception:
        try:
            link_result = await client(ExportChatInviteRequest(entity.id))
            invite_link = f"\n🔗 Link: {link_result.link}"
        except Exception:
            pass
    summary = (
        f"✅ **DONE!**\n\n"
        f"🤖 Bots added: `{bots_added}/{len(bots)}`\n"
        f"👑 Bots promoted: `{bots_promoted}/{len(bots)}`"
        f"{invite_link}"
    )
    if errors:
        summary += f"\n\n⚠️ Errors ({len(errors)}):\n" + "\n".join(errors[:5])
    await status_msg.edit_text(summary, parse_mode="Markdown")


async def gclink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    try:
        link = await context.bot.export_chat_invite_link(chat_id)
        return await update.message.reply_text(
            f"🔗 **Invite Link:**\n{link}", parse_mode="Markdown"
        )
    except:
        pass
    client = await _check_user_client(update)
    if not client:
        return await update.message.reply_text(
            "❌ Bot doesn't have permission and no user account configured."
        )
    try:
        entity = await client.get_entity(chat_id)
        link_result = await client(ExportInviteRequest(entity))
        await update.message.reply_text(
            f"🔗 **Invite Link:**\n{link_result.link}", parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"gclink error: {e}")
        await update.message.reply_text(f"❌ Failed to export link: {e}")


async def makegc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await creategc_cmd(update, context)


# ================= MESSAGE HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user or not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    known_chats.add(chat_id)
    uid = update.message.from_user.id

    msg_text = (update.message.text or "").strip()

    # Session gen state — all bots track, but only primary replies
    if uid in _session_gen_state and msg_text:
        if _is_primary_bot(context):
            consumed = await _handle_session_gen(update, msg_text, uid)
            if consumed:
                return
        else:
            return

    msg_lower = msg_text.lower()
    if msg_lower in ("+menu", "+ menu"):
        if _is_primary_bot(context):
            await plus_menu(update, context)
        return

    if msg_lower.startswith("+sasukenc"):
        if is_admin(uid) and _is_primary_bot(context):
            await sasukenc(update, context)
        return

    # STEADYNC V2 — plus-prefix NC commands (order matters: longest match first)
    # _is_primary_bot check is inside each handler — skip silently on secondary bots
    if msg_lower.startswith("+burstnc"):
        if is_admin(uid):
            await plus_burstnc(update, context)
        return

    if msg_lower.startswith("+ultranc"):
        if is_admin(uid):
            await plus_ultranc(update, context)
        return

    if msg_lower.startswith("+fastnc"):
        if is_admin(uid):
            await plus_fastnc(update, context)
        return

    if msg_lower.startswith("+sasmaxnc"):
        if is_admin(uid):
            await plus_sasmaxnc(update, context)
        return

    if msg_lower.startswith("+smoothsas"):
        if is_admin(uid):
            await plus_smoothsas(update, context)
        return

    if msg_lower.startswith("+slide"):
        if is_admin(uid):
            await plus_slide(update, context)
        return

    if msg_lower.startswith("+sasnc"):
        if is_admin(uid):
            await sasnc(update, context)
        return

    if msg_lower.startswith("+nc"):
        if is_admin(uid):
            await plus_nc(update, context)
        return

    if uid in slide_reply_targets:
        reply_msg = slide_reply_targets.get(uid)
        if reply_msg:
            try:
                await update.message.reply_text(reply_msg)
            except:
                pass


# ================= HANDLER REGISTRATION =================
def _register_handlers(app):
    cmds = {
        "start": start,
        "menu": menu_cmd,
        "cmds": plus_menu,
        "help": help_command,
        # Stop commands
        "stop": stop_command,
        "stopnc": stop_nc,
        "Stopspm": stop_spam,
        "Stopimgspm": lambda u, c: task_controller.stop_task(u.effective_chat.id, "imagespam") if u.effective_chat else None,
        "Stoppfp": lambda u, c: task_controller.stop_task(u.effective_chat.id, "pfp") if u.effective_chat else None,
        "stopspnc": stop_spnc,
        "Stopncpfp": stop_ncpfp,
        "stoptarget": stop_target,
        "dynstop": dynstop,
        "gstop": gstop,
        # Speed modes
        "ncsteady": nc_set_steady,
        "ncfast": nc_set_fast,
        "ncultra": nc_set_ultra,
        "ncburst": nc_set_burst,
        # Spam
        "spam": spam,
        "imagespam": imagespam,
        "raidspam": raidspam,
        "gspam": gspam,
        # NC — all STEADYNC engine
        "nc": rename,
        "gcnc": gcnc,
        "sasukenc": sasukenc,
        "sasnc": sasnc,
        "ncbaap": ncbaap,
        "godspeed": godspeed,
        "customnc": customnc,
        "smoothnc": rename,
        "delaync": delaync,
        "setgodspeed": set_godspeed_delay,
        "gnc": gnc,
        # PFP
        "changepfp": change_pfp,
        "gpfp": gpfp,
        # Combos
        "spnc": spnc,
        "ncpfp": ncpfp,
        "all": all_cmd,
        # Voice
        "vn": vn_cmd,
        # Reply
        "slidespam": slidespam,
        "slidestop": slidestop,
        # Settings
        "speed": speed,
        "threads": set_threads,
        # Target
        "target": set_target,
        "settemplate": set_template,
        "spamtarget": spam_target,
        "showtemplate": show_templates,
        # Kill switch
        "kill": kill_cmd,
        "gkill": gkill_cmd,
        # Global control
        "globalactivate": global_activate,
        "offglobal": off_global,
        "activategbl": activategbl,
        "offgbl": offgbl,
        "leaveglobal": leave_global,
        "g": execute_global,
        # Groups
        "groups": show_groups,
        "leavegc": leave_gc,
        "leavegbl": leave_gbl,
        # Bot manager
        "addtoken": addtoken_cmd,
        "bots": bots_cmd,
        "removebot": removebot_cmd,
        "addbot": addbot_cmd,
        "gaddbot": gaddbot_cmd,
        "joinlink": joinlink_cmd,
        "setupgc": setupgc_cmd,
        "setname": setname_cmd,
        "setpfp": setpfp_cmd,
        "setbotpfp": setbotpfp_cmd,
        # Announce
        "announce": announce,
        # Stats
        "test": test_cmd,
        "status": status_cmd,
        "dashboard": dashboard_cmd,
        "rlstats": ratelimit_stats,
        "resetrl": reset_ratelimit,
        "perf": performance_stats,
        # Admin
        "sudo": add_sudo,
        "delsudo": del_sudo,
        "Listsudo": list_sudo,
        "Owner": owner_cmd,
        "getallbots": get_all_bots,
        "raid": raidspam,
        # Telethon user account
        "creategc": creategc_cmd,
        "makegc": makegc_cmd,
        "newgc": creategc_cmd,
        "addpromote": addpromote_cmd,
        "addmybots": addpromote_cmd,
        "gclink": gclink_cmd,
        "userstatus": userstatus_cmd,
        "gensession": gensession_cmd,
        "login": gensession_cmd,
    }
    for cmd, h in cmds.items():
        if callable(h):
            app.add_handler(CommandHandler(cmd, _dedup(h)))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _dedup(message_handler)))


# ================= MAIN BOT RUNNER =================
async def run_bots():
    global all_bot_instances, all_apps
    all_tokens = get_base_tokens() + [t for t in extra_tokens if t not in get_base_tokens()]
    print(f"🚀 Starting {len(all_tokens)} bots... (𝙍𝙐𝙇𝙀𝙍 𝘽𝙊𝙏 STEADYNC)")

    from telegram.request import HTTPXRequest
    request_config = HTTPXRequest(
        connection_pool_size=500,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30,
        pool_timeout=5
    )

    apps = []
    for token in all_tokens:
        if "YOUR_BOT" in token:
            continue
        try:
            app = Application.builder().token(token).request(request_config).build()
            _register_handlers(app)
            await app.initialize()
            await app.start()
            if app.updater:
                await app.updater.start_polling(drop_pending_updates=True)
            apps.append(app)
            all_apps.append(app)
            try:
                me = await app.bot.get_me()
                bot_manager.add_bot_info(token, app, app.bot, me.username or "unknown", me.id)
            except:
                bot_manager.add_bot_info(token, app, app.bot, "unknown", 0)
            print(f"✅ Bot {token[:15]}... started")
        except Exception as e:
            print(f"❌ Error {token[:15]}: {e}")

    all_bot_instances.clear()
    for app in apps:
        all_bot_instances.append(app.bot)

    print(f"🎯 {len(all_bot_instances)} bots ready | Known groups: {len(known_chats)}")
    print(f"⚡ STEADYNC engine active — zero jitter, instant stop, no task leaks")

    asyncio.create_task(periodic_cleanup())

    try:
        await asyncio.Event().wait()
    finally:
        for app in apps:
            try:
                await app.stop()
                await app.shutdown()
            except:
                pass


if __name__ == "__main__":
    threading.Thread(target=run_health_check_server, daemon=True).start()
    try:
        asyncio.run(run_bots())
    except KeyboardInterrupt:
        pass
