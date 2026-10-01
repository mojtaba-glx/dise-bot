"""Bilingual copy and labels for the private admin experience."""

LANG_EN = "en"
LANG_FA = "fa"
SUPPORTED_LANGUAGES = {LANG_EN, LANG_FA}

BUTTONS = {
    LANG_EN: {
        "panel": "👑 ᏢᎪᏁᎬᏞ",
        "ban": "🚫 Ban user",
        "unban": "✅ Unban user",
        "add_admin": "⭐ Add admin",
        "remove_admin": "❎ Remove admin",
        "auto_replies": "💬 Auto replies",
        "force_join": "🔒 Required membership",
        "settings": "⚙️ Settings",
        "back": "↩️ Back",
        "language": "🌐 Language",
        "join_on": "🟢 Membership ON",
        "join_off": "🔴 Membership OFF",
        "join_add": "➕ Add channel",
        "join_remove": "➖ Remove channel",
        "join_list": "📋 Channels",
    },
    LANG_FA: {
        "panel": "👑 پنل مدیریت",
        "ban": "🚫 مسدود کردن کاربر",
        "unban": "✅ رفع مسدودی",
        "add_admin": "⭐ افزودن ادمین",
        "remove_admin": "❎ حذف ادمین",
        "auto_replies": "💬 پاسخ‌های خودکار",
        "force_join": "🔒 عضویت اجباری",
        "settings": "⚙️ تنظیمات",
        "back": "↩️ بازگشت",
        "language": "🌐 زبان",
        "join_on": "🟢 روشن کردن عضویت",
        "join_off": "🔴 خاموش کردن عضویت",
        "join_add": "➕ افزودن کانال",
        "join_remove": "➖ حذف کانال",
        "join_list": "📋 کانال‌ها",
    },
}

LANGUAGE_BUTTONS = {
    LANG_EN: "🇬🇧 English",
    LANG_FA: "🇮🇷 فارسی",
}

