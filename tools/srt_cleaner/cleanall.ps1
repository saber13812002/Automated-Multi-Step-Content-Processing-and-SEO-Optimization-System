$INPUT_DIR = "D:\media\96"
$OUTPUT_DIR = "D:\media\96"

# ایجاد پوشه خروجی در صورت عدم وجود
if (-Not (Test-Path -Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Force -Path $OUTPUT_DIR
}

# پردازش هر فایل .srt در پوشه ورودی
Get-ChildItem -Path $INPUT_DIR -Filter "*.srt" | ForEach-Object {
    $file = $_.FullName
    Write-Host "Cleaning $file ..."
    python srt_cleaner.py $file --output "$OUTPUT_DIR\$($_.Name)"
}
