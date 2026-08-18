import os
import logging
import sqlite3
from datetime import datetime, timedelta

from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# =========================================================
# CONFIGURATION
# =========================================================

# Your file is named bot.env
load_dotenv("bot.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")

REGISTRATION_URL = os.getenv(
    "REGISTRATION_URL",
    "https://h5.sw-smart13.top?invite=KFEOG5AS"
)

# Put your own Telegram numeric ID in bot.env:
#
# ADMIN_ID=123456789
#
ADMIN_ID = os.getenv("ADMIN_ID")

if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        ADMIN_ID = None


DB_FILE = "smartwallet.db"


# =========================================================
# BASIC VALIDATION
# =========================================================

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is missing in bot.env"
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# DATABASE
# =========================================================

def init_db():
    """
    Create the users table if it does not exist.
    """

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            start_count INTEGER DEFAULT 0,
            interaction_count INTEGER DEFAULT 0
        )
        """
    )

    conn.commit()
    conn.close()


def track_user(user):
    """
    Record/update user activity.
    """

    if not user:
        return

    now = datetime.now().isoformat()

    username = user.username or ""
    full_name = user.full_name or ""

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            user_id,
            username,
            full_name,
            first_seen,
            last_seen,
            start_count,
            interaction_count
        )
        VALUES (?, ?, ?, ?, ?, 0, 1)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            last_seen = excluded.last_seen,
            interaction_count =
                users.interaction_count + 1
        """,
        (
            user.id,
            username,
            full_name,
            now,
            now,
        )
    )

    conn.commit()
    conn.close()


def track_start(user):
    """
    Record /start separately.
    """

    if not user:
        return

    track_user(user)

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET start_count = start_count + 1
        WHERE user_id = ?
        """,
        (user.id,)
    )

    conn.commit()
    conn.close()


def get_stats():
    """
    Return:
    total users
    active users in last 5 minutes
    total starts
    total interactions
    """

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    # Total unique users
    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total_users = cursor.fetchone()[0]

    # Active in last 5 minutes
    cutoff = (
        datetime.now()
        - timedelta(minutes=5)
    ).isoformat()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE last_seen >= ?
        """,
        (cutoff,)
    )

    active_users = cursor.fetchone()[0]

    # Total /start
    cursor.execute(
        """
        SELECT COALESCE(SUM(start_count), 0)
        FROM users
        """
    )

    total_starts = cursor.fetchone()[0]

    # Total interactions
    cursor.execute(
        """
        SELECT COALESCE(SUM(interaction_count), 0)
        FROM users
        """
    )

    total_interactions = cursor.fetchone()[0]

    conn.close()

    return (
        total_users,
        active_users,
        total_starts,
        total_interactions,
    )


