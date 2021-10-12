import socket # Used for handling connections
import selectors # High level I/O multiplexing
import logging # Used for stream & file handling in order to monitor connections to the server socket

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
        """

        message = client_socket_token.recv(1024).decode("utf-8")
        addr = client_socket_token.getpeername()

        if message:
            print("[{0}] {1}".format(
                addr,
                message
            ))
        else:
            print("Connection stopped with {0}".format(addr))

            self.selector.unregister(client_socket_token)
            client_socket_token.close()

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

server = Server(socket.gethostname(), 50000, "connections.log")

try:
    while True:
        for key, mask in server.selector.select():
            key.data(server.selector, key.fileobj)
except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError):
    pass