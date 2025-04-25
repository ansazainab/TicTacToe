"""
Module to handle user-input commands and messages received from the server.
This also contains all relevant variables/attributes of a client.
"""
import sys
import game

client_username = ""
current_room = None
player_1 = ""
player_2 = ""
current_turn = ""
is_player = False
game_commenced = False
place_queue = None
board = "000000000"

in_game = False
waiting = False
tmp_room_type = ""
tmp_room_mode = ""


def handle_user_input(user_input: str) -> str | None:
    """
    Executes a command based on the user input, handling commands related to user actions 
    such as logging in, registering, room management, and game actions.

    Args:
        user_input (str): The command input by the user.

    Returns:
        str | None:
            - A string formatted message for the server
            - None if the command is unknown.
    """

    global board, client_username, tmp_room_type, current_room, tmp_room_mode, waiting
    
    if user_input == "LOGIN":
        username = input("Enter username: ").strip()
        password = input("Enter password: ").strip()
        client_username = username
        msg = f"LOGIN:{username}:{password}\n"
        return msg   
    
    if user_input == "REGISTER":
        while True:
            username = input("Enter username: ").strip()
            if len(username) > 20:
                print("Error: username length limitation is 20 characters.", file=sys.stderr)
                continue
            break
        
        while True:
            password = input("Enter password: ").strip()
            if len(password) > 20:
                print("Error: password length limitation is 20 characters.", file=sys.stderr)
                continue
            break
        
        msg = f"REGISTER:{username}:{password}\n"
        client_username = username
        return msg
    
    if user_input == "ROOMLIST":
        while True:
            room_type = input("Do you want to have a room list as player or viewer? (Player/Viewer) ").strip().upper()
            if room_type != "PLAYER" and room_type != "VIEWER":
                print("Error: Please input a valid mode.", file=sys.stderr)
                continue
            break
        
        msg = f"ROOMLIST:{room_type}\n"
        tmp_room_type = room_type
        return msg
    
    if user_input == "CREATE":
        room_name = input("Enter room name you want to create: ").strip()
        msg = f"CREATE:{room_name}\n"
        current_room = room_name
        return msg
    
    if user_input == "JOIN":
        room_name = input("Enter room name you want to join: ").strip()
        while True:
            mode = input("You wish to join the room as: (Player/Viewer) ").strip().upper()
            if mode != "PLAYER" and mode != "VIEWER":
                print("Unknown input")
                continue
            break
        
        msg = f"JOIN:{room_name}:{mode}\n"
        current_room = room_name
        tmp_room_mode = mode
        return msg
    
    if user_input == "PLACE":
        x, y = game.validate_move(board)
        msg = f"PLACE:{x}:{y}\n"
        waiting = True
        return msg
    
    if user_input == "FORFEIT":
        msg = "FORFEIT\n"
        return msg
    
    return None


