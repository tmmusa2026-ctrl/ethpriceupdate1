import os
import json
import time
import io
import threading

import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyBboxPatch


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable is not set."
    )

if not TELEGRAM_CHANNEL_ID:
    raise RuntimeError(
        "TELEGRAM_CHANNEL_ID environment variable is not set."
    )

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ETH price movement required for a new notification
PRICE_TRIGGER = 10.0

# Check ETH price every 60 seconds
# This is NOT the notification interval.
CHECK_INTERVAL = 60

SUBSCRIBERS_FILE = "subscribers.json"
STATE_FILE = "bot_state.json"


# ============================================================
# LOAD / SAVE DATA
# ============================================================

subscribers_lock = threading.Lock()


def load_json(filename, default):

    try:

        if not os.path.exists(filename):
            return default

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception as e:

        print(
            f"❌ {filename} load error: {e}"
        )

        return default


def save_json(filename, data):

    try:

        temp_file = filename + ".tmp"

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        os.replace(
            temp_file,
            filename
        )

    except Exception as e:

        print(
            f"❌ {filename} save error: {e}"
        )


# ============================================================
# SUBSCRIBERS
# ============================================================

loaded_subscribers = load_json(
    SUBSCRIBERS_FILE,
    []
)

subscribers = set()

for item in loaded_subscribers:

    try:

        subscribers.add(
            int(item)
        )

    except Exception:

        pass


# ============================================================
# BOT STATE
# ============================================================

state = load_json(
    STATE_FILE,
    {
        "last_sent_price": None
    }
)


# ============================================================
# TELEGRAM SEND MESSAGE
# ============================================================

def send_message(chat_id, text):

    url = f"{TELEGRAM_API}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        if not response.ok:

            print(
                f"❌ Telegram message error "
                f"{response.status_code}: "
                f"{response.text}"
            )

            return False

        return True

    except Exception as e:

        print(
            f"❌ send_message error: {e}"
        )

        return False


# ============================================================
# TELEGRAM SEND PHOTO
# ============================================================

def send_photo(
    chat_id,
    image_buffer,
    caption
):

    url = f"{TELEGRAM_API}/sendPhoto"

    try:

        image_buffer.seek(0)

        files = {
            "photo": (
                "eth_price.png",
                image_buffer,
                "image/png"
            )
        }

        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML"
        }

        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=30
        )

        if not response.ok:

            print(
                f"❌ Telegram photo error "
                f"{response.status_code}: "
                f"{response.text}"
            )

            return False

        return True

    except Exception as e:

        print(
            f"❌ send_photo error: {e}"
        )

        return False


# ============================================================
# TELEGRAM GET UPDATES
# ============================================================

def get_updates(offset=None):

    url = f"{TELEGRAM_API}/getUpdates"

    params = {
        "timeout": 20
    }

    if offset is not None:

        params["offset"] = offset

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            return []

        return data.get(
            "result",
            []
        )

    except Exception as e:

        print(
            f"❌ getUpdates error: {e}"
        )

        return []


# ============================================================
# TELEGRAM LISTENER
# ============================================================

