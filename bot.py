import os
import json
import time
import io

import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyBboxPatch


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable is not set."
    )

if not CHANNEL_ID:
    raise RuntimeError(
        "TELEGRAM_CHANNEL_ID environment variable is not set."
    )

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ============================================================
# PRICE UPDATE INTERVAL
# ============================================================

# 10 minutes = 600 seconds
CHECK_INTERVAL = 600


# ============================================================
# STATE FILE
# ============================================================

STATE_FILE = "bot_state.json"


# ============================================================
# LOAD / SAVE JSON
# ============================================================

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
# BOT STATE
# ============================================================

state = load_json(
    STATE_FILE,
    {
        "last_sent_price": None
    }
)


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
# TELEGRAM TEST
# ============================================================

def test_telegram():

    url = f"{TELEGRAM_API}/getMe"

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            print(
                "❌ Telegram bot verification failed."
            )

            return False

        bot_username = (
            data.get("result", {})
            .get("username", "Unknown")
        )

        print(
            f"🤖 Telegram bot connected: "
            f"@{bot_username}"
        )

        print(
            f"📢 Channel: {CHANNEL_ID}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Telegram connection error: {e}"
        )

        return False


# ============================================================
# GET ETH PRICE FROM BINANCE
# ============================================================

def get_eth_price():

    url = (
        "https://api.binance.com/"
        "api/v3/ticker/price"
    )

    params = {
        "symbol": "ETHUSDT"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if "price" not in data:

        raise ValueError(
            "Binance ETH price missing."
        )

    price = float(
        data["price"]
    )

    return {
        "usd": price,
        "usd_24h_change": 0
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


    ax.add_patch(
        FancyBboxPatch(
            (
                0,
                0
            ),
            WIDTH,
            HEIGHT,
            boxstyle=(
                "round,pad=0,"
                "rounding_size=2"
            ),
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
    # TOP RIGHT
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
    # TELEGRAM USERNAME PILL
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
        "@import os
import json
import time
import io

import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyBboxPatch


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not BOT_TOKEN:
    raise RuntimeError(
        "TELEGRAM_BOT_TOKEN environment variable is not set."
    )

if not CHANNEL_ID:
    raise RuntimeError(
        "TELEGRAM_CHANNEL_ID environment variable is not set."
    )

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ============================================================
# PRICE UPDATE INTERVAL
# ============================================================

# 10 minutes = 600 seconds
CHECK_INTERVAL = 600


# ============================================================
# STATE FILE
# ============================================================

STATE_FILE = "bot_state.json"


# ============================================================
# LOAD / SAVE JSON
# ============================================================

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
# BOT STATE
# ============================================================

state = load_json(
    STATE_FILE,
    {
        "last_sent_price": None
    }
)


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
# TELEGRAM TEST
# ============================================================

def test_telegram():

    url = f"{TELEGRAM_API}/getMe"

    try:

        response = requests.get(
            url,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):

            print(
                "❌ Telegram bot verification failed."
            )

            return False

        bot_username = (
            data.get("result", {})
            .get("username", "Unknown")
        )

        print(
            f"🤖 Telegram bot connected: "
            f"@{bot_username}"
        )

        print(
            f"📢 Channel: {CHANNEL_ID}"
        )

        return True

    except Exception as e:

        print(
            f"❌ Telegram connection error: {e}"
        )

        return False


# ============================================================
# GET ETH PRICE FROM BINANCE
# ============================================================

def get_eth_price():

    url = (
        "https://api.binance.com/"
        "api/v3/ticker/price"
    )

    params = {
        "symbol": "ETHUSDT"
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if "price" not in data:

        raise ValueError(
            "Binance ETH price missing."
        )

    price = float(
        data["price"]
    )

    return {
        "usd": price,
        "usd_24h_change": 0
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


    ax.add_patch(
        FancyBboxPatch(
            (
                0,
                0
            ),
            WIDTH,
            HEIGHT,
            boxstyle=(
                "round,pad=0,"
                "rounding_size=2"
            ),
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
    # TOP RIGHT
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
    # TELEGRAM USERNAME PILL
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
        fontsize=7.8,
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
        "BINANCE",
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

def format_caption(
    price_data,
    previous_price=None
):

    price = price_data["usd"]


    # ========================================================
    # PRICE DIRECTION
    # ========================================================

    if previous_price is None:

        arrow = "📈"

    elif price > previous_price:

        arrow = "📈"

    elif price < previous_price:

        arrow = "📉"

    else:

        arrow = "📈"


    # ========================================================
    # CAPTION
    # ========================================================

    return (
        f'{arrow} ${price:,.2f} '
        f'<a href="https://t.me/tmmusa73">'
        f'@eth_price'
        f'</a>'
    )


# ============================================================
# SEND UPDATE TO CHANNEL
# ============================================================

def send_channel_update(
    price_data,
    previous_price=None
):

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

        return False


    caption = format_caption(
        price_data,
        previous_price
    )


    print(
        f"📡 Sending update to "
        f"{CHANNEL_ID}..."
    )


    success = send_photo(
        CHANNEL_ID,
        image,
        caption
    )


    if success:

        print(
            "✅ Channel update sent successfully."
        )

        return True


    print(
        "❌ Failed to send channel update."
    )

    return False


# ============================================================
# PRICE MONITOR
# ============================================================

def price_monitor():

    print(
        "📈 ETH price monitor started."
    )

    print(
        "💱 Price source: Binance"
    )

    print(
        "💰 Symbol: ETHUSDT"
    )

    print(
        f"📢 Channel: {CHANNEL_ID}"
    )

    print(
        "⏰ Update interval: 10 minutes"
    )


    while True:

        try:

            # =================================================
            # GET CURRENT PRICE
            # =================================================

            price_data = get_eth_price()

            current_price = price_data[
                "usd"
            ]


            print(
                f"💵 Current ETH price: "
                f"${current_price:,.2f}"
            )


            # =================================================
            # GET PREVIOUS PRICE
            # =================================================

            previous_price = state.get(
                "last_sent_price"
            )


            # =================================================
            # SHOW DIRECTION IN LOG
            # =================================================

            if previous_price is None:

                direction = "📈"

            elif current_price > previous_price:

                direction = "📈"

            elif current_price < previous_price:

                direction = "📉"

            else:

                direction = "📈"


            if previous_price is not None:

                print(
                    f"{direction} Previous: "
                    f"${previous_price:,.2f}"
                )

                print(
                    f"Movement: "
                    f"${current_price - previous_price:,.2f}"
                )


            # =================================================
            # SEND UPDATE
            # =================================================

            success = send_channel_update(
                price_data,
                previous_price
            )


            # =================================================
            # SAVE PRICE ONLY AFTER SUCCESS
            # =================================================

            if success:

                state[
                    "last_sent_price"
                ] = current_price


                save_json(
                    STATE_FILE,
                    state
                )


                print(
                    f"✅ Last sent price saved: "
                    f"${current_price:,.2f}"
                )


            else:

                print(
                    "⚠️ Update failed. "
                    "Previous price kept."
                )


        except requests.exceptions.RequestException as e:

            print(
                f"🌐 Binance API error: {e}"
            )


        except Exception as e:

            print(
                f"❌ Price monitor error: {e}"
            )


        # =====================================================
        # WAIT 10 MINUTES
        # =====================================================

        print(
            "⏳ Next update in 10 minutes..."
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
        "🚀 ETH PRICE CHANNEL BOT"
    )

    print(
        "=============================================="
    )

    print(
        f"📢 Channel: {CHANNEL_ID}"
    )

    print(
        "💱 Price source: Binance"
    )

    print(
        "💰 Symbol: ETHUSDT"
    )

    print(
        "⏰ Update interval: 10 minutes"
    )

    print(
        "🖼️ Image size: 413 x 108 px"
    )

    print(
        "📈 UP: 📈"
    )

    print(
        "📉 DOWN: 📉"
    )

    print(
        "👤 Username: @eth_pricealert"
    )

    print(
        "=============================================="
    )


    # ========================================================
    # TELEGRAM CONNECTION TEST
    # ========================================================

    if not test_telegram():

        raise RuntimeError(
            "Telegram connection failed."
        )


    print(
        "🚀 Starting price monitor..."
    )


    # ========================================================
    # START MONITOR
    # ========================================================

    price_monitor()


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    main() eth_price ",
        ha="center",
        va="center",
        fontsize=7.8,
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
        "BINANCE",
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

def format_caption(
    price_data,
    previous_price=None
):

    price = price_data["usd"]


    # ========================================================
    # PRICE DIRECTION
    # ========================================================

    if previous_price is None:

        arrow = "📈"

    elif price > previous_price:

        arrow = "📈"

    elif price < previous_price:

        arrow = "📉"

    else:

        arrow = "📈"


    # ========================================================
    # CAPTION
    # ========================================================

    return (
        f'{arrow} ${price:,.2f} '
        f'<a href="https://t.me/tmmusa73">'
        f'@eth_price'
        f'</a>'
    )


# ============================================================
# SEND UPDATE TO CHANNEL
# ============================================================

def send_channel_update(
    price_data,
    previous_price=None
):

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

        return False


    caption = format_caption(
        price_data,
        previous_price
    )


    print(
        f"📡 Sending update to "
        f"{CHANNEL_ID}..."
    )


    success = send_photo(
        CHANNEL_ID,
        image,
        caption
    )


    if success:

        print(
            "✅ Channel update sent successfully."
        )

        return True


    print(
        "❌ Failed to send channel update."
    )

    return False


# ============================================================
# PRICE MONITOR
# ============================================================

def price_monitor():

    print(
        "📈 ETH price monitor started."
    )

    print(
        "💱 Price source: Binance"
    )

    print(
        "💰 Symbol: ETHUSDT"
    )

    print(
        f"📢 Channel: {CHANNEL_ID}"
    )

    print(
        "⏰ Update interval: 10 minutes"
    )


    while True:

        try:

            # =================================================
            # GET CURRENT PRICE
            # =================================================

            price_data = get_eth_price()

            current_price = price_data[
                "usd"
            ]


            print(
                f"💵 Current ETH price: "
                f"${current_price:,.2f}"
            )


            # =================================================
            # GET PREVIOUS PRICE
            # =================================================

            previous_price = state.get(
                "last_sent_price"
            )


            # =================================================
            # SHOW DIRECTION IN LOG
            # =================================================

            if previous_price is None:

                direction = "📈"

            elif current_price > previous_price:

                direction = "📈"

            elif current_price < previous_price:

                direction = "📉"

            else:

                direction = "📈"


            if previous_price is not None:

                print(
                    f"{direction} Previous: "
                    f"${previous_price:,.2f}"
                )

                print(
                    f"Movement: "
                    f"${current_price - previous_price:,.2f}"
                )


            # =================================================
            # SEND UPDATE
            # =================================================

            success = send_channel_update(
                price_data,
                previous_price
            )


            # =================================================
            # SAVE PRICE ONLY AFTER SUCCESS
            # =================================================

            if success:

                state[
                    "last_sent_price"
                ] = current_price


                save_json(
                    STATE_FILE,
                    state
                )


                print(
                    f"✅ Last sent price saved: "
                    f"${current_price:,.2f}"
                )


            else:

                print(
                    "⚠️ Update failed. "
                    "Previous price kept."
                )


        except requests.exceptions.RequestException as e:

            print(
                f"🌐 Binance API error: {e}"
            )


        except Exception as e:

            print(
                f"❌ Price monitor error: {e}"
            )


        # =====================================================
        # WAIT 10 MINUTES
        # =====================================================

        print(
            "⏳ Next update in 10 minutes..."
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
        "🚀 ETH PRICE CHANNEL BOT"
    )

    print(
        "=============================================="
    )

    print(
        f"📢 Channel: {CHANNEL_ID}"
    )

    print(
        "💱 Price source: Binance"
    )

    print(
        "💰 Symbol: ETHUSDT"
    )

    print(
        "⏰ Update interval: 10 minutes"
    )

    print(
        "🖼️ Image size: 413 x 108 px"
    )

    print(
        "📈 UP: 📈"
    )

    print(
        "📉 DOWN: 📉"
    )

    print(
        "👤 Username: @eth_pricealert"
    )

    print(
        "=============================================="
    )


    # ========================================================
    # TELEGRAM CONNECTION TEST
    # ========================================================

    if not test_telegram():

        raise RuntimeError(
            "Telegram connection failed."
        )


    print(
        "🚀 Starting price monitor..."
    )


    # ========================================================
    # START MONITOR
    # ========================================================

    price_monitor()


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    main()