def get_recent_users(limit=10):
    """
    Return recently active users.
    """

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            username,
            full_name,
            last_seen
        FROM users
        ORDER BY last_seen DESC
        LIMIT ?
        """,
        (limit,)
    )

    users = cursor.fetchall()

    conn.close()

    return users


# =========================================================
# TEXT
# =========================================================

TEXT = {

    # =====================================================
    # ENGLISH
    # =====================================================

    "en": {

        "welcome": (
            "👋 <b>Welcome to Smart Wallet</b>\n\n"

            "🔐 Welcome to the Smart Wallet assistant.\n\n"

            "Use the menu below to access the current "
            "registration link, help and basic information.\n\n"

            "⚠️ <b>Important:</b>\n"
            "For a smoother registration/access experience, "
            "always use the current link provided by this bot.\n\n"

            "👇 <b>Select an option:</b>"
        ),

        "register": (
            "🔗 <b>Smart Wallet Registration</b>\n\n"

            "Please use the current registration link below.\n\n"

            "⚠️ If you are using an older link, stop using "
            "the old link and use the current link provided here "
            "to avoid possible registration or access issues.\n\n"

            "🇬🇧 <b>English:</b>\n"
            "Use the current registration link below.\n\n"

            "🇮🇳 <b>हिन्दी:</b>\n"
            "किसी भी registration या access की परेशानी से बचने "
            "के लिए नीचे दिया गया current link इस्तेमाल करें।"
        ),

        "help": (
            "🆘 <b>Smart Wallet Help Center</b>\n\n"

            "🔗 <b>Registration</b>\n"
            "Use the current registration link provided by this bot.\n\n"

            "⚠️ If you are using an older link, use the current "
            "link instead.\n\n"

            "🌐 <b>Language</b>\n"
            "Switch between English and Hindi from the Language menu.\n\n"

            "👤 <b>Support</b>\n"
            "For assistance, contact:\n"
            "👉 @smartwallet002\n\n"

            "🔒 <b>Security</b>\n"
            "Never share your password, OTP, PIN or private keys "
            "with anyone."
        ),

        "about": (
            "ℹ️ <b>About Smart Wallet</b>\n\n"

            "Smart Wallet is a Telegram assistant designed to "
            "make registration and basic information easier to access.\n\n"

            "🔗 The bot provides the current registration link "
            "configured by the administrator.\n\n"

            "⚠️ Always verify important account and transaction "
            "information before taking any financial action."
        ),

        "language": (
            "🌐 <b>Select your language</b>\n\n"
            "Choose English or Hindi."
        ),

        "back": "⬅️ Back",

        "english": "🇬🇧 English",

        "hindi": "🇮🇳 हिन्दी",

        "stats_title": (
            "📊 <b>Smart Wallet Live Statistics</b>"
        ),

        "not_admin": (
            "⛔ You are not authorized to view statistics."
        ),
    },


    # =====================================================
    # HINDI
    # =====================================================

    "hi": {

        "welcome": (
            "👋 <b>Smart Wallet में आपका स्वागत है</b>\n\n"

            "🔐 यह Smart Wallet assistant है।\n\n"

            "नीचे दिए गए menu से current registration link, "
            "help और basic information access करें।\n\n"

            "⚠️ <b>महत्वपूर्ण:</b>\n"
            "Registration/access से जुड़ी परेशानी से बचने के लिए "
            "हमेशा इस bot द्वारा दिया गया current link इस्तेमाल करें।\n\n"

            "👇 <b>कोई option चुनें:</b>"
        ),

        "register": (
            "🔗 <b>Smart Wallet Registration</b>\n\n"

            "नीचे दिया गया current registration link इस्तेमाल करें।\n\n"

            "⚠️ अगर आप किसी पुराने link का इस्तेमाल कर रहे हैं, "
            "तो पुराने link को छोड़कर यहां दिया गया current link "
            "इस्तेमाल करें ताकि registration या access से जुड़ी "
            "संभावित परेशानी से बचा जा सके।\n\n"

            "🇮🇳 <b>हिन्दी:</b>\n"
            "Current registration link नीचे दिया गया है।\n\n"

            "🇬🇧 <b>English:</b>\n"
            "Please use the current registration link below."
        ),

        "help": (
            "🆘 <b>Smart Wallet Help Center</b>\n\n"

            "🔗 <b>Registration</b>\n"
            "इस bot द्वारा दिया गया current registration link इस्तेमाल करें।\n\n"

            "⚠️ अगर आप पुराने link का इस्तेमाल कर रहे हैं, "
            "तो current link इस्तेमाल करें।\n\n"

            "🌐 <b>Language</b>\n"
            "Language menu से English और Hindi के बीच बदल सकते हैं।\n\n"

            "👤 <b>Support</b>\n"
            "किसी सहायता के लिए संपर्क करें:\n"
            "👉 @smartwallet002\n\n"

            "🔒 <b>Security</b>\n"
            "अपना password, OTP, PIN या private keys किसी के साथ share न करें।"
        ),

        "about": (
            "ℹ️ <b>Smart Wallet के बारे में</b>\n\n"

            "Smart Wallet एक Telegram assistant है जो registration "
            "और basic information तक आसान access देने के लिए बनाया गया है।\n\n"

            "🔗 Bot administrator द्वारा configured current "
            "registration link यहां उपलब्ध कराया जाता है।\n\n"

            "⚠️ किसी भी financial action से पहले important account "
            "और transaction information verify करें।"
        ),

        "language": (
            "🌐 <b>अपनी भाषा चुनें</b>\n\n"
            "English या Hindi चुनें।"
        ),

        "back": "⬅️ वापस",

        "english": "🇬🇧 English",

        "hindi": "🇮🇳 हिन्दी",

        "stats_title": (
            "📊 <b>Smart Wallet Live Statistics</b>"
        ),

        "not_admin": (
            "⛔ आपको statistics देखने की अनुमति नहीं है।"
        ),
    }
}


# =========================================================
# KEYBOARDS
# =========================================================

def main_keyboard(lang="en"):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔗 Registration",
                callback_data="registration"
            )
        ],

        [
            InlineKeyboardButton(
                "🆘 Help",
                callback_data="help"
            ),

            InlineKeyboardButton(
                "ℹ️ About",
                callback_data="about"
            )
        ],

        [
            InlineKeyboardButton(
                "🌐 Language",
                callback_data="language"
            )
        ]

    ])


def registration_keyboard(lang="en"):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔗 Open Current Registration",
                url=REGISTRATION_URL
            )
        ],

        [
            InlineKeyboardButton(
                TEXT[lang]["back"],
                callback_data="home"
            )
        ]

    ])


def language_keyboard():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🇬🇧 English",
                callback_data="lang_en"
            ),

            InlineKeyboardButton(
                "🇮🇳 हिन्दी",
                callback_data="lang_hi"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="home"
            )
        ]

    ])


def back_keyboard(lang="en"):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                TEXT[lang]["back"],
                callback_data="home"
            )
        ]

    ])


# =========================================================
# LANGUAGE
# =========================================================

def get_lang(context):

    return context.user_data.get(
        "lang",
        "en"
    )


# =========================================================
# ACTIVITY LOGGER
# =========================================================

def log_activity(user, action):

    if not user:
        return

    username = (
        f"@{user.username}"
        if user.username
        else "NoUsername"
    )

    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 SMART WALLET ACTIVITY\n"
        f"👤 Name: {user.full_name}\n"
        f"🔹 Username: {username}\n"
        f"🆔 User ID: {user.id}\n"
        f"⚡ Action: {action}\n"
        f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    track_start(user)

    log_activity(
        user,
        "/start"
    )

    context.user_data.setdefault(
        "lang",
        "en"
    )

    lang = get_lang(context)

    await update.message.reply_text(
        TEXT[lang]["welcome"],
        parse_mode="HTML",
        reply_markup=main_keyboard(lang)
    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    track_user(user)

    log_activity(
        user,
        "/help"
    )

    lang = get_lang(context)

    await update.message.reply_text(
        TEXT[lang]["help"],
        parse_mode="HTML",
        reply_markup=back_keyboard(lang)
    )


# =========================================================
# /ABOUT
# =========================================================

async def about_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    track_user(user)

    log_activity(
        user,
        "/about"
    )

    lang = get_lang(context)

    await update.message.reply_text(
        TEXT[lang]["about"],
        parse_mode="HTML",
        reply_markup=back_keyboard(lang)
    )


# =========================================================
# /STATS
# =========================================================

async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    # Track admin activity too
    track_user(user)

    # Admin protection
    if ADMIN_ID is None:

        await update.message.reply_text(
            "⚠️ ADMIN_ID is not configured in bot.env."
        )

        return

    if user.id != ADMIN_ID:

        await update.message.reply_text(
            TEXT["en"]["not_admin"]
        )

        return

    (
        total_users,
        active_users,
        total_starts,
        total_interactions
    ) = get_stats()

    recent_users = get_recent_users(5)

    message = (
        "📊 <b>Smart Wallet Live Statistics</b>\n\n"

        f"👥 <b>Total Users:</b> {total_users}\n"

        f"🟢 <b>Active — last 5 min:</b> "
        f"{active_users}\n"

        f"🚀 <b>Total /start:</b> "
        f"{total_starts}\n"

        f"💬 <b>Total Interactions:</b> "
        f"{total_interactions}\n\n"

        "🕒 <b>Recently Active</b>\n"
    )

    if recent_users:

        for (
            user_id,
            username,
            full_name,
            last_seen
        ) in recent_users:

            display_username = (
                f"@{username}"
                if username
                else "No username"
            )

            message += (
                f"\n👤 {full_name}\n"
                f"   {display_username}\n"
                f"   🆔 {user_id}\n"
                f"   🕒 {last_seen[:19]}\n"
            )

    else:

        message += "\nNo users yet."

    await update.message.reply_text(
        message,
        parse_mode="HTML"
    )

    log_activity(
        user,
        "/stats"
    )


# =========================================================
# CALLBACK HANDLER
# =========================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user = query.from_user

    # Every button interaction counts as activity
    track_user(user)

    log_activity(
        user,
        query.data
    )

    lang = get_lang(context)


    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    if query.data == "home":

        await query.edit_message_text(
            TEXT[lang]["welcome"],
            parse_mode="HTML",
            reply_markup=main_keyboard(lang)
        )

        return


    # -----------------------------------------------------
    # REGISTRATION
    # -----------------------------------------------------

    if query.data == "registration":

        await query.edit_message_text(
            TEXT[lang]["register"],
            parse_mode="HTML",
            reply_markup=registration_keyboard(lang)
        )

        return


    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if query.data == "help":

        await query.edit_message_text(
            TEXT[lang]["help"],
            parse_mode="HTML",
            reply_markup=back_keyboard(lang)
        )

        return


    # -----------------------------------------------------
    # ABOUT
    # -----------------------------------------------------

    if query.data == "about":

        await query.edit_message_text(
            TEXT[lang]["about"],
            parse_mode="HTML",
            reply_markup=back_keyboard(lang)
        )

        return


    # -----------------------------------------------------
    # LANGUAGE
    # -----------------------------------------------------

    if query.data == "language":

        await query.edit_message_text(
            TEXT[lang]["language"],
            parse_mode="HTML",
            reply_markup=language_keyboard()
        )

        return


    # -----------------------------------------------------
    # ENGLISH
    # -----------------------------------------------------

    if query.data == "lang_en":

        context.user_data["lang"] = "en"

        await query.edit_message_text(
            TEXT["en"]["welcome"],
            parse_mode="HTML",
            reply_markup=main_keyboard("en")
        )

        return


    # -----------------------------------------------------
    # HINDI
    # -----------------------------------------------------

    if query.data == "lang_hi":

        context.user_data["lang"] = "hi"

        await query.edit_message_text(
            TEXT["hi"]["welcome"],
            parse_mode="HTML",
            reply_markup=main_keyboard("hi")
        )

        return


# =========================================================
# NORMAL TEXT MESSAGE
# =========================================================

async def unknown(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    track_user(user)

    message_text = (
        update.message.text
        if update.message
        else ""
    )

    log_activity(
        user,
        f"Message: {message_text[:50]}"
    )

    lang = get_lang(context)

    await update.message.reply_text(
        TEXT[lang]["welcome"],
        parse_mode="HTML",
        reply_markup=main_keyboard(lang)
    )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Exception while processing update:",
        exc_info=context.error
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # Initialize database
    init_db()

    print(
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 SMART WALLET BOT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 Bot is starting...\n"
        "💾 Database: smartwallet.db\n"
        f"🔗 Registration: {REGISTRATION_URL}\n"
        "📊 Activity tracking: ENABLED\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )


    # -----------------------------------------------------
    # COMMANDS
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        CommandHandler(
            "about",
            about_command
        )
    )

    application.add_handler(
        CommandHandler(
            "stats",
            stats_command
        )
    )


    # -----------------------------------------------------
    # BUTTONS
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )


    # -----------------------------------------------------
    # NORMAL TEXT
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown
        )
    )


    # -----------------------------------------------------
    # ERRORS
    # -----------------------------------------------------

    application.add_error_handler(
        error_handler
    )


    print(
        "✅ Smart Wallet Bot is running!"
    )

    print(
        "📡 Waiting for Telegram activity...\n"
    )


    # -----------------------------------------------------
    # START POLLING
    # -----------------------------------------------------

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()