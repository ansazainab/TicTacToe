"""
Module to initialise, implement and bind the main server.
"""
import sys
import socket
import os
import json
import select
from server_commands import *
import variables


def check_config(args: list[str]) -> tuple[int, str] | int:
    """
    Validates the server configuration JSON file and checks for required keys.

    Args:
        args (list[str]): A list containing a single string, the path to the server config file.

    Returns:
        tuple[int, str] | int: 
            - A tuple `(port, userDatabase)` if valid.
            - -1 if errors occur (e.g., file not found, invalid JSON, or missing keys).
    """
    
    if len(args) != 1:
        print("Error: Expecting 1 argument: <server config path>.", file=sys.stderr)
        return -1

    server_config_path = args[0]
    server_config_path = os.path.expanduser(server_config_path)
    try:
        json_file = open(server_config_path, "r")
        config_data = json.load(json_file)
    except FileNotFoundError:
        print(f"Error: {args[0]} doesn't exist.", file=sys.stderr)
        return -1
    except json.JSONDecodeError:
        print(f"Error: {args[0]} is not in a valid JSON format.", file=sys.stderr)
        return -1

    missing_keys = []
    port = config_data.get("port")
    if port != None:
        if not isinstance(port, int):
            return -1
        if port < 1024 or port > 65535:
            print("Error: port number out of range", file=sys.stderr)
            return -1
    else:
        missing_keys.append("port")

    userDatabase = config_data.get("userDatabase")
    if userDatabase is None:
        missing_keys.append("userDatabase")

    if len(missing_keys) == 1:
        print(f"Error: {args[0]} missing key(s): {missing_keys[0]}", file=sys.stderr)
        return -1
    elif len(missing_keys) == 2:
        missing_keys.sort()
        print(f"Error: {args[0]} missing key(s): {missing_keys[0]}, {missing_keys[1]}", file=sys.stderr)
        return -1
    
    return port, userDatabase


def check_userdb(userDb: str) -> list[dict[str, str]] | int:
    """
    Validates the user database JSON file and ensures it contains correctly formatted user records.

    Args:
        userDb (str): The path to the user database JSON file.

    Returns:
        list[dict[str, str]] | int: 
            - A list of user records if valid.
            - -1 if errors occur (e.g., file not found, invalid JSON, or incorrect formats).
    """

    try:
        json_file = open(os.path.expanduser(userDb), "r")
        user_config_data = json.load(json_file)
        json_file.close()
    except FileNotFoundError:
        print(f"Error: {userDb} doesn't exist.", file=sys.stderr)
        return -1
    except json.JSONDecodeError:
        print(f"Error: {userDb} is not in a valid JSON format.", file=sys.stderr)
        return -1
    
    if not isinstance(user_config_data, list):
        print(f"Error: {userDb} is not a JSON array.", file=sys.stderr)
        return -1
    
    for item in user_config_data:
        keyss = list(item.keys())
        if len(keyss) != 2:
            print(f"Error: {userDb} contains invalid user record formats.", file=sys.stderr)
            return -1
        if not (("username" in keyss) and ("password" in keyss)):
            print(f"Error: {userDb} contains invalid user record formats.", file=sys.stderr)
            return -1
    
    return user_config_data


def server_loop(server_sock: socket.socket) -> None:
    """
    Manages the server's main loop, handling client connections and messages.

    Args:
        server_sock (socket.socket): The server's main socket, listening for new connections.

    Returns:
        None
    """

    read_socks = {server_sock}
    
    while True:
        select_read_socks, _, select_except_socks = select.select(read_socks, (), ())
        
        for sock in select_read_socks:
            if sock is server_sock:
                client_sock, client_addr = sock.accept()
                client_sock.setblocking(False)
                read_socks.add(client_sock)
            else:
                try:
                    client_msg = sock.recv(8192)
                except ConnectionResetError:
                    actual_forfeit(sock)
                    read_socks.remove(sock)
                    if sock in variables.authenticated_socks:
                        variables.authenticated_socks.remove(sock)
                    if sock in variables.username_socks:
                        del variables.username_socks[sock]
                    continue
                
                if not client_msg:
                    actual_forfeit(sock)
                    read_socks.remove(sock)
                    if sock in variables.authenticated_socks:
                        variables.authenticated_socks.remove(sock)
                    if sock in variables.username_socks:
                        del variables.username_socks[sock]
                    continue
                
                client_msg = client_msg.decode().strip()

                viewer = False
                for details in variables.room_details.values():
                    if sock in details["viewers"]:
                        viewer = True
                        break
                if viewer:
                    continue
                
                if "LOGIN" in client_msg:
                    login(sock, client_msg)
                
                elif "REGISTER" in client_msg:
                    register(sock, client_msg)
                
                elif "ROOMLIST" in client_msg:
                    roomlist(sock, client_msg)
                
                elif "CREATE" in client_msg:
                    create(sock, client_msg)
                
                elif "JOIN" in client_msg:
                    join(sock, client_msg)
                
                elif "PLACE" in client_msg:
                    place(sock, client_msg)
                
                elif "FORFEIT" in client_msg:
                    forfeit(sock)

        for sock in select_except_socks:
            read_socks.remove(sock)
            sock.close()


def main(args: list[str]) -> None:
    """
    Initializes the server by loading configurations, setting up the socket, 
    and entering the main server loop.

    Args:
        args (list[str]): Command-line arguments, where the first element is the server config path.

    Returns:
        None
    """

    if check_config(args) != -1:
        port, userDatabase = check_config(args)
    else:
        return

    if check_userdb(userDatabase) != -1:
        user_config_data = check_userdb(userDatabase)
    else:
        return

    variables.userDatabase = userDatabase
    variables.user_config_data = user_config_data

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", port))
    s.listen()
    s.setblocking(False)
    
    with s:
        try:
            server_loop(s)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main(sys.argv[1:])