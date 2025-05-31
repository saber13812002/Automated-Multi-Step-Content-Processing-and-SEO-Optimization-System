<?php
$password = "!QAZ2wsx3edc";  // رشته‌ای که می‌خواهید رمزنگاری کنید
$hashedPassword = password_hash($password, PASSWORD_DEFAULT);  // رمزنگاری پسورد
echo $hashedPassword;  // نمایش هش رمزعبور
?>