def listen_for_users():

    offset = None

    print(
        "👂 Telegram listener started."
    )

    while True:

        try:

            updates = get_updates(
                offset
            )

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                message = update.get(
                    "message",
                    {}
                )

                if not message:

                    continue

                text = message.get(
                    "text",
                    ""
                ).strip()

                chat = message.get(
                    "chat",
                    {}
                )

                chat_id = chat.get(
                    "id"
                )

                if not chat_id:

                    continue


                # ====================================================
                # /START
                # ====================================================

                if text.startswith("/start"):

                    with subscribers_lock:

                        if chat_id not in subscribers:

                            subscribers.add(
                                chat_id
                            )

                            save_json(
                                SUBSCRIBERS_FILE,
                                list(subscribers)
                            )

                            new_subscriber = True

                        else:

                            new_subscriber = False


                    if new_subscriber:

                        send_message(
                            chat_id,
                            "✅ <b>সাবস্ক্রাইব করা হয়েছে!</b>\n\n"
                            "ETH-এর দাম শেষ update price থেকে "
                            "<b>$30</b> উপরে বা নিচে গেলে "
                            "নতুন price update পাবেন। 🚀\n\n"
                            "বন্ধ করতে /stop পাঠান।"
                        )

                        print(
                            f"✅ New subscriber: {chat_id}"
                        )

                    else:

                        send_message(
                            chat_id,
                            "ℹ️ আপনি ইতিমধ্যেই subscribed আছেন।\n\n"
                            "ETH প্রতি $30 movement হলে "
                            "নতুন update পাবেন।"
                        )


                # ====================================================
                # /STOP
                # ====================================================

                elif text.startswith("/stop"):

                    with subscribers_lock:

                        if chat_id in subscribers:

                            subscribers.remove(
                                chat_id
                            )

                            save_json(
                                SUBSCRIBERS_FILE,
                                list(subscribers)
                            )

                            removed = True

                        else:

                            removed = False


                    if removed:

                        send_message(
                            chat_id,
                            "❌ <b>আপনাকে update list থেকে "
                            "সরিয়ে দেওয়া হয়েছে।</b>\n\n"
                            "আবার update পেতে /start পাঠান।"
                        )

                        print(
                            f"❌ Unsubscribed: {chat_id}"
                        )

                    else:

                        send_message(
                            chat_id,
                            "ℹ️ আপনি বর্তমানে subscribed নন।"
                        )


                # ====================================================
                # /STATUS
                # ====================================================

                elif text.startswith("/status"):

                    with subscribers_lock:

                        count = len(
                            subscribers
                        )

                    last_price = state.get(
                        "last_sent_price"
                    )

                    if last_price is not None:

                        send_message(
                            chat_id,
                            "📊 <b>ETH PRICE BOT STATUS</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            f"💵 Last update: "
                            f"<b>${last_price:,.2f}</b>\n"
                            f"🎯 Trigger: "
                            f"<b>${PRICE_TRIGGER:.0f}</b>\n"
                            f"🔎 Price check: "
                            f"<b>60 seconds</b>"
                        )

                    else:

                        send_message(
                            chat_id,
                            "📊 <b>ETH PRICE BOT STATUS</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            "💵 Last update: <b>Not yet</b>\n"
                            f"🎯 Trigger: "
                            f"<b>${PRICE_TRIGGER:.0f}</b>\n"
                            f"🔎 Price check: "
                            f"<b>60 seconds</b>"
                        )


        except Exception as e:

            print(
                f"❌ Listener error: {e}"
            )

        time.sleep(1)


# ============================================================
# GET ETH PRICE
# ============================================================

def get_eth_price():

    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price"
    )

    params = {
        "ids": "ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    ethereum = data.get(
        "ethereum"
    )

    if not ethereum:

        raise ValueError(
            "Ethereum data missing."
        )

    if "usd" not in ethereum:

        raise ValueError(
            "ETH USD price missing."
        )

    price = float(
        ethereum["usd"]
    )

    change_24h = float(
        ethereum.get(
            "usd_24h_change",
            0
        )
    )

    return {
        "usd": price,
        "usd_24h_change": change_24h
    }


# ============================================================
# DRAW ETH ICON
# ============================================================

def draw_eth_icon(
    ax,
    x,
    y,
    size,
    alpha=0.65
):

    top = (
        x,
        y + size
    )

    left = (
        x - size * 0.55,
        y
    )

    right = (
        x + size * 0.55,
        y
    )

    center = (
        x,
        y - size * 0.12
    )

    bottom = (
        x,
        y - size
    )


    ax.add_patch(
        Polygon(
            [
                top,
                left,
                center
            ],
            closed=True,
            facecolor="white",
            edgecolor="white",
            alpha=alpha
        )
    )


    ax.add_patch(
        Polygon(
            [
                top,
                center,
                right
            ],
            closed=True,
            facecolor="#d9ddff",
            edgecolor="white",
            alpha=alpha
        )
    )


    ax.add_patch(
        Polygon(
            [
                left,
                bottom,
                center
            ],
            closed=True,
            facecolor="#b9c2ff",
            edgecolor="white",
            alpha=alpha
        )
    )


    ax.add_patch(
        Polygon(
            [
                center,
                bottom,
                right
            ],
            closed=True,
            facecolor="#929eff",
            edgecolor="white",
            alpha=alpha
        )
    )


# ============================================================
# CREATE 413 x 108 PRICE CARD
# ============================================================

