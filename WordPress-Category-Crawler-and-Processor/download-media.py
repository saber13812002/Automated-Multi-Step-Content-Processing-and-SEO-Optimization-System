import os
from dotenv import load_dotenv
import mysql.connector
import requests
import urllib.parse
from pathlib import Path
import argparse

# بارگذاری متغیرهای محیطی
load_dotenv()

def connect_to_laravel_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST_LARAVEL', 'localhost'),
            port=os.getenv('DB_PORT_LARAVEL', '3306'),
            user=os.getenv('DB_USER_LARAVEL'),
            password=os.getenv('DB_PASSWORD_LARAVEL'),
            database=os.getenv('DB_NAME_LARAVEL')
        )
        return connection
    except mysql.connector.Error as err:
        print(f"خطا در اتصال به دیتابیس: {err}")
        return None

def get_media_files(connection, category_id=None):
    try:
        cursor = connection.cursor(dictionary=True)
        if category_id:
            query = "SELECT * FROM asil_tv_medias WHERE category_id = %s"
            cursor.execute(query, (category_id,))
        else:
            query = "SELECT * FROM asil_tv_medias"
            cursor.execute(query)
        
        media_files = cursor.fetchall()
        cursor.close()
        return media_files
    except mysql.connector.Error as err:
        print(f"خطا در دریافت اطلاعات: {err}")
        return []

def download_file(url, destination):
    try:
        # ایجاد پوشه در صورت عدم وجود
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        # بررسی وجود فایل
        if os.path.exists(destination):
            print(f"فایل از قبل وجود دارد: {destination}")
            return True

        # دانلود فایل
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # ذخیره فایل
        with open(destination, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"دانلود موفق: {destination}")
        return True
    except Exception as e:
        print(f"خطا در دانلود {url}: {str(e)}")
        return False

def update_media_record(connection, media_id, local_file):
    try:
        cursor = connection.cursor()
        query = """
            UPDATE asil_tv_medias 
            SET downloaded_at = CURRENT_TIMESTAMP,
                local_file = %s
            WHERE id = %s
        """
        cursor.execute(query, (local_file, media_id))
        connection.commit()
        cursor.close()
    except mysql.connector.Error as err:
        print(f"خطا در به‌روزرسانی رکورد: {err}")


def main():
    parser = argparse.ArgumentParser(description='دانلود فایل‌های رسانه از asil_tv_medias')
    parser.add_argument('--category_id', type=int, help='شناسه دسته‌بندی برای دانلود')
    args = parser.parse_args()

    # اتصال به دیتابیس
    connection = connect_to_laravel_database()
    if not connection:
        return

    # دریافت فایل‌های رسانه
    media_files = get_media_files(connection, args.category_id)
    
    # ایجاد پوشه اصلی media اگر وجود ندارد
    base_path = Path('media')
    base_path.mkdir(exist_ok=True)

    # دانلود فایل‌ها
    for media in media_files:
        # ساخت مسیر فایل بر اساس category_id
        category_folder = base_path / str(media['category_id'])
        filename = os.path.basename(urllib.parse.urlparse(media['media_url']).path)
        if not filename:
            filename = f"media_{media['id']}.mp4"
        
        destination = category_folder / filename
        
        print(f"\nدر حال دانلود {media['media_url']}")
        print(f"ذخیره در: {destination}")
        
        download_file(media['media_url'], str(destination))

        # به‌روزرسانی رکورد در دیتابیس
        relative_path = str(destination.relative_to(base_path))
        update_media_record(connection, media['id'], relative_path)

    connection.close()
    print("\nعملیات دانلود به پایان رسید.")

if __name__ == "__main__":
    main() 