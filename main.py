import socket
import json
import os
from datetime import datetime
from multiprocessing import Process
from pymongo import MongoClient

MONGO_HOST = "mongo"
MONGO_PORT = 27017
DB_NAME = "messages_db"
COLLECTION_NAME = "messages"

def run_socket_server():
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    host = "0.0.0.0"
    port = 5000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[Сокет-сервер] Слухає порт {port}...")
        while True:
            conn, addr = server_socket.accept()
            with conn:
                data = conn.recv(4096)
                if not data:
                    continue
                try:
                    message_data = json.loads(data.decode("utf-8"))
                except Exception as e:
                    print("[Сокет-сервер] Помилка декодування JSON:", e)
                    continue
                message_data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                collection.insert_one(message_data)
                print(f"[Сокет-сервер] Збережено в БД: {message_data}")

def send_response(client_socket, status_code, body, content_type="text/html"):
    headers = f"HTTP/1.1 {status_code}\r\n"
    headers += f"Content-Type: {content_type}\r\n"
    headers += f"Content-Length: {len(body)}\r\n"
    headers += "Connection: close\r\n"
    headers += "\r\n"
    if isinstance(body, str):
        body = body.encode("utf-8")
    response = headers.encode("utf-8") + body
    client_socket.sendall(response)

def serve_static_file(path):
    if path.startswith("/"):
        path = path[1:]
    if not os.path.exists(path):
        return None, None
    _, ext = os.path.splitext(path)
    content_type = "text/html"
    if ext == ".css":
        content_type = "text/css"
    elif ext == ".png":
        content_type = "image/png"
    elif ext == ".js":
        content_type = "application/javascript"
    elif ext == ".ico":
        content_type = "image/x-icon"
    with open(path, "rb") as f:
        content = f.read()
    return content, content_type

def run_http_server():
    host = "0.0.0.0"
    port = 3000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"[HTTP-сервер] Слухає порт {port}...")
        while True:
            client_socket, addr = server_socket.accept()
            with client_socket:
                request_data = b""
                try:
                    client_socket.settimeout(1)
                    chunk = client_socket.recv(4096)
                    request_data += chunk
                except socket.timeout:
                    pass
                if not request_data:
                    continue
                request_text = request_data.decode("utf-8", errors="ignore")
                headers_part, _, body_part = request_text.partition("\r\n\r\n")
                first_line = headers_part.split("\r\n")[0]
                parts = first_line.split(" ")
                if len(parts) < 2:
                    continue
                method = parts[0]
                path = parts[1]
                if path == "/":
                    path = "/index.html"
                if method == "POST" and path == "/message":
                    form_data = {}
                    for kv in body_part.split("&"):
                        if "=" in kv:
                            key, value = kv.split("=", 1)
                            key = key.strip()
                            value = decode_url_component(value.strip())
                            if key in ("username", "message"):
                                form_data[key] = value
                    forward_to_socket_server(form_data)
                    body = f"<html><body><h1>Повідомлення отримано!</h1></body></html>"
                    send_response(client_socket, "302 Found", body)
                    continue
                content, content_type = serve_static_file(path)
                if content is not None:
                    send_response(client_socket, "200 OK", content, content_type)
                else:
                    content_404, ctype_404 = serve_static_file("error.html")
                    if content_404 is None:
                        content_404 = f"<h1>404 Not Found</h1>"
                        ctype_404 = "text/html"
                    send_response(client_socket, "404 Not Found", content_404, ctype_404)

def forward_to_socket_server(data_dict):
    host = "127.0.0.1"
    port = 5000
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            json_data = json.dumps(data_dict)
            s.sendall(json_data.encode("utf-8"))
    except Exception as e:
        print("[HTTP-сервер] Помилка пересилки на сокет-сервер:", e)

def decode_url_component(value):
    from urllib.parse import unquote_plus
    return unquote_plus(value)

if __name__ == "__main__":
    p_http = Process(target=run_http_server)
    p_socket = Process(target=run_socket_server)
    p_http.start()
    p_socket.start()
    p_http.join()
    p_socket.join()
