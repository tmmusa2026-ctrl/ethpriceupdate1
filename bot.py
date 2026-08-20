import os
import json
import time
import io
import threading
from datetime import datetime

import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# =========================================================
# CONFIG
# =========================================================

# Linux / VPS:
# export TELEGRAM_BOT_TOKEN="8744254991:AAE4Xayr01TjdBy16ESBwON6wFke0MMYt48"

# Windows:
# set TELEGRAM_BOT_TOKEN=YOUR_NEW_BOT_TOKEN

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable is not set."
    )

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

SUBSCRIBERS_FILE = "subscribers.json"
STATE_FILE = "bot_state.json"

# ETH must move at least $30 from the last sent price
PRICE_TRIGGER = 30.0

# How often the bot checks the ETH price.
# This is NOT the notification interval.
CHECK_INTERVAL = 60  # 60 seconds


# =========================================================
# FILE / STATE FUNCTIONS
# =========================================================

def load_json(filename, default):
    try:
        if not os.path.exists(filename):
            return default

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:
        print(f"❌ {filename} load error:", e)
        return default


def save_json(filename, data):
    try:
        temp_file = filename + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        os.replace(temp_file, filename)

    except Exception as e:
        print(f"❌ {filename} save error:", e)


subscribers_lock = threading.Lock()

subscribers = set(
    int(x) for x in load_json(SUBSCRIBERS_FILE, [])
)

state = load_json(
    STATE_FILE,
    {
        "last_sent_price": None
    }
)


# =========================================================
# TELEGRAM
# =========================================================

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
                f"❌ Telegram sendMessage error "
                f"{response.status_code}: {response.text}"
            )

        return response.ok

    except Exception as e:
        print(f"❌ send_message error: {e}")
        return False


def send_photo_with_caption(chat_id, photo_buf, caption):
    url = f"{TELEGRAM_API}/sendPhoto"

    try:
        photo_buf.seek(0)

        files = {
            "photo": (
                "eth_chart.png",
                photo_buf,
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
                f"❌ Telegram sendPhoto error "
                f"{response.status_code}: {response.text}"
            )

        return response.ok

    except Exception as e:
        print(f"❌ send_photo error: {e}")
        return False


# =========================================================
# TELEGRAM UPDATES
# =========================================================

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

        return data.get("result", [])

    except Exception as e:
        print(f"❌ getUpdates error: {e}")
        return []


def listen_for_users():
    offset = None

    print("👂 Telegram listener চালু হয়েছে...")

    while True:

        try:
            updates = get_updates(offset)

            for update in updates:

                offset = update["update_id"] + 1

                message = update.get("message", {})

                if not message:
                    continue

                text = message.get("text", "").strip()
                chat_id = message.get("chat", {}).get("id")

                if not chat_id:
                    continue


                # =============================================
                # START
                # =============================================

                if text.startswith("/start"):

                    with subscribers_lock:

                        if chat_id not in subscribers:

                            subscribers.add(chat_id)

                            save_json(
                                SUBSCRIBERS_FILE,
                                list(subscribers)
                            )

                            added = True

                        else:
                            added = False


                    if added:

                        send_message(
                            chat_id,
                            "✅ <b>সাবস্ক্রাইব করা হয়েছে!</b>\n\n"
                            "ETH-এর দাম শেষবারের পাঠানো দামের তুলনায় "
                            "<b>$30</b> উপরে বা নিচে গেলে নতুন update পাবেন। 🚀\n\n"
                            "বন্ধ করতে /stop পাঠান।"
                        )

                        print(
                            f"✅ নতুন subscriber: {chat_id}"
                        )

                    else:

                        send_message(
                            chat_id,
                            "ℹ️ আপনি ইতিমধ্যেই subscribed আছেন।\n\n"
                            "ETH প্রতি $30 movement হলে update পাবেন। 📈"
                        )


                # =============================================
                # STOP
                # =============================================

                elif text.startswith("/stop"):

                    with subscribers_lock:

                        if chat_id in subscribers:

                            subscribers.discard(chat_id)

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
                            "❌ আপনাকে update list থেকে সরিয়ে দেওয়া হয়েছে।\n\n"
                            "আবার পেতে /start পাঠান।"
                        )

                        print(
                            f"❌ Unsubscribed: {chat_id}"
                        )

                    else:

                        send_message(
                            chat_id,
                            "ℹ️ আপনি বর্তমানে subscribed নন।"
                        )


                # =============================================
                # STATUS
                # =============================================

                elif text.startswith("/status"):

                    with subscribers_lock:
                        count = len(subscribers)

                    last_price = state.get("last_sent_price")

                    if last_price:

                        send_message(
                            chat_id,
                            f"📊 <b>ETH Bot Status</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            f"💵 Last update price: "
                            f"<b>${last_price:,.2f}</b>\n"
                            f"🎯 Trigger: <b>$30 movement</b>"
                        )

                    else:

                        send_message(
                            chat_id,
                            f"📊 <b>ETH Bot Status</b>\n\n"
                            f"👥 Subscribers: <b>{count}</b>\n"
                            f"🎯 Trigger: <b>$30 movement</b>"
                        )


        except Exception as e:
            print(f"❌ Listener error: {e}")

        time.sleep(1)


