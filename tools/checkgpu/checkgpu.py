import subprocess

def check_gpu_idle():
    # اجرای دستور nvidia-smi و گرفتن درصد استفاده GPU هر کارت
    cmd = ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits']
    result = subprocess.run(cmd, capture_output=True, text=True)

    # چک کردن خطا
    if result.returncode != 0:
        print("Error executing nvidia-smi")
        return 1  # فرض می‌کنیم اشکال یعنی کارت مشغول یا غیرقابل اطمینان

    # استخراج مقادیر و تبدیل به عدد
    gpu_utils = [int(line.strip()) for line in result.stdout.strip().split('\n')]

    # اگر همه صفر باشند یعنی کارت‌ها آزادند
    if all(util == 0 for util in gpu_utils):
        return 0
    else:
        return 1

if __name__ == '__main__':
    status = check_gpu_idle()
    print(status)
