import pygame
import sys
import requests
import json
import time

# --- Konfigurasi Klien ---
SERVER_URL = "" # Isi URL Server Anda di sini
PLAYER_ID = None
GAME_STATE = None

# --- Pengaturan Jendela (Tidak Fullscreen) ---
WINDOW_W, WINDOW_H = 1280, 800

# Ukuran default, akan diperbarui dari server
CELL_SIZE = 45
MARGIN = 4
STARTING_HP = 3

# Colors
COLOR_BG = (30, 30, 30)
COLOR_GRID_LINE = (50, 50, 50)
COLOR_TREASURE = (0, 255, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_GOLD = (255, 215, 0)  # Warna Emas untuk teks pemain
COLOR_MY_GRID_BG = (0, 100, 200)
COLOR_DIG_GRID_BG = (200, 150, 100)
COLOR_BTN = (70, 70, 70)
COLOR_BTN_ACTIVE = (100, 100, 100)
COLOR_HP_FULL = (0, 200, 0)
COLOR_HP_EMPTY_FILL = (80, 80, 80)
COLOR_HP_BORDER = (0, 255, 0)
COLOR_HIT = (255, 0, 0)
COLOR_MISS = (150, 150, 150)
COLOR_PENDING = (255, 255, 0)

# --- Inisialisasi Pygame untuk Mode Jendela ---
pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Treasure Hunt Client")

font_sm = pygame.font.SysFont(None, 32)
font_md = pygame.font.SysFont(None, 42)
font_lg = pygame.font.SysFont(None, 56)
font_xl = pygame.font.SysFont(None, 72) # Font lebih besar untuk ID Pemain
clock = pygame.time.Clock()

# --- Fungsi Komunikasi Server (Tidak ada perubahan) ---
def join_game():
    try:
        res = requests.post(f"{SERVER_URL}/join")
        if res.status_code == 200:
            return res.json().get('player_id')
        return None
    except requests.exceptions.ConnectionError:
        return None

def get_game_state(player_id):
    try:
        res = requests.get(f"{SERVER_URL}/state?player_id={player_id}")
        return res.json() if res.status_code == 200 else None
    except requests.exceptions.ConnectionError:
        return None

def send_placement(player_id, y, x):
    payload = {"player_id": player_id, "coords": [y, x]}
    try:
        requests.post(f"{SERVER_URL}/place", json=payload)
    except requests.exceptions.ConnectionError:
        print("Koneksi ke server terputus.")

def send_action(player_id, action_type, y, x):
    payload = {"player_id": player_id, "type": action_type, "coords": [y, x]}
    try:
        requests.post(f"{SERVER_URL}/action", json=payload)
    except requests.exceptions.ConnectionError:
        print("Koneksi ke server terputus.")


# --- Fungsi Helper & Drawing ---
def draw_text(text, font, color, surface, x, y, center=False):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)
    return text_rect

def draw_hp(label, hp, max_hp, x, y):
    # Menggeser posisi teks "HP:" agar bar tidak menabrak
    text_rect = draw_text(f"{label}:", font_md, COLOR_TEXT, screen, x, y)
    box_size = 30
    spacing = 6
    # Posisi bar HP dimulai setelah teks label
    hp_start_x = text_rect.right + 15
    for i in range(max_hp):
        box_rect = pygame.Rect(hp_start_x + i * (box_size + spacing), y + 5, box_size, box_size)
        if i < hp:
            pygame.draw.rect(screen, COLOR_HP_FULL, box_rect)
        else:
            pygame.draw.rect(screen, COLOR_HP_EMPTY_FILL, box_rect)
            pygame.draw.rect(screen, COLOR_HP_BORDER, box_rect, 2)

def pixel_to_grid(mx, my, off_x, off_y, grid_size):
    if mx < off_x or my < off_y: return None
    gx = (mx - off_x) // (CELL_SIZE + MARGIN)
    gy = (my - off_y) // (CELL_SIZE + MARGIN)
    if 0 <= gx < grid_size and 0 <= gy < grid_size:
        return gy, gx
    return None

