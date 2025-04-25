"""
Module to handle actual tic-tac-toe related actions.
"""
import sys

__author__ = "Luca Napoli"


BOARD_SIZE = 3

NOUGHT = '2'
CROSS = '1'
EMPTY = '0'

Board = list[list[str]]

#############################################################
############### Private functions—do not use! ###############
#############################################################

def _player_wins_vertically(player: str, board: Board) -> bool:
    return any(
        all(board[y][x] == player for y in range(BOARD_SIZE)) 
        for x in range(BOARD_SIZE)
    )


def _player_wins_horizontally(player: str, board: Board) -> bool:
    return any(
        all(board[x][y] == player for y in range(BOARD_SIZE)) 
        for x in range(BOARD_SIZE)
    )


def _player_wins_diagonally(player: str, board: Board) -> bool:
    return (
        all(board[y][y] == player for y in range(BOARD_SIZE)) or
        all(board[BOARD_SIZE - 1 - y][y] == player for y in range(BOARD_SIZE))
    )


##########################################################
############### Public functions—use these ###############
##########################################################



def validate_move(board: str) -> tuple[int, int]:
    """
    Validates a player's move in the game board.

    Args:
        board (str): The current state of the game board represented as a string.

    Returns:
        tuple[int, int]: A tuple containing the validated column (x) and row (y) coordinates.
    """

    board_array = []
    for i in range(0, 9, 3):
        ls = list(board[i:i+3])
        board_array.append(ls)
    
    while True:
        try:
            x = int(input("Enter column: ").strip())
            y = int(input("Enter row: ").strip())
        except ValueError:
            print("(Column/Row) values must be an integer between 0 and 2", file=sys.stderr)
            continue
        
        if (x>2 or x<0) or (y>2 or y<0):
            print("(Column/Row) values must be an integer between 0 and 2", file=sys.stderr)
            continue
        
        if board_array[y][x] != EMPTY:
            if board_array[y][x] == CROSS:
                marker_character = 'X'
            else:
                marker_character = 'O'
            
            print(f"({x}, {y}) is occupied by {marker_character}.", file=sys.stderr)
            continue
        
        return x, y

def print_board(board: Board) -> None:
    """
    Prints the current state of the game board.

    Args:
        board (Board): The current state of the game board.

    Returns:
        None
    """
    
    board_array = []
    for i in range(0, 9, 3):
        ls = list(board[i:i+3])
        
        for j in range(len(ls)):
            if ls[j] == EMPTY:
                ls[j] = ' '
            
            elif ls[j] == CROSS:
                ls[j] = 'X'
            
            else:
                ls[j] = 'O'
        board_array.append(ls)
    
    for row in board_array:
        print("|".join(row))
        print("-" * 5)
    
    return


def player_wins(player: str, board: Board) -> bool:
    """Determines whether the specified player wins given the board"""
    return (
        _player_wins_vertically(player, board) or
        _player_wins_horizontally(player, board) or
        _player_wins_diagonally(player, board)
    )


def players_draw(board: Board) -> bool:
    """Determines whether the players draw on the given board"""
    return all(
        board[y][x] != EMPTY 
        for y in range(BOARD_SIZE) 
        for x in range(BOARD_SIZE)
    )