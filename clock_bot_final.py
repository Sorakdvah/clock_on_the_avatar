import telebot
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import datetime
from threading import Thread
import time


API_TOKEN = 'ваш_Telegram-токен' # получить токен через Bot Father и вставить сюда
bot = telebot.TeleBot(API_TOKEN)

group_avatar_original = None
is_clock_on = False


# Загрузка файла по идентификатору файла.
def download_file(file_id):
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        return BytesIO(downloaded_file)
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        return None


# Получение и сохранение текущей аватарки чата.
def get_chat_avatar(chat_id):
    global group_avatar_original
    try:
        photos = bot.get_chat(chat_id).photo
        if photos:
            big_photo = photos.big_file_id
            bio = download_file(big_photo)
            if bio:
                group_avatar_original = Image.open(bio)
            else:
                print(f"Не удалось загрузить аватарку чата.")
                return False
    except Exception as e:
        print(f"Ошибка при получении аватарки: {e}")
        return False
    return True


def get_image_brightness(image):
    gray_image = image.convert('L')  # Переводим изображение в оттенки серого
    brightness = gray_image.getdata()  # Получаем данные яркости пикселей
    avg_brightness = sum(brightness) / len(brightness)  # Среднее значение яркости пикселей

    return avg_brightness


def update_avatar(chat_id):
    global is_clock_on, group_avatar_original
    while is_clock_on:
        if group_avatar_original:
            img = group_avatar_original.copy()
            current_time = datetime.datetime.now().strftime("%H:%M")

            # Определяем тон изображения
            brightness = get_image_brightness(img)
            # Если яркость выше порога, делаем текст черным
            if brightness > 128:
                text_color = "black"
            else:
                text_color = "white"

            draw = ImageDraw.Draw(img)
            font_size = max(72, int(img.size[0] * 0.35))
            font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size)

            left, top, right, bottom = draw.textbbox((0, 0), current_time, font=font)
            text_width = right - left
            text_height = bottom - top

            text_x = (img.width - text_width) / 2
            text_y = (img.height - text_height) / 2.25

            draw.text((text_x, text_y), current_time, fill=text_color, font=font)

            # Применяем размытие к изображению
            blurred_img = img.filter(ImageFilter.GaussianBlur(30))

            # Наносим время на размытое изображение
            draw_blurred = ImageDraw.Draw(blurred_img)
            draw_blurred.text((text_x, text_y), current_time, fill="white", font=font)

            bio = BytesIO()
            bio.name = 'image.jpeg'
            blurred_img.save(bio, 'JPEG')
            bio.seek(0)

            # bot.delete_chat_photo(chat_id) #пока закомментил эту строку, вроде бы удаление происходит и через set, причем осуществляется бесшовно, без морганий. Наполнения аватарок позволяет избежать удаление технического сообщения о замене фото.
            bot.set_chat_photo(chat_id, bio)

        time.sleep(60)


@bot.message_handler(commands=['clock_on'])
def handle_clock_on(message):
    global is_clock_on
    if not is_clock_on:
        is_clock_on = True
        if get_chat_avatar(message.chat.id):
            thread = Thread(target=update_avatar, args=(message.chat.id,))
            thread.start()
            bot.reply_to(message, "Часы включены!")
        else:
            bot.reply_to(message, "Не удалось получить аватар чата.")


@bot.message_handler(commands=['clock_off'])
def handle_clock_off(message):
    global is_clock_on, group_avatar_original
    if is_clock_on:

        # Загрузка исходной аватарки обратно в чат
        if group_avatar_original:
            bio = BytesIO()
            bio.name = 'image.jpeg'
            group_avatar_original.save(bio, 'JPEG')
            bio.seek(0)
            bot.set_chat_photo(message.chat.id, bio)

        time.sleep(1)
        is_clock_on = False
        bot.reply_to(message, "Часы выключены!")
        # После отправки исходной аватарки, вы можете удалить её из памяти, если она больше не нужна
        group_avatar_original = None


# удаление технических сообщений об изменении аватарок группы
@bot.message_handler(content_types=['new_chat_photo', 'delete_chat_photo'])
def handle_chat_photo_change(message):
    if is_clock_on:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


if __name__ == '__main__':
    bot.infinity_polling()
