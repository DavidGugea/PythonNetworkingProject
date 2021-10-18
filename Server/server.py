import socket # Used for handling connections
import selectors # High level I/O multiplexing
import logging # Used for stream & file handling in order to monitor connections to the server socket
import sqlite3 # Connect to the DB in order to send responses back to the clients in order to check login/register data
from sqlite3.dbapi2 import IntegrityError
import sys # Close the server when needed

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
        A client can send a message to the server and also specify who should receive it. We can redirect the message from the server to the specified client that should get the message by searching for its address inside the dict.
        
        The structure of the dict:
        
        keys : Username ( from DB, after the client has been registered )
        values : Client socket token address ( .getpeername () )
        """
        self.currently_connected_users = dict()

        # Create the non-blocking server socket so it can be a multiplex server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(
            (IPv4, PORT)
        )
        self.server_socket.setblocking(False)
        # the backlog specifies the number of unaccepted connections that the system will allow before refusing new connections.
        self.server_socket.listen(100)

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
            elif client_message.startswith("{CLIENT_LOGIN_INFO_UID_NOT_VALID}"):
                # Use the stream and the file logger to log the failed login - step 2 UID - attempt
                failed_uid_logger_critical_message = "Wrong UID. Client address : {0}".format(
                    client_address
                )
                self.stream_logger.critical(failed_uid_logger_critical_message)
                self.file_logger.critical(failed_uid_logger_critical_message)
            elif client_message.startswith("{CLIENT_LOGIN_INFO_UID_SUCCESSFUL}"):
                self.client_login_uid(client_message, client_socket_token)
            elif client_message.startswith("{CLIENT_REGISTER_DATA}"):
                self.register_user(client_message, client_socket_token)
            elif client_message.startswith("{CLIENT_COMMUNICATION_DATA}"):
                self.save_client_for_communication(client_message, client_socket_token)
            elif client_message.startswith("{CLIENT_MESSAGE}"):
                self.send_message_to_another_client(client_message, client_socket_token)
        else:
            # Delete the registered UID from the currently connected users dict
            unregister_client_socket_token_address = client_socket_token.getpeername()

            if unregister_client_socket_token_address in self.currently_connected_users.values():
                key_to_delete = None

                for key, value in self.currently_connected_users.items():
                    if value == unregister_client_socket_token_address:
                        key_to_delete = key
                        break
                    else:
                        continue
            
                self.currently_connected_users.pop(key_to_delete)

            # Unregister the client socket from the selector && close its connection to the server.
            self.selector.unregister(client_socket_token)
            client_socket_token.close()

            # Use the stream & file loggers in order to monitor the lost connection to the client
            logger_info_string = "Connection lost with {0}".format(client_address)
            self.stream_logger.info(logger_info_string)
            self.file_logger.info(logger_info_string)

    def send_message_to_another_client(self, client_message, client_socket_token):
        """
        Send the given message from the client to another client by reading the client_message and extracting the username and the message out of the body.
        Afterwards, look inside the dictionary that contains all the addresses for all the currently registered clients and their usernames, look for the address, and send the message to the given username

        STEPS:
        
        1. Extract the username and the message from the client message body
        2. Look for the given username inside the dictionary that contains all the currently connected users and try to get the address of the client.
        3. If the given username was not connected to the server at the moment, return a response that contains that message back to the client. Otherwise, send the message to the client
        """

        client_receiver_address_found = True
        client_receiver_address = None

        ############################# STEP 1 #############################
        # 1. Extract the username and the message from the client message body
        client_message_body = client_message[client_message.index("}")+2:-1]
        sender_username, receiver_username, sender_message = client_message_body.split("_")

        ############################# STEP 1 #############################
        ############################# STEP 2 #############################
        # 2. Look for the given username inside the dictionary that contains all the currently connected users and try to get the address of the client.
        try:
            client_receiver_address = self.currently_connected_users[receiver_username]
        except KeyError:
            client_receiver_address_found = False
        
        ############################# STEP 2 #############################
        ############################# STEP 3 #############################
        # 3. If the given username was not connected to the server at the moment, return a response that contains that message back to the client. Otherwise, send the message to the client
        if not client_receiver_address_found:
            server_response_client_message_error_username_not_found = "{CLIENT_MESSAGE_ERROR_USERNAME_NOT_FOUND}"
            client_socket_token.send(server_response_client_message_error_username_not_found.encode("utf-8"))
        else:
            # Format the message from the server
            HEADER = "{MESSAGE_FROM_CLIENT}"
            body_message = "{0}_{1}".format(
                sender_username, sender_message
            )
            BODY = "{{{0}}}".format(
                body_message
            )

            server_message = "{0}{1}".format(
                HEADER, BODY
            )

            print("-------------- INFO DATA --------------")
            print("sender username -- > {0}".format(sender_username))
            print("receiver_username -- > {0}".format(receiver_username))
            print("sender_message -- > {0}".format(sender_message))
            print("currently connected usernames -- > {0}".format(self.currently_connected_users.keys()))
            print("currently connected addresses -- > {0}".format(self.currently_connected_users.values()))
            print("-------------- INFO DATA --------------")

            # Send the message to the receiver
            self.server_socket.sendto(
                server_message.encode("utf-8"),
                self.currently_connected_users.get(receiver_username)
            )

        ############################# STEP 3 #############################

    def save_client_for_communication(self, client_message, client_socket_token):
        """
        This method will save the client so it can communicate with other clients. 
        The client will be saved inside self.currently_connected_users. The username will be the key, the address of the client will be the address.

        CLIENT : {CLIENT_COMMUNICATION_DATA}{<USERNAME>}
        """

        # Get the username out of the client_message
        client_username = client_message[client_message.index("}")+2:-1]
        self.currently_connected_users[client_username] = client_socket_token.getpeername()

        # Use the stream and file logger to register the new client and its username
        logger_message = "New communication socket with the username {0} connected. Address : {1}".format(
            client_username,
            client_socket_token.getpeername()
        )
        self.stream_logger.info(logger_message)
        self.file_logger.info(logger_message)

        print(self.currently_connected_users)

    def register_user(self, client_message, client_socket_token):
        '''
        This method will register a new user to the DB and will send a response back to the client.

        Possible server responses:
        1. {SERVER_REGISTER_INFO_ERROR} -- Send this when something went wrong when trying to add a new user to the database
        2. {SERVER_REGISTER_INFO_SUCCESSFUL} -- Send this when the server has successfully added a new user to the database

        Steps:
        
        1. Extract the body from the client message
        2. Try to add the new user to the DB and log the interaction using the stream- and file logger
        3. Send the response back to the client
        '''

        SERVER_RESPONSE = None

        ############################################## STEP 1 ##############################################
        # 1. Extract the body from the client message

        client_message_body = client_message[client_message.index("}")+2:-1]

        # Example user data -- > user_data = "UID:12345|Username:testUsername|Password:testPassword|FirstName:testFirstName|LastName:testLastName|Age:17|City:testCity|PostalCode:12345|StreetName:testStreetName|HouseNumber:11|Salary:800"
        user_data_pipe_split = client_message_body.split("|")
        user_data = dict()
        for data in user_data_pipe_split:
            key, value = data.split(":")
            user_data[key] = value

        # Update the types inside the user_data where neccessary ( the values that should be integers, are strings )
        user_data["UID"] = int(user_data["UID"])
        user_data["Age"] = int(user_data["Age"])
        user_data["PostalCode"] = int(user_data["PostalCode"])
        user_data["HouseNumber"] = int(user_data["HouseNumber"])
        user_data["Salary"] = int(user_data["Salary"])

        ############################################## STEP 1 ##############################################
        ############################################## STEP 2 ##############################################
        # 2. Try to add the new user to the DB

        try:
            user_sql_query = "INSERT INTO users VALUES({0}, '{1}', '{2}', '{3}', '{4}', {5}, '{6}', {7}, '{8}', {9}, {10})".format(*user_data.values())

            self.DB_CURSOR.execute(user_sql_query)
            self.DB_CONNECTION.commit()

            SERVER_RESPONSE = "{SERVER_REGISTER_INFO_SUCCESSFUL}"

            logger_message = "User successfully registered to the DB. Address -- > {0}".format(
                client_socket_token.getpeername()
            )
            self.stream_logger.info(logger_message)
            self.file_logger.info(logger_message)
        except IntegrityError:
            SERVER_RESPONSE = "{SERVER_REGISTER_INFO_ERROR}"

            logger_message = "User couldn't register to the DB. Address -- > {0}".format(
                client_socket_token.getpeername()
            ) 
            self.stream_logger.critical(logger_message)
            self.file_logger.critical(logger_message)

        ############################################## STEP 2 ##############################################
        ############################################## STEP 3 ##############################################
        # 3. Send the response back to the client

        client_socket_token.send(SERVER_RESPONSE.encode("utf-8"))

        ############################################## STEP 3 ##############################################

    def client_login_uid(self, client_message, client_socket_token):
        """
        Sends all the values of the user back to the client based on the given UID that we'll get from the body from the client_message 

        {SERVER_LOGIN_INFO_UID_SUCCESSFULL}{UID:<UID>|Username:<>|Password:<>|FirstName:<>|...}

        Following steps:
        
        1. Extract the UID from the body
        2. Get all the values of the user from the DB based on the given UID from the body
        3. Use the stream- and file logger to log the successful connection to the server
        4. Pack all the values of the user inside a dict and send it back to the client
        """
        
        ######################### STEP 1 #########################
        # 1. Extract the UID from the body
        client_message_body = client_message[client_message.index("}")+2:-1]

        client_UID = client_message_body.split(":")[1]
        ######################### STEP 1 #########################
        ######################### STEP 2 #########################
        # 2. Get all the values of the user from the DB based on the given UID from the body
        user_data = self.DB_get_user_data_with_UID(client_UID)
        ######################### STEP 2 #########################
        ######################### STEP 3 #########################
        # 3. Use the stream- and file logger to log the successful connection to the server

        self.currently_connected_users[user_data.get("Username")] = client_socket_token.getpeername()

        logger_user_registered_message = "Successful UID login > UID : {0} | Address : {1}".format(
            user_data.get("UID"),
            client_socket_token.getpeername()
        )
        self.stream_logger.info(logger_user_registered_message)
        self.file_logger.info(logger_user_registered_message)
        ######################### STEP 3 #########################
        ######################### STEP 4 #########################
        # 4. Pack all the values of the user inside a dict and send it back to the client
        user_data = str(user_data)
        client_socket_token.send(user_data.encode("utf-8"))
        ######################### STEP 4 #########################

    def DB_get_user_data_with_UID(self, client_UID):
        """
        Returns the user data base on the given UID

        Return value ( type : dict ):
        {
            'UID' : <UID>,
            'Username' : <Username>,
            'Password' : <Password>,
            ...
        }
        """

        # Execute the sql query and fetch the data
        sql_execute_query = "SELECT * FROM users WHERE UID='{0}'".format(client_UID)
        self.DB_CURSOR.execute(sql_execute_query)
        db_user_data = self.DB_CURSOR.fetchone()

        # Create the dict that contains all the user data that will be returned
        return_user_data_dict = dict()
        return_user_data_dict["UID"] =  db_user_data[0]
        return_user_data_dict["Username"] = db_user_data[1]
        return_user_data_dict["Password"] = db_user_data[2]
        return_user_data_dict["FirstName"] = db_user_data[3]
        return_user_data_dict["LastName"] = db_user_data[4]
        return_user_data_dict["Age"] = db_user_data[5]
        return_user_data_dict["City"] = db_user_data[6]
        return_user_data_dict["PostalCode"] = db_user_data[7]
        return_user_data_dict["StreetName"] = db_user_data[8]
        return_user_data_dict["HouseNumber"] = db_user_data[9]
        return_user_data_dict["Salary"] = db_user_data[10]

        # Return the dict that contains the user data
        return return_user_data_dict

    def client_login_username_password(self, client_message, client_socket_token):
        """
        The user is at the first point of the login. They want to log in using the username and the password. 
        The body structure looks like this : {USERNAME:{0}|PASSWORD:{1}}. 
        Following steps:
        
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

        # Extract username & password
        client_message_Username, client_message_Password = client_message_body.split("|")
        client_message_Username = client_message_Username.split(":")[1]
        client_message_Password = client_message_Password.split(":")[1]
        ######################### STEP 1 #########################
        ######################### STEP 2 #########################
        user_credentials = self.DB_check_username_password_credentials(client_message_Username, client_message_Password)
        ######################### STEP 2 #########################
        ######################### STEP 3 #########################
        server_response_message = None

        if user_credentials[0]:
            # ( True , UID )
            UID = user_credentials[1]

            server_response_message = "SERVER_LOGIN_INFO_USERNAME_PASSWORD_SUCCESSFUL_{0}".format(UID)

            # Use the stream and the file logger to register the successful login - step 1 -
            logger_info_message = "SUCCESSFUL STEP 1 LOGIN FROM {0}".format(client_socket_token.getpeername())
            self.stream_logger.error(logger_info_message)
            self.file_logger.error(logger_info_message)
        else:
            # ( False, None )
            server_response_message = "SERVER_LOGIN_INFO_USERNAME_PASSWORD_WRONG"

            # Use the stream- and file logger to register the failed login attempt
            logger_error_message = "FAILED STREAM LOG FROM {0}".format(client_socket_token.getpeername())
            self.stream_logger.error(logger_error_message)
            self.file_logger.error(logger_error_message)


        # Send the response back to the client
        client_socket_token.send(server_response_message.encode("utf-8"))
        ######################### STEP 3 #########################

    def DB_check_username_password_credentials(self, username, password):
        """
        Checks if the given username & password can be found in the db.
        If found returns:
        (True, UID) > The UID is the UID found on the row for the given username & password
        If not found returns:
        (False, None)
        """

        # Fetch the data from the DB using the cursor
        sql_select_query = "SELECT UID, Username, Password FROM users WHERE Username='{0}' AND Password='{1}'".format(
            username, password
        )
        self.DB_CURSOR.execute(sql_select_query)
        fetched_user_credentials_UID_username_password = self.DB_CURSOR.fetchone()

        if fetched_user_credentials_UID_username_password:
            return (True, fetched_user_credentials_UID_username_password[0])
        else:
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
