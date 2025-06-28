import pygame
import sys

# --- Configuration ---
GRID_SIZE = 7
CELL_SIZE = 35
MARGIN = 2
TREASURE_SIZE = 2
TREASURE_HP = 3

# Colors
COLOR_BG = (30, 30, 30)
COLOR_GRID_LINE = (50, 50, 50)
COLOR_TREASURE = (0, 255, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_A_DIG_BG = (180, 220, 255)
COLOR_A_PLACE_BG = (0, 100, 200)
COLOR_B_DIG_BG = (255, 200, 150)
COLOR_B_PLACE_BG = (200, 0, 0)
COLOR_BTN = (70, 70, 70)
COLOR_BTN_ACTIVE = (100, 100, 100)
COLOR_HP_FULL = (0, 200, 0)
COLOR_HP_EMPTY_FILL = (80, 80, 80)
COLOR_HP_BORDER = (0, 255, 0)


# Initialize Pygame
pygame.init()
font = pygame.font.SysFont(None, 28)
title_font = pygame.font.SysFont(None, 36)
clock = pygame.time.Clock()

# Fullscreen setup
display_info = pygame.display.Info()
SCREEN_W, SCREEN_H = display_info.current_w, display_info.current_h
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
full_screen = True


# ==============================================================================
# ### PERUBAHAN UTAMA: Kalkulasi Layout Sesuai Permintaan ###
# ==============================================================================

# Core dimensions
grid_pixels = GRID_SIZE * CELL_SIZE + (GRID_SIZE + 1) * MARGIN
total_grid_width = grid_pixels * 2 + 100 # Total lebar untuk area kedua pemain + spasi
center_x = SCREEN_W // 2

# Horizontal offsets (membagi layar untuk Player A dan B)
off_x1 = (SCREEN_W - total_grid_width) // 2
off_x2 = off_x1 + grid_pixels + 100

# Definisi layout vertikal yang baru
V_GAP_HEADER = 15       # Spasi setelah header (Player A/B)
V_GAP_LABEL = 5         # Spasi setelah label grid
V_GAP_GRID = 40         # Spasi antar grid (Dig dan Treasure)
V_GAP_BOTTOM = 20       # Spasi sebelum area tombol
header_font_h = 36      # Perkiraan tinggi font judul
label_font_h = 28       # Perkiraan tinggi font biasa
button_h = 40           # Tinggi tombol
turn_text_h = 36        # Tinggi teks giliran

# Kalkulasi total tinggi blok konten untuk memposisikannya di tengah secara vertikal
total_h = (header_font_h + V_GAP_HEADER +
           label_font_h + V_GAP_LABEL +
           grid_pixels + V_GAP_GRID +
           label_font_h + V_GAP_LABEL +
           grid_pixels + V_GAP_BOTTOM +
           turn_text_h + V_GAP_LABEL +
           button_h)
start_y = (SCREEN_H - total_h) // 2

# Mendefinisikan koordinat Y untuk setiap baris layout
y_header = start_y
y_dig_grid_label = y_header + header_font_h + V_GAP_HEADER
y_dig_grid = y_dig_grid_label + label_font_h + V_GAP_LABEL
y_treasure_grid_label = y_dig_grid + grid_pixels + V_GAP_GRID
y_treasure_grid = y_treasure_grid_label + label_font_h + V_GAP_LABEL
y_turn_text = y_treasure_grid + grid_pixels + V_GAP_BOTTOM
y_buttons = y_turn_text + turn_text_h + V_GAP_LABEL

# Definisi Tombol (sekarang semua di posisi Y yang sama)
btn_width = 100
btn_height = 40
btn_dig = pygame.Rect(center_x - btn_width - 10, y_buttons, btn_width, btn_height)
btn_move = pygame.Rect(center_x + 10, y_buttons, btn_width, btn_height)
btn_confirm = pygame.Rect(center_x - btn_width - 10, y_buttons, btn_width, btn_height)
btn_cancel = pygame.Rect(center_x + 10, y_buttons, btn_width, btn_height)
btn_ready = pygame.Rect(center_x - btn_width // 2, y_buttons, btn_width, btn_height)


# Game state (TIDAK ADA PERUBAHAN)
treasure_pos = [None, None]
hp = [TREASURE_HP, TREASURE_HP]
turn = 0
phase = 'place_select'
placing = 0
pending = None
ready = [False, False]
action = None
winner = None
dig_marks = [ [[None]*GRID_SIZE for _ in range(GRID_SIZE)] for _ in range(2) ]


# --- Helpers --- (TIDAK ADA PERUBAHAN)
def draw_centered_text(s, rect, color=COLOR_TEXT, use_font=font):
    text_surf = use_font.render(s, True, color)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)
    
def draw_text_at_center(s, center_x, y, color=COLOR_TEXT, use_font=font):
    text_surf = use_font.render(s, True, color)
    text_rect = text_surf.get_rect(center=(center_x, y))
    screen.blit(text_surf, text_rect)

def draw_text(s, x, y, color=COLOR_TEXT, use_title_font=False):
    f = title_font if use_title_font else font
    screen.blit(f.render(s, True, color), (x, y))

def draw_hp_boxes(x, y, current, maximum):
    box_size = 20
    spacing = 5
    for i in range(maximum):
        box_rect = pygame.Rect(x + i * (box_size + spacing), y, box_size, box_size)
        if i < current:
            pygame.draw.rect(screen, COLOR_HP_FULL, box_rect)
        else:
            pygame.draw.rect(screen, COLOR_HP_EMPTY_FILL, box_rect)
            pygame.draw.rect(screen, COLOR_HP_BORDER, box_rect, 2)

def pixel_to_grid(mx, my, off_x, off_y):
    gx = (mx - off_x - MARGIN) // (CELL_SIZE + MARGIN)
    gy = (my - off_y - MARGIN) // (CELL_SIZE + MARGIN)
    if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
        return gy, gx
    return None

# --- Drawers --- (TIDAK ADA PERUBAHAN LOGIKA)
def draw_dig_grid(off_x, off_y, owner):
    bg = COLOR_A_DIG_BG if owner==0 else COLOR_B_DIG_BG
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = off_x + MARGIN + c*(CELL_SIZE+MARGIN)
            y = off_y + MARGIN + r*(CELL_SIZE+MARGIN)
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, bg, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
            mark = dig_marks[owner][r][c]
            if mark == 'hit':
                pygame.draw.rect(screen, (255,0,0), rect.inflate(-4,-4))
            elif mark == 'miss':
                pygame.draw.rect(screen, (150,150,150), rect.inflate(-4,-4))

def draw_place_grid(off_x, off_y, owner):
    bg = COLOR_A_PLACE_BG if owner==0 else COLOR_B_PLACE_BG
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            x = off_x + MARGIN + c*(CELL_SIZE+MARGIN)
            y = off_y + MARGIN + r*(CELL_SIZE+MARGIN)
            rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, bg, rect)
            pygame.draw.rect(screen, COLOR_GRID_LINE, rect, 1)
    pos = treasure_pos[owner]
    if pos:
        ty, tx = pos
        for dy in range(TREASURE_SIZE):
            for dx in range(TREASURE_SIZE):
                x = off_x + MARGIN + (tx+dx)*(CELL_SIZE+MARGIN)
                y = off_y + MARGIN + (ty+dy)*(CELL_SIZE+MARGIN)
                rect = pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(screen, COLOR_TREASURE, rect.inflate(-4,-4))

