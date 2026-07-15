import sys

if "--gui" in sys.argv:
    from kungfu_chess.realtime.game_engine import GameEngine
    from kungfu_chess.input.controller import Controller
    from kungfu_chess.model.position import Position
    from kungfu_chess.view.image_view import ImageView
    from kungfu_chess.shared.constants import Color
    import cv2

    _DEFAULT_BOARD = [
        ['bR', 'bN', 'bB', 'bK', 'bQ', 'bB', 'bN', 'bR'],
        ['bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP', 'bP'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['.', '.', '.', '.', '.', '.', '.', '.'],
        ['wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP', 'wP'],
        ['wR', 'wN', 'wB', 'wK', 'wQ', 'wB', 'wN', 'wR'],
    ]

    game = GameEngine(_DEFAULT_BOARD)
    view = ImageView()
    controller = Controller(game, board_cols=8, board_rows=8)

    while True:
        game.execute_pending_moves()
        key = view.render(game.get_snapshot())

        if key == 27 or cv2.getWindowProperty('KungFu Chess', cv2.WND_PROP_VISIBLE) < 1:
            break

        click = view.poll_click()
        if click:
            row, col = view.cell_of(*click)
            controller.handle_click(Position(row, col))

    cv2.destroyAllWindows()

else:
    from kungfu_chess.input.controller import main
    main()
