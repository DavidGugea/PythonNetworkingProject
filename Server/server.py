import socket # Used for handling connections
import selectors # High level I/O multiplexing
import logging # Used for stream & file handling in order to monitor connections to the server socket
import sqlite3 # Connect to the DB in order to send responses back to the clients in order to check login/register data

class Server:
    def __init__(self, IPv4, PORT, monitoringFileName):
        """
        A server-type socket using IPv4 & tcp connected ( AF_INET, SOCK_STREAM ).
        It will monitor the connections made to the server as well using a stream & a file handler.
        The monitoringFileName doens't have to contain any extensions. ( Correct input : myfile <> Wrong input : myfile.log )
        """

        self.monitoringFileName = monitoringFileName

        """
        The currently_connected_users dict will store all the connected usernames and their addresses. 
        A client can send a message to the server and also specify whom should receive it. We can redirect the message from the server to the specified client that should get the message by searching for its address inside the dict.
        
        The structure of the dict:
        
        keys : Usernames ( from db, after the client has been registered )
        values : Client address ( .getpeername () )
        """
        self.currently_connected_users = dict()

        # Create the non-blocking server socket so it can be a multiplex server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(
            (IPv4, PORT)
        )
        self.server_socket.setblocking(False)
        # the backlog specifies the number of unaccepted connections that the system will allow before refusing new connections.
        self.server_socket.listen(2)

        # Get the stream & file loggers in order to monitor connections to the server
        self.stream_logger, self.file_logger = self.create_file_stream_loggers()

        # Create connection with the database
        self.DB_CONNECTION = sqlite3.connect("../DB/dummy_db.db")
        self.DB_CURSOR = self.DB_CONNECTION.cursor()

        # Create the default selector
        self.selector = selectors.DefaultSelector() # Kqueue-based selector. Kqueue is a scalable event notification.

        # Set up the server socket to be the fileobj, set the event mask to be selectors.EVENT_READ because we want the server fileobj to be available for reading. It work similarly to event listeners in JS. The >>data<< parameter works is the callback handler
        self.selector.register(self.server_socket, selectors.EVENT_READ, self.selector_register_accept_new_connection)

    def selector_register_accept_new_connection(self, selector, server_socket):
        """
        Not intended for use outside class. It is only intended for the selector to handle connections.
        """

        # Get the client socket token and its address + set it to a non blocking socket
        client_socket_token, client_socket_address = server_socket.accept()
        client_socket_token.setblocking(False)

        # Use the stream & file handlers to register the new connection
        logger_info_message = "New connection established with >> {0}".format(
            client_socket_address
        )

        self.file_logger.info(logger_info_message)
        self.stream_logger.info(logger_info_message)

        # Register a callback handler for handling messages from the client socket
        self.selector.register(client_socket_token, selectors.EVENT_READ, self.selector_register_handle_messages)

    def selector_register_handle_messages(self, selector, client_socket_token):
        """
        Not intended for use outside class. It is only intended for the selector to handle messages from the client socket.
        Read ../Documentation/server_client_communication_blueprint.txt
        """

        # Get the client message & its address
        client_message = client_socket_token.recv(1024).decode("utf-8")
        client_address = client_socket_token.getpeername()

        if client_message:
            if client_message.startswith("{CLIENT_LOGIN_INFO_USERNAME_PASSWORD}"):
                self.client_login_username_password(client_message, client_socket_token)
        else:
            # Unregister the client socket from the selector && close its connection to the server.
            self.selector.unregister(client_socket_token)
            client_socket_token.close()

            # Use the stream & file loggers in order to monitor the lost connection to the client
            logger_info_string = "Connection lost with {0}".format(client_address)
            self.stream_logger.info(logger_info_string)
            self.file_logger.info(logger_info_string)

    def client_login_username_password(self, client_message, client_socket_token):
        """
        The user is at the first point of the login. They want to log in using the username and the password. 
        The body structure looks like this : {USERNAME:{0}|PASSWORD:{1}}. 
        The next steps are the following:
        
        1. Extract the username & the password from the body
        2. Check to see if the username and the password are valid credentials inside the db
        3. Send the response back to the client
        
        RESPONSE FROM THE SERVER:

        Successful:
        SERVER_LOGIN_INFO_USERNAME_PASSWORD_SUCCESSFUL_<UID>

        Username or password wrong:
        SERVER_LOGIN_INFO_USERNAME_PASSWORD_WRONG
        """

        ######################### STEP 1 #########################
        # Extract the body from the client message ( delete the additionally addeded curly braces at the start & the end of the body before extracting the credentials out of it )
        client_message_body = client_message[client_message.index("}")+2:-1]
        client_message_body = client_message_body[1:-1]

        # Extract username & password
        client_message_Username, client_message_Password = client_message_body.split("|")
        client_message_Username = client_message_Username.split(":")[1]
        client_message_Password = client_message_Password.split(":")[1]
        print("CLIENT USERNAME -- > {0}".format(client_message_Username))
        print("CLIENT PASSWORD -- > {0}".format(client_message_Password))
        ######################### STEP 1 #########################
        ######################### STEP 2 #########################
        user_credentials = self.check_username_password_credentials(client_message_Username, client_message_Password)
        ######################### STEP 2 #########################
        ######################### STEP 3 #########################
        server_response_message = None

        if user_credentials[0]:
            # ( True , UID )
            UID = user_credentials[1]

            server_response_message = "SERVER_LOGIN_INFO_USERNAME_PASSWORD_SUCCESSFUL_{0}".format(UID)
        else:
            # ( False, None )
            server_response_message = "SERVER_LOGIN_INFO_USERNAME_PASSWORD_WRONG"

        # Send the response back to the client
        client_socket_token.send(server_response_message.encode("utf-8"))
        ######################### STEP 3 #########################

    def check_username_password_credentials(self, username, password):
        print("CHECKING USERNAME AND PASSWORD CREDENTIALS")
        """
        Checks if the given username & password can be found in the db.
        If found returns:
        (True, UID) > The UID is the UID found on the row for the given username & password
        If not found returns:
        (False, None)
        """

        # Fetch the data from the DB using the cursor
        self.DB_CURSOR.execute("SELECT UID, Username, Password FROM users WHERE Username='{0}' AND Password='{1}'".format(
            username, password
        ))
        fetched_user_credentials_UID_username_password = self.DB_CURSOR.fetchone()
        print(fetched_user_credentials_UID_username_password)
        print("SELECT UID, Username, Password FROM users WHERE Username='{0}' AND Password='{1}'".format(
            username, password
        ))

        if fetched_user_credentials_UID_username_password:
            print("SENDING BACK TRUE RESPONSE FROM CHECKING USERNAME AND PASSWORD CREDENTIALS")
            print(fetched_user_credentials_UID_username_password)
            return (True, fetched_user_credentials_UID_username_password[0])
        else:
            print("SENDING BACK FALSE RESPONSE FROM CHECKING USERNAME AND PASSWORD CREDENTIALS")
            return (False, None)


    def create_file_stream_loggers(self):
        """
        Returns a stream and a file logger inside a tuple -> ( STREAM_LOGGER, FILE_LOGGER ) 
        Both loggers are level 50 loggers.
        """

        # Create the formatter used by the both loggers
        HANDLER_FORMATTER = logging.Formatter("{asctime} [ {levelname:8} ] > {message}", datefmt="%d.%m.%Y <> %H:%M:%S", style="{")
        
        # Create the handlers and set the formatter to both of them
        STREAM_HANDLER = logging.StreamHandler()
        STREAM_HANDLER.setFormatter(HANDLER_FORMATTER)

        FILE_HANDLER =  logging.FileHandler(self.monitoringFileName)
        FILE_HANDLER.setFormatter(HANDLER_FORMATTER)

        # Create the loggers and  add the handlers to them
        file_logger = logging.getLogger("file_logger")
        file_logger.addHandler(FILE_HANDLER)

        stream_logger = logging.getLogger("stream_logger")
        stream_logger.addHandler(STREAM_HANDLER)

        # Set the loggers to be level 50 loggers
        file_logger.setLevel(logging.DEBUG)
        stream_logger.setLevel(logging.DEBUG)

        # Return the loggers inside a tuple > ( STREAM_LOGGER, FILE_LOGGER )
        return ( stream_logger, file_logger )

server = Server(socket.gethostname(), 55555, "connections.log")

try:
    while True:
        for key, mask in server.selector.select():
            key.data(server.selector, key.fileobj)
except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
    pass