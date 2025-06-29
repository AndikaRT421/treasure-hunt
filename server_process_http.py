import socket
import logging
from multiprocessing import Process, Lock
from multiprocessing.managers import BaseManager
from game_http_handler_process import HttpServer, GameState

class GameStateManagerServer(BaseManager):
    pass

GameStateManagerServer.register('GameState', GameState)
GameStateManagerServer.register('Lock', Lock)

class ProcessTheClient(Process):
    def __init__(self, connection, address, httpserver):
        self.connection = connection
        self.address = address
        self.httpserver = httpserver
        super().__init__()

    def run(self):
        rcv = ""
        # Set timeout pada socket untuk mencegah proses macet
        self.connection.settimeout(5.0)
        while True:
            try:
                data = self.connection.recv(4096)
                if data:
                    d = data.decode('utf-8')
                    rcv += d

                    # Cek jika header sudah lengkap diterima
                    if "\r\n\r\n" in rcv:
                        headers_part, _, body_part = rcv.partition('\r\n\r\n')
                        content_length_header = [h for h in headers_part.split('\r\n') if h.lower().startswith('content-length:')]

                        if content_length_header:
                            content_length = int(content_length_header[0].split(':')[-1].strip())
                            if len(body_part.encode('utf-8')) < content_length:
                                continue # Body belum lengkap, tunggu lagi

                        # LOGGING 
                        logging.warning(f"Data dari client {self.address}: {rcv.strip()}")
                        hasil = self.httpserver.proses(rcv)
                        
                        header, _, _ = hasil.partition(b'\r\n\r\n')
                        logging.warning(f"Balas ke client {self.address}: {header.decode()}...")
                        
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
        
        logging.warning(f"Connection from {self.address} closed.")
        self.connection.close()


class Server:
    def __init__(self, httpserver):
        self.the_clients = []
        self.httpserver = httpserver
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.my_socket.bind(('0.0.0.0', 8889))
        self.my_socket.listen(10)
        logging.warning("Server listening on port 8889")
        while True:
            try:
                connection, client_address = self.my_socket.accept()
                # --- LOGGING DITAMBAHKAN ---
                logging.warning(f"Connection from {client_address}")

                clt = ProcessTheClient(connection, client_address, self.httpserver)
                clt.start()
                self.the_clients.append(clt)
            except KeyboardInterrupt:
                logging.warning("Server shutting down.")
                break
            except Exception as e:
                logging.error(f"Error in server loop: {e}")
                break
        self.my_socket.close()

def main():
    game_state_manager = GameStateManagerServer()
    game_state_manager.start()
    lock = game_state_manager.Lock()
    shared_game_state = game_state_manager.GameState(lock=lock)
    httpserver_instance = HttpServer(shared_game_state)
    svr = Server(httpserver_instance)
    
    try:
        svr.start()
    finally:
        logging.warning("Shutting down game state manager.")
        game_state_manager.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    main()