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

BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_SYMBOL = "ETHUSDT"

PRICE_TRIGGER = 30.0
CHECK_INTERVAL = 60

STATE_FILE = "bot_state.json"


# =========================================================
# IMAGE SETTINGS
# EXACT SIZE: 413 x 108 PIXELS
# =========================================================

IMAGE_WIDTH = 413
IMAGE_HEIGHT = 108


# =========================================================
# TELEGRAM USERNAME
# =========================================================

USERNAME = "@eth_pricealert"


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

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]

    else:

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for path in font_paths:

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

        print(
            "Telegram bot connected:",
            result["result"].get("username")
        )

        return True

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
# STATE
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

    except:

        return None


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
# ETHEREUM COIN ICON
# =========================================================

def draw_eth_icon(
    draw,
    center_x,
    center_y,
    radius
):

    # Circle
    draw.ellipse(
        (
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius
        ),
        fill=(108, 130, 225),
        outline=(165, 180, 245),
        width=1
    )

    # Ethereum diamond

    top = (
        center_x,
        center_y - 8
    )

    left = (
        center_x - 5,
        center_y
    )

    right = (
        center_x + 5,
        center_y
    )

    middle = (
        center_x,
        center_y + 3
    )

    bottom = (
        center_x,
        center_y + 8
    )

    draw.polygon(
        [
            top,
            left,
            middle
        ],
        fill=(230, 235, 255)
    )

    draw.polygon(
        [
            top,
            right,
            middle
        ],
        fill=(195, 205, 250)
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
# CREATE PNG
# =========================================================

def create_price_image(price):

    # -----------------------------------------------------
    # EXACT 413 x 108 PNG
    # -----------------------------------------------------

    image = Image.new(
        "RGB",
        (
            IMAGE_WIDTH,
            IMAGE_HEIGHT
        ),
        (103, 117, 238)
    )

    draw = ImageDraw.Draw(image)

    # =====================================================
    # BACKGROUND
    # =====================================================

    # Soft top-left decorative lines

    draw.line(
        [
            (0, 7),
            (10, 2),
            (20, 7),
            (29, 2)
        ],
        fill=(180, 190, 255),
        width=1
    )

    draw.line(
        [
            (0, 11),
            (11, 6),
            (20, 11)
        ],
        fill=(160, 175, 250),
        width=1
    )

    # Top-right diagonal

    draw.line(
        [
            (390, 0),
            (413, 16)
        ],
        fill=(180, 190, 255),
        width=1
    )

    # Bottom-right decorative lines

    draw.line(
        [
            (359, 108),
            (413, 63)
        ],
        fill=(226, 190, 255),
        width=2
    )

    draw.line(
        [
            (369, 108),
            (413, 70)
        ],
        fill=(250, 205, 245),
        width=2
    )

    # =====================================================
    # LEFT ETH ICON
    # =====================================================

    draw_eth_icon(
        draw,
        96,
        29,
        14
    )

    # =====================================================
    # RIGHT ETH ICON
    # =====================================================

    draw_eth_icon(
        draw,
        314,
        29,
        14
    )

    # =====================================================
    # TOP CENTER "ETHEREUM"
    # =====================================================

    ethereum_font = get_font(
        8,
        bold=True
    )

    ethereum_text = "ETHEREUM"

    bbox = draw.textbbox(
        (0, 0),
        ethereum_text,
        font=ethereum_font
    )

    ethereum_width = (
        bbox[2] - bbox[0]
    )

    draw.text(
        (
            (IMAGE_WIDTH - ethereum_width) / 2,
            2
        ),
        ethereum_text,
        font=ethereum_font,
        fill=(255, 255, 255)
    )

    # =====================================================
    # RIGHT TOP ETH
    # =====================================================

    eth_font = get_font(
        10,
        bold=True
    )

    draw.text(
        (377, 1),
        "ETH",
        font=eth_font,
        fill=(255, 255, 255)
    )

    price_bot_font = get_font(
        4,
        bold=True
    )

    draw.text(
        (377, 13),
        "PRICE BOT",
        font=price_bot_font,
        fill=(235, 235, 255)
    )

    # =====================================================
    # MAIN PRICE
    # =====================================================

    price_font = get_font(
        42,
        bold=True
    )

    # Reference-style price
    price_text = f"${price:,.0f}"

    bbox = draw.textbbox(
        (0, 0),
        price_text,
        font=price_font
    )

    price_width = (
        bbox[2] - bbox[0]
    )

    # Center horizontally
    price_x = (
        IMAGE_WIDTH - price_width
    ) // 2

    # Same general vertical position
    price_y = 12

    draw.text(
        (
            price_x,
            price_y
        ),
        price_text,
        font=price_font,
        fill=(0, 0, 0)
    )

    # =====================================================
    # USERNAME PILL
    # =====================================================

    username_font = get_font(
        9,
        bold=True
    )

    bbox = draw.textbbox(
        (0, 0),
        USERNAME,
        font=username_font
    )

    username_width = (
        bbox[2] - bbox[0]
    )

    username_height = (
        bbox[3] - bbox[1]
    )

    pill_width = username_width + 17
    pill_height = 15

    pill_x = (
        IMAGE_WIDTH - pill_width
    ) // 2

    pill_y = 62

    # Pill background
    draw.rounded_rectangle(
        (
            pill_x,
            pill_y,
            pill_x + pill_width,
            pill_y + pill_height
        ),
        radius=7,
        fill=(204, 205, 220)
    )

    # Small icon
    icon_x = pill_x + 6
    icon_y = pill_y + 7

    draw.ellipse(
        (
            icon_x - 2,
            icon_y - 2,
            icon_x + 2,
            icon_y + 2
        ),
        fill=(45, 45, 55)
    )

    # Username
    draw.text(
        (
            pill_x + 11,
            pill_y + 1
        ),
        USERNAME,
        font=username_font,
        fill=(30, 30, 40)
    )

    # =====================================================
    # SMALL BOTTOM WATERMARK
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
    # SAVE AS PNG
    # =====================================================

    output_file = "eth_price.png"

    image.save(
        output_file,
        format="PNG",
        optimize=True
    )

    return output_file


# =========================================================
# TELEGRAM CAPTION
# =========================================================

def create_caption(
    price,
    previous_price=None
):

    if previous_price is None:

        emoji = "🔺"

    elif price >= previous_price:

        emoji = "🔺"

    else:

        emoji = "🔻"

    return (
        f'{emoji} ${price:,.2f} '
        f'<a href="https://t.me/tmmusa73">'
        f'{USERNAME}'
        f'</a>'
    )


# =========================================================
# SEND IMAGE TO CHANNEL
# =========================================================

def send_alert(
    price,
    previous_price=None
):

    try:

        image_path = create_price_image(
            price
        )

        caption = create_caption(
            price,
            previous_price
        )

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

        return False

    except Exception as e:

        print(
            "Alert error:",
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
    print(
        "Image Size:",
        f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}"
    )
    print("==============================")
    print("")

    while True:

        try:

            current_price = get_eth_price()

            if current_price is None:

                print(
                    "Unable to get Binance price."
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            print(
                f"Current ETH price: "
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

                    last_alert_price = (
                        current_price
                    )

                    save_state(
                        current_price
                    )

            # =================================================
            # $30 MOVEMENT
            # =================================================

            else:

                movement = abs(
                    current_price
                    - last_alert_price
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
                        "Sending alert..."
                    )

                    success = send_alert(
                        current_price,
                        last_alert_price
                    )

                    if success:

                        last_alert_price = (
                            current_price
                        )

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
            "Telegram connection failed!"
        )

        return

    price_monitor()


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    main()
