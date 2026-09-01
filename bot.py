import os
import time
import json
import requests
from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIG
# =========================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

PRICE_TRIGGER = 1.0
CHECK_INTERVAL = 60

STATE_FILE = "bot_state.json"

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


# =========================
# CHECK ENVIRONMENT
# =========================

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing!")

if not CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID is missing!")


# =========================
# TELEGRAM API
# =========================

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


# =========================
# TEST BOT
# =========================

def test_telegram():

    result = telegram_request("getMe")

    if result and result.get("ok"):

        bot_username = result["result"].get("username")

        print("Telegram bot connected:", bot_username)

        return True

    print("Telegram bot connection failed.")

    return False


# =========================
# GET ETH PRICE
# =========================

def get_eth_price():

    params = {
        "ids": "ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }

    try:

        response = requests.get(
            COINGECKO_URL,
            params=params,
            timeout=20
        )

        data = response.json()

        price = float(data["ethereum"]["usd"])

        change_24h = float(
            data["ethereum"].get("usd_24h_change", 0)
        )

        return price, change_24h

    except Exception as e:

        print("CoinGecko error:", e)

        return None, None


# =========================
# LOAD STATE
# =========================

def load_state():

    if not os.path.exists(STATE_FILE):
        return None

    try:

        with open(STATE_FILE, "r") as file:

            data = json.load(file)

            return data.get("last_alert_price")

    except Exception:

        return None


# =========================
# SAVE STATE
# =========================

def save_state(price):

    data = {
        "last_alert_price": price
    }

    try:

        with open(STATE_FILE, "w") as file:

            json.dump(data, file)

    except Exception as e:

        print("State save error:", e)


# =========================
# FONT
# =========================

def get_font(size):

    font_paths = [

        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"

    ]

    for path in font_paths:

        if os.path.exists(path):

            try:

                return ImageFont.truetype(path, size)

            except:
                pass

    return ImageFont.load_default()


# =========================
# CREATE ETH IMAGE
# =========================

def create_price_image(price):

    width = 413
    height = 108

    image = Image.new(
        "RGB",
        (width, height),
        (25, 20, 70)
    )

    draw = ImageDraw.Draw(image)

    # Background gradient
    for x in range(width):

        r = int(25 + (70 - 25) * x / width)
        g = int(20 + (25 - 20) * x / width)
        b = int(70 + (150 - 70) * x / width)

        draw.line(
            [(x, 0), (x, height)],
            fill=(r, g, b)
        )

    # Fonts
    title_font = get_font(13)
    price_font = get_font(32)
    small_font = get_font(10)

    # Header
    draw.text(
        (18, 10),
        "ETHEREUM",
        font=title_font,
        fill=(255, 255, 255)
    )

    draw.text(
        (18, 28),
        "ETH PRICE BOT",
        font=small_font,
        fill=(190, 200, 255)
    )

    # Price
    price_text = f"${price:,.0f}"

    bbox = draw.textbbox(
        (0, 0),
        price_text,
        font=price_font
    )

    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    draw.text(
        (
            (width - text_width) / 2,
            36
        ),
        price_text,
        font=price_font,
        fill=(255, 255, 255)
    )

    # Bottom username pill
    pill_text = "@eth_price"

    bbox = draw.textbbox(
        (0, 0),
        pill_text,
        font=small_font
    )

    pill_width = bbox[2] - bbox[0] + 18
    pill_height = 22

    pill_x = width - pill_width - 15
    pill_y = height - 30

    draw.rounded_rectangle(
        (
            pill_x,
            pill_y,
            pill_x + pill_width,
            pill_y + pill_height
        ),
        radius=11,
        fill=(255, 255, 255)
    )

    draw.text(
        (
            pill_x + 9,
            pill_y + 5
        ),
        pill_text,
        font=small_font,
        fill=(40, 40, 100)
    )

    image.save(
        "eth_price.png",
        format="PNG"
    )

    return "eth_price.png"


# =========================
# CREATE CAPTION
# =========================

def create_caption(price, change_24h):

    if change_24h >= 0:

        arrow = "🔺"

    else:

        arrow = "🔻"

    return (
        f'{arrow} ${price:,.0f} '
        f'<a href="https://t.me/tmmusa73">@eth_price</a>'
    )


# =========================
# SEND TO CHANNEL
# =========================

def send_to_channel(price, change_24h):

    image_path = create_price_image(price)

    caption = create_caption(
        price,
        change_24h
    )

    try:

        with open(image_path, "rb") as photo:

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
                f"Alert sent successfully: ${price:,.2f}"
            )

            return True

        print("Failed to send alert.")

        return False

    except Exception as e:

        print("Photo sending error:", e)

        return False


# =========================
# PRICE MONITOR
# =========================

def price_monitor():

    last_alert_price = load_state()

    print("ETH Price Monitor Started")
    print("Channel:", CHANNEL_ID)
    print("Trigger: $", PRICE_TRIGGER)
    print("Check interval:", CHECK_INTERVAL, "seconds")

    while True:

        try:

            price, change_24h = get_eth_price()

            if price is None:

                print("Unable to get ETH price.")

                time.sleep(CHECK_INTERVAL)

                continue

            print(
                f"Current ETH price: ${price:,.2f}"
            )

            # First run
            if last_alert_price is None:

                print(
                    "First price detected. Sending initial alert..."
                )

                success = send_to_channel(
                    price,
                    change_24h
                )

                if success:

                    last_alert_price = price

                    save_state(price)

            else:

                price_difference = abs(
                    price - last_alert_price
                )

                print(
                    f"Movement from last alert: "
                    f"${price_difference:,.2f}"
                )

                # $30 movement
                if price_difference >= PRICE_TRIGGER:

                    print(
                        "Price moved $30+. Sending alert..."
                    )

                    success = send_to_channel(
                        price,
                        change_24h
                    )

                    if success:

                        last_alert_price = price

                        save_state(price)

            time.sleep(CHECK_INTERVAL)

        except Exception as e:

            print(
                "Monitor error:",
                e
            )

            time.sleep(CHECK_INTERVAL)


# =========================
# MAIN
# =========================

def main():

    print("==============================")
    print(" ETH PRICE CHANNEL BOT")
    print("==============================")

    if not test_telegram():

        print(
            "Please check your TELEGRAM_BOT_TOKEN."
        )

        return

    price_monitor()


if __name__ == "__main__":
    main()
