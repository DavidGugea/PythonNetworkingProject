class User:
    def __init__(self, UID, username, password, firstName, lastName, age, city, postalCode, streetName, houseNumber, salary):
        """Creates a new user"""

        self.UID = UID
        self.username = username
        self.password = password
        self.firstName = firstName
        self.lastName = lastName
        self.age = age
        self.city = city
        self.postalCode = postalCode
        self.streetName = streetName
        self.houseNumber = houseNumber
        self.salary = salary

    def get_data(self):
        """Returns all data in form of a string"""
        return \
            """
            UID > {0}
            username > {1}
            password > {2}
            First Name > {3}
            Last Name > {4}
            Age > {5}
            City > {6}
            Postal code > {7}
            Street name > {8}
            House number > {9}
            Salary > {10}
            """.format(
                self.UID,
                self.username,
                self.password,
                self.firstname,
                self.lastName,
                self.age,
                self.city,
                self.postalCode,
                self.streetname,
                self.houseNumber,
                self.salary
            )