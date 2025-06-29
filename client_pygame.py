import os
import json
import atexit
import pygame
import sys
import requests
import time

# --- Konfigurasi Klien ---
SERVER_URL = "http://192.168.0.104:8889"

# --- Auto‐allocate session file A/B dengan lock sederhana ---
def allocate_session_file():
    candidates = ['session_A.json', 'session_B.json']
    for fn in candidates:
        lockfile = fn + '.lock'
        # jika data ada & sedang dipakai, skip
        if os.path.exists(fn) and os.path.exists(lockfile):
            continue
        # reservasi: buat lock
        with open(lockfile, 'w') as f:
            f.write(str(os.getpid()))
        # hapus lock saat program keluar
        atexit.register(lambda l=lockfile: os.remove(l) if os.path.exists(l) else None)
        return fn
    # fallback jika keduanya penuh
    return 'session_fallback.json'

SESSION_FILE = allocate_session_file()

# FLAG: apakah file session perlu dihapus saat exit?
session_should_delete = False

def cleanup_session_file():
    if session_should_delete and os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

# register cleanup agar dijalankan saat client exit
atexit.register(cleanup_session_file)

# --- Load / Save session ---
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
        return data.get('player_id'), data.get('session_token')
    return None, None

def save_session(pid, token):
    with open(SESSION_FILE, 'w') as f:
        json.dump({'player_id': pid, 'session_token': token}, f)

# --- Pygame setup ---
WINDOW_W, WINDOW_H = 1280, 800
CELL_SIZE = 45
MARGIN = 4
STARTING_HP = 3

# Colors
COLOR_BG          = (30, 30, 30)
COLOR_GRID_LINE   = (50, 50, 50)
COLOR_TREASURE    = (0, 255, 0)
COLOR_TEXT        = (255, 255, 255)
COLOR_GOLD        = (255, 215, 0)
COLOR_MY_GRID_BG  = (0, 100, 200)
COLOR_DIG_GRID_BG = (200, 150, 100)
COLOR_BTN         = (70, 70, 70)
COLOR_BTN_ACTIVE  = (100,100,100)
COLOR_HP_FULL     = (0,200,0)
COLOR_HP_EMPTY    = (80,80,80)
COLOR_HP_BORDER   = (0,255,0)
COLOR_HIT         = (255,0,0)
COLOR_MISS        = (150,150,150)
COLOR_PENDING     = (255,255,0)
COLOR_GRID_BASE      = (40, 40, 40)
COLOR_HOVER_BLUE     = (0, 191, 255)
COLOR_HOVER_ORANGE   = (255, 140, 0)
COLOR_BTN_HOVER = (255, 200, 100) 

pygame.init()
screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
pygame.display.set_caption("Treasure Hunt Client")
font_sm = pygame.font.SysFont(None, 32)
font_md = pygame.font.SysFont(None, 42)
font_lg = pygame.font.SysFont(None, 56)
font_xl = pygame.font.SysFont(None, 72)
clock   = pygame.time.Clock()

# Load background dan treasure image
try:
    ARENA_BG = pygame.image.load("asset/arena_bg2.png")
    ARENA_BG = pygame.transform.scale(ARENA_BG, (WINDOW_W, WINDOW_H))
except:
    ARENA_BG = None  # fallback: bg warna polos

try:
    TREASURE_IMG = pygame.image.load("asset/treasure.png")
    TREASURE_IMG = pygame.transform.scale(TREASURE_IMG, (CELL_SIZE - 10, CELL_SIZE - 10))
except:
    TREASURE_IMG = None  # fallback: warna hijau


# --- Server communication ---
def join_game():
    prev_id, prev_token = load_session()
    payload = {}
    if prev_id and prev_token:
        payload = {'player_id': prev_id, 'session_token': prev_token}

    try:
        if payload:
            res = requests.post(f"{SERVER_URL}/join", json=payload)
        else:
            res = requests.post(f"{SERVER_URL}/join")
    except requests.exceptions.ConnectionError:
        return None

    if res.status_code == 200:
        data = res.json()
        pid   = data.get('player_id')
        token = data.get('session_token')
        save_session(pid, token)
        return pid
    return None

