import socket
import threading
import logging
from game_http_handler import HttpServer

# Setup logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(levelname)s - %(message)s')

httpserver = HttpServer()

# --- Dapatkan IP lokal yang aktif (untuk koneksi keluar jaringan) ---
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


class ProcessTheClient(threading.Thread):
    def __init__(self, connection, address, server_ref):
        super().__init__()
        self.connection = connection
        self.address = address
        self.server_ref = server_ref

    def run(self):
        rcv = ""
        self.connection.settimeout(5.0)
        while True:
            try:
                data = self.connection.recv(4096)
                if data:
                    d = data.decode('utf-8')
                    rcv += d

                    if "\r\n\r\n" in rcv:
                        headers_part, _, body_part = rcv.partition('\r\n\r\n')
                        content_length_header = [h for h in headers_part.split('\r\n') if h.lower().startswith('content-length:')]
                        if content_length_header:
                            content_length = int(content_length_header[0].split(':')[-1].strip())
                            if len(body_part.encode('utf-8')) < content_length:
                                continue

                        logging.warning(f"Data dari client {self.address}: {rcv.strip()}")
                        hasil = httpserver.proses(rcv)
                        separator = b'\r\n\r\n'
                        header = hasil.split(separator)[0]
                        logging.warning(f"Balas ke client {self.address}: {header}...")
                        self.connection.sendall(hasil)
                        break
                else:
                    break
            except socket.timeout:
                logging.warning(f"Connection from {self.address} timed out.")
                break
            except Exception as e:
                logging.error(f"Error processing client {self.address}: {e}")
                break

        self.connection.close()
        logging.warning(f"Connection from {self.address} closed.")
        self.server_ref.remove_client(self)


class Server(threading.Thread):
    def __init__(self, port=8889):
        super().__init__()
        self.the_clients = []
        self.port = port
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def remove_client(self, client_thread):
        if client_thread in self.the_clients:
            self.the_clients.remove(client_thread)
            logging.warning(f"Client {client_thread.address} dihapus dari daftar aktif.")

    def print_active_clients(self):
        active_ips = [str(client.address[0]) for client in self.the_clients if client.is_alive()]
        logging.warning(f"Daftar client aktif: {', '.join(active_ips)}")

    def run(self):
        self.my_socket.bind(('0.0.0.0', self.port))
        self.my_socket.listen(5)
        logging.warning(f"Server berjalan di port {self.port}")

        while True:
            try:
                connection, client_address = self.my_socket.accept()
                logging.warning(f"Koneksi baru dari {client_address}")
                clt = ProcessTheClient(connection, client_address, self)
                clt.start()
                self.the_clients.append(clt)
                self.print_active_clients()
            except KeyboardInterrupt:
                logging.warning("Server dihentikan oleh pengguna.")
                break
            except Exception as e:
                logging.error(f"Server error: {e}")
                break


def main():
    svr = Server(port=8889)
    svr.start()


if __name__ == "__main__":
    main()
