git config --local user.name "saber taba"
git config --local user.email "saber.tabataba@gmail.com"


git add .


git commit -m "توضیح تغییرات"


git push asil main




git remote set-url asil http://192.168.2.246/product/automated-multi-step-content-processing-and-seo-optimization-system.git


username : saber13812002
password : wy6osFFjpqZ9WmKc7PCnxP4BCE4QnebrTBcARJqEf9w=






## نکات مهم برای راه‌اندازی پروژه

### 1. GitLab

* از GitLab CE 16.3.2 استفاده شده و روی پورت‌های 80، 443 و SSH (در Compose اول 2222) در دسترس است.
* **اتصال به دیتابیس و Redis خارجی** است؛ بنابراین PostgreSQL و Redis باید قبل از راه‌اندازی GitLab آماده باشند و IP/پورت صحیح در `GITLAB_OMNIBUS_CONFIG` وارد شود.
* برای **فعال کردن کاربر** از `gitlab-rails console` استفاده کنید:

  ```bash
  docker exec -it gitlab gitlab-rails console
  user = User.find_by(username: 'USERNAME')
  user.activate
  user.save
  ```
* حجم‌های persistent (`gitlab_config`, `gitlab_logs`, `gitlab_data`) باید حفظ شوند تا اطلاعات GitLab از بین نرود.

---

### 2. PostgreSQL

* حتما **کاربر و دیتابیس درست** ایجاد شده باشد (POSTGRES_USER, POSTGRES_DB, POSTGRES_PASSWORD).
* پورت روی سرور قابل دسترسی باشد (مثلاً `5432:5432`).
* Healthcheck تعریف شده است تا اطمینان حاصل شود دیتابیس آماده است قبل از شروع سرویس‌های وابسته.

---

### 3. Redis

* از نسخه Redis 7 استفاده می‌کنیم، با **حافظه محدود و سیاست LRU** برای جلوگیری از پر شدن بیش از حد.
* Healthcheck دارد تا اطمینان حاصل شود Redis آماده است.
* اگر پسورد دارید، در environment یا `gitlab_rails['redis_password']` حتما اضافه شود.

---

### 4. سرویس‌های دیگر (ChromaDB و Typesense)

* Healthcheck برای اطمینان از آماده بودن سرویس‌ها قبل از اتصال سایر سرویس‌ها مهم است.
* Volumeهای persistent تعریف شده‌اند (`chroma_data`, `typesense_data`) تا داده‌ها از بین نرود.
* تنظیمات محیطی (`API_KEY`، `ALLOW_RESET`) را مطابق نیاز پروژه تنظیم کنید.
* پورت‌ها روی سرور باز و قابل دسترسی باشند.

---

### 5. شبکه‌ها

* همه سرویس‌ها روی یک شبکه داخلی (`rag_network`) هستند تا بتوانند با نام سرویس به هم وصل شوند بدون نیاز به IP ثابت.
* برای سرویس‌هایی که نیاز به دسترسی از بیرون دارند (GitLab, Typesense, Redis برای مانیتورینگ)، پورت‌ها باید map شوند.

---

### 6. ترتیب راه‌اندازی

1. PostgreSQL → Redis → ChromaDB / Typesense → GitLab

   > ترتیب مهم است زیرا GitLab به PostgreSQL و Redis وابسته است.
2. بعد از راه‌اندازی، Healthcheckها را چک کنید:

```bash
docker ps
docker logs <container_name>
```

---

### 7. نکات عملیاتی

* برای اعمال تغییرات در Compose یا ENV، همیشه:

```bash
docker-compose down
docker-compose up -d
```

* حجم‌ها را پاک نکنید مگر قصد reset داده‌ها داشته باشید.
* در صورت نیاز به backup:

  * PostgreSQL: `pg_dump` یا volume backup
  * Redis: dump AOF/RDB
  * GitLab: backup built-in `gitlab-backup`








# Project Setup Guide

**توضیح کوتاه:** این راهنما نشان می‌دهد چطور پروژه را از صفر روی یک سرور لینوکس با Docker Compose راه‌اندازی کنیم، شامل GitLab، Redis، PostgreSQL و اپلیکیشن‌ها.

---

## 1. نصب پیش‌نیازها

```bash
# بروزرسانی سیستم
sudo apt update && sudo apt upgrade -y

# نصب Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# نصب Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/2.22.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# بررسی نصب
docker --version
docker-compose --version
```

---

## 2. ساخت دایرکتوری پروژه

```bash
mkdir -p ~/myproject
cd ~/myproject
```

---

## 3. ساخت فایل `docker-compose.yml` نمونه

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: gitlabhq_production
      POSTGRES_USER: gitlab
      POSTGRES_PASSWORD: mypassword
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    container_name: redis
    ports:
      - "6379:6379"

  gitlab:
    image: gitlab/gitlab-ee:latest
    container_name: gitlab
    hostname: 'gitlab.local'
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://gitlab.local'
        gitlab_rails['db_adapter'] = 'postgresql'
        gitlab_rails['db_encoding'] = 'utf8'
        gitlab_rails['db_database'] = 'gitlabhq_production'
        gitlab_rails['db_username'] = 'gitlab'
        gitlab_rails['db_password'] = 'mypassword'
        gitlab_rails['db_host'] = 'postgres'
        gitlab_rails['redis_host'] = 'redis'
    ports:
      - "80:80"
      - "443:443"
      - "22:22"
    depends_on:
      - postgres
      - redis
    volumes:
      - gitlab_config:/etc/gitlab
      - gitlab_logs:/var/log/gitlab
      - gitlab_data:/var/opt/gitlab

volumes:
  pgdata:
  gitlab_config:
  gitlab_logs:
  gitlab_data:
```

---

## 4. راه‌اندازی سرویس‌ها

```bash
docker-compose up -d
```

> ⚠️ نکته: ممکن است GitLab چند دقیقه طول بکشد تا آماده شود.

---

## 5. ساخت و فعال‌سازی کاربر GitLab

1. وارد کنسول GitLab:

```bash
docker exec -it gitlab gitlab-rails console
```

2. پیدا کردن کاربر:

```ruby
user = User.find_by(username: 'saber')
```

3. فعال کردن کاربر:

```ruby
user.activate
user.save
```

---

## 6. تست اتصال به Redis و PostgreSQL

```bash
# Redis
docker exec -it redis redis-cli ping  # پاسخ: PONG

# PostgreSQL
docker exec -it postgres psql -U gitlab -d gitlabhq_production
```

---

## 7. نکات مهم

* لاگ‌ها و کانفیگ‌ها در volumes مشخص شده ذخیره می‌شوند.
* هر تغییری در `docker-compose.yml` پس از اجرا، باید با `docker-compose down && docker-compose up -d` اعمال شود.
* GitLab ممکن است نیاز به چند دقیقه زمان برای آماده شدن داشته باشد، لاگ‌ها را بررسی کنید:

```bash
docker logs -f gitlab
```