def get_game_state(pid):
    try:
        res = requests.get(f"{SERVER_URL}/state?player_id={pid}")
        return res.json() if res.status_code == 200 else None
    except requests.exceptions.ConnectionError:
        return None

def send_placement(pid, y, x):
    try:
        requests.post(f"{SERVER_URL}/place", json={'player_id': pid, 'coords': [y, x]})
    except requests.exceptions.ConnectionError:
        print("Koneksi ke server terputus.")

def send_action(pid, tp, y, x):
    try:
        requests.post(f"{SERVER_URL}/action", json={'player_id': pid, 'type': tp, 'coords': [y, x]})
    except requests.exceptions.ConnectionError:
        print("Koneksi ke server terputus.")

# --- Drawing helpers ---
def draw_text(text, font, color, surf, x, y, center=False):
    obj  = font.render(text, True, color)
    rect = obj.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surf.blit(obj, rect)
    return rect

def draw_button(rect, label, is_hovered=False, selected=False):
    if selected:
        color = COLOR_BTN_ACTIVE
    elif is_hovered:
        color = COLOR_BTN_HOVER
    else:
        color = COLOR_BTN
    pygame.draw.rect(screen, color, rect, border_radius=8)
    draw_text(label, font_md, COLOR_TEXT, screen, rect.centerx, rect.centery, center=True)

def draw_hp(label, hp, max_hp, x, y):
    tr = draw_text(f"{label}:", font_md, COLOR_TEXT, screen, x, y)
    box, spacing = 30, 6
    start_x = tr.right + 15
    for i in range(max_hp):
        r = pygame.Rect(start_x + i*(box+spacing), y+5, box, box)
        if i < hp:
            pygame.draw.rect(screen, COLOR_HP_FULL, r)
        else:
            pygame.draw.rect(screen, COLOR_HP_EMPTY, r)
            pygame.draw.rect(screen, COLOR_HP_BORDER, r, 2)

def pixel_to_grid(mx, my, off_x, off_y, gs):
    if mx < off_x or my < off_y:
        return None
    gx = (mx - off_x) // (CELL_SIZE + MARGIN)
    gy = (my - off_y) // (CELL_SIZE + MARGIN)
    if 0 <= gx < gs and 0 <= gy < gs:
        return gy, gx
    return None

