import time
from Game import Game

board = [['.','.','.'],['wK','.','bR'],['.','.','.']];
game = Game(board)

game.handle_command('jump 50 150')
print('jump land_at in:', round(game.pending_jumps[0].land_at - time.time(), 3), 's')

game.handle_command('click 250 150')
game.handle_command('click 50 150')
print('move arrive_at in:', round(game.pending_moves[0].arrive_at - time.time(), 3), 's')

# simulate wait 1000
time.sleep(1.0)

print('before execute - jumps:', game.pending_jumps)
game.execute_pending_moves()
print('after execute - jumps:', game.pending_jumps)
game.board.print_board()
