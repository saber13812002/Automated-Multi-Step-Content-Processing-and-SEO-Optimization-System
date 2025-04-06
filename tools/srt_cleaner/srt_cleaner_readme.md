# SRT Cleaner
ابزاری ساده برای پاکسازی فایل‌های زیرنویس SRT از تایم‌استمپ‌ها، شماره‌ها و کلمات اضافی.

## نمونه استفاده

bash
پاکسازی ساده فایل SRT (خروجی به صورت TXT)

python srt_cleaner.py input.srt

تعیین مسیر فایل خروجی

python srt_cleaner.py input.srt -o output.txt

حذف کلمات خاص

python srt_cleaner.py input.srt -w "موسیقی" "نعم" "آه"

حفظ تایم‌استمپ‌ها در خروجی

python srt_cleaner.py input.srt --keep-timestamps








 python .\tools\srt_cleaner\srt_cleaner.py 027.srt  -w "موسیقی" "نعم" "آه"  