import os
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip

# تنظیمات
input_video = "vertical_video.mp4"
output_folder = "frames"
output_video = "horizontal_output.mp4"
fps = 30  # نرخ فریم ویدیو

# مرحله 1: استخراج فریم‌ها
os.makedirs(output_folder, exist_ok=True)
cap = cv2.VideoCapture(input_video)
frame_num = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.imwrite(f"{output_folder}/frame_{frame_num:04d}.png", frame)
    frame_num += 1

cap.release()

# مرحله 2: تغییر سایز فریم‌ها به 16:9 با پس‌زمینه خاکستری یا سیاه
def pad_to_16_9(img):
    h, w, _ = img.shape
    target_w = int(h * 16 / 9)
    pad = (target_w - w) // 2
    padded_img = cv2.copyMakeBorder(img, 0, 0, pad, pad, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    return padded_img

processed_frames = []

for i in range(frame_num):
    img = cv2.imread(f"{output_folder}/frame_{i:04d}.png")
    padded = pad_to_16_9(img)

    # اینجا می‌تونی AI inpainting استفاده کنی
    # فعلاً فقط کشیدن تصویر با blur
    background = cv2.GaussianBlur(padded, (101, 101), 30)
    center_w = img.shape[1]
    h = img.shape[0]
    target_w = background.shape[1]
    offset = (target_w - center_w) // 2

    background[:, offset:offset+center_w] = img
    processed_frames.append(background)

# مرحله 3: ساخت ویدیو جدید
clip = ImageSequenceClip([cv2.cvtColor(f, cv2.COLOR_BGR2RGB) for f in processed_frames], fps=fps)
clip.write_videofile(output_video, codec="libx264")