def draw_digging_grid(off_x, off_y, gs, label, marks, hover_cell=None, hover_color=None):
    draw_text(label, font_md, COLOR_TEXT, screen, off_x, off_y - 50)
    for r in range(gs):
        for c in range(gs):
            rect = pygame.Rect(
                off_x + c*(CELL_SIZE+MARGIN),
                off_y + r*(CELL_SIZE+MARGIN),
                CELL_SIZE, CELL_SIZE
            )
            base_color = hover_color if hover_cell == (r, c) else COLOR_GRID_BASE
            pygame.draw.rect(screen, base_color, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
            m = marks[r][c]
            if m == 'hit':
                pygame.draw.rect(screen, COLOR_HIT, rect.inflate(-8,-8))
            elif m == 'miss':
                pygame.draw.rect(screen, COLOR_MISS, rect.inflate(-8,-8))


def draw_my_treasure_grid(off_x, off_y, gs, ts, label, pos, hover_cell=None, hover_color=None):
    draw_text(label, font_md, COLOR_TEXT, screen, off_x, off_y - 50)
    for r in range(gs):
        for c in range(gs):
            rect = pygame.Rect(
                off_x + c*(CELL_SIZE+MARGIN),
                off_y + r*(CELL_SIZE+MARGIN),
                CELL_SIZE, CELL_SIZE
            )
            base_color = hover_color if hover_cell == (r, c) else COLOR_GRID_BASE
            pygame.draw.rect(screen, base_color, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
    if pos:
        ty, tx = pos
        for dy in range(ts):
            for dx in range(ts):
                if tx+dx < gs and ty+dy < gs:
                    rect = pygame.Rect(
                        off_x + (tx+dx)*(CELL_SIZE+MARGIN),
                        off_y + (ty+dy)*(CELL_SIZE+MARGIN),
                        CELL_SIZE, CELL_SIZE
                    )
                    if TREASURE_IMG:
                        img = pygame.transform.scale(TREASURE_IMG, (CELL_SIZE - 10, CELL_SIZE - 10))
                        screen.blit(img, rect.inflate(-8, -8).topleft)
                    else:
                        pygame.draw.rect(screen, COLOR_TREASURE, rect.inflate(-8, -8))


# --- Main game loop ---
def game_loop():
    global PLAYER_ID, session_should_delete
    selected = None
    running = True

    while running:
        state = get_game_state(PLAYER_ID)
        if not state:
            draw_text("Koneksi ke server terputus...", font_lg, COLOR_HIT,
                      screen, WINDOW_W//2, WINDOW_H//2, center=True)
            pygame.display.flip()
            time.sleep(2)
            break

        if state['game_phase'] == "ENDED":
            session_should_delete = True

        gs = state['grid_size']
        ts = state['treasure_size']
        pix = gs * (CELL_SIZE + MARGIN)
        HEADER_Y = 140
        GAP = 120
        total_w = pix * 2 + GAP
        start_x = (WINDOW_W - total_w) // 2
        dig_x = start_x
        my_x = start_x + pix + GAP
        grid_y = HEADER_Y + ((WINDOW_H - HEADER_Y - 120) - pix) // 2
        btn_y = grid_y + pix + 35
        txt_y = btn_y + 75
        btn_cx = start_x + pix + GAP // 2
        btn_move = pygame.Rect(btn_cx - 140, btn_y, 120, 50)
        btn_dig = pygame.Rect(btn_cx + 20, btn_y, 120, 50)

        phase = state['game_phase']
        my_turn = (state['turn'] == PLAYER_ID)

        # Cek posisi mouse
        mouse_pos = pygame.mouse.get_pos()
        hover_my = pixel_to_grid(mouse_pos[0], mouse_pos[1], my_x, grid_y, gs)
        hover_dig = pixel_to_grid(mouse_pos[0], mouse_pos[1], dig_x, grid_y, gs)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                running = False
            if ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                if phase == "PLACEMENT" and state['my_treasure_pos'] is None:
                    cell = pixel_to_grid(mx, my, my_x, grid_y, gs)
                    if cell:
                        y, x = cell
                        if x <= gs - ts and y <= gs - ts:
                            send_placement(PLAYER_ID, y, x)
                            selected = None
                elif phase == "BATTLE" and my_turn:
                    if btn_move.collidepoint(mx, my):
                        selected = 'move'
                    elif btn_dig.collidepoint(mx, my):
                        selected = 'dig'
                    else:
                        target = None
                        if selected == 'dig':
                            target = pixel_to_grid(mx, my, dig_x, grid_y, gs)
                        elif selected == 'move':
                            target = pixel_to_grid(mx, my, my_x, grid_y, gs)
                        if target:
                            y, x = target
                            if selected == 'move' and (x > gs - ts or y > gs - ts):
                                continue
                            send_action(PLAYER_ID, selected, y, x)
                            selected = None

        if ARENA_BG:
            screen.blit(ARENA_BG, (0, 0))
        else:
            screen.fill(COLOR_BG)

        draw_text(PLAYER_ID, font_xl, COLOR_GOLD, screen, btn_cx, 35, center=True)
        draw_text(state['action_message'], font_lg, COLOR_TEXT, screen, WINDOW_W // 2, 80, center=True)
        draw_hp("Opponent", state['opponent_hp'], STARTING_HP, dig_x, 25)
        draw_hp("My HP", state['my_hp'], STARTING_HP, my_x, 25)

        # Identifikasi apakah Player A atau B
        is_player_a = PLAYER_ID.lower().endswith("a")

        # Warna hover dan label teks disesuaikan berdasarkan player
        hover_color_my = (0, 0, 180) if is_player_a else (255, 140, 0)
        hover_color_dig = (255, 140, 0) if is_player_a else (0, 0, 180)

        # Warna teks label grid
        label_color_opponent = (255, 140, 0) if is_player_a else (0, 70, 160)
        label_color_treasure = (0, 191, 255) if is_player_a else (255, 140, 0)

        # Draw Opponent's Grid
        # Draw background box and label for Opponent's Grid
        label_text = "Opponent's Grid"
        label_surface = font_md.render(label_text, True, label_color_opponent)
        label_rect = label_surface.get_rect(topleft=(dig_x, grid_y - 60))
        box_rect = pygame.Rect(label_rect.x - 10, label_rect.y - 5, label_rect.width + 20, label_rect.height + 10)
        pygame.draw.rect(screen, (100, 100, 100), box_rect, border_radius=6)  # abu-abu
        screen.blit(label_surface, label_rect)
        for r in range(gs):
            for c in range(gs):
                rect = pygame.Rect(
                    dig_x + c * (CELL_SIZE + MARGIN),
                    grid_y + r * (CELL_SIZE + MARGIN),
                    CELL_SIZE, CELL_SIZE
                )
                if hover_dig == (r, c):
                    pygame.draw.rect(screen, hover_color_dig, rect)
                else:
                    pygame.draw.rect(screen, (60, 60, 60), rect)

                if state['my_dig_marks'][r][c] == 'hit':
                    pygame.draw.rect(screen, COLOR_HIT, rect.inflate(-8, -8))
                elif state['my_dig_marks'][r][c] == 'miss':
                    pygame.draw.rect(screen, COLOR_MISS, rect.inflate(-8, -8))

                pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)

        # Draw My Treasure Grid
        # Draw background box and label for Your Treasure
        label_text = "Your Treasure"
        label_surface = font_md.render(label_text, True, label_color_treasure)
        label_rect = label_surface.get_rect(topleft=(my_x, grid_y - 60))
        box_rect = pygame.Rect(label_rect.x - 10, label_rect.y - 5, label_rect.width + 20, label_rect.height + 10)
        pygame.draw.rect(screen, (100, 100, 100), box_rect, border_radius=6)  # abu-abu
        screen.blit(label_surface, label_rect)
        for r in range(gs):
            for c in range(gs):
                rect = pygame.Rect(
                    my_x + c * (CELL_SIZE + MARGIN),
                    grid_y + r * (CELL_SIZE + MARGIN),
                    CELL_SIZE, CELL_SIZE
                )
                if hover_my == (r, c):
                    pygame.draw.rect(screen, hover_color_my, rect)
                else:
                    pygame.draw.rect(screen, (60, 60, 60), rect)

                pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)

        if state['my_treasure_pos']:
            ty, tx = state['my_treasure_pos']
            for dy in range(ts):
                for dx in range(ts):
                    if tx + dx < gs and ty + dy < gs:
                        rect = pygame.Rect(
                            my_x + (tx + dx) * (CELL_SIZE + MARGIN),
                            grid_y + (ty + dy) * (CELL_SIZE + MARGIN),
                            CELL_SIZE, CELL_SIZE
                        )
                        if TREASURE_IMG:
                            img = pygame.transform.scale(TREASURE_IMG, (CELL_SIZE - 10, CELL_SIZE - 10))
                            screen.blit(img, rect.inflate(-8, -8).topleft)
                        else:
                            pygame.draw.rect(screen, COLOR_TREASURE, rect.inflate(-8, -8))

        # Tombol dan info bawah
        if phase == "PLACEMENT":
            if state['my_treasure_pos'] is None:
                draw_text("Klik di grid 'Your Treasure' untuk menempatkan harta.",
                          font_md, COLOR_PENDING, screen, WINDOW_W // 2, txt_y, center=True)
            else:
                draw_text("Menunggu pemain lain...", font_md, COLOR_TEXT,
                          screen, WINDOW_W // 2, txt_y, center=True)
        elif phase == "BATTLE":
            if my_turn:
                hover_move = btn_move.collidepoint(mouse_pos)
                hover_dig = btn_dig.collidepoint(mouse_pos)

                pygame.draw.rect(screen,
                                COLOR_BTN_HOVER if hover_move else (COLOR_BTN_ACTIVE if selected == 'move' else COLOR_BTN),
                                btn_move, border_radius=8)
                draw_text("Move", font_md, COLOR_TEXT,
                        screen, btn_move.centerx, btn_move.centery, center=True)

                pygame.draw.rect(screen,
                                COLOR_BTN_HOVER if hover_dig else (COLOR_BTN_ACTIVE if selected == 'dig' else COLOR_BTN),
                                btn_dig, border_radius=8)
                draw_text("Dig", font_md, COLOR_TEXT,
                        screen, btn_dig.centerx, btn_dig.centery, center=True)

                if selected:
                    draw_text(f"Mode: {selected.upper()}. Klik grid yang sesuai.",
                            font_md, COLOR_PENDING, screen, WINDOW_W // 2, txt_y, center=True)
                else:
                    draw_text("Giliran Anda! Pilih 'Move' atau 'Dig'.",
                            font_md, COLOR_PENDING, screen, WINDOW_W // 2, txt_y, center=True)
            else:
                draw_text(f"Giliran Pemain {state['turn']} untuk beraksi.",
                          font_md, COLOR_TEXT, screen, WINDOW_W // 2, txt_y, center=True)
        elif phase == "ENDED":
            msg = "Anda Menang!" if state['winner'] == PLAYER_ID else "Anda Kalah."
            draw_text(msg, font_lg, COLOR_PENDING,
                      screen, WINDOW_W // 2, WINDOW_H // 2, center=True)

        pygame.display.flip()
        clock.tick(10)

    pygame.quit()
    sys.exit()

def main_menu():
    # Fallback flags
    use_default_bg = False
    use_default_title_font = False
    use_default_button_font = False

    # Load background
    try:
        bg_image = pygame.image.load("asset/Main_menu.jpg")
        bg_image = pygame.transform.scale(bg_image, (WINDOW_W, WINDOW_H))
    except:
        use_default_bg = True
        bg_image = pygame.Surface((WINDOW_W, WINDOW_H))
        bg_image.fill((0, 0, 0))  # fallback: hitam

    # Load fonts
    try:
        title_font = pygame.font.Font("asset/MightySouly-lxggD.ttf", 96)
    except:
        title_font = pygame.font.SysFont(None, 96, bold=True)
        use_default_title_font = True

    try:
        button_font = pygame.font.Font("asset/rimouski sb.otf", 48)
    except:
        button_font = pygame.font.SysFont(None, 48)
        use_default_button_font = True

    # Tombol Start
    start_btn_rect = pygame.Rect(WINDOW_W // 2 - 150, WINDOW_H // 2, 300, 80)
    btn_color_normal = (190, 81, 3) if not use_default_bg else (0, 200, 0)  # fallback: hijau
    btn_color_hover  = (220, 110, 30) if not use_default_bg else (0, 255, 0)

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if start_btn_rect.collidepoint(mouse_pos):
                    return  # Start game

        screen.blit(bg_image, (0, 0))

        # Judul
        title_color = (0, 0, 0) if not use_default_bg else (255, 255, 255)
        draw_text("Treasure Hunt", title_font, title_color,
                  screen, WINDOW_W // 2, 150, center=True)

        # Tombol Start dengan efek hover
        if start_btn_rect.collidepoint(mouse_pos):
            btn_color = btn_color_hover
        else:
            btn_color = btn_color_normal

        pygame.draw.rect(screen, btn_color, start_btn_rect, border_radius=12)
        draw_text("Start Game", button_font, (255, 255, 255),
                  screen, start_btn_rect.centerx, start_btn_rect.centery, center=True)

        pygame.display.flip()
        clock.tick(30)


# --- Main execution ---
if __name__ == "__main__":
    PLAYER_ID = None

    main_menu()

    # loop until join successful
    while PLAYER_ID is None:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT or (ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE):
                pygame.quit()
                sys.exit()
        screen.fill(COLOR_BG)
        draw_text("Menghubungi server...", font_lg, COLOR_TEXT,
                  screen, WINDOW_W//2, WINDOW_H//2, center=True)
        pygame.display.flip()

        PLAYER_ID = join_game()
        if PLAYER_ID is None:
            screen.fill(COLOR_BG)
            draw_text("Gagal bergabung. Server penuh atau tidak aktif.", font_md, COLOR_HIT,
                      screen, WINDOW_W//2, WINDOW_H//2 - 30, center=True)
            draw_text("Mencoba lagi dalam 5 detik... (ESC untuk keluar)", font_sm, COLOR_TEXT,
                      screen, WINDOW_W//2, WINDOW_H//2 + 30, center=True)
            pygame.display.flip()
            time.sleep(5)

    game_loop()