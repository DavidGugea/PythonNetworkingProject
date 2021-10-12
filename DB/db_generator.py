import sqlite3
import random

class UserAmountOutOfBoundsException(Exception):
    def __init__(self, min_amount, max_amount):
        '''Use this exception inside the .start() method of the database generator when the desired users amount inside the users table from the database exceeeds certain limits.'''
        self.error_info = "The desired amount of users exceeds certain limits. Choose a number between {0} and {1}".format(min_amount, max_amount)

class Generator:
    def __init__(self):
        '''
        Inside the __init__ we'll just build the connection with the db and the cursor. On top of that we will create the table users using the cursor. The name of the table will be >users<.
        '''

        # The user_table_sql_structure represents only the structure of the table, it doesn't contain the full sql query needed to create the table
        self._user_table_sql_structure = """
        UID UNSIGNED BIGINT PRIMARY KEY,
        Username CHAR(20) UNIQUE NOT NULL,
        Password CHAR(20) UNIQUE NOT NULL,
        FirstName VARCHAR(50) NOT NULL,
        LastName VARCHAR(50) NOT NULL,
        Age UNSIGNED TINYINT NOT NULL,
        City VARCHAR(50) NOT NULL,
        PostalCode UNSIGNED TINYINT NOT NULL,
        StreetName VARCHAR(100) NOT NULL,
        HouseNumber UNSINGED TINYINT NOT NULL,
        Salary UNSIGNED TINYINT NOT NULL
        """

        # The minimum and maximum amount of users allowed in the database
        self._min_users_amount = 100
        self._max_users_amount = 20000 # max 18446744073709551615 for unsigned bigint 

        self._db_connection= sqlite3.connect("dummy_db.db")
        self._cursor = self._db_connection.cursor()

        # Create the table >users< with the user_table_sql_structure
        create_users_table_sql_query = "CREATE TABLE IF NOT EXISTS users({0})".format(self._user_table_sql_structure)
        self._cursor.execute(create_users_table_sql_query)

        # Save
        self._db_connection.commit()

    def generate_dummy_users(self, length=100, remove_existing=True):
        '''
            The length argument specifies the amount of users that should to be generated. It defaults to 100.
            If remove_existing is set to true, the existing users will be removed from the table. It defaults to true.
        '''

        if remove_existing:
            self._cursor.execute("DELETE FROM users")

        # We need 2 lists with all the letters of the alphabet so we can create the user data
        lowercase_and_uppercase_alphabet = list()

        for lowercase_letter_unicode_value in range(ord("a"), ord("z")+1, 1):
            lowercase_and_uppercase_alphabet.append(chr(lowercase_letter_unicode_value))

        for uppercase_letter_unicode_value in range(ord("A"), ord("Z")+1, 1):
            lowercase_and_uppercase_alphabet.append(chr(uppercase_letter_unicode_value))
        
        user_counter = 0
        while user_counter < length:
            # Random user id number with 6 digits
            UID = random.randint(100000, 999999)

            # Random username & password using the lowercase & uppercase letters from the alphabet + numbers
            # There are 62^20 combinations possible ( lowercase & uppercase letters && digits 0-9 )
            Username = ""
            Password = ""

            for j in range(20):
                # Choose between letter or digit for the current i [ True => use letter | False => use digit ]
                username_letter_or_digit = random.choice([True, False])
                password_letter_or_digit = random.choice([True, False])

                if username_letter_or_digit:
                    Username += random.choice(lowercase_and_uppercase_alphabet)
                else:
                    random_digit = random.choice(list(range(10)))
                    Username += str(random_digit)
                
                if password_letter_or_digit:
                    Password += random.choice(lowercase_and_uppercase_alphabet)
                else:
                    random_digit = random.choice(list(range(10)))
                    Password += str(random_digit)

            FirstName = "FirstName{0}".format(UID)
            LastName = "LastName{0}".format(UID)
            Age = random.randint(16, 65)
            City = "City{0}".format(UID)
            PostalCode = random.randint(10000, 99999)
            StreetName = "StreetName{0}".format(UID)
            HouseNumber = random.randint(1, 99)
            Salary = random.randint(1500, 4000)

            try:
                # Insert the row with all the user data inside the table
                self._cursor.execute("INSERT INTO users VALUES({0}, '{1}', '{2}', '{3}', '{4}', {5}, '{6}', {7}, '{8}', {9}, {10})".format(
                    UID, # 0
                    Username, # 1
                    Password, # 2 
                    FirstName, # 3
                    LastName, # 4
                    Age, # 5 
                    City, # 6 
                    PostalCode, # 7 
                    StreetName, # 8 
                    HouseNumber, # 9
                    Salary # 10
                ))

                user_counter += 1
            except sqlite3.IntegrityError:
                continue

        # Save all the changes to the db
        self._db_connection.commit()

    def errorMessage(self, error_msg, spaces=3):
        '''An error message displayed in the console with spaces used as padding. The number of spaces used as padding defaults to 3'''
        for i in range(spaces):
            print()

        print(error_msg)

        for i in range(spaces):
            print()

    def start(self):
        # Get the desired number of users that we want to create
        number_of_users = 100
        while True:
            number_of_users = input("How many users do you want to generate ( between {0} and {1} ) ? -- > ".format(self._min_users_amount, self._max_users_amount))
            
            try:
                number_of_users = int(number_of_users)
                
                if number_of_users <= self._max_users_amount and number_of_users >= self._min_users_amount:
                    # If the given number of users is a number and it doesn't exceed the allowd bounds, break the while loop
                    break
                else:
                    raise UserAmountOutOfBoundsException(self._min_users_amount, self._max_users_amount)
                    continue
            except ValueError:
                self.errorMessage("You must input a number.")
                continue
            except UserAmountOutOfBoundsException as exception:
                self.errorMessage(exception.error_info)
                continue

        # Check if there are already users in the users table. If there are, get the remove_existing value
        self._cursor.execute("SELECT COUNT(UID) FROM users")
        current_users_amount_in_db = self._cursor.fetchone()[0]
        remove_existing_input = False

        if current_users_amount_in_db != 0:
            while True:
                remove_existing_input = input("Do you want to delete all the existing users from the users table ( y/n ) ? -- > ")
                remove_existing_input = remove_existing_input.lower()

                if remove_existing_input == "y":
                    remove_existing_input = True
                    break
                elif remove_existing_input == "n":
                    remove_existing_input = False
                    break
                else:
                    self.errorMessage("y/n input")
                    continue

        self.generate_dummy_users(number_of_users, remove_existing_input)

generator = Generator()
generator.start()