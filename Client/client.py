import socket  # Use the socket module in order to connect to the server
from ..User.user import User  # From outside toplevel > python -m <top_level>.Client.client
import sys  # Close the client when needed
from concurrent import \
    futures  # Used with the communication socket. 2 workers are assigned to a thread pool executor. One worker works with the input, the other receives messages from the server.
from ctypes import get_errno


class InputEmptyException(Exception):
    def __init__(self, error_msg=None):
        """Raise this exception when you are asking the user for an input and the input remains empty"""
        if not error_msg:
            self.error_msg = "Your input can't be empty"
        else:
            self.error_msg = error_msg


class InputOutOfBounds(Exception):
    def __init__(self, min=None, max=None, error_msg=None):
        """
            Raise this exception when you are asking the user for an input and the input exceeds certain limits.
            If you give the min and max values, this exception will create an error message using them.
            If you give the error_msg value, you will be able to create your own custom message
        """
        if min and max:
            self.error_msg = "Your input is exceeding certain limits >> Min : {0} | Max : {1} <<".format(
                min, max
            )
        else:
            self.error_msg = error_msg


class InputUnallowedCharacters(Exception):
    def __init__(self, error_msg=None, unallowed_characters_tuple=('{', '}')):
        if error_msg:
            self.error_msg = error_msg
        else:
            self.error_msg = "Your input contains unallowed characters. The unallowed characters are : {0}".format(
                unallowed_characters_tuple)


class InputUnknownCommand(Exception):
    def __init__(self, error_msg=None):
        if error_msg:
            self.error_msg = error_msg
        else:
            self.error_msg = "Unknown command. Try again."


