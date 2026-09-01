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

TEMPLATE_FILE = "template.png"
OUTPUT_FILE = "eth_price.png"

USERNAME = "@eth_pricealert"


# =========================================================
# CHECK CONFIG
# =========================================================

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

if not CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID is missing!")

if not os.path.exists(TEMPLATE_FILE):
    raise FileNotFoundError(
        "template.png is missing!"
    )


# =========================================================
# FONT
# =========================================================

def get_font(size, bold=False):

    if bold:
        fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        ]
    else:
        fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"
        ]

    for font_path in fonts:

        if os.path.exists(font_path):

            try:
                return ImageFont.truetype(
                    font_path,
                    size
                )
            except:
                pass

    return ImageFont.load_default()


# =========================================================
# BINANCE PRICE
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
# TELEGRAM
# =========================================================

def telegram_request(
    method,
    data=None,
    files=None
):

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            data=data,
            files=files,
            timeout=30
        )

        result = response.json()

        if not result.get("ok"):

            print(
                "Telegram Error:",
                result
            )

        return result

    except Exception as e:

        print(
            "Telegram connection error:",
            e
        )

        return None


# =========================================================
# TEST TELEGRAM
# =========================================================

def test_telegram():

    result = telegram_request(
        "getMe"
    )

    if result and result.get("ok"):

        print(
            "Telegram bot connected:",
            result["result"]["username"]
        )

        return True

    return False


# =========================================================
# STATE
# =========================================================

def load_state():

    if not os.path.exists(
        STATE_FILE
    ):

        return None

    try:

        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

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
        ) as f:

            json.dump(
                {
                    "last_alert_price": price
                },
                f
            )

    except Exception as e:

        print(
            "State save error:",
            e
        )


# =========================================================
# CREATE IMAGE
#
# ORIGINAL TEMPLATE:
# 413 x 108 PX
#
# The original PNG is NOT recreated.
# It is opened directly and only the dynamic
# price + username areas are changed.
# =========================================================

def create_price_image(price):

    image = Image.open(
        TEMPLATE_FILE
    ).convert("RGB")

    draw = ImageDraw.Draw(
        image
    )

    width, height = image.size

    # Safety check
    if width != 413 or height != 108:

        raise ValueError(
            f"template.png must be 413x108. "
            f"Current size: {width}x{height}"
        )


    # =====================================================
    # ORIGINAL BACKGROUND COLOR
    #
    # This is the dominant blue from your PNG.
    # =====================================================

    background_blue = (
        102,
        117,
        246
    )


    # =====================================================
    # REMOVE OLD PRICE
    #
    # Only the old "$2,419" area is covered.
    # The rest of your original PNG stays untouched.
    # =====================================================

    draw.rectangle(
        (
            115,
            13,
            300,
            59
        ),
        fill=background_blue
    )


    # =====================================================
    # NEW LIVE PRICE
    # =====================================================

    price_font = get_font(
        42,
        bold=True
    )

    price_text = (
        f"${price:,.0f}"
    )

    bbox = draw.textbbox(
        (0, 0),
        price_text,
        font=price_font
    )

    text_width = (
        bbox[2] - bbox[0]
    )

    text_height = (
        bbox[3] - bbox[1]
    )

    price_x = (
        width - text_width
    ) // 2

    price_y = 10

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
    # REMOVE OLD USERNAME
    # =====================================================

    draw.rounded_rectangle(
        (
            160,
            61,
            254,
            78
        ),
        radius=8,
        fill=(
            204,
            205,
            220
        )
    )


    # =====================================================
    # NEW USERNAME
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

    pill_width = (
        username_width + 18
    )

    pill_height = 16

    pill_x = (
        width - pill_width
    ) // 2

    pill_y = 61


    # Username pill

    draw.rounded_rectangle(
        (
            pill_x,
            pill_y,
            pill_x + pill_width,
            pill_y + pill_height
        ),
        radius=8,
        fill=(
            204,
            205,
            220
        )
    )


    # Small icon/dot

    icon_x = (
        pill_x + 6
    )

    icon_y = (
        pill_y + 8
    )

    draw.ellipse(
        (
            icon_x - 2,
            icon_y - 2,
            icon_x + 2,
            icon_y + 2
        ),
        fill=(
            45,
            45,
            55
        )
    )


    # Username

    draw.text(
        (
            pill_x + 11,
            pill_y + 1
        ),
        USERNAME,
        font=username_font,
        fill=(
            30,
            30,
            40
        )
    )


    # =====================================================
    # SAVE EXACT 413x108 PNG
    # =====================================================

    image.save(
        OUTPUT_FILE,
        format="PNG"
    )

    return OUTPUT_FILE


# =========================================================
# CAPTION
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
        f'<a href="https://t.me/eth_pricealert">'
        f'{USERNAME}'
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
                "Alert sent:",
                f"${price:,.2f}"
            )

            return True

        return False

    except Exception as e:

        print(
            "Send error:",
            e
        )

        return False


# =========================================================
# PRICE MONITOR
# =========================================================

def price_monitor():

    last_alert_price = (
        load_state()
    )

    print(
        "=============================="
    )

    print(
        "ETH PRICE CHANNEL BOT"
    )

    print(
        "=============================="
    )

    print(
        "Price Source: Binance"
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
        "Image: 413x108 PNG"
    )

    print(
        "Username:",
        USERNAME
    )

    print(
        "=============================="
    )


    while True:

        try:

            current_price = (
                get_eth_price()
            )

            if current_price is None:

                time.sleep(
                    CHECK_INTERVAL
                )

                continue


            print(
                f"ETH: "
                f"${current_price:,.2f}"
            )


            # First alert

            if last_alert_price is None:

                print(
                    "Sending first alert..."
                )

                if send_alert(
                    current_price
                ):

                    last_alert_price = (
                        current_price
                    )

                    save_state(
                        current_price
                    )


            # Normal alert

            else:

                movement = abs(
                    current_price
                    - last_alert_price
                )

                print(
                    f"Movement: "
                    f"${movement:,.2f}"
                )


                if movement >= PRICE_TRIGGER:

                    print(
                        "30 dollar movement detected."
                    )

                    if send_alert(
                        current_price,
                        last_alert_price
                    ):

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

    print(
        "Starting ETH Price Bot..."
    )

    if not test_telegram():

        print(
            "Telegram connection failed!"
        )

        return

    price_monitor()


if __name__ == "__main__":

    main()
