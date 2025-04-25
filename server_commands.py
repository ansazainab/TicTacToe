"""
Module to handle all commands and messages from a client and send relevant protocol messages.
"""
import os
import json
import bcrypt
import re
import game
import variables
import socket


def login(sock: socket.socket, client_msg: str) -> None:
    """
    Handles user login by verifying credentials and updating authenticated sockets.

    Args:
        sock (socket.socket): The client socket sending the login request.
        client_msg (str): The login message containing the username and password.

    Returns:
        None
    """

    try:
        _, username, password = client_msg.split(":")
    except ValueError:
        sock.send("LOGIN:ACKSTATUS:3\n".encode())
        return
    
    ufound = False
    for item in variables.user_config_data:
        if item.get("username") == username:
            ufound = True
            
            if bcrypt.checkpw(password.encode(), item.get("password").encode()):
                sock.send("LOGIN:ACKSTATUS:0\n".encode())
                variables.authenticated_socks.append(sock)
                variables.username_socks[sock] = username
                break
            else:
                sock.send("LOGIN:ACKSTATUS:2\n".encode())
                break
    
    if not ufound:
        sock.send("LOGIN:ACKSTATUS:1\n".encode())
        return
    
    return


def register(sock: socket.socket, client_msg: str) -> None:
    """
    Registers a new user by storing their credentials and updating the user database.

    Args:
        sock (socket.socket): The client socket sending the registration request.
        client_msg (str): The registration message containing the username and password.

    Returns:
        None
    """

    try:
        _, username, password = client_msg.split(":")
    except ValueError:
        sock.send("REGISTER:ACKSTATUS:2\n".encode())
        return
    
    ufound = False
    for item in variables.user_config_data:
        if item.get("username") == username:
            sock.send("REGISTER:ACKSTATUS:1\n".encode())
            ufound = True
            break
    
    if not ufound:
        hashedpw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        new_user = {"username": username, "password": hashedpw.decode()}
        variables.user_config_data.append(new_user)
        
        json_file = open(os.path.expanduser(variables.userDatabase), 'w')
        json.dump(variables.user_config_data, json_file, indent=3)
        json_file.close()
        sock.send("REGISTER:ACKSTATUS:0\n".encode())
    
    return


