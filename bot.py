import os
import json
import time
import io
import threading

import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyBboxPatch


# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable is not set."
    )

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ETH price must move this amount from the last sent price
PRICE_TRIGGER = 30.0

# Price check interval.
# This is NOT the notification interval.
CHECK_INTERVAL = 60

# Permanent storage files
SUBSCRIBERS_FILE = "subscribers.json"
STATE_FILE = "bot_state.json"


# ============================================================
# GLOBAL DATA
# ============================================================

subscribers_lock = threading.Lock()


def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as e:
        print(f"❌ {filename} load error: {e}")
        return default


def save_json(filename, data):
    try:
        temp_filename = filename + ".tmp"

        with open(temp_filename, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False
            )

        os.replace(temp_filename, filename)

    except Exception as e:
        print(f"❌ {filename} save error: {e}")


# Load subscribers
loaded_subscribers = load_json(
    SUBSCRIBERS_FILE,
    []
)

subscribers = set()

for item in loaded_subscribers:
    try:
        subscribers.add(int(item))
    except Exception:
        pass


# Load bot state
state = load_json(
    STATE_FILE,
    {
        "last_sent_price": None
    }
)


# ============================================================
# TELEGRAM - SEND MESSAGE
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
                f"{response.status_code}: {response.text}"
            )

            return False

        return True

    except Exception as e:

        print(
            f"❌ send_message error: {e}"
        )

        return False


# ============================================================
# TELEGRAM - SEND PHOTO
# ============================================================

def send_photo_with_caption(
    chat_id,
    photo_buffer,
    caption=""
):

    url = f"{TELEGRAM_API}/sendPhoto"

    try:

        photo_buffer.seek(0)

        files = {
            "photo": (
                "eth_price.png",
                photo_buffer,
                "image/png"
            )
        }

        data = {
            "chat_id": chat_id,
            "parse_mode": "HTML"
        }

        if caption:
            data["caption"] = caption

        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=30
        )

        if not response.ok:

            print(
                f"❌ Telegram photo error "
                f"{response.status_code}: {response.text}"
            )

            return False

        return True

    except Exception as e:

        print(
            f"❌ send_photo error: {e}"
        )

        return False


