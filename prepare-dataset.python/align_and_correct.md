# فایل اول
python align_and_correct_srt.py \
  --srt "471؛وظایف روحانیت سخنرانی ؛77.12.8؛مؤسسه؛.srt" \
  --reference "471؛وظایف روحانیت سخنرانی ؛77.12.8؛مؤسسه؛_extracted.txt" \
  --output "471_corrected.srt"

# فایل دوم
python align_and_correct_srt.py \
  --srt "انتخابات سخنرانی - 70.01.19 - در جمع کانون موتلفه اسلامی - تهران - (215).srt" \
  --reference "انتخابات سخنرانی - 70.01.19 - در جمع کانون موتلفه اسلامی - تهران - (215)_extracted.txt" \
  --output "215_corrected.srt"