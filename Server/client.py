import socket

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket_connect_ipv4 = "192.168.0.152"
client_socket.connect(
    (client_socket_connect_ipv4, 50000)
)

try:
    while True:
        message = input("Message: ")
        client_socket.send(message.encode("utf-8"))
        
        message_received = client_socket.recv(1024)
        print("[{0}] {1}".format(
            socket.gethostname(),
            message_received.decode("utf-8")
        ))
finally:
    client_socket.close()
