import subprocess
import time
import signal
import os


services = [
    ["python", "-m", "user_service.app"],
    ["python", "-m", "crypto_service.app"],
    ["python", "-m", "admin_service.app"],
    ["python", "-m", "bot_service.app"]  # Запускается последним
]

processes = []


def start_services():
    for cmd in services:
        try:
            p = subprocess.Popen(cmd)
            processes.append(p)
            print(f"Запущен: {' '.join(cmd)} (PID: {p.pid})")

            # Добавляем задержку перед следующим сервисом
            if cmd != services[-1]:  # Не ждем после последнего сервиса
                time.sleep(3)  # 3 секунды на инициализацию сервиса

        except Exception as e:
            print(f"Ошибка запуска {' '.join(cmd)}: {e}")
            stop_services()  # Останавливаем уже запущенные сервисы
            raise


def stop_services():
    # Останавливаем в обратном порядке
    for p in reversed(processes):
        try:
            os.kill(p.pid, signal.SIGTERM)
            print(f"Остановлен процесс (PID: {p.pid})")
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка остановки PID {p.pid}: {e}")


if __name__ == "__main__":
    try:
        print("=== Запуск сервисов ===")
        start_services()
        print("\nВсе сервисы запущены.")
        input("Нажмите Enter для остановки...\n")
    finally:
        print("\n=== Остановка сервисов ===")
        stop_services()