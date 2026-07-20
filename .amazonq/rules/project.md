# Kungfu Chess Engine — Project Rules

## Architecture: Layered (model / rules / realtime / input / io / view / shared / server / client)

```
kungfu_chess/
├── model/
│   ├── piece.py          — Piece: domain object, holds color, ptype, state, move_strategy
│   ├── board.py          — Board: stores and retrieves pieces only, no logic
│   ├── player.py         — Player: name + color (pure data)
│   └── position.py       — Position: frozen dataclass (row, col), used everywhere instead of raw tuples
├── rules/
│   ├── piece_rules.py    — move strategy classes per piece type (Strategy pattern)
│   └── rule_engine.py    — RuleEngine: validates moves (read-only, no board mutation)
├── realtime/
│   ├── motion.py         — PendingMove, PendingJump, PendingCooldown dataclasses
│   ├── real_time_arbiter.py — RealTimeArbiter: active motions, time progression, arrival resolution, capture events
│   ├── score_tracker.py  — ScoreTracker: records moves and captures, computes score per player
│   └── game_engine.py    — GameEngine: game-over, selection, move delegation, snapshots, EventBus publishing
├── input/
│   ├── commands.py       — Command dataclasses (ClickCommand, JumpCommand, WaitCommand, PrintBoardCommand)
│   ├── board_mapper.py   — converts raw string → Command (pixel → row/col here only)
│   └── controller.py     — entry point: parses stdin, drives GameEngine
├── io/
│   ├── board_parser.py   — parse_input / load_board_csv: splits raw text or CSV into board rows and command strings
│   └── board_printer.py  — print_board: prints BoardSnapshot to stdout
├── view/
│   ├── board_renderer.py — BoardRenderer: draws board tiles and pieces using BoardSnapshot
│   ├── image_view.py     — ImageView: OpenCV tile renderer, uses BoardSnapshot + TILE_SIZE
│   ├── name_dialog.py    — ask_player_names(): tkinter dialog shown before game starts
│   ├── panel_renderer.py — PanelRenderer: draws score/move history side panel
│   ├── sprite_loader.py  — loads and caches piece sprite images
│   └── view_controller.py — ViewController: handles mouse events, selection, feedback
└── shared/
    ├── constants.py      — MOVE_DELAY_SECONDS, JUMP_DURATION_SECONDS, COOLDOWN_SECONDS, PieceType, Color, PieceState
    ├── ui_constants.py   — TILE_SIZE, WINDOW_TITLE, KEY_ESC (UI only, never used by game logic)
    ├── interfaces.py     — IBoard, IGame, IPiece abstract classes
    ├── exceptions.py     — InvalidMoveError, OutOfBoundsError, BlockedPathError, FriendlyFireError, CoolingError, MotionInProgressError
    ├── validators.py     — validate_board() for input validation
    ├── bus.py            — EventBus + EventType (PIECE_MOVED, PIECE_CAPTURED, PIECE_JUMPED, GAME_OVER)
    └── dto.py            — PieceSnapshot, BoardSnapshot, PlayerSnapshot, GameSnapshot, MoveResult (frozen=True)

server/
    ├── game_server.py    — GameServer: async WebSocket server, 2-player slot management, 30 ms game loop, move/jump/legal_moves routing
    └── serializer.py     — snapshot_to_dict / dict_to_snapshot: GameSnapshot ↔ JSON

client/
    ├── server_bridge.py  — ServerBridge: thread-safe bridge between asyncio WebSocket and OpenCV main loop
    └── run_client.py     — OpenCV client with _RemoteGame adapter, connects to server

tests/
    unit/
        test_board.py         → model layer
        test_validators.py    → RuleEngine + validate_board
        test_move_rules.py    → piece strategy classes
        test_game.py          → realtime layer (selection, scheduling, timing, jump, game-over, snapshot, score)
        test_parse_input.py   → input layer (parse_input, controller)
        test_arbiter.py       → RealTimeArbiter edge cases
        test_bus.py           → EventBus + GameEngine event publishing
        test_serializer.py    → server/serializer round-trip
        test_server.py        → server/game_server (async, mocked WebSocket)
        test_server_bridge.py → client/server_bridge (async, mocked WebSocket)
    integration/
        *.kfc                 → scenario files
        runner.py / test_integration.py → integration runner
```

