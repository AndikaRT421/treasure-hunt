import json
from datetime import datetime

# Konfigurasi Game
GRID_SIZE = 7
TREASURE_SIZE = 2
STARTING_HP = 3

class GameState:
    def __init__(self, lock):
        self.lock = lock
        self.players = {}
        self.game_phase = "WAITING_FOR_PLAYERS"
        self.treasure_pos = {'A': None, 'B': None}
        self.hp = {'A': STARTING_HP, 'B': STARTING_HP}
        self.dig_marks = {
            'A': [[None] * GRID_SIZE for _ in range(GRID_SIZE)],
            'B': [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
        }
        self.turn = 'A'
        self.winner = None
        self.action_message = "Menunggu kedua pemain bergabung..."

    def reset_game(self):
        self.lock.acquire()
        try:
            self.players = {}
            self.game_phase = "WAITING_FOR_PLAYERS"
            self.treasure_pos = {'A': None, 'B': None}
            self.hp = {'A': STARTING_HP, 'B': STARTING_HP}
            self.dig_marks = {
                'A': [[None] * GRID_SIZE for _ in range(GRID_SIZE)],
                'B': [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
            }
            self.turn = 'A'
            self.winner = None
            self.action_message = "Menunggu kedua pemain bergabung..."
        finally:
            self.lock.release()

    def add_player(self):
        self.lock.acquire()
        try:
            if 'A' not in self.players:
                player_id = 'A'
                self.players['A'] = True
                self.action_message = "Pemain A bergabung. Menunggu Pemain B..."
                return player_id
            elif 'B' not in self.players:
                player_id = 'B'
                self.players['B'] = True
                self.game_phase = "PLACEMENT"
                self.action_message = "Pemain B bergabung. Tahap penempatan dimulai."
                return player_id
            return None
        finally:
            self.lock.release()

    def place_treasure(self, player_id, y, x):
        self.lock.acquire()
        try:
            if self.game_phase != "PLACEMENT" or self.treasure_pos.get(player_id) is not None:
                return False
            if 0 <= y <= GRID_SIZE - TREASURE_SIZE and 0 <= x <= GRID_SIZE - TREASURE_SIZE:
                self.treasure_pos[player_id] = (y, x)
                if self.treasure_pos['A'] is not None and self.treasure_pos['B'] is not None:
                    self.game_phase = "BATTLE"
                    self.action_message = "Giliran Pemain A untuk beraksi."
                return True
            return False
        finally:
            self.lock.release()

    def perform_action(self, player_id, action_type, y, x):
        self.lock.acquire()
        try:
            if self.game_phase != "BATTLE" or self.turn != player_id:
                return {"success": False, "message": "Bukan giliranmu atau game belum dimulai."}
            opponent_id = 'B' if player_id == 'A' else 'A'
            if action_type == 'move':
                if 0 <= y <= GRID_SIZE - TREASURE_SIZE and 0 <= x <= GRID_SIZE - TREASURE_SIZE:
                    self.treasure_pos[player_id] = (y, x)
                    self.turn = opponent_id
                    self.dig_marks[opponent_id] = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
                    self.action_message = f"Pemain {player_id} memindahkan hartanya. Giliran Pemain {opponent_id}."
                    return {"success": True}
                return {"success": False, "message": "Lokasi pemindahan tidak valid."}
            elif action_type == 'dig':
                opp_treasure = self.treasure_pos[opponent_id]
                ty, tx = opp_treasure
                if ty <= y < ty + TREASURE_SIZE and tx <= x < tx + TREASURE_SIZE:
                    self.dig_marks[player_id][y][x] = 'hit'
                    self.hp[opponent_id] -= 1
                    self.action_message = f"Pemain {player_id} berhasil mengenai harta! Giliran Pemain {opponent_id}."
                    if self.hp[opponent_id] <= 0:
                        self.game_phase = "ENDED"
                        self.winner = player_id
                        self.action_message = f"Game Selesai! Pemenangnya adalah Pemain {self.winner}!"
                else:
                    self.dig_marks[player_id][y][x] = 'miss'
                    self.action_message = f"Pemain {player_id} gagal menemukan harta. Giliran Pemain {opponent_id}."
                self.turn = opponent_id
                if self.game_phase == "BATTLE":
                    self.dig_marks[opponent_id] = [[None] * GRID_SIZE for _ in range(GRID_SIZE)]
                return {"success": True}
            return {"success": False, "message": "Aksi tidak dikenal."}
        finally:
            self.lock.release()

    def get_state_for_player(self, player_id):
        self.lock.acquire()
        try:
            if player_id not in ('A', 'B'):
                return {"error": "Player ID tidak valid"}
            opponent_id = 'B' if player_id == 'A' else 'A'
            state = {
                "player_id": player_id,
                "game_phase": self.game_phase,
                "my_hp": self.hp.get(player_id),
                "opponent_hp": self.hp.get(opponent_id),
                "my_treasure_pos": self.treasure_pos.get(player_id),
                "my_dig_marks": self.dig_marks.get(player_id),
                "turn": self.turn,
                "winner": self.winner,
                "action_message": self.action_message,
                "grid_size": GRID_SIZE,
                "treasure_size": TREASURE_SIZE
            }
            return state
        finally:
            self.lock.release()

    def get_game_phase(self):
        self.lock.acquire()
        try:
            return self.game_phase
        finally:
            self.lock.release()

class HttpServer:
    def __init__(self, shared_game_state):
        self.sessions = {}
        self.game_state = shared_game_state

    def response(self, code=404, message='Not Found', body=b'', headers={}):
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type'
        if isinstance(body, dict) or isinstance(body, list):
            body = json.dumps(body).encode('utf-8')
        elif isinstance(body, str):
            body = body.encode('utf-8')
        resp = [
            f"HTTP/1.1 {code} {message}\r\n",
            f"Date: {datetime.now().strftime('%c')}\r\n",
            "Server: GameServer/1.0\r\n",
            f"Content-Length: {len(body)}\r\n"
        ]
        for k, v in headers.items():
            resp.append(f"{k}: {v}\r\n")
        resp.append("\r\n")
        response_headers = "".join(resp).encode('utf-8')
        return response_headers + body

    def get_request_body(self, request_lines):
        try:
            separator_index = request_lines.index('')
            body_lines = request_lines[separator_index+1:]
            return "".join(body_lines)
        except ValueError:
            return ""

    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]
        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            object_address = j[1].strip()
            if method == 'OPTIONS':
                return self.response(204, 'No Content', headers={'Allow': 'OPTIONS, GET, POST'})
            if method == 'GET':
                return self.http_get(object_address)
            elif method == 'POST':
                body = self.get_request_body(requests)
                return self.http_post(object_address, body)
            else:
                return self.response(400, 'Bad Request', {'error': 'Unsupported method'})
        except IndexError:
            return self.response(400, 'Bad Request', {'error': 'Malformed request'})

    def http_get(self, object_address):
        if object_address.startswith('/state?player_id='):
            player_id = object_address.split('=')[-1]
            state = self.game_state.get_state_for_player(player_id)
            return self.response(200, 'OK', state)
        return self.response(404, 'Not Found', {'error': f"Endpoint GET {object_address} tidak ditemukan"})

    def http_post(self, object_address, body):
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            return self.response(400, 'Bad Request', {'error': 'Invalid JSON body'})

        if object_address == '/join':
            if self.game_state.get_game_phase() == "ENDED":
                self.game_state.reset_game()
            player_id = self.game_state.add_player()
            if player_id:
                return self.response(200, 'OK', {'player_id': player_id})
            else:
                return self.response(403, 'Forbidden', {'error': 'Game sudah penuh'})

        player_id = payload.get('player_id')
        if not player_id:
            return self.response(400, 'Bad Request', {'error': 'player_id dibutuhkan'})

        if object_address == '/place':
            coords = payload.get('coords')
            if coords and isinstance(coords, list) and len(coords) == 2:
                success = self.game_state.place_treasure(player_id, coords[0], coords[1])
                if success:
                    return self.response(200, 'OK', {'success': True})
                return self.response(400, 'Bad Request', {'error': 'Penempatan tidak valid'})
            return self.response(400, 'Bad Request', {'error': 'Koordinat tidak valid'})

        if object_address == '/action':
            action_type = payload.get('type')
            coords = payload.get('coords')
            if action_type and coords and isinstance(coords, list) and len(coords) == 2:
                result = self.game_state.perform_action(player_id, action_type, coords[0], coords[1])
                if result.get('success'):
                    return self.response(200, 'OK', result)
                return self.response(400, 'Bad Request', result)
            return self.response(400, 'Bad Request', {'error': 'Payload aksi tidak lengkap'})
            
        if object_address == '/reset':
            self.game_state.reset_game()
            return self.response(200, 'OK', {'message': 'Game state has been reset.'})

        return self.response(404, 'Not Found', {'error': f"Endpoint POST {object_address} tidak ditemukan"})