# ============================================================
# TELEGRAM - GET UPDATES
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

        result = response.json()

        if not result.get("ok"):
            return []

        return result.get(
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

    print("👂 Telegram listener started.")

    while True:

        try:

            updates = get_updates(offset)

            for update in updates:

                offset = update["update_id"] + 1

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
                            "ETH-এর দাম শেষবারের update price থেকে "
                            "<b>$30</b> উপরে বা নিচে গেলে নতুন price update পাবেন। 🚀\n\n"
                            "বন্ধ করতে /stop পাঠান।"
                        )

                        print(
                            f"✅ New subscriber: {chat_id}"
                        )

                    else:

                        send_message(
                            chat_id,
                            "ℹ️ আপনি ইতিমধ্যেই subscribed আছেন।\n\n"
                            "ETH প্রতি $30 movement হলে নতুন update পাবেন। 📈"
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
                            "❌ <b>আপনাকে update list থেকে সরিয়ে দেওয়া হয়েছে।</b>\n\n"
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
                        count = len(subscribers)

                    last_price = state.get(
                        "last_sent_price"
                    )

                    if last_price is not None:

                        send_message(
                            chat_id,
                            "📊 <b>ETH PRICE BOT STATUS</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            f"💵 Last update: <b>${last_price:,.2f}</b>\n"
                            f"🎯 Trigger: <b>${PRICE_TRIGGER:.0f}</b>\n"
                            f"🔎 Check: <b>60 seconds</b>"
                        )

                    else:

                        send_message(
                            chat_id,
                            "📊 <b>ETH PRICE BOT STATUS</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            "💵 Last update: <b>Not yet</b>\n"
                            f"🎯 Trigger: <b>${PRICE_TRIGGER:.0f}</b>\n"
                            f"🔎 Check: <b>60 seconds</b>"
                        )


        except Exception as e:

            print(
                f"❌ Listener error: {e}"
            )

        time.sleep(1)


# ============================================================
# GET CURRENT ETH PRICE
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
# DRAW ETHEREUM ICON
# ============================================================

def draw_eth_icon(
    ax,
    x,
    y,
    size,
    alpha=0.8
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


    # Left upper
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


    # Right upper
    ax.add_patch(
        Polygon(
            [
                top,
                center,
                right
            ],
            closed=True,
            facecolor="#d8e0ff",
            edgecolor="white",
            alpha=alpha
        )
    )


    # Left lower
    ax.add_patch(
        Polygon(
            [
                left,
                bottom,
                center
            ],
            closed=True,
            facecolor="#b6c4ff",
            edgecolor="white",
            alpha=alpha
        )
    )


    # Right lower
    ax.add_patch(
        Polygon(
            [
                center,
                bottom,
                right
            ],
            closed=True,
            facecolor="#899cff",
            edgecolor="white",
            alpha=alpha
        )
    )


# ============================================================
# CREATE PREMIUM ETH PRICE CARD
# ============================================================

def create_price_card(price_data):

    price = price_data["usd"]

    change_24h = price_data[
        "usd_24h_change"
    ]


    # --------------------------------------------------------
    # Canvas
    # --------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(12, 7),
        dpi=130
    )

    ax.set_xlim(
        0,
        1200
    )

    ax.set_ylim(
        0,
        700
    )

    ax.axis("off")


    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    fig.patch.set_facecolor(
        "#6574F5"
    )

    ax.set_facecolor(
        "#6574F5"
    )


    # Main background blocks

    ax.add_patch(
        FancyBboxPatch(
            (
                0,
                0
            ),
            1200,
            700,
            boxstyle="round,pad=0",
            facecolor="#6675F6",
            edgecolor="none"
        )
    )


    # --------------------------------------------------------
    # Purple gradient-style decorative panels
    # --------------------------------------------------------

    ax.add_patch(
        Polygon(
            [
                (0, 700),
                (1200, 700),
                (1200, 490),
                (850, 600),
                (400, 500),
                (0, 590)
            ],
            closed=True,
            facecolor="#5866E8",
            alpha=0.65,
            edgecolor="none"
        )
    )


    ax.add_patch(
        Polygon(
            [
                (0, 0),
                (1200, 0),
                (1200, 170),
                (900, 110),
                (500, 180),
                (0, 100)
            ],
            closed=True,
            facecolor="#765BEA",
            alpha=0.45,
            edgecolor="none"
        )
    )


    # --------------------------------------------------------
    # Lightning decorations
    # --------------------------------------------------------

    ax.plot(
        [
            0,
            85,
            48,
            155
        ],
        [
            620,
            680,
            625,
            690
        ],
        color="white",
        linewidth=9,
        alpha=0.75
    )


    ax.plot(
        [
            1040,
            1200
        ],
        [
            95,
            260
        ],
        color="#d6b2ff",
        linewidth=10,
        alpha=0.85
    )


    ax.plot(
        [
            1090,
            1200
        ],
        [
            80,
            195
        ],
        color="white",
        linewidth=5,
        alpha=0.4
    )


    # --------------------------------------------------------
    # Decorative circles
    # --------------------------------------------------------

    decorative_coins = [
        (
            120,
            565,
            42
        ),
        (
            1055,
            570,
            40
        ),
        (
            965,
            125,
            30
        )
    ]


    for cx, cy, radius in decorative_coins:

        ax.add_patch(
            Circle(
                (
                    cx,
                    cy
                ),
                radius,
                facecolor="#ffffff",
                edgecolor="#dce1ff",
                linewidth=3,
                alpha=0.20
            )
        )


    # --------------------------------------------------------
    # ETH icons
    # --------------------------------------------------------

    draw_eth_icon(
        ax,
        120,
        565,
        25,
        0.75
    )

    draw_eth_icon(
        ax,
        1055,
        570,
        25,
        0.70
    )

    draw_eth_icon(
        ax,
        965,
        125,
        18,
        0.40
    )


    # --------------------------------------------------------
    # Top right ETH PRICE BOT
    # --------------------------------------------------------

    ax.text(
        1160,
        660,
        "ETH",
        ha="right",
        va="center",
        fontsize=22,
        fontweight="bold",
        color="white"
    )

    ax.text(
        1160,
        635,
        "PRICE BOT",
        ha="right",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#e7e9ff"
    )


    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    ax.text(
        600,
        650,
        "ETHEREUM",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="bold",
        color="#f0f1ff"
    )


    # --------------------------------------------------------
    # Main price
    # --------------------------------------------------------

    ax.text(
        600,
        405,
        f"${price:,.0f}",
        ha="center",
        va="center",
        fontsize=76,
        fontweight="bold",
        color="black"
    )


    # --------------------------------------------------------
    # 24H movement
    # --------------------------------------------------------

    if change_24h >= 0:

        change_text = (
            f"▲ +{change_24h:.2f}%  24H"
        )

        change_color = "#d9ffe9"

    else:

        change_text = (
            f"▼ {change_24h:.2f}%  24H"
        )

        change_color = "#ffe1e5"


    ax.text(
        600,
        315,
        change_text,
        ha="center",
        va="center",
        fontsize=21,
        fontweight="bold",
        color=change_color
    )


    # --------------------------------------------------------
    # Telegram username pill
    # --------------------------------------------------------

    pill = FancyBboxPatch(
        (
            455,
            220
        ),
        290,
        65,
        boxstyle="round,pad=0.02,rounding_size=28",
        facecolor="#8A69E8",
        edgecolor="#b9a6ff",
        linewidth=2,
        alpha=0.95
    )

    ax.add_patch(
        pill
    )


    ax.text(
        600,
        252,
        "✈  @eth_price",
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color="white"
    )


    # --------------------------------------------------------
    # Bottom branding
    # --------------------------------------------------------

    ax.text(
        35,
        38,
        "POWERED BY WATCH-ETH",
        ha="left",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#f0f1ff",
        alpha=0.9
    )


    ax.text(
        1165,
        38,
        "ETH / USD",
        ha="right",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="white",
        alpha=0.9
    )


    # --------------------------------------------------------
    # Save to memory
    # --------------------------------------------------------

    plt.subplots_adjust(
        left=0,
        right=1,
        top=1,
        bottom=0
    )

    image_buffer = io.BytesIO()

    plt.savefig(
        image_buffer,
        format="png",
        dpi=130,
        bbox_inches="tight",
        pad_inches=0,
        facecolor=fig.get_facecolor()
    )

    image_buffer.seek(0)

    plt.close(fig)

    return image_buffer


# ============================================================
# CAPTION
# ============================================================

def format_caption(price_data):

    # Main information is already inside the image.
    # Keep Telegram caption empty.

    return ""


# ============================================================
# SEND UPDATE TO ALL SUBSCRIBERS
# ============================================================

def broadcast_update(price_data):

    print(
        "🎨 Premium ETH price card তৈরি হচ্ছে..."
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


    with subscribers_lock:

        current_subscribers = list(
            subscribers
        )


    if not current_subscribers:

        print(
            "⏳ কোনো subscriber নেই।"
        )

        return


    print(
        f"📡 {len(current_subscribers)} জনকে image পাঠানো হচ্ছে..."
    )


    failed_users = []


    for chat_id in current_subscribers:

        success = send_photo_with_caption(
            chat_id,
            image,
            caption
        )


        if success:

            print(
                f"✅ Sent: {chat_id}"
            )

        else:

            print(
                f"❌ Failed: {chat_id}"
            )

            failed_users.append(
                chat_id
            )


        time.sleep(0.25)


    # Remove failed users
    if failed_users:

        with subscribers_lock:

            for chat_id in failed_users:

                subscribers.discard(
                    chat_id
                )


            save_json(
                SUBSCRIBERS_FILE,
                list(subscribers)
            )


        print(
            f"🗑️ {len(failed_users)} invalid subscriber removed."
        )


    print(
        "✅ সবাইকে ETH price card পাঠানো হয়েছে!"
    )


# ============================================================
# PRICE MONITOR
# ============================================================

def price_monitor():

    print(
        "📈 ETH price monitor started."
    )

    print(
        f"🎯 Price trigger: ${PRICE_TRIGGER:.2f}"
    )

    print(
        f"🔎 Price check: every {CHECK_INTERVAL} seconds"
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


            if last_sent_price is None:

                print(
                    f"💵 ETH: ${current_price:,.2f}"
                )

                with subscribers_lock:

                    has_subscribers = bool(
                        subscribers
                    )


                if has_subscribers:

                    print(
                        "🚀 প্রথম ETH update পাঠানো হচ্ছে..."
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


                else:

                    print(
                        "⏳ Subscriber নেই।"
                    )


            else:

                movement = abs(
                    current_price -
                    last_sent_price
                )


                print(
                    f"💵 ETH: ${current_price:,.2f} | "
                    f"Last update: ${last_sent_price:,.2f} | "
                    f"Movement: ${movement:,.2f}"
                )


                # ==================================================
                # $30 MOVEMENT REACHED
                # ==================================================

                if movement >= PRICE_TRIGGER:

                    if current_price > last_sent_price:

                        direction = "📈 UP"

                    else:

                        direction = "📉 DOWN"


                    print(
                        f"🚨 ${movement:,.2f} movement detected! "
                        f"{direction}"
                    )


                    with subscribers_lock:

                        has_subscribers = bool(
                            subscribers
                        )


                    if has_subscribers:

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
                            f"✅ New reference price: "
                            f"${current_price:,.2f}"
                        )


                    else:

                        state[
                            "last_sent_price"
                        ] = current_price


                        save_json(
                            STATE_FILE,
                            state
                        )


                else:

                    remaining = (
                        PRICE_TRIGGER -
                        movement
                    )


                    print(
                        f"⏳ Next update-এর জন্য "
                        f"${remaining:,.2f} movement বাকি."
                    )


        except requests.exceptions.RequestException as e:

            print(
                f"🌐 CoinGecko/API error: {e}"
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
        "=================================================="
    )

    print(
        "🚀 ETH $30 MOVEMENT TELEGRAM PRICE BOT"
    )

    print(
        "=================================================="
    )

    print(
        f"👥 Subscribers: {len(subscribers)}"
    )

    print(
        f"🎯 Price trigger: ${PRICE_TRIGGER:.2f}"
    )

    print(
        f"🔎 Check interval: {CHECK_INTERVAL} seconds"
    )

    print(
        "🖼️ Premium price card: ENABLED"
    )

    print(
        "📊 7-day chart: DISABLED"
    )

    print(
        "=================================================="
    )


    # --------------------------------------------------------
    # Telegram listener thread
    # --------------------------------------------------------

    listener = threading.Thread(
        target=listen_for_users,
        daemon=True
    )

    listener.start()


    # --------------------------------------------------------
    # ETH price monitor thread
    # --------------------------------------------------------

    monitor = threading.Thread(
        target=price_monitor,
        daemon=True
    )

    monitor.start()


    # --------------------------------------------------------
    # Keep Railway worker alive
    # --------------------------------------------------------

    while True:

        time.sleep(60)


# ============================================================
# PYTHON ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
