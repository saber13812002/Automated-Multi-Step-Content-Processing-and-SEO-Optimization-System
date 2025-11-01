

# How to use

 1. Install the requirements


```bash
pip install -r requirements.txt
```

install whisper
```
    pip install --upgrade --force-reinstall git+https://github.com/openai/whisper.git
```


if you have problem
```
sudo chown -R $USER:$USER /home/s.tabatabaei/Automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/Subtitle-Generator/myenv/

deactivate
source myenv/bin/activate
pip install --upgrade --force-reinstall git+https://github.com/openai/whisper.git
```


install ffmpeg

```
apt-get update && apt-get install -y ffmpeg
```



 2. Run the script

    ```bash
    py subAlljob.py --directory ./96 --language fa 
    ```




# نحوه استفاده از اسکریپت تولید زیرنویس خودکار

## پیش‌نیازها
- پایتون 3.11 یا بالاتر
- نصب کتابخانه‌های مورد نیاز:
  ```bash
  pip install whisper openai-whisper pydub
  ```

## دستور اجرا

```bash
py subAlljob.py --directory ./96 --language fa 
```

   