# --- Main loop ---
running = True
while running:
    # ### PERUBAHAN: Penyesuaian Event Handling dengan Layout Baru ###
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.key == pygame.K_f:
                full_screen = not full_screen
                if full_screen:
                    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            mx, my = ev.pos
            if phase == 'place_select':
                off_x = off_x1 if placing==0 else off_x2
                # Menggunakan y_treasure_grid untuk deteksi klik
                off_y = y_treasure_grid 
                cell = pixel_to_grid(mx, my, off_x, off_y)
                if cell:
                    y, x = cell
                    if x <= GRID_SIZE-TREASURE_SIZE and y <= GRID_SIZE-TREASURE_SIZE:
                        pending = (y, x)
                        phase = 'place_confirm'
            elif phase == 'place_confirm':
                if btn_confirm.collidepoint(mx, my):
                    treasure_pos[placing] = pending
                    pending = None
                    phase = 'place_ready'
                elif btn_cancel.collidepoint(mx, my):
                    pending = None
                    phase = 'place_select'
            elif phase == 'place_ready':
                if btn_ready.collidepoint(mx, my):
                    ready[placing] = True
                    if placing == 0:
                        placing = 1
                        phase = 'place_select'
                    else:
                        phase = 'battle'
            elif phase == 'battle':
                if btn_dig.collidepoint(mx, my):
                    action = 'dig'
                elif btn_move.collidepoint(mx, my):
                    action = 'move'
                else:
                    if action == 'dig':
                        off_x = off_x1 if turn==0 else off_x2
                        # Menggunakan y_dig_grid untuk deteksi klik
                        off_y = y_dig_grid 
                        cell = pixel_to_grid(mx, my, off_x, off_y)
                        if cell:
                            y, x = cell
                            if dig_marks[turn][y][x] is None:
                                opp = 1 - turn
                                pos = treasure_pos[opp]
                                if pos and pos[0] <= y < pos[0]+TREASURE_SIZE and pos[1] <= x < pos[1]+TREASURE_SIZE:
                                    dig_marks[turn][y][x] = 'hit'
                                    hp[opp] -= 1
                                else:
                                    dig_marks[turn][y][x] = 'miss'
                                turn = opp
                                dig_marks[turn] = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]
                                action = None
                    elif action == 'move':
                        off_x = off_x1 if turn==0 else off_x2
                        # Menggunakan y_treasure_grid untuk deteksi klik
                        off_y = y_treasure_grid 
                        cell = pixel_to_grid(mx, my, off_x, off_y)
                        if cell:
                            y, x = cell
                            if x <= GRID_SIZE-TREASURE_SIZE and y <= GRID_SIZE-TREASURE_SIZE:
                                treasure_pos[turn] = (y, x)
                                turn = 1 - turn
                                dig_marks[turn] = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]
                                action = None

    # Win check (TIDAK ADA PERUBAHAN)
    if phase == 'battle':
        for p in (0, 1):
            if hp[p] <= 0:
                winner = 1 - p
                phase = 'ended'

    # ==============================================================================
    # ### PERUBAHAN: Bagian Drawing Menggunakan Variabel Layout Baru ###
    # ==============================================================================
    screen.fill(COLOR_BG)
    draw_text("Press F to toggle fullscreen, ESC to quit", 10, 10)

    # --- Gambar Elemen Sesuai Layout Baru ---
    # Header (Nama Player + HP)
    draw_text("Player A", off_x1, y_header, use_title_font=True)
    draw_hp_boxes(off_x1 + 120, y_header, hp[0], TREASURE_HP)
    draw_text("Player B", off_x2, y_header, use_title_font=True)
    draw_hp_boxes(off_x2 + 120, y_header, hp[1], TREASURE_HP)

    # Label untuk Dig Grid
    draw_text_at_center("Dig Grid", off_x1 + grid_pixels // 2, y_dig_grid_label, use_font=font)
    draw_text_at_center("Dig Grid", off_x2 + grid_pixels // 2, y_dig_grid_label, use_font=font)
    
    # Dig Grid
    draw_dig_grid(off_x1, y_dig_grid, 0)
    draw_dig_grid(off_x2, y_dig_grid, 1)

    # Label untuk Treasure Grid
    draw_text_at_center("Your Treasure Grid", off_x1 + grid_pixels // 2, y_treasure_grid_label, use_font=font)
    draw_text_at_center("Your Treasure Grid", off_x2 + grid_pixels // 2, y_treasure_grid_label, use_font=font)

    # Treasure Grid
    draw_place_grid(off_x1, y_treasure_grid, 0)
    draw_place_grid(off_x2, y_treasure_grid, 1)


    # --- Menggambar UI/Tombol di Area Bawah Tengah ---
    if phase == 'place_confirm':
        off_x = off_x1 if placing==0 else off_x2
        # Menggunakan y_treasure_grid untuk highlight
        off_y = y_treasure_grid 
        y, x = pending
        for dy in range(TREASURE_SIZE):
            for dx in range(TREASURE_SIZE):
                rx = off_x + MARGIN + (x+dx)*(CELL_SIZE+MARGIN)
                ry = off_y + MARGIN + (y+dy)*(CELL_SIZE+MARGIN)
                pygame.draw.rect(screen, (255,255,0), (rx, ry, CELL_SIZE, CELL_SIZE), 3)

        pygame.draw.rect(screen, COLOR_BTN, btn_confirm)
        draw_centered_text("Confirm", btn_confirm)
        pygame.draw.rect(screen, COLOR_BTN, btn_cancel)
        draw_centered_text("Cancel", btn_cancel)

    elif phase == 'place_ready':
        pygame.draw.rect(screen, COLOR_BTN, btn_ready)
        draw_centered_text("Ready", btn_ready)

    elif phase == 'battle':
        pygame.draw.rect(screen, COLOR_BTN_ACTIVE if action=='dig' else COLOR_BTN, btn_dig)
        draw_centered_text("Dig", btn_dig)
        pygame.draw.rect(screen, COLOR_BTN_ACTIVE if action=='move' else COLOR_BTN, btn_move)
        draw_centered_text("Move", btn_move)

        # Teks giliran diposisikan di atas tombol
        draw_text_at_center(f"Turn: Player {'A' if turn==0 else 'B'}", center_x, y_turn_text, use_font=title_font)

    elif phase == 'ended':
        winner_text = f"Game Over! Winner: Player {'A' if winner==0 else 'B'}"
        # Teks pemenang ditampilkan di posisi teks giliran
        draw_text_at_center(winner_text, center_x, y_turn_text, use_font=title_font)

    else: # phase == 'place_select'
        placing_text = f"Player {'A' if placing==0 else 'B'}: place your treasure"
        # Teks instruksi penempatan ditampilkan di posisi teks giliran
        draw_text_at_center(placing_text, center_x, y_turn_text)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()