import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((sockte.gethostname(), 50000))

try:
    wihle True:
        message = input("Message -- > ")
        client.send(message.encode("utf-8"))
finally:
    client.close()
