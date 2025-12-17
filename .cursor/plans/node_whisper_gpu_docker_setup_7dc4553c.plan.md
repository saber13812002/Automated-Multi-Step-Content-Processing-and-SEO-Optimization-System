---
name: node_whisper_gpu_docker_setup
overview: طراحی دو پروژه نود با داکر و داکر کامپوز برای پردازش زیرنویس با ویسپر روی GPU، شامل صف تسک، MySQL پرسیست، وب‌سرویس‌ها و کران‌جاب قابل‌پیکربندی.
todos:
  - id: init-folders
    content: ایجاد دو پوشه جدید whisper-task-runner و whisper-cron-worker با ساختار پایه نود
    status: completed
  - id: docker-configs
    content: نوشتن Dockerfile و docker-compose برای هر دو پروژه با تنظیم GPU و MySQL پرسیست در پروژه اول
    status: completed
    dependencies:
      - init-folders
  - id: task-runner-logic
    content: پیاده‌سازی منطق صف فایل‌ها، وب‌سرویس‌ها و ارتباط MySQL در whisper-task-runner
    status: completed
    dependencies:
      - docker-configs
  - id: cron-worker-logic
    content: پیاده‌سازی کران‌جاب، وب‌سرویس کنترل کران و گزارش‌دهی در whisper-cron-worker
    status: completed
    dependencies:
      - docker-configs
  - id: env-and-docs
    content: تعریف متغیرهای محیطی، نمونه .env و مستند کوتاه نحوه اجرا و تست
    status: completed
    dependencies:
      - task-runner-logic
      - cron-worker-logic
---

## طرح کلی پیاده‌سازی

در این طرح، دو فولدر نود جدید ایجاد می‌کنیم (مثلاً `whisper-task-runner` و `whisper-cron-worker`) که هر کدام Dockerfile و `docker-compose.yml` مخصوص خود را دارند و با GPU سازگار هستند. وب‌سرویس‌ها با نود + Express پیاده می‌شوند، MySQL در پروژه اول داخل همان `docker-compose` به‌صورت پرسیست است، و کران‌جاب در پروژه دوم با کتابخانه `node-cron` و متغیرهای محیطی کنترل می‌شود.

---

### 1) ساختار کلی دو پوشه جدید

- **پوشه اول**: `whisper-task-runner`
  - **هدف**: ماشین تخصصی زیرنویس‌گذاری با ویسپر روی GPU، کنترل‌شده با بازه زمانی مشخص، متصل به صف فایل‌ها و بانک MySQL.
  - **محتویات اصلی**:
    - `package.json`، `tsconfig.json` (در صورت استفاده از TypeScript) یا نود ساده
    - `src/server.ts` (Express app برای وب‌سرویس‌ها)
    - `src/worker.ts` (منطق اصلی برداشتن تسک، پردازش ویسپر، ذخیره SRT)
    - `src/db.ts` (اتصال MySQL و کوئری‌ها)
    - `src/config.ts` (خواندن env و منطق بازه زمانی)
    - `Dockerfile` (نود + وابستگی ویسپر + CUDA Runtime)
    - `docker-compose.yml`:
      - سرویس `app` (نود + GPU)
      - سرویس `mysql` با volume پرسیست (`mysql_data`)
      - سرویس `adminer` یا مشابه برای مدیریت دیتابیس در صورت نیاز
    - `.env.example` / `.env` برای متغیرهای محیطی (ساعت شروع/پایان، مسیر پوشه، تنظیمات DB، اندازه batch صف، و ...)

- **پوشه دوم**: `whisper-cron-worker`
  - **هدف**: ماشین ویسپر که هر ساعت (یا هر N دقیقه) روی مجموعه‌ای از فایل‌ها کار می‌کند، نتایج را پردازش و به ربات (مثلاً تلگرام) گزارش می‌دهد.
  - **محتویات اصلی**:
    - `package.json`
    - `src/server.ts` (Express app برای وب‌سرویس‌های کنترل کران و گزارش)
    - `src/cron.ts` (تعریف job با `node-cron`)
    - `src/whisper-job.ts` (منطق پردازش ویسپر در این پروژه)
    - `src/notifier.ts` (ارسال گزارش به ربات/وب‌هوک – در حد اسکلت و قابل‌تنظیم)
    - `src/config.ts` (ENV و فلگ فعال/غیرفعال بودن کران)
    - `Dockerfile`
    - `docker-compose.yml` (حداقل سرویس `app` + احتمالا Redis یا DB مجزا در صورت نیاز)
    - `.env.example` / `.env` شامل فلگ فعال‌سازی کران و زمان‌بندی

