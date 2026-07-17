# Kungfu Chess Engine — Project Rules

## Architecture: Layered (model / rules / realtime / input / io / view / shared)

```
kungfu_chess/
├── model/
│   ├── piece.py          — Piece: domain object, holds color, ptype, move_strategy
│   ├── board.py          — Board: stores and retrieves pieces only, no logic, exposes snapshot()
│   └── position.py       — Position: frozen dataclass (row, col), used everywhere instead of raw tuples
├── rules/
│   ├── piece_rules.py    — move strategy classes per piece type (Strategy pattern)
│   └── rule_engine.py    — RuleEngine: validates moves (read-only, no board mutation)
├── realtime/
│   ├── motion.py         — PendingMove, PendingJump dataclasses
│   ├── real_time_arbiter.py — RealTimeArbiter: active motions, time progression, arrival resolution, capture events
│   └── game_engine.py    — GameEngine: game-over, selection, move delegation, snapshots
├── input/
│   ├── commands.py       — Command dataclasses (ClickCommand, JumpCommand, WaitCommand, PrintBoardCommand)
│   ├── board_mapper.py   — converts raw string → Command (pixel → row/col here only)
│   └── controller.py     — entry point: parses stdin, drives GameEngine
├── io/
│   ├── board_parser.py   — parse_input: splits raw text lines into board rows and command strings
│   └── board_printer.py  — print_board: prints BoardSnapshot to stdout
├── view/
│   ├── renderer.py       — Renderer: abstract base class for rendering
│   ├── image_view.py     — ImageView: OpenCV tile renderer, uses BoardSnapshot + TILE_SIZE
│   └── name_dialog.py    — ask_player_names(): tkinter dialog shown before game starts
└── shared/
    ├── constants.py      — MOVE_DELAY_SECONDS, JUMP_DURATION_SECONDS, PieceType, Color
    ├── ui_constants.py   — TILE_SIZE (UI only, never used by game logic)
    ├── interfaces.py     — IBoard, IGame, IPiece abstract classes
    ├── exceptions.py     — InvalidMoveError, OutOfBoundsError, BlockedPathError, FriendlyFireError
    ├── validators.py     — validate_board() for input validation
    └── dto.py            — PieceSnapshot, BoardSnapshot (frozen=True, no live objects)

tests/                    — flat, one file per layer
    test_board.py         → model layer (parsing, move_piece, snapshot, dimensions, add_piece)
    test_validators.py    → RuleEngine + validate_board
    test_move_rules.py    → piece strategy classes
    test_game.py          → realtime layer (selection, scheduling, timing, jump, game-over, snapshot)
    test_parse_input.py   → input layer (parse_input, controller)
```

## Layer Responsibilities

| Layer | Owns | Must NOT own |
|---|---|---|
| `model` | board state, piece identity, piece lifecycle, Position | pixels, click type, rendering, motion rules, timing |
| `rules` | motion rules only (read-only) | board mutation, animation, click interpretation, game-over |
| `realtime` | active motion objects, time progression, arrival resolution, capture events, game-over | tool-specific motion logic, rendering, input parsing, pixel mapping |
| `input` | interpret clicks, pixel→cell mapping, stdin parsing | movement rules, board mutation, rendering, timing |
| `io` | text parsing and printing of board state | game logic, rendering, timing |
| `view` | OpenCV rendering + tkinter name dialog using BoardSnapshot | game logic, board mutation, input parsing |
| `shared` | constants, exceptions, interfaces, DTOs, input validation | business logic of any kind |

## Key Rules

- `Board` must NOT contain `is_legal`, `is_path_clear`, or `print_board` — those belong to `rules`/`realtime`
- `RuleEngine` is owned by `GameEngine`, not `Board`
- `TILE_SIZE` lives in `shared/ui_constants.py` — never in `constants.py` or game logic
- External code (tests, UI) must use `game.get_snapshot()` / `board.snapshot()` — never hold live `Piece` objects
- `dto.PieceSnapshot` and `dto.BoardSnapshot` are `frozen=True` dataclasses
- No `time.sleep()` in tests — manipulate `arrive_at = time.time() - 1` instead
- No pixel values inside `GameEngine`, `Board`, or `Piece`
- All internal coordinates use `Position(row, col)` — never raw tuples

## Timing Model

- Every move is scheduled with `arrive_at = time.time() + MOVE_DELAY_SECONDS`
- `game.execute_pending_moves()` is called at the start of every `handle_command()`
- Only one color can have pending moves at a time
- A piece that is pending cannot be selected or redirected
- `RealTimeArbiter` owns all timing logic — `GameEngine` only delegates to it

## Jump Mechanic

- `jump` command makes a piece airborne for `JUMP_DURATION_SECONDS`
- An airborne piece captures any enemy that arrives at its cell during the jump
- A moving piece cannot jump; a piece cannot jump twice

## Coordinate System

- Input: pixel coordinates `(x, y)`
- Conversion: `row = y // TILE_SIZE`, `col = x // TILE_SIZE` — done in `board_mapper` only
- Internal: always `Position(row, col)` — converted from command in `GameEngine.handle_command`
