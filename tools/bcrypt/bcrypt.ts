const bcrypt = require('bcrypt');
const saltRounds = 10;
const myPlaintextPassword = 'YourNewPassword123!'; // رمز عبور جدید
bcrypt.hash(myPlaintextPassword, saltRounds, function(err, hash) {
    console.log(hash); // این مقدار را در دیتابیس جایگزین کنید
});
