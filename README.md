
# Treasure Hunt - Multiplayer Game
Multiplayer Treasure Hunting Game (Guessing Game) using HTTP Method in Python 



## Overview
Treasure Hunt is a strategic 2-player game played on a 7x7 grid where players hide their treasures and attempt to find and destroy their opponent's treasure.

## Game Features
- **Online Multiplayer**: Play against remote opponents via HTTP protocol
- **Strategic Gameplay**: 
  - Hide 2x2 treasures on your grid
  - Attack opponent's grid to find their treasure
  - 3 HP system - destroy all treasure blocks to win
- **Interactive UI**: Pygame-based graphical interface
- **Turn-based System**: Fair alternating turns

## Technical Specifications
### Game Architecture
- **Client-Server Model**
- **Server Components**:
  - Game state management
  - HTTP request handling
  - Synchronization between players
- **Client Components**:
  - Graphical interface
  - Input handling
  - Server communication
