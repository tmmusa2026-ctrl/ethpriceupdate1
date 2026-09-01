import os
import time
import json
import requests

from PIL import Image, ImageDraw, ImageFont, ImageOps


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Binance
BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_SYMBOL = "ETHUSDT"

# Alert settings
PRICE_TRIGGER = 30.0
CHECK_INTERVAL = 60

# Files
STATE_FILE = "bot_state.json"
TEMPLATE_FILE = "template.png"
OUTPUT_FILE = "eth_price.png"

# Telegram username
USERNAME = "@eth_pricealert"

# Exact final image size
IMAGE_WIDTH = 413
IMAGE_HEIGHT = 108


# =========================================================
# CHECK ENVIRONMENT
# =========================================================

if not BOT_TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN is missing!"
    )

if not CHANNEL_ID:
    raise ValueError(
        "TELEGRAM_CHANNEL_ID is missing!"
    )

if not os.path.exists(TEMPLATE_FILE):
    raise FileNotFoundError(
        "template.png is missing!"
    )


# =========================================================
# FONT
# =========================================================

def get_font(size, bold=False):

    if bold:

        paths = [
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans-Bold.ttf",

            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Bold.ttf"
        ]

    else:

        paths = [
            "/usr/share/fonts/truetype/dejavu/"
            "DejaVuSans.ttf",

            "/usr/share/fonts/truetype/liberation2/"
            "LiberationSans-Regular.ttf"
        ]

    for path in paths:

        if os.path.exists(path):

            try:

                return ImageFont.truetype(
                    path,
                    size
                )

            except Exception:
                pass

    return ImageFont.load_default()


# =========================================================
# TELEGRAM API
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
# TEST TELEGRAM BOT
# =========================================================

def test_telegram():

    result = telegram_request(
        "getMe"
    )

    if result and result.get("ok"):

        username = (
            result["result"]
            .get("username")
        )

        print(
            "Telegram bot connected:",
            username
        )

        return True

    print(
        "Telegram bot connection failed!"
    )

    return False


# =========================================================
# GET ETH PRICE FROM BINANCE
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

        price = float(
            data["price"]
        )

        return price

    except Exception as e:

        print(
            "Binance API error:",
            e
        )

        return None


# =========================================================
# LOAD LAST ALERT PRICE
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
# SAVE LAST ALERT PRICE
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
# CREATE PRICE IMAGE
# =========================================================