TEXTS = {
    LANG_EN: {
        "access_denied": "Access denied.",
        "panel_private": "Open /panel in a private chat with this bot.",
        "panel_title": (
            "👑 Control panel\nChoose an action. Moderation applies across this bot; "
            "group-specific settings are managed separately."
        ),
        "only_owner_roles": "Only the owner can change admin roles.",
        "target_prompt": (
            "Send the numeric Telegram user ID now. Use /id to find your own ID, "
            "or reply to a person's message in a group with a moderation command."
        ),
        "target_error": "Send one numeric user ID or reply to a person's message.",
        "target_bot_error": "Reply to a person's message or send their numeric ID.",
        "target_id_error": "Use a valid positive Telegram user ID.",
        "unknown_action": "Unknown moderation action.",
        "ban_done": "User {user_id} banned from this bot.",
        "unban_done": "User {user_id} unbanned.",
        "admin_done": "User {user_id} is now a bot admin.",
        "unadmin_done": "User {user_id} is no longer a bot admin.",
        "reply_guide": (
            "In the target group, use:\n"
            "/reply add سلام | سلام!\n"
            "/reply remove سلام\n"
            "/reply list\n\n"
            "Triggers match whole messages. Persian ی/ي and ک/ك are treated alike."
        ),
        "no_replies": "No auto replies in this group yet.",
        "triggers": "Group triggers:\n{items}{suffix}",
        "reply_saved": "Auto reply saved for: {trigger}",
        "reply_removed": "Auto reply removed.",
        "reply_missing": "No matching trigger found.",
        "settings_title": "⚙️ Admin settings\nCurrent language: {language_name}",
        "language_changed": "✅ Admin language changed to English.",
        "join_title": "🔒 Required membership",
        "join_status": "Status: {status}\nChannels: {count}",
        "on": "ON",
        "off": "OFF",
        "join_add_prompt": (
            "Send @channelname, -1001234567890, or "
            "-1001234567890 https://t.me/+invitecode"
        ),
        "join_add_help": (
            "Add channels with:\n"
            "/join add @channelname\n"
            "/join add -1001234567890\n"
            "/join add -1001234567890 https://t.me/+invitecode\n\n"
            "The bot must be an administrator in every required channel."
        ),
        "join_remove_prompt": "Send the numeric channel ID to remove, for example -1001234567890.",
        "join_remove_help": "Remove a channel with /join remove <chat_id>.",
        "join_none": "No required channels are configured.",
        "join_channels": "Required channels:\n{items}",
        "join_enabled": "✅ Required membership is ON for {count} channel(s).",
        "join_disabled": "🔴 Required membership is OFF.",
        "join_need_channel": "Add at least one channel before enabling required membership.",
        "join_only_private": "Use /join in a private chat with this bot.",
        "join_added": "✅ Added: {title} ({chat_id})",
        "join_removed": "✅ Removed required channel {chat_id}.",
        "join_remove_missing": "No required channel with ID {chat_id}.",
        "join_verify_error": (
            "Could not verify every configured channel. Check bot admin permissions."
        ),
        "join_bad_chat": "Choose a channel or supergroup.",
        "join_make_admin": "Make this bot an admin in that chat, then retry.",
        "join_private_link": (
            "Give this bot permission to invite users, or provide a private "
            "https://t.me/+... link after the channel ID."
        ),
        "join_access_error": "Could not access that chat. Add this bot as an admin, then retry.",
        "join_invalid_private_link": "Use a valid private Telegram invite link: https://t.me/+...",
        "join_guide": (
            "Commands:\n"
            "/join add @channelname\n"
            "/join remove <chat_id>\n"
            "/join list\n"
            "/join on\n"
            "/join off\n"
            "/join status"
        ),
    },
    LANG_FA: {
        "access_denied": "دسترسی ندارید.",
        "panel_private": "دستور /panel را در گفتگوی خصوصی با ربات باز کنید.",
        "panel_title": (
            "👑 پنل مدیریت\nیک گزینه را انتخاب کنید. مدیریت کاربران سراسری است و "
            "تنظیمات گروه به‌صورت جداگانه مدیریت می‌شود."
        ),
        "only_owner_roles": "فقط مالک ربات می‌تواند نقش ادمین‌ها را تغییر دهد.",
        "target_prompt": (
            "شناسه عددی تلگرام کاربر را ارسال کنید. برای دیدن شناسه خودتان /id بزنید، "
            "یا در گروه روی پیام کاربر ریپلای کرده و دستور مدیریتی را بفرستید."
        ),
        "target_error": "یک شناسه عددی بفرستید یا روی پیام کاربر ریپلای کنید.",
        "target_bot_error": "روی پیام یک کاربر ریپلای کنید یا شناسه عددی او را بفرستید.",
        "target_id_error": "یک شناسه عددی معتبر و مثبت تلگرام وارد کنید.",
        "unknown_action": "عملیات مدیریتی نامعتبر است.",
        "ban_done": "کاربر {user_id} از ربات مسدود شد.",
        "unban_done": "مسدودی کاربر {user_id} برداشته شد.",
        "admin_done": "کاربر {user_id} ادمین ربات شد.",
        "unadmin_done": "دسترسی ادمین کاربر {user_id} حذف شد.",
        "reply_guide": (
            "در گروه موردنظر استفاده کنید:\n"
            "/reply add سلام | سلام!\n"
            "/reply remove سلام\n"
            "/reply list\n\n"
            "عبارت باید کامل مطابق پیام باشد و ی/ي و ک/ك یکسان در نظر گرفته می‌شوند."
        ),
        "no_replies": "هنوز پاسخ خودکاری برای این گروه ثبت نشده است.",
        "triggers": "عبارت‌های گروه:\n{items}{suffix}",
        "reply_saved": "پاسخ خودکار برای «{trigger}» ذخیره شد.",
        "reply_removed": "پاسخ خودکار حذف شد.",
        "reply_missing": "عبارت مطابقی پیدا نشد.",
        "settings_title": "⚙️ تنظیمات ادمین\nزبان فعلی: {language_name}",
        "language_changed": "✅ زبان پنل ادمین به فارسی تغییر کرد.",
        "join_title": "🔒 عضویت اجباری",
        "join_status": "وضعیت: {status}\nتعداد کانال‌ها: {count}",
        "on": "روشن",
        "off": "خاموش",
        "join_add_prompt": (
            "@channelname یا -1001234567890 یا "
            "-1001234567890 https://t.me/+invitecode را ارسال کنید."
        ),
        "join_add_help": (
            "برای افزودن کانال:\n"
            "/join add @channelname\n"
            "/join add -1001234567890\n"
            "/join add -1001234567890 https://t.me/+invitecode\n\n"
            "ربات باید در تمام کانال‌های اجباری ادمین باشد."
        ),
        "join_remove_prompt": "شناسه عددی کانال را برای حذف ارسال کنید؛ مثال: -1001234567890",
        "join_remove_help": "برای حذف کانال: /join remove <chat_id>",
        "join_none": "هیچ کانالی برای عضویت اجباری تنظیم نشده است.",
        "join_channels": "کانال‌های عضویت اجباری:\n{items}",
        "join_enabled": "✅ عضویت اجباری برای {count} کانال روشن شد.",
        "join_disabled": "🔴 عضویت اجباری خاموش شد.",
        "join_need_channel": "قبل از روشن‌کردن، حداقل یک کانال اضافه کنید.",
        "join_only_private": "دستور /join را در گفتگوی خصوصی با ربات استفاده کنید.",
        "join_added": "✅ اضافه شد: {title} ({chat_id})",
        "join_removed": "✅ کانال {chat_id} از عضویت اجباری حذف شد.",
        "join_remove_missing": "کانالی با شناسه {chat_id} پیدا نشد.",
        "join_verify_error": "بررسی همه کانال‌ها ممکن نشد. دسترسی ادمین ربات را بررسی کنید.",
        "join_bad_chat": "یک کانال یا سوپرگروه انتخاب کنید.",
        "join_make_admin": "ربات را در آن کانال ادمین کنید و دوباره تلاش کنید.",
        "join_private_link": (
            "به ربات اجازه ساخت لینک دعوت بدهید یا بعد از شناسه کانال یک لینک خصوصی "
            "https://t.me/+... وارد کنید."
        ),
        "join_access_error": "دسترسی به کانال ممکن نشد. ربات را ادمین کنید و دوباره تلاش کنید.",
        "join_invalid_private_link": "یک لینک خصوصی معتبر تلگرام مثل https://t.me/+... وارد کنید.",
        "join_guide": (
            "دستورها:\n"
            "/join add @channelname\n"
            "/join remove <chat_id>\n"
            "/join list\n"
            "/join on\n"
            "/join off\n"
            "/join status"
        ),
    },
}


def button(language: str, key: str) -> str:
    language = language if language in SUPPORTED_LANGUAGES else LANG_EN
    return BUTTONS[language][key]


def button_labels(key: str) -> set[str]:
    return {BUTTONS[language][key] for language in SUPPORTED_LANGUAGES}


def text(language: str, key: str, **kwargs) -> str:
    language = language if language in SUPPORTED_LANGUAGES else LANG_EN
    return TEXTS[language][key].format(**kwargs)


def language_name(language: str) -> str:
    return "فارسی" if language == LANG_FA else "English"