def create_price_card(price_data):

    price = price_data["usd"]


    # EXACT IMAGE SIZE:
    # 413 x 108 pixels

    WIDTH = 413
    HEIGHT = 108
    DPI = 100


    fig = plt.figure(
        figsize=(
            WIDTH / DPI,
            HEIGHT / DPI
        ),
        dpi=DPI
    )


    ax = fig.add_axes(
        [
            0,
            0,
            1,
            1
        ]
    )


    ax.set_xlim(
        0,
        WIDTH
    )

    ax.set_ylim(
        0,
        HEIGHT
    )

    ax.axis("off")


    # ========================================================
    # BLUE / PURPLE BACKGROUND
    # ========================================================

    ax.set_facecolor(
        "#6675F5"
    )


    # Main background

    ax.add_patch(
        FancyBboxPatch(
            (
                0,
                0
            ),
            WIDTH,
            HEIGHT,
            boxstyle="round,pad=0,rounding_size=2",
            facecolor="#6675F5",
            edgecolor="none"
        )
    )


    # Purple upper area

    ax.add_patch(
        Polygon(
            [
                (0, 108),
                (413, 108),
                (413, 82),
                (310, 99),
                (180, 84),
                (65, 100),
                (0, 90)
            ],
            closed=True,
            facecolor="#725FEA",
            alpha=0.70,
            edgecolor="none"
        )
    )


    # Light blue middle shape

    ax.add_patch(
        Polygon(
            [
                (0, 67),
                (85, 79),
                (170, 63),
                (255, 82),
                (330, 68),
                (413, 79),
                (413, 108),
                (0, 108)
            ],
            closed=True,
            facecolor="#7082F7",
            alpha=0.45,
            edgecolor="none"
        )
    )


    # ========================================================
    # LIGHTNING - LEFT
    # ========================================================

    ax.plot(
        [
            0,
            24,
            17,
            43,
            29,
            51
        ],
        [
            99,
            106,
            97,
            101,
            91,
            94
        ],
        color="white",
        linewidth=2.5,
        alpha=0.85
    )


    # ========================================================
    # LIGHTNING - RIGHT
    # ========================================================

    ax.plot(
        [
            361,
            381,
            375,
            413
        ],
        [
            34,
            53,
            47,
            82
        ],
        color="#d7b0ff",
        linewidth=3,
        alpha=0.90
    )


    ax.plot(
        [
            375,
            394,
            388,
            413
        ],
        [
            38,
            57,
            52,
            75
        ],
        color="#ffffff",
        linewidth=1.4,
        alpha=0.65
    )


    # ========================================================
    # DECORATIVE COINS
    # ========================================================

    coins = [
        (
            97,
            80,
            14
        ),
        (
            313,
            76,
            13
        )
    ]


    for cx, cy, radius in coins:

        ax.add_patch(
            Circle(
                (
                    cx,
                    cy
                ),
                radius,
                facecolor="#ffffff",
                edgecolor="#dfe3ff",
                linewidth=1.5,
                alpha=0.25
            )
        )

        draw_eth_icon(
            ax,
            cx,
            cy,
            7,
            0.65
        )


    # ========================================================
    # TOP CENTER
    # ========================================================

    ax.text(
        207,
        101,
        "ETHEREUM",
        ha="center",
        va="center",
        fontsize=6.3,
        fontweight="bold",
        color="white"
    )


    # ========================================================
    # TOP RIGHT LOGO
    # ========================================================

    ax.text(
        405,
        101,
        "ETH",
        ha="right",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="white"
    )


    ax.text(
        405,
        94,
        "PRICE BOT",
        ha="right",
        va="center",
        fontsize=3.6,
        fontweight="bold",
        color="#eeeeff"
    )


    # ========================================================
    # MAIN PRICE
    # ========================================================

    ax.text(
        207,
        67,
        f"${price:,.0f}",
        ha="center",
        va="center",
        fontsize=34,
        fontweight="bold",
        color="black"
    )


    # ========================================================
    # TELEGRAM PILL
    # ========================================================

    pill = FancyBboxPatch(
        (
            161,
            30
        ),
        94,
        18,
        boxstyle=(
            "round,pad=0.02,"
            "rounding_size=8"
        ),
        facecolor="#8D72E7",
        edgecolor="#BBA9FF",
        linewidth=0.8,
        alpha=0.98
    )

    ax.add_patch(
        pill
    )


    ax.text(
        208,
        39,
        "✈  @eth_price",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#151515"
    )


    # ========================================================
    # POWERED BY
    # ========================================================

    ax.text(
        7,
        8,
        "POWERED BY",
        ha="left",
        va="center",
        fontsize=3.5,
        fontweight="bold",
        color="white"
    )


    ax.text(
        7,
        4,
        "WATCH-ETH",
        ha="left",
        va="center",
        fontsize=3.5,
        fontweight="bold",
        color="white"
    )


    # ========================================================
    # SAVE EXACT SIZE
    # ========================================================

    image_buffer = io.BytesIO()


    fig.savefig(
        image_buffer,
        format="png",
        dpi=DPI,
        facecolor="#6675F5",
        edgecolor="none",
        pad_inches=0
    )


    image_buffer.seek(0)

    plt.close(fig)


    return image_buffer