def create_price_image(price):

    # -----------------------------------------------------
    # OPEN YOUR ORIGINAL TEMPLATE
    # -----------------------------------------------------

    image = Image.open(
        TEMPLATE_FILE
    ).convert("RGB")

    original_width, original_height = (
        image.size
    )

    print(
        "Original template size:",
        f"{original_width}x{original_height}"
    )


    # -----------------------------------------------------
    # CONVERT TO EXACT 413x108
    #
    # Keeps the original proportions as much as possible.
    # -----------------------------------------------------

    image = ImageOps.fit(
        image,
        (
            IMAGE_WIDTH,
            IMAGE_HEIGHT
        ),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5)
    )


    # Make sure it is RGB
    image = image.convert(
        "RGB"
    )

    draw = ImageDraw.Draw(
        image
    )


    # =====================================================
    # IMPORTANT
    #
    # At this point:
    #
    # image = EXACTLY 413 x 108
    #
    # We don't create a new background.
    # We use your original PNG.
    # =====================================================


    # =====================================================
    # PRICE AREA
    #
    # Cover ONLY the old price.
    # =====================================================

    # Background color sampled/approximated
    # from your blue template.

    blue = (
        102,
        117,
        238
    )

    draw.rectangle(
        (
            112,
            13,
            301,
            58
        ),
        fill=blue
    )


    # =====================================================
    # LIVE ETH PRICE
    # =====================================================

    price_font = get_font(
        42,
        bold=True
    )

    # Reference style:
    # $2,419
    #
    # No decimal inside image.

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

    # Center horizontally
    price_x = (
        IMAGE_WIDTH
        - text_width
    ) // 2

    # Vertical position
    price_y = 8

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
    # USERNAME AREA
    # =====================================================

    # Cover old @eth_price area

    draw.rounded_rectangle(
        (
            158,
            60,
            255,
            79
        ),
        radius=9,
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

    username_height = (
        bbox[3] - bbox[1]
    )

    # Pill size
    padding_left = 12
    padding_right = 8
    padding_top = 2
    padding_bottom = 3

    pill_width = (
        username_width
        + padding_left
        + padding_right
    )

    pill_height = (
        username_height
        + padding_top
        + padding_bottom
    )

    # Center pill
    pill_x = (
        IMAGE_WIDTH
        - pill_width
    ) // 2

    pill_y = 61


    # =====================================================
    # USERNAME PILL
    # =====================================================

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


    # =====================================================
    # SMALL ICON
    # =====================================================

    icon_x = (
        pill_x + 6
    )

    icon_y = (
        pill_y
        + pill_height // 2
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


    # =====================================================
    # USERNAME TEXT
    # =====================================================

    draw.text(
        (
            pill_x + padding_left,
            pill_y + padding_top
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
    # SAVE FINAL PNG
    # =====================================================

    image.save(
        OUTPUT_FILE,
        format="PNG",
        optimize=True
    )


    # Verify final size

    final_image = Image.open(
        OUTPUT_FILE
    )

    print(
        "Final PNG size:",
        final_image.size
    )

    final_image.close()

    return OUTPUT_FILE


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
# SEND ALERT TO CHANNEL
# =========================================================

def send_alert(
    price,
    previous_price=None
):

    try:

        # Create image
        image_path = (
            create_price_image(
                price
            )
        )

        # Create caption
        caption = (
            create_caption(
                price,
                previous_price
            )
        )


        # Send photo

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


        # Check result

        if result and result.get("ok"):

            print(
                "================================"
            )

            print(
                "ALERT SENT SUCCESSFULLY"
            )

            print(
                f"ETH Price: ${price:,.2f}"
            )

            print(
                "================================"
            )

            return True


        print(
            "Failed to send alert."
        )

        return False


    except Exception as e:

        print(
            "Alert sending error:",
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


    print("")
    print(
        "================================"
    )
    print(
        "       ETH PRICE CHANNEL BOT"
    )
    print(
        "================================"
    )

    print(
        "Price Source : Binance"
    )

    print(
        "Symbol       :",
        BINANCE_SYMBOL
    )

    print(
        "Channel      :",
        CHANNEL_ID
    )

    print(
        "Trigger      : $",
        PRICE_TRIGGER
    )

    print(
        "Interval     :",
        CHECK_INTERVAL,
        "seconds"
    )

    print(
        "Image Size   :",
        f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}"
    )

    print(
        "Username     :",
        USERNAME
    )

    print(
        "================================"
    )

    print("")


    # =====================================================
    # INFINITE MONITOR LOOP
    # =====================================================

    while True:

        try:

            # Get Binance price

            current_price = (
                get_eth_price()
            )


            if current_price is None:

                print(
                    "Could not get ETH price."
                )

                time.sleep(
                    CHECK_INTERVAL
                )

                continue


            print(
                f"Current ETH Price: "
                f"${current_price:,.2f}"
            )


            # =================================================
            # FIRST RUN
            # =================================================

            if last_alert_price is None:

                print(
                    "No previous alert price found."
                )

                print(
                    "Sending first alert..."
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

                    print(
                        "Initial price saved."
                    )


            # =================================================
            # NORMAL RUN
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


                # =================================================
                # $30 MOVEMENT DETECTED
                # =================================================

                if movement >= PRICE_TRIGGER:

                    print(
                        "================================"
                    )

                    print(
                        "$30 PRICE MOVEMENT DETECTED!"
                    )

                    print(
                        f"Previous: "
                        f"${last_alert_price:,.2f}"
                    )

                    print(
                        f"Current: "
                        f"${current_price:,.2f}"
                    )

                    print(
                        "Sending alert..."
                    )


                    success = send_alert(
                        current_price,
                        last_alert_price
                    )


                    if success:

                        # New reference price
                        last_alert_price = (
                            current_price
                        )

                        save_state(
                            current_price
                        )

                        print(
                            "New alert price saved."
                        )

                    print(
                        "================================"
                    )


            # Wait

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
    print(
        "Starting ETH Price Bot..."
    )
    print("")


    # Test Telegram

    if not test_telegram():

        print(
            "Telegram connection failed!"
        )

        return


    # Start monitor

    price_monitor()


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":

    main()
