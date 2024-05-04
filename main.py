import http.server
import socketserver
import socket
import os
import json
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import parse_qs, urlparse

PORT = 3000
SOCKET_PORT = 5000
DB_HOST = 'mongodb://localhost:27017/'
DB_NAME = 'messages'
COLLECTION_NAME = 'records'

# Socket Server
def socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', SOCKET_PORT))
        s.listen()
        while True:
            conn, addr = s.accept()
            with conn:
                print(f'Connected by {addr}')
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    # Process and save data to MongoDB
                    data_dict = json.loads(data.decode('utf-8'))
                    save_to_mongo(data_dict)

def save_to_mongo(data_dict):
    client = MongoClient(DB_HOST)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    collection.insert_one(data_dict)

# HTTP Server
class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'
        elif self.path == '/message':
            self.path = '/message.html'
        try:
            file_to_open = open(self.path[1:]).read()
            self.send_response(200)
        except FileNotFoundError:
            self.path = '/error.html'
            file_to_open = open(self.path[1:]).read()
            self.send_response(404)
        self.end_headers()
        self.wfile.write(bytes(file_to_open, 'utf-8'))

    def do_POST(self):
        if self.path == '/submit':
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length).decode('utf-8')
            parsed_body = parse_qs(body)
            message_data = {
                'date': str(datetime.now()),
                'username': parsed_body['username'][0],
                'message': parsed_body['message'][0]
            }
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', SOCKET_PORT))
                s.sendall(json.dumps(message_data).encode('utf-8'))
            self.send_response(302)
            self.send_header('Location', '/message')
            self.end_headers()

if __name__ == '__main__':
    # Run HTTP server in a separate process
    from multiprocessing import Process
    p = Process(target=socket_server)
    p.start()

    # HTTP server
    with socketserver.TCPServer(('', PORT), SimpleHTTPRequestHandler) as httpd:
        print(f"HTTP Server Serving at port {PORT}")
        httpd.serve_forever()
