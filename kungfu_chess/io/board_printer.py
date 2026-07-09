from kungfu_chess.shared.dto import BoardSnapshot


def print_board(snapshot: BoardSnapshot):
    for r in range(snapshot.rows):
        print(" ".join(
            f"{p.color.value}{p.ptype.value}" if p else '.'
            for p in (snapshot.get(r, c) for c in range(snapshot.cols))
        ))