class Client:
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

    def errorMessage(self, customException=None, error_msg="Error"):
        for i in range(3):
            print()

        if customException:
            print(customException.error_msg)
        else:
            print(error_msg)

        for i in range(3):
            print()

    def login(self):
        """
        Read ../Documentation/server_client_communication_bluerpint.txt 
        """

        # Start the first login step, by asking the user for the username & password. Afterwards, in case that the input from the user was correct and the response from the server was successful, we'll ask the user about his UID ( User ID )
        SERVER_LOGIN_USERNAME_PASSWORD_RESPONSE = None  # Store the server response of the first step inside this variable
        while True:
            SERVER_LOGIN_USERNAME_PASSWORD_RESPONSE = self.LOGIN_USERNAME_PASSWORD()

            # Depending on the server response, close the client or go to the next step of the login where the user is asked about their UID
            if SERVER_LOGIN_USERNAME_PASSWORD_RESPONSE == "SERVER_LOGIN_INFO_USERNAME_PASSWORD_WRONG":
                # Inform the user about the wrong credentials 
                self.errorMessage(error_msg="Wrong username and/or password")
                continue
            else:
                break

        # Start the second login step, by asking the user for the UID.
        UID = SERVER_LOGIN_USERNAME_PASSWORD_RESPONSE.split("_")[
            -1]  # SERVER_LOGIN_INFO_USERNAME_PASSWORD_SUCCESSFUL_<UID>

        # Get the user data from the login with the uid
        USER_DATA = self.LOGIN_UID(UID)

        self.user = User(
            USER_DATA["UID"],
            USER_DATA["Username"],
            USER_DATA["Password"],
            USER_DATA["FirstName"],
            USER_DATA["LastName"],
            USER_DATA["Age"],
            USER_DATA["City"],
            USER_DATA["PostalCode"],
            USER_DATA["StreetName"],
            USER_DATA["HouseNumber"],
            USER_DATA["Salary"]
        )

        # Allow the user to start communicating with other clients
        self.start_communicating()

    def start_communicating(self):
        """
        Allow the user to start communicating with other clients
        """

        # Create a non blocking client socket and connect it to the server
        communication_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        communication_socket.connect(
            (self.IPv4, self.PORT)
        )
        communication_socket.setblocking(False)

        # Use the communication socket to send the username of the client to the server so it can be registered by the server inside a dictionary that contains the address of the client as well
        HEADER = "{CLIENT_COMMUNICATION_DATA}"
        BODY = "{{{0}}}".format(self.user.Username)
        communication_socket_client_username = "{0}{1}".format(
            HEADER, BODY
        )

        communication_socket.send(communication_socket_client_username.encode("utf-8"))

        # Let the user communicate with other sockets
        for i in range(3):
            print()

        print("-" * 25)

        print("Info")
        print("Send message to a username > 'username_your message'")
        print("Get your data > 'getData'")
        print("Exit > 'exit'")

        print("-" * 25)

        for i in range(3):
            print()

        # Create a thread pool executor and assign 2 workers to it. One worker must operate the user input and the other one should receive data from the server. We are doing this so we don't have to wait for the user input before seeing the messages that we got from the server.
        self.thread_pool_executor = futures.ThreadPoolExecutor(max_workers=2)
        self.thread_pool_executor_user_exit = False  # If this value is changed to true then we should stop trying to receive messages from the server
        self.thread_pool_executor.submit(self.communicationSocketThreadWorker_Input, communication_socket)
        self.thread_pool_executor.submit(self.communicationSocketThreadWorker_Recv, communication_socket)
        self.thread_pool_executor.shutdown(True)

    def communicationSocketThreadWorker_Input(self, communication_socket):
        """
        Used as a worker for the communication socket. This worker will handle the user input.
        """
        while True:
            try:
                user_input = input("> ")

                # Custom error handling
                if not user_input:
                    raise InputEmptyException()
                elif ("{" in user_input) or ("}" in user_input):
                    raise InputUnallowedCharacters()
                elif (len(user_input.split("_")) != 2) and (user_input != "getData" and user_input != "exit"):
                    raise InputUnknownCommand()

                # Look at all the different options
                if user_input == "getData":
                    print(self.user.get_data())
                elif user_input == "exit":
                    self.thread_pool_executor_user_exit = True
                    sys.exit(0)  # Closes the input worker thread
                else:
                    """
                    Send the message to the server
                    When the client wants to send data to the server:

                    CLIENT : {CLIENT_MESSAGE}{<SENDER_USERNAME>_<RECEIVER_USERNAME>_<MESSAGE>}

                    In case that the username doesn't exist:
                    SERVER : {CLIENT_MESSAGE_ERROR_USERNAME_NOT_FOUND}
                    """

                    HEADER = "{CLIENT_MESSAGE}"
                    receiver_username, message = user_input.split("_")
                    body_message = "{0}_{1}_{2}".format(self.user.Username, receiver_username, message)
                    BODY = "{{{0}}}".format(body_message)
                    client_message = "{0}{1}".format(
                        HEADER, BODY
                    )

                    communication_socket.send(
                        client_message.encode("utf-8")
                    )

                    """
                    We are going to add a timeout here since after an input we are trying to use .recv() to read something from the buffer that we got from the server.
                    The problem is that if we don't put a timeout before reading the buffer, we'll skip the .recv() since the server needed more time to transfer the message to the client socket.
                    This would mean that we would have another input and >afterwards< we would read the buffer.
                    By setting a timeout on the communication socket we can ensure that we'll give the server enough time to process the given information and return it back to the client
                    """
                    communication_socket.settimeout(0.05)
            except (InputEmptyException, InputUnallowedCharacters, InputUnknownCommand) as e:
                self.errorMessage(e)

    def communicationSocketThreadWorker_Recv(self, communication_socket):
        """
        Used as a worker for the communication socket. This worker will handle the messages received from the server
        """
        while not self.thread_pool_executor_user_exit:
            try:
                server_message = communication_socket.recv(1024).decode("utf-8")

                # We add the end to be a new line and a > char because the message that we get from the server will collide with the user input and the user won't understand anymore where to write his input.
                message_end = "\n> "
                if server_message == "{CLIENT_MESSAGE_ERROR_USERNAME_NOT_FOUND}":
                    print("Username not found. We couldn't send the message", end=message_end)
                elif server_message.startswith("{MESSAGE_FROM_CLIENT}"):
                    # Extract the message from the server
                    # SERVER: {MESSAGE_FROM_CLIENT}{<Sender_username>_<message>;<Receiver_Addr>}
                    server_message_body = server_message[server_message.index("}") + 2:-1].split(";")

                    server_receiver_client_token_raddr = server_message_body[1]
                    sender_username, sender_message = server_message_body[0].split("_")

                    if str(communication_socket.getsockname()) == server_receiver_client_token_raddr:
                        print("{0} > {1}".format(
                            sender_username,
                            sender_message
                        ), end=message_end)
            except (BlockingIOError, socket.timeout):
                # BlockingIOError -- > We get this from .recv() since we have a non blocking communication socket
                # socket.timeout -- > Used when .recv() is executed during a timeout
                pass

    def LOGIN_USERNAME_PASSWORD(self):
        """
        {CLIENT_LOGIN_INFO_USERNAME_PASSWORD} -> Used when the client is logging in with the username and password
        Body structure : {USERNAME:{0}|PASSWORD:{1}}

        RESPONSE FROM THE SERVER, >>ALSO RETURNED BY THIS METHOD<<:

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
                    SERVER_RESPONSE = server_login_info_username_password_response.decode("utf-8")
                    break
                else:
                    continue
            except Exception:
                pass
            finally:
                login_username_password_client.close()

        return SERVER_RESPONSE

    def LOGIN_UID(self, VALID_UID):
        """
        Asks the user for the UID. 
        If the given UID is correct, we will create a socket that will connect to the server and ask for the rest of the credentials.
        The value returned from this method is a dictionary containing all the user data.
        {UID:<UID>, Username: <>, Password: <>, FirstName : <> , ...}
        """

        # Create a socket in order to communicate with the server
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(
            (self.IPv4, self.PORT)
        )

        # Asking the user for the UID until it's given in correctly ( max 5 tries )
        try_counter = 1
        while True:
            input_UID = input("UID -- > ")

            if input_UID == VALID_UID:
                break
            else:
                try_counter += 1
                client.send("{CLIENT_LOGIN_INFO_UID_NOT_VALID}".encode("utf-8"))
                self.errorMessage(error_msg="Wrong UID. Try again")

                if try_counter == 6:
                    sys.exit(0)

                continue

        # Send uid back to the server in order to get the rest of the values for the user
        HEADER = "{CLIENT_LOGIN_INFO_UID_SUCCESSFUL}"
        BODY = "{{UID:{0}}}".format(VALID_UID)

        client_login_info_uid_successful_message = "{0}{1}".format(
            HEADER,
            BODY
        )

        client.send(client_login_info_uid_successful_message.encode("utf-8"))

        # Wait for the user data from the server. It will come as a encoded dict inside a string
        USER_DATA = None

        while True:
            try:
                USER_DATA = client.recv(1024)

                if USER_DATA:
                    USER_DATA.decode("utf-8")
                    break
                else:
                    continue
            except Exception:
                pass
            finally:
                client.close()

        USER_DATA = eval(USER_DATA.decode("utf-8"))

        # Return the user containing all the user data
        return USER_DATA

    def register(self):
        """
        Will allow the user to register a new account to the server
        Read ../Documentation/server_client_communication.txt

        Steps:
        1. Get the user data needed for the registration
        2. Send the registration data to the server
        3. Wait for the resposne from the server
        """

        client_registration_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_registration_socket.connect(
            (self.IPv4, self.PORT)
        )

        ##################################################### STEP 1 #####################################################
        # 1. Get the user data needed for the registration

        user_data = self.get_register_data()
        # For testing -- > user_data = "UID:12345|Username:testUsername|Password:testPassword|FirstName:testFirstName|LastName:testLastName|Age:17|City:testCity|PostalCode:12345|StreetName:testStreetName|HouseNumber:11|Salary:800"

        ##################################################### STEP 1 #####################################################
        ##################################################### STEP 2 #####################################################
        # 2. Send the registration data to the server
        # STRUCTURE -- > CLIENT : {CLIENT_REGISTER_DATA}{USERNAME:{0}|PASSWORD:{1}, ...}

        client_registration_HEADER = "{CLIENT_REGISTER_DATA}"
        client_registration_BODY = "{{{0}}}".format(user_data)
        client_registration_message = "{0}{1}".format(client_registration_HEADER, client_registration_BODY)

        client_registration_socket.send(client_registration_message.encode("utf-8"))
        ##################################################### STEP 2 #####################################################
        ##################################################### STEP 3 #####################################################
        # 3. Wait for the resposne from the server

        SERVER_RESPONSE = None

        while True:
            try:
                SERVER_RESPONSE = client_registration_socket.recv(1024)
                SERVER_RESPONSE.decode("utf-8")

                if SERVER_RESPONSE:
                    break
            except Exception:
                pass
            finally:
                client_registration_socket.close()

        if SERVER_RESPONSE == "{SERVER_REGISTER_INFO_SUCCESSFUL}":
            print("You have been successfully registered to the server")
        elif SERVER_RESPONSE == "{SERVER_REGISTER_INFO_ERROR}":
            print("Something went wrong when trying to register you to the server")
        else:
            print("Unknown server response -- > {0}".format(
                SERVER_RESPONSE
            ))

        ##################################################### STEP 3 #####################################################

    def get_register_data(self):
        '''
        Returns all the checked user data needed for the registration.
        Return value structure : "UID:<>|Username:<>|Password:<>|..."
        '''
        # Get all the data needed for the registration
        user_data = ""

        # GET : UID
        while True:
            UID = input("UID -- > ")

            try:
                if not UID:
                    raise InputEmptyException()
                if len(UID) > 15:
                    raise InputOutOfBounds(error_msg="The user id number is too big")

                UID = int(UID)

                user_data += "UID:{0}|".format(UID)
                break
            except ValueError:
                self.errorMessage(error_msg="The user id must be an integer")
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : Username
        while True:
            try:
                Username = input("Username -- > ")

                if not Username:
                    raise InputEmptyException()
                if len(Username) > 20 or len(Username) < 5:
                    raise InputOutOfBounds(min=5, max=20)

                user_data += "Username:{0}|".format(Username)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : Password
        while True:
            try:
                Password = input("Password -- > ")

                if not Password:
                    raise InputEmptyException()
                if len(Password) > 20 or len(Password) < 5:
                    raise InputOutOfBounds(min=5, max=20)

                user_data += "Password:{0}|".format(Password)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : FirstName
        while True:
            try:
                FirstName = input("First name -- > ")

                if not FirstName:
                    raise InputEmptyException()
                if len(FirstName) < 2 or len(FirstName) > 50:
                    raise InputOutOfBounds(min=2, max=50)

                user_data += "FirstName:{0}|".format(FirstName)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : LastName
        while True:
            try:
                LastName = input("Last name -- > ")

                if not LastName:
                    raise InputEmptyException()
                if len(LastName) < 2 or len(LastName) > 50:
                    raise InputOutOfBounds(min=2, max=50)

                user_data += "LastName:{0}|".format(LastName)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : Age
        while True:
            try:
                Age = input("Age -- > ")

                if not Age:
                    raise InputEmptyException()

                Age = int(Age)

                if Age < 16 or Age > 65:
                    raise InputOutOfBounds(min=16, max=65)

                user_data += "Age:{0}|".format(Age)
                break
            except ValueError:
                self.errorMessage(error_msg="The age must be a number")
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : City
        while True:
            try:
                City = input("City -- > ")

                if not City:
                    raise InputEmptyException()
                if len(City) > 50 or len(City) < 2:
                    raise InputOutOfBounds(min=2, max=50)

                user_data += "City:{0}|".format(City)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : PostalCode
        while True:
            try:
                PostalCode = input("Postal code -- > ")

                if not PostalCode:
                    raise InputEmptyException()

                PostalCode = int(PostalCode)

                if PostalCode < 10000 or PostalCode > 99999:
                    raise InputOutOfBounds(min=10000, max=99999)

                user_data += "PostalCode:{0}|".format(PostalCode)
                break
            except ValueError:
                self.errorMessage(error_msg="The postal code must be a number")
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : StreetName
        while True:
            try:
                StreetName = input("Street name -- > ")

                if not StreetName:
                    raise InputEmptyException()
                if len(StreetName) < 2 or len(StreetName) > 100:
                    raise InputOutOfBounds(min=2, max=100)

                user_data += "StreetName:{0}|".format(StreetName)
                break
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : HouseNUmber
        while True:
            try:
                HouseNumber = input("House number -- > ")

                if not HouseNumber:
                    raise InputEmptyException()

                HouseNumber = int(HouseNumber)

                if HouseNumber < 1 or HouseNumber > 100:
                    raise InputOutOfBounds(min=1, max=100)

                user_data += "HouseNumber:{0}|".format(HouseNumber)
                break
            except ValueError:
                self.errorMessage(error_msg="The house number must be a number between 2 and 100")
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        # GET : Salary
        while True:
            try:
                Salary = input("Salary -- > ")

                if not Salary:
                    raise InputEmptyException()

                Salary = int(Salary)

                if Salary < 400 or Salary > 4000:
                    raise InputOutOfBounds(min=400, max=4000)

                user_data += "Salary:{0}".format(Salary)
                break
            except ValueError:
                self.errorMessage("The salary must be a number between 400 and 4000")
            except (InputEmptyException, InputOutOfBounds) as e:
                self.errorMessage(e)

        return user_data

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
                    self.errorMessage(error_msg="Input 1 or 2.")
                    continue

                for i in range(5):
                    print()

                break
            except ValueError:
                self.errorMessage(error_msg="You must input a number.")


client = Client(socket.gethostname(), 55555)
client.start()
