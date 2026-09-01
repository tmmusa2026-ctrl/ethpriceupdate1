import os
import time
import io
import requests
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

CHECK_INTERVAL = 600  # 10 minutes


if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

if not CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID is missing!")


# =========================================================
# BINANCE ETH PRICE
# =========================================================

def get_eth_price():

    url = "https://api.binance.com/api/v3/ticker/24hr"

    params = {
        "symbol": "ETHUSDT"
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        price = float(data["lastPrice"])
        change_24h = float(data["priceChangePercent"])

        return {
            "usd": price,
            "usd_24h_change": change_24h
        }

    except Exception as e:

        print("Binance API Error:", e)

        return None


# =========================================================
# CREATE PRICE CARD
# =========================================================

def create_price_card(price_data, previous_price=None):

    price = price_data["usd"]
    change_24h = price_data["usd_24h_change"]

    # -----------------------------------------------------
    # Direction
    # -----------------------------------------------------

    if previous_price is None:

        direction = "up"

    elif price > previous_price:

        direction = "up"

    elif price < previous_price:

        direction = "down"

    else:

        direction = "same"


    # -----------------------------------------------------
    # Figure
    # -----------------------------------------------------

    fig = plt.figure(
        figsize=(4.13, 1.08),
        dpi=100
    )

    ax = fig.add_axes([0, 0, 1, 1])

    ax.set_xlim(0, 413)
    ax.set_ylim(0, 108)

    ax.axis("off")


    # =====================================================
    # BACKGROUND
    # =====================================================

    ax.set_facecolor("#10162D")

    fig.patch.set_facecolor("#10162D")


    # =====================================================
    # BACKGROUND GRADIENT STYLE BLOCKS
    # =====================================================

    ax.add_patch(
        FancyBboxPatch(
            (0, 0),
            413,
            108,
            boxstyle="round,pad=0,rounding_size=0",
            facecolor="#111A3A",
            edgecolor="none"
        )
    )


    # Purple decorative area

    ax.add_patch(
        FancyBboxPatch(
            (300, -20),
            150,
            150,
            boxstyle="round,pad=0,rounding_size=80",
            facecolor="#25195C",
            edgecolor="none",
            alpha=0.65
        )
    )


    # Blue decorative area

    ax.add_patch(
        FancyBboxPatch(
            (-50, 65),
            150,
            100,
            boxstyle="round,pad=0,rounding_size=60",
            facecolor="#142E69",
            edgecolor="none",
            alpha=0.55
        )
    )


    # =====================================================
    # ETH LOGO
    # =====================================================

    eth_x = 25

    top_triangle = Polygon(
        [
            (eth_x, 83),
            (eth_x - 8, 57),
            (eth_x + 8, 57)
        ],
        closed=True,
        facecolor="#627EEA",
        edgecolor="none"
    )

    bottom_triangle = Polygon(
        [
            (eth_x, 53),
            (eth_x - 8, 57),
            (eth_x + 8, 57)
        ],
        closed=True,
        facecolor="#4054B2",
        edgecolor="none"
    )

    ax.add_patch(top_triangle)
    ax.add_patch(bottom_triangle)


    # =====================================================
    # ETHEREUM TEXT
    # =====================================================

    ax.text(
        42,
        82,
        "ETHEREUM",
        fontsize=7,
        fontweight="bold",
        color="white",
        va="center"
    )

    ax.text(
        42,
        69,
        "ETH / USDT",
        fontsize=5.5,
        color="#9DA8C7",
        va="center"
    )


    # =====================================================
    # PRICE
    # =====================================================

    if direction == "up":

        price_color = "#20D878"

    elif direction == "down":

        price_color = "#FF4F67"

    else:

        price_color = "white"


    price_text = f"${price:,.2f}"


    ax.text(
        206,
        62,
        price_text,
        fontsize=21,
        fontweight="bold",
        color=price_color,
        ha="center",
        va="center"
    )


    # =====================================================
    # UP / DOWN TRIANGLE
    # =====================================================

    if direction == "up":

        triangle = Polygon(
            [
                (315, 68),
                (306, 53),
                (324, 53)
            ],
            closed=True,
            facecolor="#20D878",
            edgecolor="none"
        )

        ax.add_patch(triangle)

        ax.text(
            315,
            45,
            "UP",
            fontsize=5,
            fontweight="bold",
            color="#20D878",
            ha="center"
        )


    elif direction == "down":

        triangle = Polygon(
            [
                (315, 53),
                (306, 68),
                (324, 68)
            ],
            closed=True,
            facecolor="#FF4F67",
            edgecolor="none"
        )

        ax.add_patch(triangle)

        ax.text(
            315,
            45,
            "DOWN",
            fontsize=5,
            fontweight="bold",
            color="#FF4F67",
            ha="center"
        )


    else:

        ax.text(
            315,
            59,
            "•",
            fontsize=16,
            fontweight="bold",
            color="#B5BCD2",
            ha="center"
        )


    # =====================================================
    # 24H CHANGE
    # =====================================================

    if change_24h >= 0:

        change_color = "#20D878"
        change_sign = "+"

    else:

        change_color = "#FF4F67"
        change_sign = ""


    change_text = f"{change_sign}{change_24h:.2f}% 24H"


    ax.text(
        355,
        63,
        change_text,
        fontsize=7,
        fontweight="bold",
        color=change_color,
        ha="center",
        va="center"
    )


    # =====================================================
    # CHANNEL PILL
    # =====================================================

    pill = FancyBboxPatch(
        (18, 9),
        125,
        19,
        boxstyle="round,pad=0.4,rounding_size=9",
        facecolor="#1D2850",
        edgecolor="#344276",
        linewidth=0.6
    )

    ax.add_patch(pill)


    ax.text(
        80.5,
        18.5,
        "@eth_pricealert",
        fontsize=6.5,
        fontweight="bold",
        color="white",
        ha="center",
        va="center"
    )


    # =====================================================
    # BINANCE LABEL
    # =====================================================

    ax.text(
        350,
        18,
        "BINANCE",
        fontsize=5.5,
        fontweight="bold",
        color="#9DA8C7",
        ha="center",
        va="center"
    )


    # =====================================================
    # SMALL MOVEMENT INDICATORS
    # =====================================================

    if direction == "up":

        for i in range(5):

            x = 155 + (i * 7)

            h = 4 + (i * 2)

            ax.add_patch(
                FancyBboxPatch(
                    (x, 9),
                    4,
                    h,
                    boxstyle="round,pad=0.1,rounding_size=1",
                    facecolor="#20D878",
                    edgecolor="none",
                    alpha=0.85
                )
            )


    elif direction == "down":

        for i in range(5):

            x = 155 + (i * 7)

            h = 12 - (i * 1.5)

            ax.add_patch(
                FancyBboxPatch(
                    (x, 9),
                    4,
                    h,
                    boxstyle="round,pad=0.1,rounding_size=1",
                    facecolor="#FF4F67",
                    edgecolor="none",
                    alpha=0.85
                )
            )


    # =====================================================
    # SAVE IMAGE TO MEMORY
    # =====================================================

    image_buffer = io.BytesIO()

    plt.savefig(
        image_buffer,
        format="png",
        dpi=100,
        bbox_inches=None,
        pad_inches=0
    )

    plt.close(fig)

    image_buffer.seek(0)

    return image_buffer


# =========================================================
# TELEGRAM SEND PHOTO
# =========================================================

def send_photo(image_buffer, caption):

    url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendPhoto"
    )

    files = {
        "photo": (
            "eth_price.png",
            image_buffer,
            "image/png"
        )
    }

    data = {
        "chat_id": CHANNEL_ID,
        "caption": caption,
        "parse_mode": "HTML"
    }

    try:

        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=30
        )

        print("Telegram:", response.text)

        return response.ok

    except Exception as e:

        print("Telegram Error:", e)

        return False