def draw_digging_grid(off_x, off_y, grid_size, label, dig_marks):
    draw_text(label, font_md, COLOR_TEXT, screen, off_x, off_y - 50, center=False)
    for r in range(grid_size):
        for c in range(grid_size):
            rect = pygame.Rect(off_x + c * (CELL_SIZE + MARGIN), off_y + r * (CELL_SIZE + MARGIN), CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, COLOR_DIG_GRID_BG, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
            
            mark = dig_marks[r][c]
            if mark == 'hit':
                pygame.draw.rect(screen, COLOR_HIT, rect.inflate(-8, -8))
            elif mark == 'miss':
                pygame.draw.rect(screen, COLOR_MISS, rect.inflate(-8, -8))

def draw_my_treasure_grid(off_x, off_y, grid_size, treasure_size, label, treasure_pos):
    draw_text(label, font_md, COLOR_TEXT, screen, off_x, off_y - 50, center=False)
    for r in range(grid_size):
        for c in range(grid_size):
            rect = pygame.Rect(off_x + c * (CELL_SIZE + MARGIN), off_y + r * (CELL_SIZE + MARGIN), CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, COLOR_MY_GRID_BG, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
    
    if treasure_pos:
        ty, tx = treasure_pos
        for dy in range(treasure_size):
            for dx in range(treasure_size):
                if (tx + dx < grid_size) and (ty + dy < grid_size):
                    rect = pygame.Rect(off_x + (tx+dx) * (CELL_SIZE + MARGIN), off_y + (ty+dy) * (CELL_SIZE + MARGIN), CELL_SIZE, CELL_SIZE)
                    pygame.draw.rect(screen, COLOR_TREASURE, rect.inflate(-8, -8))

# --- Loop Utama Game ---
def game_loop():
    global PLAYER_ID, GAME_STATE
    
    selected_action = None
    running = True
    
    while running:
        # 1. Get State
        new_state = get_game_state(PLAYER_ID)
        if not new_state:
            draw_text("Koneksi ke server terputus...", font_lg, COLOR_HIT, screen, WINDOW_W // 2, WINDOW_H // 2, center=True)
            pygame.display.flip()
            time.sleep(2)
            running = False
            continue

        GAME_STATE = new_state
        
        # 2. Kalkulasi Layout Dinamis (dengan perbaikan)
        grid_size = GAME_STATE['grid_size']
        treasure_size = GAME_STATE['treasure_size']
        grid_pixels = grid_size * (CELL_SIZE + MARGIN)
        
        # --- UI Spacing Constants ---
        HEADER_Y_FINISH = 140
        SPACING_BETWEEN_GRIDS = 120

        # Posisi Horizontal Grid
        total_content_width = (grid_pixels * 2) + SPACING_BETWEEN_GRIDS
        start_x = (WINDOW_W - total_content_width) // 2
        dig_grid_x = start_x
        my_grid_x = start_x + grid_pixels + SPACING_BETWEEN_GRIDS
        
        # Posisi Vertikal Grid
        grid_y = HEADER_Y_FINISH + ((WINDOW_H - HEADER_Y_FINISH - 120) - grid_pixels) // 2 # Centering vertikal
        
        # --- PERBAIKAN: Posisi Tombol dan Teks Bawah ---
        buttons_y = grid_y + grid_pixels + 35  # Tombol sedikit ke atas
        bottom_text_y = buttons_y + 75 # Teks lebih jauh di bawah tombol
        
        buttons_center_x = start_x + grid_pixels + (SPACING_BETWEEN_GRIDS // 2)
        btn_move = pygame.Rect(buttons_center_x - 140, buttons_y, 120, 50)
        btn_dig = pygame.Rect(buttons_center_x + 20, buttons_y, 120, 50)
        
        phase = GAME_STATE['game_phase']
        is_my_turn = GAME_STATE['turn'] == PLAYER_ID

        # 3. Handle Input (Tidak ada perubahan)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if phase == "PLACEMENT" and GAME_STATE.get('my_treasure_pos') is None:
                    cell = pixel_to_grid(mx, my, my_grid_x, grid_y, grid_size)
                    if cell:
                        y, x = cell
                        if x <= grid_size - treasure_size and y <= grid_size - treasure_size:
                            send_placement(PLAYER_ID, y, x)
                            selected_action = None 
                
                elif phase == "BATTLE" and is_my_turn:
                    if btn_move.collidepoint(mx,my): selected_action = 'move'
                    elif btn_dig.collidepoint(mx,my): selected_action = 'dig'
                    else:
                        grid_to_check = None
                        if selected_action == 'dig':
                           grid_to_check = pixel_to_grid(mx, my, dig_grid_x, grid_y, grid_size)
                        elif selected_action == 'move':
                           grid_to_check = pixel_to_grid(mx, my, my_grid_x, grid_y, grid_size)

                        if grid_to_check:
                            y, x = grid_to_check
                            if selected_action == 'move' and (x > grid_size - treasure_size or y > grid_size - treasure_size):
                                continue 
                            send_action(PLAYER_ID, selected_action, y, x)
                            selected_action = None

        # 4. Drawing (dengan posisi UI yang baru)
        screen.fill(COLOR_BG)
        
        # --- PERBAIKAN: Header Area ---
        # Tampilkan ID Pemain di tengah atas dengan warna Emas
        draw_text(PLAYER_ID, font_xl, COLOR_GOLD, screen, buttons_center_x, 35, center=True)
        
        # Tampilkan pesan aksi dari server
        draw_text(GAME_STATE.get('action_message', ''), font_lg, COLOR_TEXT, screen, WINDOW_W // 2, 80, center=True)
        
        # Posisi HP dinamis sesuai posisi grid
        draw_hp("Opponent", GAME_STATE['opponent_hp'], STARTING_HP, dig_grid_x, 25)
        draw_hp("My HP", GAME_STATE['my_hp'], STARTING_HP, my_grid_x, 25)
        
        # Grid Area
        draw_digging_grid(dig_grid_x, grid_y, grid_size, "Opponent's Grid", GAME_STATE['my_dig_marks'])
        draw_my_treasure_grid(my_grid_x, grid_y, grid_size, treasure_size, "Your Treasure", GAME_STATE['my_treasure_pos'])

        # Bottom Area
        if phase == "PLACEMENT":
            if GAME_STATE.get('my_treasure_pos') is None:
                draw_text("Klik di grid 'Your Treasure' untuk menempatkan harta.", font_md, COLOR_PENDING, screen, WINDOW_W // 2, bottom_text_y, center=True)
            else:
                draw_text("Menunggu pemain lain...", font_md, COLOR_TEXT, screen, WINDOW_W // 2, bottom_text_y, center=True)
        
        elif phase == "BATTLE":
            if is_my_turn:
                # --- PERBAIKAN: Menggambar tombol dan teksnya ---
                pygame.draw.rect(screen, COLOR_BTN_ACTIVE if selected_action == 'move' else COLOR_BTN, btn_move, border_radius=8)
                draw_text("Move", font_md, COLOR_TEXT, screen, btn_move.centerx, btn_move.centery, center=True)
                
                pygame.draw.rect(screen, COLOR_BTN_ACTIVE if selected_action == 'dig' else COLOR_BTN, btn_dig, border_radius=8)
                draw_text("Dig", font_md, COLOR_TEXT, screen, btn_dig.centerx, btn_dig.centery, center=True)

                if selected_action:
                    draw_text(f"Mode: {selected_action.upper()}. Klik grid yang sesuai.", font_md, COLOR_PENDING, screen, WINDOW_W // 2, bottom_text_y, center=True)
                else:
                    draw_text("Giliran Anda! Pilih 'Move' atau 'Dig'.", font_md, COLOR_PENDING, screen, WINDOW_W // 2, bottom_text_y, center=True)
            else:
                draw_text(f"Giliran Pemain {GAME_STATE['turn']} untuk beraksi.", font_md, COLOR_TEXT, screen, WINDOW_W // 2, bottom_text_y, center=True)


        elif phase == "ENDED":
            winner_text = "Anda Menang!" if GAME_STATE['winner'] == PLAYER_ID else "Anda Kalah."
            draw_text(winner_text, font_lg, COLOR_PENDING, screen, WINDOW_W // 2, WINDOW_H // 2, center=True)
        
        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()

# --- Main execution (Tidak ada perubahan) ---
if __name__ == "__main__":
    while PLAYER_ID is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()

        screen.fill(COLOR_BG)
        draw_text("Menghubungi server...", font_lg, COLOR_TEXT, screen, WINDOW_W // 2, WINDOW_H // 2, center=True)
        pygame.display.flip()
        
        PLAYER_ID = join_game()
        if PLAYER_ID is None:
            screen.fill(COLOR_BG)
            draw_text("Gagal bergabung. Server penuh atau tidak aktif.", font_md, COLOR_HIT, screen, WINDOW_W // 2, WINDOW_H // 2 - 30, center=True)
            draw_text("Mencoba lagi dalam 5 detik... (ESC untuk keluar)", font_sm, COLOR_TEXT, screen, WINDOW_W // 2, WINDOW_H // 2 + 30, center=True)
            pygame.display.flip()
            time.sleep(5)
    
    game_loop()