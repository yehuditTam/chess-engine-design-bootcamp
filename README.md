# Kungfu Chess Engine

A real-time chess engine where both players move simultaneously — no turns, no waiting.  
Pieces take time to travel, can jump over enemies, and need to cool down after arriving.  
Supports both local single-machine play and networked two-player mode over WebSockets.

---

## Rules

- **Both players move at the same time** — there are no turns.
- **Every move takes time** — a piece travels at 1 second per square.
- **Cooldown** — after arriving, a piece rests for 5 seconds before it can move again.
- **Friendly blocking** — a piece stops one square before a cell that a friendly piece will occupy.
- **Jump** — a piece can leap into the air for 1 second. Any enemy that arrives at its cell during the jump is captured instead. The airborne piece stays put.
- **Game over** — the first player to capture the opponent's King wins.
- **Promotion** — a Pawn that reaches the last row is immediately promoted to Queen.

---

## Project Structure

```
kungfu_chess/
├── model/        — Board, Piece, Position (pure data, no logic)
├── rules/        — Move validation per piece type (Strategy pattern)
├── realtime/     — Timing, motion scheduling, arrival resolution, score tracking
├── input/        — Command parsing, click handling, stdin controller
├── io/           — Text board parsing and printing
├── view/         — OpenCV rendering, sprite animation, mouse input
└── shared/       — Constants, DTOs, interfaces, exceptions, validators, EventBus

server/
├── game_server.py  — Async WebSocket server (2-player slot management, 30 ms game loop)
└── serializer.py   — GameSnapshot ↔ JSON conversion

client/
├── server_bridge.py  — Thread-safe bridge between asyncio WebSocket and OpenCV loop
└── run_client.py     — OpenCV client that connects to the server

tests/
├── unit/         — One file per layer
└── integration/  — .kfc scenario files + runner
```

---

## Installation

```bash
pip install -r requirements.txt
```

> **Sound on Windows:** sound playback uses the built-in Windows MCI (`winmm`) via
> `ctypes` — no extra package needed. `playsound` is no longer a dependency.

---

## Running

### Networked mode (two players over WebSocket)

Start the server first:

```bash
python -m server.game_server
```

Then each player connects with the client:

```bash
python -m client.run_client
```

You will be prompted for a username. The first connection is assigned White, the second Black.

**Mouse controls:**
- Left click — select a piece, then click destination to move
- Right click — make the selected piece jump

> The timer starts when the **first move or jump** is made by either player.

### Local visual mode (single machine, OpenCV window)

```bash
python run_view.py
```

A dialog will appear to enter player names before the game starts. Leave blank to use the defaults ("Black" / "White").

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

With coverage:

```bash
python -m pytest tests/ --cov=kungfu_chess --cov=server --cov=client --cov-report=term-missing
```

---

## Timing Model

| Event | Duration |
|---|---|
| Move (per square) | 1.0 second |
| Jump (airborne) | 2.0 seconds |
| Cooldown after arrival | 5.0 seconds |

Only one color can have pieces in motion at a time.  
A piece that is pending, airborne, or cooling cannot be selected or moved.

The **timer** displayed at the top starts on the first move or jump and is
synchronised across both networked clients.

While cooling or airborne, a **circular countdown arc** is drawn around the piece:
- 🟢 Green arc — cooling down after a move (5 s)
- 🔵 Cyan arc — airborne after a jump (2 s)

## Sounds

| File | Event |
|---|---|
| `click.mp3` | Piece moves |
| `eat.mp3` | Piece captured |
| `jump.mp3` | Piece jumps |
| `error.mp3` | Invalid move attempt |
| `game_over.mp3` | Game ends |

All sound files live in `assets/sounds/`.

---

## Game Over Screen

When the game ends an overlay displays:
- Winner name
- Game duration (MM:SS)
- Both players' names and scores
- `R` to restart, `ESC` to exit

---



## WebSocket Protocol

All messages are JSON. Server → client:

| Message type | Fields | Description |
|---|---|---|
| `assigned` | `color` (`"w"` / `"b"`) | Sent immediately on connect |
| `state` | `board`, `black`, `white`, `game_over` | Broadcast every 30 ms |
| `legal_moves` | `cell`, `moves` | Reply to a `legal_moves` request |
| `error` | `reason` | Sent when server is full |

Client → server:

| Message type | Fields | Description |
|---|---|---|
| `join` | `username` | First message after connect |
| `move` | `from`, `to` | Request a piece move |
| `jump` | `cell` | Request a piece jump |
| `legal_moves` | `cell` | Request legal moves for a cell |
