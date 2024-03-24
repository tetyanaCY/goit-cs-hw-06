# client.py
import asyncio
import json
from datetime import datetime

async def tcp_client(message, username="User"):
    host = 'localhost'  # Адреса сервера
    port = 5000  # Порт сервера

    reader, writer = await asyncio.open_connection(host, port)

    # Підготовка даних до відправки
    data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "username": username,
        "message": message
    }
    data_str = json.dumps(data)
    writer.write(data_str.encode())

    print(f"Відправлено: {data_str}")

    # Очікування відповіді від сервера
    data_received = await reader.read(100)
    print(f"Отримано: {data_received.decode()}")

    print("Закриття з'єднання")
    writer.close()
    await writer.wait_closed()

# Для тестування, відправимо приклад повідомлення
async def main():
    await tcp_client("Привіт, це тестове повідомлення", "hey, we are simply the best. so far.")

if __name__ == '__main__':
    asyncio.run(main())