## Layer Responsibilities

| Layer | Owns | Must NOT own |
|---|---|---|
| `model` | board state, piece identity, piece lifecycle, Position | pixels, click type, rendering, motion rules, timing |
| `rules` | motion rules only (read-only) | board mutation, animation, click interpretation, game-over |
| `realtime` | active motion objects, time progression, arrival resolution, capture events, game-over, score tracking | rendering, input parsing, pixel mapping |
| `input` | interpret clicks, pixel→cell mapping, stdin parsing | movement rules, board mutation, rendering, timing |
| `io` | text/CSV parsing and printing of board state | game logic, rendering, timing |
| `view` | OpenCV rendering + tkinter name dialog using BoardSnapshot | game logic, board mutation, input parsing |
| `shared` | constants, exceptions, interfaces, DTOs, EventBus, input validation | business logic of any kind |
| `server` | WebSocket server, game loop broadcasting, client slot management | rendering, pixel mapping |
| `client` | WebSocket client bridge, OpenCV main loop, remote game adapter | server logic, board mutation |

## Key Rules

- `Board` must NOT contain `is_legal`, `is_path_clear`, or `print_board` — those belong to `rules`/`realtime`
- `RuleEngine` is owned by `GameEngine`, not `Board`
- `TILE_SIZE` lives in `shared/ui_constants.py` — never in `constants.py` or game logic
- External code (tests, UI, client) must use `game.get_snapshot()` / `game.get_game_snapshot()` — never hold live `Piece` objects
- `dto.PieceSnapshot` and `dto.BoardSnapshot` are `frozen=True` dataclasses
- No `time.sleep()` in tests — manipulate `arrive_at = time.time() - 1` instead
- No pixel values inside `GameEngine`, `Board`, or `Piece`
- All internal coordinates use `Position(row, col)` — never raw tuples

## Timing Model

- Every move is scheduled with `arrive_at = time.time() + steps * MOVE_DELAY_SECONDS`
- `game.execute_pending_moves()` is called at the start of every `handle_command()` and every server tick
- Only one color can have pending moves at a time
- A piece that is pending, cooling, or airborne cannot be selected or moved
- `RealTimeArbiter` owns all timing logic — `GameEngine` only delegates to it
- `PendingCooldown` tracks `ready_at` and `started_at` for snapshot serialization

## Friendly Blocking Rule

- When scheduling a move, `_compute_actual_end` walks the path step by step
- At each cell, `_other_occupies_at` checks if a friendly piece will **end** at that cell before the moving piece arrives
- A piece that merely passes through a cell does NOT block — only a piece whose destination is that cell blocks
- If blocked at the first step, the piece stays at its start position

## Jump Mechanic

- `jump` command makes a piece airborne for `JUMP_DURATION_SECONDS`
- An airborne piece captures any enemy that arrives at its cell during the jump
- A moving piece cannot jump; a piece cannot jump twice
- Jump timing fields (`jump_started_at`) are included in `PieceSnapshot` for client animation

## EventBus

- `GameEngine` publishes events via `EventBus` on: piece moved, piece captured, piece jumped, game over
- `EventBus` is injected into `GameEngine` (defaults to a private instance)
- Tests can inject a custom bus to assert events were published

## WebSocket Protocol

Server → client messages:

| type | key fields | when |
|---|---|---|
| `assigned` | `color` | immediately on connect |
| `state` | `board`, `black`, `white`, `game_over` | every 30 ms tick |
| `legal_moves` | `cell`, `moves` | reply to client request |
| `error` | `reason` | server full |

Client → server messages:

| type | key fields | meaning |
|---|---|---|
| `join` | `username` | first message after connect |
| `move` | `from`, `to` | request piece move |
| `jump` | `cell` | request piece jump |
| `legal_moves` | `cell` | request legal destinations |

## Coordinate System

- Input: pixel coordinates `(x, y)`
- Conversion: `row = y // TILE_SIZE`, `col = x // TILE_SIZE` — done in `board_mapper` only
- Internal: always `Position(row, col)` — never raw tuples
