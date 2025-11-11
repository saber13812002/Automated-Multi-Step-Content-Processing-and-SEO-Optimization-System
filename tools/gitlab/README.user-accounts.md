# راهنمای مدیریت کاربران GitLab داخلی

این راهنما خلاصه‌ای از مراحل ایجاد و مدیریت کاربران داخلی GitLab (کاربران `root` و `saber`) را ارائه می‌دهد و توضیح می‌دهد چطور می‌توان رمز عبور آن‌ها را بازنشانی کرد.

---

## مشخصات کاربران

| کاربر | نقش | وضعیت | رمز فعلی |
|-------|------|--------|-----------|
| `root` | مدیر کل | فعال | `NewR00tP@ss!` |
| `saber` | کاربر معمولی | فعال | `Sup3r@ssw0rd42` |

> در صورت تغییر رمزها، مقدار جدید را در این جدول به‌روزرسانی کنید.

---

## مراحل فعال‌سازی کاربر `saber`

```
docker exec -it gitlab gitlab-rails console
user = User.find_by(username: 'saber')
user.activate
user.save
exit
```

- اگر کاربر پیدا نشد، از `User.create!` یا رابط وب برای ساخت آن استفاده کنید.
- بعد از فعال‌سازی، اطلاعات ورود را به کاربر اطلاع دهید.

---

## مشاهده کاربران فعال

```
docker exec -it gitlab bash
gitlab-rails runner "puts User.where(state: 'active').pluck(:id, :username, :admin).map{|r| r.join(' | ')}"
```

خروجی نمونه:

```
1 | root | true
2 | saber | false
```

---

## بازنشانی یا تغییر رمز عبور

### نکته درباره کاراکتر `!`

پیش از اجرای دستورات حاوی `!`، برای جلوگیری از history expansion در Bash، دستور زیر را اجرا کنید:

```
set +H
```

### تغییر رمز از داخل کانتینر

1. ورود به کانتینر GitLab:

   ```
   docker exec -it gitlab bash
   ```

2. اجرای دستور runner با رمز جدید:

   ```
   gitlab-rails runner "u = User.find_by(username:'USERNAME'); u.password = 'NEW_PASSWORD'; u.password_confirmation = 'NEW_PASSWORD'; u.save!; puts 'password updated'"
   ```

   - برای `root`: `NEW_PASSWORD` = `NewR00tP@ss!`
   - برای `saber`: `NEW_PASSWORD` = `MyN3wP@ssw0rd!`

3. در صورت استفاده از کاراکترهای خاص، می‌توانید از کوتیشن تک ‌ (`'`) استفاده کنید و در صورت نیاز کاراکتر را escape کنید (مثلاً `\$`).

---

## راهنمای خروج

- پس از اتمام کار، با `exit` از کنسول Ruby یا Bash خارج شوید تا کانتینر در حال اجرا باقی بماند.

---

## رفع خطاهای متداول

- **خطای `unknown regexp options - gt`**: این خطا معمولاً به‌دلیل وارد کردن دستورات Bash داخل کنسول Ruby (`irb`) رخ می‌دهد. دستورات سیستم را خارج از `gitlab-rails console` اجرا کنید.
- **خطای `gitlab-rails: command not found`**: ابتدا وارد کانتینر GitLab شوید (`docker exec -it gitlab bash`) و سپس دستور را اجرا کنید.

---

## یادآوری

- همواره بعد از تغییر رمز عبور، از ورود موفق با رمز جدید در رابط وب اطمینان حاصل کنید.
- برای امنیت بیشتر، رمزهای پیش‌فرض را پس از اولین ورود تغییر دهید و آن‌ها را در یک محل امن ذخیره کنید.

