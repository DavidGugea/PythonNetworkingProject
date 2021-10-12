import socket
import selectors

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((socket.gethostname(), 50000))
server.setblocking(False)
server.listen(20)

selector = selectors.DefaultSelector()
selector.register(server, selectors.EVENT_READ, accept)

def accept(selector, server_socket):
    clientsocket_token, clientsocket_address = server_socket.accept()
    clientsocket_token.setblocking(False)
    selector.register(clientsocket_token, selectors.EVENT_READ, message)

def message(selector, clientsocket_token):
    message = clientsocket_token.recv(1024)
    ip = clientsocket_token.getpeername()[0]

    if message:
        print("[{0}] {1}".format(ip, message.decode("utf-8")))
    else:
        print("Connection to {0} closed".format(ip))

        selector.unregister(client)
        clientsocket_token.close()

while True:
    for key, mask in selector.select():
        key.data(selector, key.fileobj)
