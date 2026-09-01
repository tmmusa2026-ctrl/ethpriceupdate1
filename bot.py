import os
import time
import json
import requests
from PIL import Image, ImageDraw, ImageFont


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

BINANCE_SYMBOL = "ETHUSDT"

PRICE_TRIGGER = 30.0

CHECK_INTERVAL = 60

STATE_FILE = "bot_state.json"

BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"


# =========================================================
# CHECK VARIABLES
# =========================================================

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

if not CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID is missing!")


# =========================================================
# FONT
# =========================================================

def get_font(size, bold=False):

    if bold:

        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]

    else:

        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for path in paths:

        if os.path.exists(path):

            try:
                return ImageFont.truetype(path, size)

            except:
                pass

    return ImageFont.load_default()


# =========================================================
# TELEGRAM REQUEST
# =========================================================

def telegram_request(method, data=None, files=None):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    try:

        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=30
        )

        result = response.json()

        if not result.get("ok"):

            print("Telegram Error:", result)

        return result

    except Exception as e:

        print("Telegram connection error:", e)

        return None


# =========================================================
# TEST TELEGRAM
# =========================================================

def test_telegram():

    result = telegram_request("getMe")

    if result and result.get("ok"):

        username = result["result"].get("username")

        print(
            "Telegram bot connected:",
            username
        )

        return True

    print("Telegram bot connection failed.")

    return False


# =========================================================
# BINANCE ETH PRICE
# =========================================================

def get_eth_price():

    try:

        response = requests.get(
            BINANCE_URL,
            params={
                "symbol": BINANCE_SYMBOL
            },
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        return float(data["price"])

    except Exception as e:

        print(
            "Binance API error:",
            e
        )

        return None


# =========================================================
# LOAD STATE
# =========================================================

def load_state():

    if not os.path.exists(STATE_FILE):

        return None

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            return data.get(
                "last_alert_price"
            )

    except Exception as e:

        print(
            "State read error:",
            e
        )

        return None


# =========================================================
# SAVE STATE
# =========================================================

def save_state(price):

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {
                    "last_alert_price": price
                },
                file
            )

    except Exception as e:

        print(
            "State save error:",
            e
        )


# =========================================================
# DRAW ETH COIN
# =========================================================

def draw_eth_coin(draw, cx, cy, radius):

    # Outer circle
    draw.ellipse(
        (
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius
        ),
        fill=(113, 136, 228),
        outline=(170, 185, 250),
        width=1
    )

    # Small ETH diamond
    top = (cx, cy - radius + 4)

    left = (cx - 5, cy)

    right = (cx + 5, cy)

    middle = (cx, cy + 3)

    bottom = (cx, cy + radius - 4)

    draw.polygon(
        [
            top,
            left,
            middle
        ],
        fill=(225, 230, 255)
    )

    draw.polygon(
        [
            top,
            right,
            middle
        ],
        fill=(190, 200, 245)
    )

    draw.polygon(
        [
            left,
            middle,
            bottom
        ],
        fill=(180, 190, 235)
    )

    draw.polygon(
        [
            middle,
            right,
            bottom
        ],
        fill=(205, 212, 250)
    )


# =========================================================
# CREATE IMAGE
# =========================================================

def create_price_image(price):

    # EXACT REFERENCE SIZE
    width = 413
    height = 108

    # =====================================================
    # BACKGROUND
    # =====================================================

    image = Image.new(
        "RGB",
        (width, height),
        (105, 119, 238)
    )

    draw = ImageDraw.Draw(image)

    # =====================================================
    # SOFT BACKGROUND SHAPES
    # =====================================================

    # Top-left diagonal decoration
    draw.line(
        [
            (0, 10),
            (14, 3),
            (28, 10),
            (40, 3)
        ],
        fill=(180, 190, 255),
        width=2
    )

    draw.line(
        [
            (0, 14),
            (14, 7),
            (25, 13)
        ],
        fill=(155, 170, 250),
        width=1
    )

    # Top-right diagonal decoration
    draw.line(
        [
            (390, 0),
            (413, 18)
        ],
        fill=(185, 195, 255),
        width=2
    )

    # Bottom-right diagonal lines
    draw.line(
        [
            (381, 108),
            (413, 76)
        ],
        fill=(230, 190, 255),
        width=2
    )

    draw.line(
        [
            (389, 108),
            (413, 82)
        ],
        fill=(255, 205, 245),
        width=2
    )

    # =====================================================
    # ETH COINS
    # =====================================================

    draw_eth_coin(
        draw,
        96,
        29,
        14
    )

    draw_eth_coin(
        draw,
        314,
        29,
        14
    )

    # =====================================================
    # TOP TITLE
    # =====================================================

    title_font = get_font(
        9,
        bold=True
    )

    title = "ETHEREUM"

    bbox = draw.textbbox(
        (0, 0),
        title,
        font=title_font
    )

    title_width = bbox[2] - bbox[0]

    draw.text(
        (
            (width - title_width) / 2,
            2
        ),
        title,
        font=title_font,
        fill=(255, 255, 255)
    )

    # =====================================================
    # RIGHT TITLE
    # =====================================================

    eth_font = get_font(
        11,
        bold=True
    )

    bot_font = get_font(
        5,
        bold=True
    )

    draw.text(
        (377, 2),
        "ETH",
        font=eth_font,
        fill=(255, 255, 255)
    )

    draw.text(
        (377, 15),
        "PRICE BOT",
        font=bot_font,
        fill=(235, 235, 255)
    )

    # =====================================================
    # PRICE
    # =====================================================

    price_font = get_font(
        43,
        bold=True
    )

    # No comma — exactly like reference
    price_text = f"${price:,.0f}"

    bbox = draw.textbbox(
        (0, 0),
        price_text,
        font=price_font
    )

    price_width = bbox[2] - bbox[0]

    price_x = (width - price_width) / 2

    draw.text(
        (
            price_x,
            14
        ),
        price_text,
        font=price_font,
        fill=(0, 0, 0)
    )

    # =====================================================
    # USERNAME PILL
    # =====================================================

    username = "@eth_pricealert"

    username_font = get_font(
        10,
        bold=True
    )

    bbox = draw.textbbox(
        (0, 0),
        username,
        font=username_font
    )

    username_width = bbox[2] - bbox[0]
    username_height = bbox[3] - bbox[1]

    pill_width = username_width + 18
    pill_height = 16

    pill_x = (width - pill_width) / 2
    pill_y = 61

    # Pill
    draw.rounded_rectangle(
        (
            pill_x,
            pill_y,
            pill_x + pill_width,
            pill_y + pill_height
        ),
        radius=8,
        fill=(202, 204, 224)
    )

    # Small Telegram-style icon
    icon_x = pill_x + 6
    icon_y = pill_y + 8

    draw.ellipse(
        (
            icon_x - 3,
            icon_y - 3,
            icon_x + 3,
            icon_y + 3
        ),
        fill=(55, 55, 70)
    )

    # Username
    draw.text(
        (
            pill_x + 13,
            pill_y + 2
        ),
        username,
        font=username_font,
        fill=(25, 25, 35)
    )

    # =====================================================
    # SMALL WATERMARK
    # =====================================================

    watermark_font = get_font(
        4,
        bold=True
    )

    draw.text(
        (7, 96),
        "POWERED BY",
        font=watermark_font,
        fill=(240, 240, 255)
    )

    draw.text(
        (7, 101),
        "BINANCE",
        font=watermark_font,
        fill=(240, 240, 255)
    )

    # =====================================================
    # SAVE
    # =====================================================

    image_path = "eth_price.png"

    image.save(
        image_path,
        format="PNG",
        optimize=True
    )

    return image_path


