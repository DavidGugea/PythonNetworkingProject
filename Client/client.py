import socket
from ..User import user

class Client():
    def __init__(self, IPv4, PORT):
        """
        Creates a client socket including the user interaction inside the console.
        The IPv4 and the PORT are used to connect to the server socket.
        """

        # Set up the non blocking client socket
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect(
            (IPv4, PORT)
        )
        self.client_socket.setblocking(False)

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
        Accepts users input and then logs the user inside of the console.
        Ask first for the username & password. After a succesfull request, ask the user for the UID. The UID will be inside the response from the server, if the username&password registration was succesfull.
        After the complete registration, the user will be able to get all the data & communicate with the server

        **************** HEADER STYLE ****************

        Whenever the client sends data to the server we will insert a header in front of the information given from the user

        {HEADER}{BODY}

        The user will never be able to use [] inside the messages sent to the server in order to make sure that we can separate the header from the body. 

        Inside the body we will have data given from the user. It's like an HTTP/HTTPS get request.

        POSSIBLE HEADER VALUES:
        
        {CLIENT_LOGIN_INFO_USERNAME_PASSWORD} -> Used when the client is logging in with the username and password
        Body structure : {USERNAME:{0}|PASSWORD:{1}}

        {CLIENT_LOGIN_INFO_UID} -> Used when the client is logging in with the UID, after a successfull username & password response
        Body structure : {UID:{0}:|USERNAME:{1}|PASSWORD:{2}|...}

        {CLIENT_MESSAGE} -> Used when the client sends a message
        Body structure : {ADDRESS_OF_CLIENT_TO_GET_MESSAGE|{0}}


        **************** HEADER STYLE ****************
        """

        while True:
            # Ask for username/password credentials
            username = input("Username: ")
            password = input("Password: ")

            # Pack the username & password and send them to the server. 
            HEADER = "{CLIENT_LOGIN_INFO_USERNAME_PASSWORD}"
            BODY = "{USERNAME:{0}|PASSWORD:{1}}".format(
                username,
                password
            )

            # Send the data to the server and wait for a response
            self.client_socket.send(
                "{0}{1}".format(HEADER, BODY).encode("utf-8")
            )

            try:
                while True:
                    server_login_response = ""

    
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

client = Client(socket.gethostname(), 50000)
client.start()