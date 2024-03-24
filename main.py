import mimetypes
import socket
import logging
from urllib.parse import urlparse, unquote_plus
from http.server import HTTPServer, BaseHTTPRequestHandler
from pymongo.mongo_client import MongoClient
from datetime import datetime
from threading import Thread
from pathlib import Path

# Налаштування для підключення до MongoDB і серверних параметрів
URI = "mongodb://mongoserver:27017/"
BASE_DIR = Path(__file__).parent
BUFFER_SIZE = 1024
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 3000
SOCKET_HOST = "127.0.0.1"
SOCKET_PORT = 5000

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Обробка GET-запитів
        route = urlparse(self.path).path
        # Перевірка маршруту і відправлення відповідного HTML файлу
        match route:
            case "/":
                self.send_html_file("index.html")
            case "/message":
                self.send_html_file("message.html")
            case _:
                # Спроба відправити статичний файл з кореневої директорії
                file = BASE_DIR.joinpath(route[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    # Відправлення сторінки помилки, якщо файл не знайдено
                    self.send_html_file("error.html", status=404)

    def do_POST(self):
        # Обробка POST-запитів
        size = self.headers.get("Content-length")
        data = self.rfile.read(int(size)).decode()
        # Відправлення даних на сокет-сервер
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data.encode(), (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()
        # Перенаправлення користувача на головну сторінку
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html_file(self, filename, status=200):
        # Відправлення HTML файлів
        self.send_response(status)
        self.send_header("content-type", "text/html")
        self.end_headers()
        try:
            with open(filename, "rb") as fd:
                self.wfile.write(fd.read())
        except FileNotFoundError:
            logging.error(f"Файл {filename} не знайдено")
        except Exception as e:
            logging.error(f"Несподівана помилка: {e}")

    def send_static(self, filename):
        # Відправлення статичних файлів
        self.send_response(200)
        mime_type = mimetypes.guess_type(filename)[0] or "text/plain"
        self.send_header("Content-type", mime_type)
        self.end_headers()
        try:
            with open(filename, "rb") as fd:
                self.wfile.write(fd.read())
        except FileNotFoundError:
            logging.error(f"Файл {filename} не знайдено")
        except Exception as e:
            logging.error(f"Несподівана помилка: {e}")

# Функція для збереження даних отриманих через сокет
def save_data(data):
    client = MongoClient(URI)
    db = client.homework6
    data = unquote_plus(data.decode())
    try:
        parsed_data = {
            key: value for key, value in [el.split("=") for el in data.split("&")]
        }
        parsed_data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.messages.insert_one(parsed_data)
    except ValueError as e:
        logging.error(f"Помилка парсингу: {e}")
    except Exception as e:
        logging.error(f"Несподівана помилка при збереженні даних: {e}")
    finally:
        logging.info("З'єднання з базою даних закрито")
        client.close()

# Запуск HTTP сервера
def run_http_server():
    server_address = (HTTP_HOST, HTTP_PORT)
    httpd = HTTPServer(server_address, RequestHandler)
    logging.info(f"HTTP сервер запущено на порту {HTTP_PORT}")
    try:
        httpd.serve_forever()
    except Exception as e:
        logging.error(f"Несподівана помилка: {e}")
    finally:
        logging.info("HTTP сервер зупинено")
        httpd.server_close()

# Запуск сокет сервера
def run_socket_server():
    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    soc.bind((SOCKET_HOST, SOCKET_PORT))
    logging.info(f"Сокет сервер запущено на порту: {SOCKET_PORT}")
    try:
        while True:
            data, addr = soc.recvfrom(BUFFER_SIZE)
            logging.info(f"Отримано повідомлення від {addr}: {data.decode()}")
            save_data(data)
            logging.info("Повідомлення збережено в базу даних")
    except Exception as e:
        logging.error(f"Несподівана помилка: {e}")
    finally:
        logging.info("Сокет сервер зупинено")
        soc.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(threadName)s - %(message)s")

    # Запускаємо HTTP та сокет сервери у паралельних потоках
    http_thread = Thread(target=run_http_server, name="HTTPServer")
    socket_thread = Thread(target=run_socket_server, name="SocketServer")

    http_thread.start()
    socket_thread.start()
