import os
from dotenv import load_dotenv
import mysql.connector
from bs4 import BeautifulSoup
import requests
import urllib.parse
import time
import argparse

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '3306'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        return connection
    except mysql.connector.Error as err:
        print(f"خطا در اتصال به دیتابیس: {err}")
        return None

def get_categories(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT term_id, name, slug FROM wp_terms WHERE term_id IN (SELECT term_id FROM wp_term_taxonomy WHERE taxonomy = 'category')")
    categories = cursor.fetchall()
    cursor.close()
    return categories

def get_posts_by_category(connection, category_id):
    cursor = connection.cursor()
    query = """
    SELECT p.ID, p.post_title, p.post_name
    FROM wp_posts p
    JOIN wp_term_relationships tr ON p.ID = tr.object_id
    JOIN wp_term_taxonomy tt ON tr.term_taxonomy_id = tt.term_taxonomy_id
    WHERE tt.term_id = %s AND p.post_type = 'post' AND p.post_status = 'publish'
    """
    cursor.execute(query, (category_id,))
    posts = cursor.fetchall()
    cursor.close()
    return posts

def scan_post_for_media(connection, url, post_id):
    print(url)
    print(post_id)
    # بررسی محتوای پست در دیتابیس
    cursor = connection.cursor()
    # دریافت محتوای پست از دیتابیس
    cursor.execute("SELECT post_content FROM wp_posts WHERE ID = %s", (post_id,))
    post_content = cursor.fetchone()
    cursor.close()

    if not post_content:
        return []

    media_urls = []
    soup = BeautifulSoup(post_content[0], 'html.parser')

    # پیدا کردن تمام تگ‌های ویدیو
    videos = soup.find_all('video')
    for video in videos:
        if video.get('src'):
            media_urls.append(video['src'])

    # پیدا کردن تمام تگ‌های source در ویدیو
    video_sources = soup.find_all('source')
    for source in video_sources:
        if source.get('src'):
            media_urls.append(source['src'])

    # پیدا کردن تمام تگ‌های figure که شامل ویدیو هستند
    video_figures = soup.find_all('figure', class_='wp-block-video')
    for figure in video_figures:
        video = figure.find('video')
        if video and video.get('src'):
            media_urls.append(video['src'])

    return media_urls

def main():
    # اضافه کردن پارسر آرگومان‌های خط فرمان
    parser = argparse.ArgumentParser(description='اسکنر دسته‌بندی وردپرس')
    parser.add_argument('--category_id', type=int, help='شناسه دسته‌بندی')
    args = parser.parse_args()

    connection = connect_to_database()
    if not connection:
        return

    if args.category_id:
        # اگر شناسه دسته‌بندی از طریق پارامتر ارائه شده باشد
        cursor = connection.cursor()
        cursor.execute("SELECT term_id, name, slug FROM wp_terms WHERE term_id = %s", (args.category_id,))
        selected_category = cursor.fetchone()
        cursor.close()
        
        if not selected_category:
            print(f"دسته‌بندی با شناسه {args.category_id} یافت نشد.")
            return
    else:
        # نمایش دسته‌بندی‌ها و درخواست ورودی از کاربر (کد قبلی)
        categories = get_categories(connection)
        print("\nدسته‌بندی‌های موجود:")
        for i, category in enumerate(categories, 1):
            print(f"{i}. {category[1]} (ID: {category[0]})")

        category_index = int(input("\nشماره دسته‌بندی مورد نظر را وارد کنید: ")) - 1
        selected_category = categories[category_index]

    # دریافت پست‌های دسته‌بندی انتخاب شده
    posts = get_posts_by_category(connection, selected_category[0])
    
    # ایجاد فایل‌های خروجی
    bat_content = []
    txt_content = []
    post_data = []

    base_url = "https://asil.tv/"
    
    for post in posts:
        post_url = f"{base_url}{post[2]}"
        post_id = post[0]
        media_urls = scan_post_for_media(connection, post_url, post_id)
        
        for media_url in media_urls:
            local_filename = f"media/post_{post[0]}_{os.path.basename(urllib.parse.urlparse(media_url).path)}"
            bat_content.append(f'wget "{media_url}" -O "{local_filename}"')
            txt_content.append(media_url)
            post_data.append({
                'post_id': post[0],
                'post_url': post_url,
                'media_url': media_url,
                'local_file': local_filename
            })

    # ذخیره فایل‌ها
    with open('download.bat', 'w', encoding='utf-8') as f:
        f.write('\n'.join(bat_content))

    with open('download_urls.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_content))

    with open('post_data.txt', 'w', encoding='utf-8') as f:
        for data in post_data:
            f.write(f"Post ID: {data['post_id']}\n")
            f.write(f"Post URL: {data['post_url']}\n")
            f.write(f"Media URL: {data['media_url']}\n")
            f.write(f"Local File: {data['local_file']}\n")
            f.write("-" * 50 + "\n")

    print("\nفایل‌های خروجی ایجاد شدند:")
    print("1. download.bat - برای دانلود با wget")
    print("2. download_urls.txt - برای دانلود با Download Accelerator")
    print("3. post_data.txt - اطلاعات کامل پست‌ها و فایل‌های مدیا")

    connection.close()

if __name__ == "__main__":
    main()