# =========================================================
# ETH PRICE
# =========================================================

def get_eth_price():

    url = "https://api.coingecko.com/api/v3/simple/price"

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

    eth = data.get("ethereum")

    if not eth or "usd" not in eth:
        raise ValueError("Invalid ETH price response")

    return {
        "usd": float(eth["usd"]),
        "usd_24h_change": float(
            eth.get("usd_24h_change", 0)
        )
    }


# =========================================================
# 7 DAY CHART DATA
# =========================================================

def get_eth_chart_data():

    url = (
        "https://api.coingecko.com/api/v3/"
        "coins/ethereum/market_chart"
    )

    params = {
        "vs_currency": "usd",
        "days": "7",
        "interval": "hourly"
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    prices = data.get("prices")

    if not prices:
        raise ValueError("No chart data received")

    times = [
        datetime.fromtimestamp(timestamp / 1000)
        for timestamp, price in prices
    ]

    values = [
        float(price)
        for timestamp, price in prices
    ]

    return times, values


# =========================================================
# CREATE CHART
# =========================================================

def create_chart(
    times,
    values,
    current_price,
    change_24h
):

    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    if change_24h >= 0:
        color = "#00ff88"
    else:
        color = "#ff4444"

    ax.plot(
        times,
        values,
        color=color,
        linewidth=2.5,
        zorder=3
    )

    ax.fill_between(
        times,
        values,
        min(values),
        color=color,
        alpha=0.08,
        zorder=2
    )

    ax.grid(
        color="#1e2530",
        linewidth=0.8,
        linestyle="--",
        alpha=0.7
    )

    ax.set_axisbelow(True)

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d %b")
    )

    ax.xaxis.set_major_locator(
        mdates.DayLocator()
    )

    plt.xticks(
        color="#aaaaaa",
        fontsize=9
    )

    plt.yticks(
        color="#aaaaaa",
        fontsize=9
    )

    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(
            lambda x, _: f"${x:,.0f}"
        )
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    arrow = "▲" if change_24h >= 0 else "▼"
    sign = "+" if change_24h >= 0 else ""

    ax.set_title(
        f"ETH/USD  ${current_price:,.2f}   "
        f"{arrow} {sign}{change_24h:.2f}%  (7 Days)",
        color=color,
        fontsize=14,
        fontweight="bold",
        pad=15
    )

    ax.scatter(
        [times[-1]],
        [values[-1]],
        color=color,
        s=60,
        zorder=5
    )

    ax.annotate(
        f"${values[-1]:,.0f}",
        (times[-1], values[-1]),
        textcoords="offset points",
        xytext=(-60, 10),
        color=color,
        fontsize=9,
        fontweight="bold"
    )

    plt.tight_layout()

    buf = io.BytesIO()

    plt.savefig(
        buf,
        format="png",
        dpi=130,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    buf.seek(0)

    plt.close(fig)

    return buf


# =========================================================
# CAPTION
# =========================================================

def format_caption(price_data):

    usd = price_data["usd"]
    change_24h = price_data["usd_24h_change"]

    arrow = "🟢" if change_24h >= 0 else "🔴"

    sign = "+" if change_24h >= 0 else ""

    return (
        f'{arrow} <b>ETH ${usd:,.0f}</b>\n'
        f'24H: {sign}{change_24h:.2f}%\n\n'
        f'<a href="https://t.me/tmmusa73">@eth_price</a>'
    )


# =========================================================
# BROADCAST UPDATE
# =========================================================

def broadcast_update(price_data):

    global subscribers

    print("📊 Chart data নেওয়া হচ্ছে...")

    times, values = get_eth_chart_data()

    chart = create_chart(
        times,
        values,
        price_data["usd"],
        price_data["usd_24h_change"]
    )

    caption = format_caption(price_data)

    with subscribers_lock:
        current_subscribers = list(subscribers)

    print(
        f"📡 {len(current_subscribers)} জনকে update পাঠানো হচ্ছে..."
    )

    failed = []

    for chat_id in current_subscribers:

        success = send_photo_with_caption(
            chat_id,
            chart,
            caption
        )

        if not success:
            failed.append(chat_id)

        time.sleep(0.2)

    # Invalid / blocked users remove
    if failed:

        with subscribers_lock:

            for chat_id in failed:
                subscribers.discard(chat_id)

            save_json(
                SUBSCRIBERS_FILE,
                list(subscribers)
            )

        print(
            f"🗑️ {len(failed)} জন subscriber remove করা হয়েছে।"
        )

    print("✅ ETH update পাঠানো সম্পন্ন।")


# =========================================================
# MAIN PRICE MONITOR
# =========================================================

def price_monitor():

    print("📈 ETH price monitor চালু হয়েছে.")
    print(f"🎯 Trigger: ${PRICE_TRIGGER:.0f} movement")
    print(f"🔎 Check every: {CHECK_INTERVAL} seconds")

    while True:

        try:

            price_data = get_eth_price()

            current_price = price_data["usd"]

            last_sent_price = state.get(
                "last_sent_price"
            )

            print(
                f"💵 ETH: ${current_price:,.2f} | "
                f"Last: "
                f"{('$' + format(last_sent_price, ',.2f')) if last_sent_price else 'Not set'}"
            )


            # =================================================
            # FIRST RUN
            # =================================================

            if last_sent_price is None:

                if subscribers:

                    print(
                        "🚀 প্রথম update পাঠানো হচ্ছে..."
                    )

                    broadcast_update(price_data)

                    state["last_sent_price"] = current_price

                    save_json(
                        STATE_FILE,
                        state
                    )

                else:

                    print(
                        "⏳ Subscriber নেই। "
                        "প্রথম subscriber আসা পর্যন্ত অপেক্ষা করছি..."
                    )


            # =================================================
            # $30 MOVEMENT
            # =================================================

            else:

                movement = abs(
                    current_price - last_sent_price
                )

                if movement >= PRICE_TRIGGER:

                    direction = (
                        "📈 UP"
                        if current_price > last_sent_price
                        else "📉 DOWN"
                    )

                    print(
                        f"🚨 ${movement:,.2f} movement detected! "
                        f"{direction}"
                    )

                    with subscribers_lock:
                        has_subscribers = bool(subscribers)

                    if has_subscribers:

                        broadcast_update(
                            price_data
                        )

                        # IMPORTANT:
                        # New reference price becomes
                        # the price at which the update was sent.

                        state["last_sent_price"] = current_price

                        save_json(
                            STATE_FILE,
                            state
                        )

                        print(
                            f"✅ New reference price: "
                            f"${current_price:,.2f}"
                        )

                    else:

                        # No subscribers.
                        # Reset reference price so the first
                        # subscriber gets a fresh update.

                        state["last_sent_price"] = current_price

                        save_json(
                            STATE_FILE,
                            state
                        )

                else:

                    remaining = (
                        PRICE_TRIGGER - movement
                    )

                    print(
                        f"⏳ Trigger পর্যন্ত "
                        f"${remaining:,.2f} বাকি..."
                    )


        except Exception as e:

            print(
                f"❌ Price monitor error: {e}"
            )

        time.sleep(CHECK_INTERVAL)


# =========================================================
# START BOT
# =========================================================

def main():

    print("=" * 50)
    print("🚀 ETH $30 MOVEMENT TELEGRAM BOT")
    print("=" * 50)

    print(
        f"👥 Subscribers: {len(subscribers)}"
    )

    print(
        f"🎯 Price trigger: ${PRICE_TRIGGER:.2f}"
    )

    print(
        f"🔎 Check interval: {CHECK_INTERVAL}s"
    )

    print("=" * 50)


    # Telegram listener
    listener_thread = threading.Thread(
        target=listen_for_users,
        daemon=True
    )

    listener_thread.start()


    # Price monitor
    monitor_thread = threading.Thread(
        target=price_monitor,
        daemon=True
    )

    monitor_thread.start()


    # Keep program alive
    while True:

        time.sleep(60)


# =========================================================
# CORRECT PYTHON ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
