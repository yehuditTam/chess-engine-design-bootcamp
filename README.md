# Kungfu Chess Engine

A real-time chess engine where both players move simultaneously — no turns, no waiting.  
Pieces take time to travel, can jump over enemies, and need to cool down after arriving.

---

## Rules

- **Both players move at the same time** — there are no turns.
- **Every move takes time** — a piece travels at 1 second per square.
- **Cooldown** — after arriving, a piece rests for 2 seconds before it can move again.
- **Jump** — a piece can leap into the air for 1 second. Any enemy that arrives at its cell during the jump is captured instead. The airborne piece stays put.
- **Game over** — the first player to capture the opponent's King wins.
- **Promotion** — a Pawn that reaches the last row is immediately promoted to Queen.

---

## Project Structure

```
kungfu_chess/
├── model/        — Board, Piece, Position (pure data, no logic)
├── rules/        — Move validation per piece type (Strategy pattern)
├── realtime/     — Timing, motion scheduling, arrival resolution
├── input/        — Command parsing, click handling, stdin controller
├── io/           — Text board parsing and printing
├── view/         — OpenCV rendering, sprite animation, mouse input
└── shared/       — Constants, DTOs, interfaces, exceptions, validators

tests/
├── unit/         — One file per layer
└── integration/  — .kfc scenario files + runner
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Running

### Visual mode (OpenCV window)

```bash
python run_view.py
```

**Mouse controls:**
- Left click — select a piece, then click destination to move
- Right click — make the selected piece jump

### Text mode (stdin)

```bash
python -m kungfu_chess < my_game.kfc
```

Input format (`.kfc` file):

```
Board:
wR . . bK
.  . . .
.  . . wK

Commands:
click 50 50
click 250 50
wait 1100
print board
```

**Commands:**
| Command | Description |
|---|---|
| `click X Y` | Click pixel (X, Y) — selects or moves a piece |
| `jump X Y` | Jump the piece at pixel (X, Y) |
| `wait N` | Advance time by N milliseconds |
| `print board` | Print the current board state to stdout |

**Board notation:** `wK` = white King, `bQ` = black Queen, `.` = empty cell.  
Pixel coordinates are converted to board cells using tile size (100px per cell).

---

## Running Tests

```bash
python -m pytest tests/
```

---

## Timing Model

| Event | Duration |
|---|---|
| Move (per square) | 1.0 second |
| Jump (airborne) | 1.0 second |
| Cooldown after arrival | 2.0 seconds |

Only one color can have pieces in motion at a time.  
A piece that is pending, airborne, or cooling cannot be selected or moved.