---

### 2) منطق زمان‌بندی استفاده از GPU در پروژه اول

- **متغیرهای محیطی** در `.env` و همچنین قابل تزریق از بیرون:
  - `ACTIVE_START_HOUR=23` (ساعت شروع، ۲۴ ساعته)
  - `ACTIVE_END_HOUR=5` (ساعت پایان)
  - `TIMEZONE=Asia/Tehran` (برای محاسبه صحیح زمان محلی)
- **ماژول `config`**:
  - تابع `isWithinActiveWindow(now)` که با توجه به ساعت فعلی و بازه (حتی اگر از نصف شب عبور کند) تعیین می‌کند آیا اجازه استفاده از GPU هست یا خیر.
- **رفتار اپلیکیشن**:
  - هنگام شروع پردازش هر تسک، ابتدا `isWithinActiveWindow` بررسی می‌شود:
    - اگر **خارج از بازه** باشد، worker:
      - وارد حالت idle می‌شود (مثلاً `setTimeout` تا شروع بازه بعدی) و ویسپر اجرا نمی‌شود.
      - از GPU استفاده نمی‌کند تا بازه شروع شود.
    - اگر **داخل بازه** باشد، پردازش انجام می‌شود.
  - برای سناریوی "بعد از اتمام کار خاموش شود":
    - وقتی صف خالی شد و دیتابیس هم تسک فعال برنمی‌گرداند، worker سیگنال graceful shutdown می‌دهد (`process.exit(0)`)، و سیستم خارجی (systemd, n8n, cron host) در بازه بعدی دوباره کانتینر را بالا می‌آورد.

---

### 3) مدیریت صف فایل‌ها و پوشه ورودی در پروژه اول

- **تنظیم مسیرها در env**:
  - `INPUT_DIR=/media/input` (مسیر mount شده از هاست)
  - `OUTPUT_DIR=/media/output`
  - `LOCK_EXTENSION=.lock` (فرمت لاک)
- **اسکن پوشه**:
  - Worker یک loop دارد که:

    1. لیست فایل‌های ویدئویی در `INPUT_DIR` را می‌خواند.
    2. برای هر فایل ویدئویی:

       - اگر کنار آن فایل SRT (`.srt`) وجود دارد، **رد می‌شود**.
       - اگر فایل `*.lock` کنار آن هست (یعنی توسط ماشینی دیگر در حال پردازش است)، **رد می‌شود**.
       - در غیر این صورت، اگر در بازه زمانی مجاز هست، آن را به‌عنوان کاندید صف قرار می‌دهد.
  - **مدیریت صف داخلی**:
    - می‌توانیم از یک آرایه در حافظه استفاده کنیم که با هر اسکن به‌روزرسانی شود.
    - اندازه batch پردازش از env (مثلاً `BATCH_SIZE=2`) خوانده می‌شود.
  - **لاک فایل**:
    - قبل از شروع پردازش هر فایل، worker یک فایل `myvideo.mp4.lock` کنار آن می‌سازد.
    - بعد از پایان موفق، لاک و در صورت نیاز فلگ دیتابیس به‌روزرسانی می‌شود.

---

### 4) ارتباط با دیتابیس MySQL در پروژه اول

- **ساختار دیتابیس مشترک** (نمونه ساده):
  - جدول `tasks`:
    - `id` (PK)
    - `input_path` (مسیر فایل روی سرور)
    - `output_path` (مسیر هدف SRT)
    - `status` (`pending`, `processing`, `done`, `failed`)
    - `assigned_to` (شناسه ماشین/کانتینر)
    - `picked_at` (زمان برداشت تسک)
    - `finished_at`
    - `timeout_minutes` (مثلاً 120 دقیقه)
  - اندیس روی `status` و `picked_at` برای کوئری‌های سریع.
