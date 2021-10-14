class User:
    def __init__(self, UID, username, password, firstName, lastName, age, city, postalCode, streetName, houseNumber, salary):
        """Creates a new user"""

        self.UID = UID
        self.Username = username
        self.Password = password
        self.FirstName = firstName
        self.LastName = lastName
        self.Age = age
        self.City = city
        self.PostalCode = postalCode
        self.StreetName = streetName
        self.HouseNumber = houseNumber
        self.Salary = salary

    def get_data(self):
        """Returns all data in form of a string"""
        return \
            """
            UID          > {0}
            username     > {1}
            password     > {2}
            First Name   > {3}
            Last Name    > {4}
            Age          > {5}
            City         > {6}
            Postal code  > {7}
            Street name  > {8}
            House number > {9}
            Salary       > {10}
            """.format(
                self.UID,
                self.Username,
                self.Password,
                self.FirstName,
                self.LastName,
                self.Age,
                self.City,
                self.PostalCode,
                self.StreetName,
                self.HouseNumber,
                self.Salary
            )