def roomlist(sock: socket.socket, client_msg: str) -> None:
    """
    Sends a list of available rooms based on the requested type (PLAYER or VIEWER).

    Args:
        sock (socket.socket): The client socket requesting the room list.
        client_msg (str): The message containing the room list request and type.

    Returns:
        None
    """

    if sock not in variables.authenticated_socks:
        sock.send("BADAUTH\n".encode())
        return
    
    try:
        _, room_type = client_msg.split(":")
    except ValueError:
        sock.send("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    
    if room_type != "PLAYER" and room_type != "VIEWER":
        sock.send("ROOMLIST:ACKSTATUS:1\n".encode())
        return
    
    if room_type == "PLAYER":
        player_rooms = []
        for room, info in variables.room_details.items():
            if len(info["players"]) < 2:
                player_rooms.append(room)
        rooms = ",".join(player_rooms)
    else:
        viewer_rooms = list(variables.room_details.keys())
        rooms = ",".join(viewer_rooms)
    
    msg = f"ROOMLIST:ACKSTATUS:0:{rooms}\n"
    sock.send(msg.encode())
    return


def create(sock: socket.socket, client_msg: str) -> None:
    """
    Creates a new game room with the specified name if valid and not already existing.

    Args:
        sock (socket.socket): The client socket requesting to create a room.
        client_msg (str): The message containing the room creation request and room name.

    Returns:
        None
    """

    if sock not in variables.authenticated_socks:
        sock.send("BADAUTH\n".encode())
        return
    
    try:
        _, room_name = client_msg.split(":")
    except ValueError:
        sock.send("CREATE:ACKSTATUS:4\n".encode())
        return
    
    good_chars = '^[A-Za-z0-9- _]+$'
    if not bool(re.match(good_chars, room_name)) or len(room_name)>20:
        sock.send("CREATE:ACKSTATUS:1\n".encode())
        return
    
    if room_name in variables.room_details:
        sock.send("CREATE:ACKSTATUS:2\n".encode())
        return
    
    if len(variables.room_details)==256:
        sock.send("CREATE:ACKSTATUS:3\n".encode())
        return
    
    variables.room_details[room_name] = {"players": [sock], "viewers": []}
    variables.room_details[room_name]["commenced"] = False
    sock.send("CREATE:ACKSTATUS:0\n".encode())
    return


def place_pending_msgs(room_name: str) -> None:
    """
    Processes and places any pending messages for the current player in the specified room.

    Args:
        room_name (str): The name of the room for which to place pending messages.

    Returns:
        None
    """

    room = variables.room_details[room_name]
    player_sock = None
    for soc, username in variables.username_socks.items():
        if room["current_turn"] == username:
            player_sock = soc
            break
    
    if player_sock in variables.place_queue:
        msg_queue = variables.place_queue[player_sock]
        
        if msg_queue:
            place_msg = msg_queue.pop(0)
            place(player_sock, place_msg)

        if not msg_queue:
            del variables.place_queue[player_sock]
    
    return


def join(sock: socket.socket, client_msg: str) -> None:
    """
    Handles a request for a client to join a game room, either as a player or a viewer.
    Also starts the game if 2 players have joined.

    Args:
        sock (socket.socket): The socket associated with the client attempting to join.
        client_msg (str): The message containing the room name and mode (PLAYER or VIEWER).

    Returns:
        None
    """

    if sock not in variables.authenticated_socks:
        sock.send("BADAUTH\n".encode())
        return
    
    try:
        _, room_name, mode = client_msg.split(":")
    except ValueError:
        sock.send("JOIN:ACKSTATUS:3\n".encode())
        return
    
    if mode != "PLAYER" and mode != "VIEWER":
        sock.send("JOIN:ACKSTATUS:3\n".encode())
        return
    
    if room_name not in variables.room_details:
        sock.send("JOIN:ACKSTATUS:1\n".encode())
        return
    
    if mode == "PLAYER":
        if len(variables.room_details[room_name]["players"]) >= 2:
            sock.send("JOIN:ACKSTATUS:2\n".encode())
            return
        if sock not in variables.room_details[room_name]["players"]:
            variables.room_details[room_name]["players"].append(sock)
    
    elif mode == "VIEWER":
        if sock not in variables.room_details[room_name]["viewers"]:
            variables.room_details[room_name]["viewers"].append(sock)

    sock.send("JOIN:ACKSTATUS:0\n".encode())
    
    if mode == "VIEWER" and variables.room_details[room_name]["commenced"]:
        cplayer = variables.room_details[room_name]["current_turn"]
        if cplayer == variables.username_socks[variables.room_details[room_name]["players"][0]]:
            oplayer = variables.username_socks[variables.room_details[room_name]["players"][1]]
        else:
            oplayer = variables.username_socks[variables.room_details[room_name]["players"][0]]
        sock.send(f"INPROGRESS:{cplayer}:{oplayer}\n".encode())
    
    if not variables.room_details[room_name]["commenced"]:
        if len(variables.room_details[room_name]["players"]) == 2:
            player1 = variables.username_socks[variables.room_details[room_name]["players"][0]]
            player2 = variables.username_socks[variables.room_details[room_name]["players"][1]]
            
            for s in variables.room_details[room_name]["players"]:
                s.send(f"BEGIN:{player1}:{player2}\n".encode())
            for s in variables.room_details[room_name]["viewers"]:
                s.send(f"BEGIN:{player1}:{player2}\n".encode())
            
            variables.room_details[room_name]["current_turn"] = player1
            variables.room_details[room_name]["board"] = "000000000"
            variables.room_details[room_name]["commenced"] = True

            place_pending_msgs(room_name)
    
    return


def place(sock: socket.socket, client_msg: str) -> None:
    """
    Processes a player's move in the game, updating the game board and handling turn logic.
    Also notifies all participants of the status of the game.

    Args:
        sock (socket.socket): The socket associated with the player making the move.
        client_msg (str): The message containing the coordinates (x, y) of the move.

    Returns:
        None
    """

    if sock not in variables.authenticated_socks:
        sock.send("BADAUTH\n".encode())
        return
    
    username = variables.username_socks[sock]
    
    room_name = None
    for room, details in variables.room_details.items():
        if sock in details["players"]:
            room_name = room
            break
    
    if not room_name:
        sock.send("NOROOM\n".encode())
        return
    
    room = variables.room_details[room_name]
    if not room["commenced"] or room["current_turn"] != username:
        if sock not in variables.place_queue:
            variables.place_queue[sock] = []
        variables.place_queue[sock].append(client_msg)
        return
    
    _, x, y = client_msg.split(":")
    x = int(x)
    y = int(y)
    board_string = room["board"]
    board = []
    for i in range(0, 9, 3):
        ls = list(board_string[i:i+3])
        board.append(ls)
    
    if username == variables.username_socks[room["players"][0]]:
        mark = '1'
    else:
        mark = '2'
    board[y][x] = mark
    
    board_string = ""
    for row in board:
        for place in row:
            board_string += place
    
    room["board"] = board_string
    
    if game.player_wins(mark, board):
        for s in room["players"]:
            s.send(f"GAMEEND:{board_string}:0:{username}\n".encode())
        for s in room["viewers"]:
            s.send(f"GAMEEND:{board_string}:0:{username}\n".encode())
        del variables.room_details[room_name]
        return
    
    if game.players_draw(board):
        for s in room["players"]:
            s.send(f"GAMEEND:{board_string}:1\n".encode())
        for s in room["viewers"]:
            s.send(f"GAMEEND:{board_string}:1\n".encode())
        del variables.room_details[room_name]
        return
    
    if username == variables.username_socks[room["players"][0]]:
        room["current_turn"] = variables.username_socks[room["players"][1]]
    else:
        room["current_turn"] = variables.username_socks[room["players"][0]]
    
    for s in room["players"]:
        s.send(f"BOARDSTATUS:{board_string}\n".encode())
    for s in room["viewers"]:
        s.send(f"BOARDSTATUS:{board_string}\n".encode())

    place_pending_msgs(room_name)
    
    return


def actual_forfeit(sock: socket.socket) -> None:
    """
    Handles a player's forfeiture, determining the winner and notifying all participants of
    the game ending.

    Args:
        sock (socket.socket): The socket associated with the player forfeiting.

    Returns:
        None
    """

    room_name = None
    for room, details in variables.room_details.items():
        if sock in details["players"]:
            room_name = room
            break
    
    if not room_name:
        return
    
    room = variables.room_details[room_name]
    if not room["commenced"]:
        del variables.room_details[room_name]
        return
    
    if sock == room["players"][0]:
        winner = room["players"][1]
    else:
        winner = room["players"][0]
    
    for s in room["players"]:
        try:
            s.send(f"GAMEEND:{room["board"]}:2:{variables.username_socks[winner]}\n".encode())
        except ConnectionResetError:
            continue
    
    for s in room["viewers"]:
        try:
            s.send(f"GAMEEND:{room["board"]}:2:{variables.username_socks[winner]}\n".encode())
        except ConnectionResetError:
            continue
    del variables.room_details[room_name]

    return


def forfeit(sock: socket.socket) -> None:
    """
    Performs authentication and error checks on a forfeit message sent by a user and
    handles it by calling the actual_forfeit() method.

    Args:
        sock (socket.socket): The socket associated with the player forfeiting.

    Returns:
        None
    """

    if sock not in variables.authenticated_socks:
        sock.send("BADAUTH\n".encode())
        return
    
    room_name = None
    for room, details in variables.room_details.items():
        if sock in details["players"]:
            room_name = room
            break
    
    if not room_name:
        sock.send("NOROOM\n".encode())
        return
    
    actual_forfeit(sock)
    
    return