"""
Module to initialise, implement and connect a client.
"""
import sys
import socket
import client_commands


def main(args: list[str]) -> None:
    """
    Main function to connect to the server and handle client commands and server responses.

    Args:
        args (list[str]): Command-line arguments containing server address and port.

    Returns:
        None
    """

    if len(args) != 2:
        print("Error: Expecting 2 arguments: <server address> <port>", file=sys.stderr)
        return
    
    server_address = args[0]
    port = int(args[1])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        s.connect((server_address, port))
    except ConnectionRefusedError:
        print(f"Error: cannot connect to server at {server_address} and {port}.", file=sys.stderr)
        return

    while True:
        if not client_commands.waiting and not client_commands.in_game:
            try:
                user_input = input("Enter command: ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                break
            
            if user_input == "QUIT":
                break
            
            if user_input:
                msg_to_send = client_commands.handle_user_input(user_input)
                if not msg_to_send:
                    print(f"Unknown command: {user_input}")
                    continue

                s.send(msg_to_send.encode())

        server_msg = s.recv(8192).decode().strip()
        if not server_msg:
            break

        server_msg = server_msg.split("\n")
        
        wrong = False
        for msg in server_msg:
            output = client_commands.handle_server_msg(msg)
            
            if output == -1:
                print("Unknown message received from server. Exiting...")
                wrong = True
                break
            elif output == -2:
                wrong = True
            elif output is not None:
                s.send(output.encode())
        if wrong:
            break

    s.close()


if __name__ == "__main__":
    main(sys.argv[1:])
