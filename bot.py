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

# Binance Spot symbol
BINANCE_SYMBOL = "ETHUSDT"

# Alert after $30 movement
PRICE_TRIGGER = 30.0

# Check price every 60 seconds
CHECK_INTERVAL = 60

# Save last alert price
STATE_FILE = "bot_state.json"

# Binance Spot API
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"


# =========================================================
# ENVIRONMENT CHECK
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
# TELEGRAM API
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
# GET ETH PRICE FROM BINANCE
# =========================================================

def get_eth_price():

    params = {
        "symbol": BINANCE_SYMBOL
    }

    try:

        response = requests.get(
            BINANCE_URL,
            params=params,
            timeout=20
        )

        response.raise_for_status()

        data = response.json()

        price = float(data["price"])

        return price

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

        data = {
            "last_alert_price": price
        }

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file
            )

    except Exception as e:

        print(
            "State save error:",
            e
        )


# =========================================================
# ETHEREUM LOGO
# =========================================================

def draw_ethereum_logo(
    draw,
    center_x,
    center_y,
    size
):

    radius = size // 2

    # Outer circle
    draw.ellipse(
        (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius
        ),
        outline=(55, 55, 65),
        width=5
    )

    top = (
        center_x,
        center_y - radius + 18
    )

    left = (
        center_x - 30,
        center_y - 5
    )

    right = (
        center_x + 30,
        center_y - 5
    )

    middle = (
        center_x,
        center_y + 12
    )

    bottom = (
        center_x,
        center_y + radius - 18
    )

    # Upper left
    draw.polygon(
        [
            top,
            left,
            middle
        ],
        fill=(105, 115, 165)
    )

    # Upper right
    draw.polygon(
        [
            top,
            right,
            middle
        ],
        fill=(75, 85, 135)
    )

    # Lower left
    draw.polygon(
        [
            left,
            middle,
            bottom
        ],
        fill=(70, 80, 125)
    )

    # Lower right
    draw.polygon(
        [
            middle,
            right,
            bottom
        ],
        fill=(90, 100, 150)
    )


# =========================================================
# CANDLESTICK
# =========================================================

def draw_candlestick(
    draw,
    x,
    y,
    body_width,
    body_height,
    wick_height,
    color
):

    center_x = x + body_width // 2

    # Wick
    draw.line(
        [
            (
                center_x,
                y - wick_height
            ),
            (
                center_x,
                y + body_height + wick_height
            )
        ],
        fill=color,
        width=5
    )

    # Body
    draw.rounded_rectangle(
        (
            x,
            y,
            x + body_width,
            y + body_height
        ),
        radius=5,
        fill=color
    )


# =========================================================
# CREATE PRICE IMAGE
# =========================================================

def create_price_image(price):

    width = 720
    height = 240

    # Yellow background
    image = Image.new(
        "RGB",
        (width, height),
        (255, 215, 0)
    )

    draw = ImageDraw.Draw(image)

    # Black rounded card
    margin = 18

    draw.rounded_rectangle(
        (
            margin,
            margin,
            width - margin,
            height - margin
        ),
        radius=18,
        fill=(5, 6, 8)
    )

    # =====================================================
    # ETH LOGO
    # =====================================================

    draw_ethereum_logo(
        draw,
        center_x=95,
        center_y=120,
        size=130
    )

    # =====================================================
    # TITLE
    # =====================================================

    title_font = get_font(
        42,
        bold=True
    )

    draw.text(
        (180, 28),
        "Ethereum (ETH)",
        font=title_font,
        fill=(240, 242, 248)
    )

    # =====================================================
    # PRICE
    # =====================================================

    price_font = get_font(
        57,
        bold=True
    )

    price_text = f"${price:,.2f}"

    draw.text(
        (205, 82),
        price_text,
        font=price_font,
        fill=(255, 45, 55)
    )

    # =====================================================
    # USERNAME
    # =====================================================

    username_font = get_font(
        31,
        bold=True
    )

    draw.text(
        (240, 170),
        "@eth_pricealert",
        font=username_font,
        fill=(190, 195, 210)
    )

    # =====================================================
    # CANDLESTICKS
    # =====================================================

    # Red candle 1
    draw_candlestick(
        draw,
        x=525,
        y=60,
        body_width=25,
        body_height=45,
        wick_height=15,
        color=(255, 45, 55)
    )

    # Red candle 2
    draw_candlestick(
        draw,
        x=580,
        y=78,
        body_width=25,
        body_height=50,
        wick_height=17,
        color=(255, 45, 55)
    )

    # Red candle 3
    draw_candlestick(
        draw,
        x=635,
        y=95,
        body_width=25,
        body_height=55,
        wick_height=20,
        color=(255, 45, 55)
    )

    # Green candle
    draw_candlestick(
        draw,
        x=680,
        y=125,
        body_width=25,
        body_height=25,
        wick_height=12,
        color=(0, 205, 80)
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

            files = {
                "photo": photo
            }

            data = {

                "chat_id": CHANNEL_ID,

                "caption": caption,

                "parse_mode": "HTML"
            }

            result = telegram_request(
                "sendPhoto",
                data=data,
                files=files
            )

        if result and result.get("ok"):

            print(
                f"Alert sent successfully: "
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
    print("     ETH PRICE CHANNEL BOT")
    print("==============================")
    print(
        "Price source: Binance"
    )
    print(
        "Symbol:",
        BINANCE_SYMBOL
    )
    print(
        "Channel:",
        CHANNEL_ID
    )
    print(
        "Trigger: $",
        PRICE_TRIGGER
    )
    print(
        "Check interval:",
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
                    "Could not get ETH price."
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
            # FIRST RUN
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
            # NORMAL MOVEMENT
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
                        "Price moved $30+."
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