def handle_server_msg(server_msg: str) -> str | int | None:
    """
    Processes messages received from the server, updating the client state based on the message content.
    
    Args:
        server_msg (str): The message received from the server.

    Returns:
        str | int | None:
            - A string message to send back to the server if required
            - -1 if unknown server message or -2 if an EOFError occured
            - None if no message needs to be sent back
    """

    global client_username, tmp_room_type, current_room, waiting, game_commenced
    global tmp_room_mode, in_game, current_turn, is_player, board
    global player_1, player_2

    if "BADAUTH" in server_msg:
        print("Error: You must be logged in to perform this action", file=sys.stderr)
        waiting = False
        current_room = None
        return
    
    if "NOROOM" in server_msg:
        waiting = False
        return

    if "LOGIN" in server_msg:
        if "ACKSTATUS:0" in server_msg:
            print(f"Welcome {client_username}")
        
        elif "ACKSTATUS:1" in server_msg:
            print(f"Error: User {client_username} not found", file=sys.stderr)
            client_username = ""
        
        elif "ACKSTATUS:2" in server_msg:
            print(f"Error: Wrong password for user {client_username}", file=sys.stderr)
            client_username = ""
        return
    
    if "REGISTER" in server_msg:
        if "ACKSTATUS:0" in server_msg:
            print(f"Successfully created user account {client_username}")
        
        elif "ACKSTATUS:1" in server_msg:
            print(f"Error: User {client_username} already exists", file=sys.stderr)
            client_username = ""
        return
    
    if "ROOMLIST" in server_msg:
        if "ACKSTATUS:0" in server_msg:
            _, _, _, rooms = server_msg.split(":")
            print(f"Room available to join as {tmp_room_type}: {rooms}")
        
        elif "ACKSTATUS:1" in server_msg:
            print("Error: Please input a valid mode.", file=sys.stderr)
        return
    
    if "CREATE" in server_msg:
        if "ACKSTATUS:0" in server_msg:
            print(f"Successfully created room {current_room}")
            print("Waiting for other player...")
            waiting = True
            in_game = True
        
        elif "ACKSTATUS:1" in server_msg:
            print(f"Error: Room {current_room} is invalid", file=sys.stderr)
            current_room = None
        
        elif "ACKSTATUS:2" in server_msg:
            print(f"Error: Room {current_room} already exists", file=sys.stderr)
            current_room = None
        
        elif "ACKSTATUS:3" in server_msg:
            print(f"Error: Server already contains a maximum of 256 rooms", file=sys.stderr)
            current_room = None
        return
    
    if "JOIN" in server_msg:
        if "ACKSTATUS:0" in server_msg:
            print(f"Successfully joined room {current_room} as a {tmp_room_mode.lower()}")
            if tmp_room_mode == "PLAYER":
                in_game = True
                waiting = (current_turn != client_username)
            elif tmp_room_mode == "VIEWER":
                waiting = True
        
        elif "ACKSTATUS:1" in server_msg:
            print(f"Error: No room named {current_room}", file=sys.stderr)
            current_room = None
        
        elif "ACKSTATUS:2" in server_msg:
            print(f"Error: The room {current_room} already has 2 players", file=sys.stderr)
            current_room = None
        return
    
    if "BEGIN" in server_msg:
        _, player_1, player_2 = server_msg.split(":")
        current_turn = player_1
        game_commenced = True
        waiting = (current_turn != client_username)
        print(f"match between {player_1} and {player_2} will commence, it is currently {player_1}'s turn.")
        
        if client_username == player_1 or client_username == player_2:
            is_player = True
            in_game = True
        if client_username == current_turn:
            while True:
                try:
                    user_input = input("Enter game command: ").strip()
                except EOFError:
                    return -2
                except KeyboardInterrupt:
                    return -2
                
                if user_input:
                    msg_to_send = handle_user_input(user_input)
                    if not msg_to_send:
                        print(f"Unknown command: {user_input}")
                        continue
                    
                    return msg_to_send
        return
    
    if "INPROGRESS" in server_msg:
        _, player_1, player_2 = server_msg.split(":")
        current_turn = player_1
        game_commenced = True
        is_player = False
        print(f"Match between {player_1} and {player_2} is currently in progress, it is {player_1}'s turn")
        return
    
    if "BOARDSTATUS" in server_msg:
        _, board = server_msg.split(":")
        game.print_board(board)

        if current_turn == player_1:
            current_turn = player_2
        else:
            current_turn = player_1

        if not is_player:
            print(f"It is {current_turn}'s turn.")
        
        elif client_username == current_turn:
            waiting = False
            print("It is the current player's turn")

            while True:
                try:
                    user_input = input("Enter game command: ").strip()
                except EOFError:
                    return -2
                except KeyboardInterrupt:
                    return -2
                
                if user_input:
                    msg_to_send = handle_user_input(user_input)
                    if not msg_to_send:
                        print(f"Unknown command: {user_input}")
                        continue
                    
                    return msg_to_send
        
        else:
            waiting = True
            print("It is the opposing player's turn")
        return
    
    if "GAMEEND" in server_msg:
        count = 0
        i = 0
        while i < len(server_msg):
            if server_msg[i] == ":":
                count += 1
            i += 1
        
        if count == 2:
            _, board, code = server_msg.split(":")
            if code == '1':
                print("Game ended in a draw")
        
        elif count == 3:
            _, board, code, winner = server_msg.split(":")
            if code == '0':
                if is_player:
                    if client_username == winner:
                        print("Congratulations, you won!")
                    else:
                        print("Sorry you lost. Good luck next time.")
                else:
                    print(f"{winner} has won this game")
            
            elif code == '2':
                print(f"{winner} won due to the opposing player forfeiting")
        
        current_room = None
        player_1 = ""
        player_2 = ""
        current_turn = ""
        is_player = False
        game_commenced = False
        board = "000000000"
        waiting = False
        in_game = False
        return
    
    return -1