- **منطق کوئری برای صف خالی**:
  - اگر پوشه ورودی خالی بود، worker این کارها را می‌کند:

    1. به MySQL وصل می‌شود.
    2. کوئری: انتخاب N تسک `pending` که `picked_at` تهی باشد یا تسک‌هایی که `status='processing'` هستند ولی `picked_at` قدیمی‌تر از ۲ ساعت (timeout) است.
    3. به صورت transaction:

       - برای هر تسک انتخاب‌شده، `status='processing'` و `picked_at=NOW()` و `assigned_to=<machine_id>` می‌شود.

    1. برای هر تسک منتخب، در پوشه فایل مربوطه لاک ساخته می‌شود و به صف داخلی اضافه می‌شود.

- **امنیت و پایداری MySQL**:
  - در `docker-compose.yml`:
    - سرویس `mysql` با volume: `mysql_data:/var/lib/mysql` برای پرسیست داده.
    - تعریف user/password از env (`MYSQL_ROOT_PASSWORD`, `MYSQL_DATABASE`, ...).
  - برای مدیریت سریع دیتابیس، یک سرویس اختیاری `adminer`/`phpmyadmin` اضافه می‌کنیم.

---

### 5) وب‌سرویس‌های پروژه اول (API برای تسک‌ها)

در `src/server.ts` با Express سه دسته وب‌سرویس اصلی پیاده می‌شود:

- **۱. گرفتن تسک‌ها**
  - `GET /api/tasks/next` یا `POST /api/tasks/claim` با پارامترهایی مثل `limit` یا `machine_id`.
  - از دیتابیس تسک‌های `pending` را به‌صورت transaction انتخاب می‌کند و وضعیت را به `processing` تغییر می‌دهد.
  - لیست تسک‌ها را برمی‌گرداند.

- **۲. ثبت زمان برداشت تسک**
  - معمولاً در همان endpoint claim انجام می‌شود، ولی می‌توان جدا هم داشت:
  - `POST /api/tasks/:id/picked` که `picked_at` و `assigned_to` را ثبت/به‌روزرسانی کند.

- **۳. ثبت نتیجه و ذخیره SRT**
  - `POST /api/tasks/:id/complete`
    - body شامل مسیر SRT نهایی یا محتوای SRT (در صورت نیاز برای ذخیره مستقیم).
    - فایل SRT در `OUTPUT_DIR` (یا کنار فایل ورودی) ذخیره می‌شود.
    - در دیتابیس: `status='done'`, `finished_at=NOW()`.
- **ایمپورت bulk و ادمین‌پنل**
  - endpoint های اضافی برای bulk import:
    - `POST /api/tasks/bulk` برای ثبت تعداد زیادی تسک (مثلاً لیستی از مسیر فایل‌ها).
  - ادمین‌پنل ساده (در همین سرور):
    - پیاده‌سازی اولیه در قالب چند endpoint JSON (بدون UI پیچیده) تا بعداً UI/N8N روی آن سوار شود.

---

### 6) Dockerfile و docker-compose پروژه اول

- **Dockerfile** (خلاصه):
  - بیس ایمیج: `node:20-slim` یا ایمیج مناسب CUDA (با فرض استفاده از ران‌تایم GPU مثل `nvidia/cuda` + نصب نود).
  - نصب وابستگی‌های ویسپر (یا کتابخانه CLI/پایتون که از طریق نود صدا زده می‌شود – در حد اسکلت در این مرحله).
  - کپی سورس، نصب پکیج‌ها، `CMD` برای اجرای worker/server.
- **docker-compose.yml**:
  - تعریف سرویس `app`:
    - `build: .`
    - `deploy` یا `runtime: nvidia` (بسته به نسخه Docker) برای GPU.
    - mount کردن پوشه‌های هاست به کانتینر (`INPUT_DIR`, `OUTPUT_DIR`).
    - تنظیم env از فایل `.env`.
  - سرویس `mysql`:
    - تصویر `mysql:8` (یا مناسب).
    - `volumes: - mysql_data:/var/lib/mysql`.
    - `environment` برای user/password/dbname.
  - سرویس `adminer` (اختیاری) برای مدیریت دیتابیس.

---

### 7) پروژه دوم: Worker با کران‌جاب و گزارش به ربات

- **منطق کلی**:
  - از کتابخانه `node-cron` برای زمان‌بندی استفاده می‌کنیم.
  - زمان‌بندی و فعال/غیرفعال بودن job از env و همچنین از طریق API کنترل می‌شود.
