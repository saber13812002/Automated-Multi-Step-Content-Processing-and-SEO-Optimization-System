import re
import argparse

def clean_srt(input_file, output_file, words_to_remove=None, remove_timestamps=True):
    if words_to_remove is None:
        words_to_remove = ['نعم']
    
    # خواندن فایل SRT
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # حذف شماره‌های زیرنویس و تایم‌استمپ‌ها
    # حذف الگوی شماره زیرنویس
    content = re.sub(r'^\d+$', '', content, flags=re.MULTILINE)
    
    # حذف تایم‌استمپ‌ها اگر remove_timestamps فعال باشد
    if remove_timestamps:
        # حذف تایم‌استمپ‌های با فرمت‌های مختلف
        content = re.sub(r'\d+:\d+:\d+(?:,\d+)?\s*-->\s*\d+:\d+:\d+(?:,\d+)?', '', content)
        # حذف تایم‌استمپ‌های تکی
        content = re.sub(r'\d+:\d+:\d+(?:,\d+)?', '', content)
    
    # حذف خطوط خالی متوالی با دقت بیشتر
    content = re.sub(r'\n{2,}', '\n', content)
    
    # حذف کلمه "موسيقى" و تکرارهای آن
    content = re.sub(r'\s*موسيقى\s*(?:,?\s*موسيقى\s*)*', ' ', content)
    
    # حذف کلمات مشخص شده
    for word in words_to_remove:
        content = content.replace(word, '')
    
    # حذف کاراکترهای اضافی و فاصله‌های تکراری
    content = re.sub(r'\s+', ' ', content)
    content = content.strip()
    
    # ذخیره متن تمیز شده
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

# مثال استفاده
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='پاک‌سازی فایل‌های زیرنویس SRT')
    parser.add_argument('input_file', help='مسیر فایل ورودی SRT')
    parser.add_argument('--output', '-o', default=None, help='مسیر فایل خروجی (اختیاری)')
    parser.add_argument('--words', '-w', nargs='+', default=['نعم'], 
                      help='لیست کلماتی که باید حذف شوند (با فاصله از هم جدا شوند)')
    parser.add_argument('--keep-timestamps', '-kt', action='store_true',
                      help='حفظ تایم‌استمپ‌ها در خروجی')
    
    args = parser.parse_args()
    
    # اگر فایل خروجی مشخص نشده باشد، از نام فایل ورودی با پسوند .txt استفاده می‌کنیم
    output_file = args.output if args.output else args.input_file.rsplit('.', 1)[0] + '.txt'
    
    clean_srt(args.input_file, output_file, args.words, not args.keep_timestamps) 