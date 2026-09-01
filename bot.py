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

# Your original reference image
TEMPLATE_FILE = "template.png"

# Output image
OUTPUT_FILE = "eth_price.png"


# =========================================================
# ENVIRONMENT VARIABLES
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

        print(
            "Telegram bot connected:",
            result["result"].get("username")
        )

        return True

    return False


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

    except:

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
# CREATE IMAGE FROM TEMPLATE
# =========================================================

def create_price_image(price):

    # -----------------------------------------------------
    # IMPORTANT:
    # template.png must be your ORIGINAL design image.
    # -----------------------------------------------------

    if not os.path.exists(TEMPLATE_FILE):

        raise FileNotFoundError(
            "template.png not found!"
        )

    image = Image.open(
        TEMPLATE_FILE
    ).convert("RGB")

    draw = ImageDraw.Draw(image)

    width, height = image.size

    # =====================================================
    # PRICE
    # =====================================================

    price_font = get_font(
        int(height * 0.40),
        bold=True
    )

    price_text = f"${price:,.0f}"

    # Find center of image
    bbox = draw.textbbox(
        (0, 0),
        price_text,
        font=price_font
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    price_x = (
        width - text_width
    ) // 2

    # Position similar to your reference
    price_y = int(
        height * 0.12
    )

    # Black price
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
    # USERNAME
    # =====================================================

    username = "@eth_pricealert"

    username_font = get_font(
        int(height * 0.095),
        bold=True
    )

    bbox = draw.textbbox(
        (0, 0),
        username,
        font=username_font
    )

    username_width = (
        bbox[2] - bbox[0]
    )

    username_height = (
        bbox[3] - bbox[1]
    )

    # Username centered
    username_x = (
        width - username_width
    ) // 2

    username_y = int(
        height * 0.61
    )

    # Pill dimensions
    padding_x = 9
    padding_y = 3

    pill_left = (
        username_x - padding_x
    )

    pill_top = (
        username_y - padding_y
    )

    pill_right = (
        username_x
        + username_width
        + padding_x
    )

    pill_bottom = (
        username_y
        + username_height
        + padding_y
    )

    # Pill
    draw.rounded_rectangle(
        (
            pill_left,
            pill_top,
            pill_right,
            pill_bottom
        ),
        radius=8,
        fill=(205, 205, 220)
    )

    # Small Telegram-style dot/icon
    icon_x = pill_left + 6
    icon_y = (
        pill_top
        + (
            pill_bottom
            - pill_top
        ) // 2
    )

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
            username_x,
            username_y
        ),
        username,
        font=username_font,
        fill=(30, 30, 40)
    )


    # =====================================================
    # SAVE
    # =====================================================

    image.save(
        OUTPUT_FILE,
        format="PNG",
        optimize=True
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
    print("==============================")
    print("")

    while True:

        try:

            current_price = get_eth_price()

            if current_price is None:

                time.sleep(
                    CHECK_INTERVAL
                )

                continue

            print(
                f"Binance ETH Price: "
                f"${current_price:,.2f}"
            )

            # First alert
            if last_alert_price is None:

                print(
                    "Sending initial alert..."
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
                        "ETH moved $30+."
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
        "ETH Price Bot Starting..."
    )

    if not test_telegram():

        print(
            "Telegram connection failed!"
        )

        return

    price_monitor()


if __name__ == "__main__":

    main()