- **متغیرهای env**:
  - `CRON_ENABLED=true|false`
  - `CRON_SCHEDULE=0 * * * *` (هر ساعت)
  - `REPORT_WEBHOOK_URL` یا `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` در صورت نیاز.
- **کران‌جاب داخل کانتینر**:
  - `src/cron.ts`:
    - در زمان بالا آمدن app، اگر `CRON_ENABLED=true` باشد، job ثبت می‌شود.
    - در هر اجرا:
      - فایل‌های جدید را از سرور/پوشه مشخص برمی‌دارد.
      - ویسپر را اجرا می‌کند (مشابه منطق پروژه اول ولی با سیاست زمانی متفاوت).
      - گزارشی از تعداد فایل‌های پردازش‌شده، موفق/ناموفق، مدت زمان و غیره تولید می‌کند.
      - گزارش را به ربات (از طریق HTTP request به webhook یا API تلگرام) ارسال می‌کند.

- **کنترل فعال/غیرفعال بودن کران**:
  - API در `server.ts`:
    - `POST /api/cron/enable` و `POST /api/cron/disable` که مقدار `CRON_ENABLED` را در یک کانفیگ داخلی (مثلاً DB یا فایل ساده) به‌روزرسانی می‌کنند.
    - بر اساس این فلگ، job جدید ثبت یا متوقف می‌شود.
  - همچنین می‌توان اسکریپت شل داخل کانتینر داشت:
    - مثلاً `toggle-cron.sh` که یک دستور ساده برای فعال/غیرفعال کردن است (قابل صدا زدن از n8n).

- **Dockerfile و docker-compose**:
  - مشابه پروژه اول، ولی بدون MySQL داخلی (در صورت نیاز می‌تواند به DB مشترک وصل شود).
  - GPU در صورت لزوم (اگر این پروژه هم ویسپر GPU می‌خواهد).

---

### 8) الگوی استفاده از ENV و تزریق از بیرون

- در هر دو پروژه:
  - همه تنظیمات مهم (ساعت شروع/پایان، زمان‌بندی کران، فعال بودن کران، مسیر پوشه‌ها، پارامترهای DB) به صورت متغیرهای محیطی تعریف می‌شوند.
  - `docker-compose.yml` از فایل `.env` استفاده می‌کند، ولی کاربر می‌تواند هنگام اجرای `docker compose up` متغیرهای محیطی را override کند (از طریق خط فرمان یا محیط سیستم).
  - در نود، ماژول `config` همه env ها را خوانده و validation ساده انجام می‌دهد (مقادیر پیش‌فرض در صورت خالی بودن).

---

### 9) دیاگرام ساده جریان داده بین اجزا

```mermaid
flowchart LR
  subgraph whisperTaskRunner [whisper-task-runner]
    A_server[Express API]
    A_worker[Worker/Whisper GPU]
    A_fs[Input/Output Folders]
    A_db[(MySQL tasks)]
  end

  subgraph whisperCronWorker [whisper-cron-worker]
    B_app[Express + node-cron]
    B_fs[Media Folders]
    B_robot[Notifier (Telegram/Webhook)]
  end

  A_server <--> A_db
  A_worker --> A_fs
  A_worker <--> A_db
  B_app --> B_fs
  B_app --> B_robot
  B_app <--> A_db
```

---

### 10) مراحل اجرایی که بعد از تأیید شما انجام می‌دهم

- **در پوشه ریشه پروژه فعلی شما**:

  1. ساخت دو پوشه جدید `whisper-task-runner` و `whisper-cron-worker`.
  2. مقداردهی اولیه هر پروژه با `package.json`، ساختار `src/`، و اسکریپت‌های `npm` لازم.
  3. نوشتن `Dockerfile` و `docker-compose.yml` برای هر پروژه، با تنظیم GPU، volumes، و env.
  4. پیاده‌سازی اسکلت کد نود: وب‌سرویس‌ها، منطق صف فایل‌ها، اتصال MySQL، کران‌جاب.
  5. اضافه‌کردن نمونه `.env.example` با همه متغیرهای مهم.
  6. (اختیاری) اضافه‌کردن اسکریپت‌های کمکی شل داخل کانتینر برای کنترل کران و اجرای job به‌صورت دستی (مناسب n8n).

پس از تأیید این طرح، شروع می‌کنم به ساخت این دو فولدر و پیاده‌سازی Dockerfile، docker-compose و کدهای نود مطابق جزئیات بالا.