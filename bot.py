import os
import threading
import subprocess
from dotenv import load_dotenv
import telebot
from moviepy.editor import VideoFileClip

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота
bot = telebot.TeleBot(os.getenv('TOKEN'))

def cleanup_files(*filenames):
    """Удаление временных файлов"""
    for filename in filenames:
        try:
            if filename and os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"Ошибка при удалении {filename}: {e}")

def make_video_note(input_file, output_file):
    """Создание круглого видео для Telegram"""
    command = [
        "ffmpeg", "-i", input_file,
        "-vf", "crop=min(iw\\,ih):min(iw\\,ih),scale=256:256,format=yuv420p",
        "-codec:v", "libx264", "-b:v", "500k", "-preset", "fast",
        "-codec:a","aac","-b:a","128k", output_file 
        ]
    subprocess.run(command, check=True)

@bot.message_handler(content_types=['video'])
def handle_video(message):
    try:
        # Проверка размера файла (макс. 50MB)
        if message.video.file_size > 50 * 1024 * 1024:
            bot.send_message(message.chat.id, "❌ Файл слишком большой (максимум 50 МБ)")
            return

        # Создаем уникальные имена файлов
        file_id = message.video.file_id
        temp_file = f"temp_{file_id}.mp4"
        processed_file = f"processed_{file_id}.mp4"
        video_note_file = f"video_note_{file_id}.mp4"

        # Отправляем подтверждение получения
        status_msg = bot.send_message(message.chat.id, "📥 Boshladim...")

        # Запускаем обработку в отдельном потоке
        def video_processing_thread():
            try:
                # Скачивание файла
                file_info = bot.get_file(file_id)
                downloaded_data = bot.download_file(file_info.file_path)
                
                with open(temp_file, 'wb') as f:
                    f.write(downloaded_data)

                # Обновление статуса
                bot.edit_message_text("🔄 Bir daqiqa...", 
                                      message.chat.id, 
                                      status_msg.message_id)

                # Обработка видео
                with VideoFileClip(temp_file) as clip:
                    # Обрезаем до 60 секунд
                    if clip.duration > 60:
                        clip = clip.subclip(0, 60)

                    # Делаем видео квадратным
                    width, height = clip.size
                    min_side = min(width, height)

                    # Центрируем обрезку, чтобы получить квадратное видео
                    clip_cropped = clip.crop(
                        width=min_side, 
                        height=min_side, 
                        x_center=width // 2, 
                        y_center=height // 2
                    )

                    # Изменяем размер до 640x640 (если нужно)
                    if min_side > 640:
                        clip_cropped = clip_cropped.resize((640, 640))

                    # Экспорт видео
                    clip_cropped.write_videofile(
                        processed_file,
                        codec="libx264",
                        audio_codec="aac",
                        preset="fast",
                        threads=4,
                        logger=None  # Отключаем логгирование moviepy
                    )

                # Делаем круглый video_note
                make_video_note(processed_file, video_note_file)

                # Отправка круглого видео
                with open(video_note_file, 'rb') as video_file:
                    bot.send_video_note(message.chat.id, video_file)

                # Отправка ссылки после видео
                bot.send_message(message.chat.id, "🔗Rahmat sizga yaxshi inson. Bot manzili @dumaloqvideo_bot")

                # Удаляем сообщение "Обрабатываю..."
                bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ Ошибка обработки: {str(e)}")
            finally:
                cleanup_files(temp_file, processed_file, video_note_file)

        # Запуск потока обработки
        threading.Thread(target=video_processing_thread).start()

    except Exception as e:
        bot.send_message(message.chat.id, f"🚨 Критическая ошибка: {str(e)}")
        cleanup_files(temp_file, processed_file, video_note_file)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Assalom aleykum yaxshi inson! Menga 20MB dan katta bo'lmagan video yuboring, men uni dumaloq ko'rinishga keltirib beraman!")

if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()             