# =========================================================
# CAPTION
# =========================================================

def format_caption(price_data, previous_price=None):

    price = price_data["usd"]

    change_24h = price_data["usd_24h_change"]


    if previous_price is None:

        direction_text = "▲"

    elif price > previous_price:

        direction_text = "▲"

    elif price < previous_price:

        direction_text = "▼"

    else:

        direction_text = "•"


    if change_24h >= 0:

        change_text = f"+{change_24h:.2f}%"

    else:

        change_text = f"{change_24h:.2f}%"


    caption = (
        f"<b>{direction_text} ETHEREUM</b>\n\n"
        f"<b>${price:,.2f}</b>  "
        f"<b>{change_text}</b> 24H\n\n"
        f"@eth_pricealert"
    )


    return caption


# =========================================================
# TEST TELEGRAM
# =========================================================

def test_telegram():

    try:

        url = (
            f"https://api.telegram.org/bot"
            f"{BOT_TOKEN}/getMe"
        )

        response = requests.get(
            url,
            timeout=15
        )

        print("Bot Test:", response.text)

    except Exception as e:

        print("Bot test error:", e)


# =========================================================
# SEND CHANNEL UPDATE
# =========================================================

def send_channel_update(price_data, previous_price=None):

    image = create_price_card(
        price_data,
        previous_price
    )

    caption = format_caption(
        price_data,
        previous_price
    )

    return send_photo(
        image,
        caption
    )


# =========================================================
# PRICE MONITOR
# =========================================================

def price_monitor():

    previous_price = None

    print("ETH Price Monitor Started")
    print("Channel:", CHANNEL_ID)
    print("Interval: 10 minutes")
    print("Source: Binance ETHUSDT")


    while True:

        try:

            price_data = get_eth_price()


            if price_data:

                current_price = price_data["usd"]


                print(
                    f"ETH: ${current_price:,.2f}"
                )


                # -----------------------------------------
                # SEND UPDATE
                # -----------------------------------------

                send_channel_update(
                    price_data,
                    previous_price
                )


                # -----------------------------------------
                # SAVE CURRENT PRICE
                # -----------------------------------------

                previous_price = current_price


            else:

                print(
                    "Could not get ETH price."
                )


        except Exception as e:

            print(
                "Monitor Error:",
                e
            )


        # ---------------------------------------------
        # WAIT 10 MINUTES
        # ---------------------------------------------

        print(
            "Next update in 10 minutes..."
        )

        time.sleep(
            CHECK_INTERVAL
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "ETH PRICE ALERT BOT"
    )

    print(
        "================================"
    )

    print(
        "Channel:",
        CHANNEL_ID
    )

    print(
        "Interval:",
        "10 minutes"
    )

    print(
        "API:",
        "Binance"
    )

    print(
        "================================"
    )


    test_telegram()

    price_monitor()
