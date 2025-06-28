import socket
import threading
import logging
from game_http_handler import HttpServer  # <-- Perubahan di sini

# Setup logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')

httpserver = HttpServer()


class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        threading.Thread.__init__(self)

    def run(self):
        rcv = ""
        # Set a timeout on the socket to prevent threads from hanging indefinitely
        self.connection.settimeout(5.0)
        while True:
            try:
                data = self.connection.recv(4096)  # Buffer size increased for POST bodies
                if data:
                    d = data.decode('utf-8')
                    rcv += d

                    # Cek jika header sudah lengkap diterima
                    if "\r\n\r\n" in rcv:
                        # Cek Content-Length untuk memastikan seluruh body diterima
                        headers_part, _, body_part = rcv.partition('\r\n\r\n')
                        content_length_header = [h for h in headers_part.split('\r\n') if h.lower().startswith('content-length:')]

                        if content_length_header:
                            content_length = int(content_length_header[0].split(':')[-1].strip())
                            # Jika body yang diterima belum lengkap, tunggu lagi
                            if len(body_part.encode('utf-8')) < content_length:
                                continue

                        # Jika sudah lengkap, proses
                        logging.warning(f"Data dari client {self.address}: {rcv.strip()}")
                        hasil = httpserver.proses(rcv)
                        separator = b'\r\n\r\n'  # <-- FIX: Hindari backslash di dalam f-string expression
                        header = hasil.split(separator)[0]
                        logging.warning(f"Balas ke client {self.address}: {header}...")
                        self.connection.sendall(hasil)
                        break  # Tutup koneksi setelah mengirim response
                else:
                    break  # Koneksi ditutup oleh client
            except socket.timeout:
                logging.warning(f"Connection from {self.address} timed out.")
                break
            except Exception as e:
                logging.error(f"Error processing client {self.address}: {e}")
                break
        self.connection.close()
        logging.warning(f"Connection from {self.address} closed.")


class Server(threading.Thread):
    def __init__(self, port=8889):
        self.the_clients = []
        self.port = port
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        threading.Thread.__init__(self)

    def run(self):
        self.my_socket.bind(('0.0.0.0', self.port))
        self.my_socket.listen(5)  # Increased backlog
        logging.warning(f"Server berjalan di port {self.port}...")
        while True:
            try:
                connection, client_address = self.my_socket.accept()
                logging.warning(f"Koneksi dari {client_address}")
                clt = ProcessTheClient(connection, client_address)
                clt.start()
                self.the_clients.append(clt)
            except KeyboardInterrupt:
                logging.warning("Server dihentikan.")
                break
            except Exception as e:
                logging.error(f"Server error: {e}")
                break


def main():
    svr = Server(port=8889)
    svr.start()


if __name__ == "__main__":
    main()