# =========================================================
# TELEGRAM CAPTION
# =========================================================

def create_caption(
    price,
    previous_price=None
):

    if previous_price is None:

        arrow = "🔺"

    elif price >= previous_price:

        arrow = "🔺"

    else:

        arrow = "🔻"

    return (
        f'{arrow} ${price:,.2f} '
        f'<a href="https://t.me/tmmusa73">'
        f'@eth_pricealert'
        f'</a>'
    )


# =========================================================
# SEND ALERT
# =========================================================

def send_alert(
    price,
    previous_price=None
):

    image_path = create_price_image(
        price
    )

    caption = create_caption(
        price,
        previous_price
    )

    try:

        with open(
            image_path,
            "rb"
        ) as photo:

            result = telegram_request(
                "sendPhoto",
                data={
                    "chat_id": CHANNEL_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                },
                files={
                    "photo": photo
                }
            )

        if result and result.get("ok"):

            print(
                "Alert sent successfully:",
                f"${price:,.2f}"
            )

            return True

        print(
            "Failed to send alert."
        )

        return False

    except Exception as e:

        print(
            "Image sending error:",
            e
        )

        return False


# =========================================================
# PRICE MONITOR
# =========================================================

def price_monitor():

    last_alert_price = load_state()

    print("")
    print("==============================")
    print("      ETH PRICE CHANNEL BOT")
    print("==============================")
    print("Price Source: Binance")
    print("Symbol:", BINANCE_SYMBOL)
    print("Channel:", CHANNEL_ID)
    print("Trigger: $", PRICE_TRIGGER)
    print(
        "Check Interval:",
        CHECK_INTERVAL,
        "seconds"
    )
    print("==============================")
    print("")

    while True:

        try:

            current_price = get_eth_price()

            if current_price is None:

                print(
                    "Could not get Binance ETH price."
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            print(
                f"Current Binance ETH price: "
                f"${current_price:,.2f}"
            )

            # =================================================
            # FIRST ALERT
            # =================================================

            if last_alert_price is None:

                print(
                    "First price detected."
                )

                print(
                    "Sending initial alert..."
                )

                success = send_alert(
                    current_price
                )

                if success:

                    last_alert_price = current_price

                    save_state(
                        current_price
                    )

            # =================================================
            # $30 MOVEMENT
            # =================================================

            else:

                movement = abs(
                    current_price -
                    last_alert_price
                )

                print(
                    f"Movement from last alert: "
                    f"${movement:,.2f}"
                )

                if movement >= PRICE_TRIGGER:

                    print(
                        "ETH moved $30+."
                    )

                    print(
                        "Sending new alert..."
                    )

                    success = send_alert(
                        current_price,
                        last_alert_price
                    )

                    if success:

                        last_alert_price = current_price

                        save_state(
                            current_price
                        )

            time.sleep(
                CHECK_INTERVAL
            )

        except Exception as e:

            print(
                "Monitor error:",
                e
            )

            time.sleep(
                CHECK_INTERVAL
            )


# =========================================================
# MAIN
# =========================================================

def main():

    print("")
    print("==============================")
    print("       ETH PRICE BOT")
    print("==============================")

    if not test_telegram():

        print(
            "Telegram connection failed."
        )

        return

    price_monitor()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
