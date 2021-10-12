import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket_bind_ipv4 = "192.168.0.152"
server_socket.bind(
    (server_socket_bind_ipv4, 50000)
)
server_socket.listen(20)

try:
    while True:
        clientsocket_token, clientsocket_address = server_socket.accept()
        while True:
            data = clientsocket_token.recv(1024)
            if not data:
                clientsocket_token.close()
                break
                
            print("[{0}] {1}".format(clientsocket_address[0], data.decode("utf-8")))
            message = input("Response : ")
            clientsocket_token.send(message.encode("utf-8"))
finally:
    server_socket.close()

"""
C way of handling non blocking I/O sockets with >>select<<
>>Windows can only use select with sockets, it doesn't work on files<<

ready_to_read, ready_to_write, in_error = \
               select.select(
                  potential_readers,
                  potential_writers,
                  potential_errs,
                  timeout)
"""