# ============================================================
# CAPTION
# ============================================================

def format_caption(price_data):

    price = price_data["usd"]

    change = price_data["usd_24h_change"]


    if change >= 0:

        arrow = "📈"

    else:

        arrow = "📉"


    # This creates the text below the image.
    # The username becomes clickable.

    return (
        f'{arrow} ${price:,.0f} '
        f'<a href="https://t.me/tmmusa73">'
        f'@eth_price'
        f'</a>'
    )


# ============================================================
# BROADCAST
# ============================================================

def broadcast_update(price_data):

    print(
        "🎨 Creating ETH price image..."
    )


    try:

        image = create_price_card(
            price_data
        )


    except Exception as e:

        print(
            f"❌ Image creation error: {e}"
        )

        return


    caption = format_caption(
        price_data
    )


    print(
        f"📡 Sending update to channel "
        f"{TELEGRAM_CHANNEL_ID}..."
    )


    success = send_photo(
        TELEGRAM_CHANNEL_ID,
        image,
        caption
    )


    if success:

        print(
            "✅ ETH update sent to channel."
        )

    else:

        print(
            "❌ Failed to send update to channel."
        )


# ============================================================
# PRICE MONITOR
# ============================================================

def price_monitor():

    print(
        "📈 ETH price monitor started."
    )

    print(
        f"🎯 Trigger: ${PRICE_TRIGGER:.0f}"
    )

    print(
        f"🔎 Checking every "
        f"{CHECK_INTERVAL} seconds."
    )


    while True:

        try:

            price_data = get_eth_price()

            current_price = price_data[
                "usd"
            ]

            last_sent_price = state.get(
                "last_sent_price"
            )


            # ==================================================
            # FIRST UPDATE
            # ==================================================

            if last_sent_price is None:

                print(
                    f"💵 Current ETH: "
                    f"${current_price:,.2f}"
                )


                print(
                    "🚀 Sending first update to channel..."
                )


                broadcast_update(
                    price_data
                )


                state[
                    "last_sent_price"
                ] = current_price


                save_json(
                    STATE_FILE,
                    state
                )


            # ==================================================
            # NORMAL $30 MOVEMENT CHECK
            # ==================================================

            else:

                movement = abs(
                    current_price -
                    last_sent_price
                )


                print(
                    f"💵 ETH: "
                    f"${current_price:,.2f} | "
                    f"Last: "
                    f"${last_sent_price:,.2f} | "
                    f"Movement: "
                    f"${movement:,.2f}"
                )


                if movement >= PRICE_TRIGGER:

                    if current_price > last_sent_price:

                        print(
                            "📈 ETH moved UP."
                        )

                    else:

                        print(
                            "📉 ETH moved DOWN."
                        )


                    print(
                        "🚨 $30 trigger reached!"
                    )


                    broadcast_update(
                        price_data
                    )


                    # New reference price

                    state[
                        "last_sent_price"
                    ] = current_price


                    save_json(
                        STATE_FILE,
                        state
                    )


                    print(
                        f"✅ New reference: "
                        f"${current_price:,.2f}"
                    )


                else:

                    remaining = (
                        PRICE_TRIGGER -
                        movement
                    )


                    print(
                        f"⏳ ${remaining:,.2f} "
                        f"movement remaining."
                    )


        except requests.exceptions.RequestException as e:

            print(
                f"🌐 API error: {e}"
            )


        except Exception as e:

            print(
                f"❌ Price monitor error: {e}"
            )


        time.sleep(
            CHECK_INTERVAL
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=============================================="
    )

    print(
        "🚀 ETH PRICE MOVEMENT TELEGRAM BOT"
    )

    print(
        "=============================================="
    )

    print(
        f"📢 Channel: "
        f"{TELEGRAM_CHANNEL_ID}"
    )

    print(
        f"🎯 Price trigger: "
        f"${PRICE_TRIGGER:.2f}"
    )

    print(
        f"🔎 Check interval: "
        f"{CHECK_INTERVAL} seconds"
    )

    print(
        "🖼️ Image size: 413 x 108 px"
    )

    print(
        "📊 7-day chart: OFF"
    )

    print(
        "=============================================="
    )


    # ETH price monitor

    monitor_thread = threading.Thread(
        target=price_monitor,
        daemon=True
    )

    monitor_thread.start()


    # Keep Railway worker alive

    while True:

        time.sleep(60)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
