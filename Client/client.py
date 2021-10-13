import socket
from ..User import user # python -m <top_level>.Client.client

class Client():
    def __init__(self, IPv4, PORT):
        """
        Stores the IPv4 and the PORT for future connections to the server.
        We won't treat the client as a permanently open socket. Every time the client wants to communicate with the server, we will open a socket. 
        Keeping the server always open and making it a non blocking multiplex server is a good idea since the server always has to talk to multiple client sockets but never
        knows when it will get those requests, so it always has to be open.
        On the other side, the client requests can be sent with individual sockets. These sockets might or might not contain information about the client ( such as UID ).
        """

        self.IPv4 = IPv4
        self.PORT = PORT

        # For now, the user will be None
        self.user = None

    def errorMessage(self, msg):
        for i in range(3):
            print()

        print(msg)

        for i in range(3):
            print()
    
    def login(self):
        """
        Read ../Documentation/server_client_communication_bluerpint.txt 
        """

        # Start the first login steps, by asking the user for the username & password. Afterwards, in case that the input from the user was correct and the response from the server was successful, we'll ask the user about his UID ( User ID )
        self.LOGIN_USERNAME_PASSWORD()

    def LOGIN_USERNAME_PASSWORD(self):
        """
        {CLIENT_LOGIN_INFO_USERNAME_PASSWORD} -> Used when the client is logging in with the username and password
        Body structure : {USERNAME:{0}|PASSWORD:{1}}
        RESPONSE FROM THE SERVER:
        Successful:
        SERVER_LOGIN_INFO_USERNAME_PASSWORD_SUCCESSFUL_<UID>
        Username or password wrong:
        SERVER_LOGIN_INFO_USERNAME_PASSWORD_WRONG
        """

        # Client a client that will connect to the server for the duration of the login process
        login_username_password_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        login_username_password_client.connect(
            (self.IPv4, self.PORT)
        )
        login_username_password_client.setblocking(True)

        # Ask for username/password credentials
        username = input("Username: ")
        password = input("Password: ")

        # Pack the username & password and send them to the server. 
        HEADER = "{CLIENT_LOGIN_INFO_USERNAME_PASSWORD}"
        BODY = "{{USERNAME:{0}|PASSWORD:{1}}}".format(
            username,
            password
        )

        # Send the data to the server and wait for a response
        login_username_password_client.send(
            "{0}{1}".format(HEADER, BODY).encode("utf-8")
        )

        # Store here the response from the server
        SERVER_RESPONSE = None
        
        while True:
            try:
                server_login_info_username_password_response = login_username_password_client.recv(1024)
                server_login_info_username_password_response.decode("utf-8")

                if server_login_info_username_password_response:
                    SERVER_RESPONSE = server_login_info_username_password_response
                    break
                else:
                    continue
            except Exception:
                pass
            
        print("PRINTING SERVER RESPONSE")
        print(SERVER_RESPONSE)

    def register(self):
        print("REGISTERING")

    def start(self):
        """
        Starts the interaction with the user from the console ( login, register, sending messages, etc. )
        """

        # Make the user register/login
        print("1. Login")
        print("2. Register")

        while True:
            user_input = input("Choice ( 1 or 2 ) -- > ")

            try:
                user_input = int(user_input)

                if user_input == 1:
                    self.login()
                elif user_input == 2:
                    self.register()
                else:
                    self.errorMessage("Input 1 or 2.")
                    continue

                for i in range(5):
                    print()

                break
            except ValueError:
                self.errorMessage("You must input a number.")

client = Client(socket.gethostname(), 55555)
client.start()