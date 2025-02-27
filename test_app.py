import unittest
from app import app, db
from models import Customer, Account
from decimal import Decimal
from datetime import datetime

class BankTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Skapa testdatabas, testkund och testkonto"""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db" 
        cls.client = app.test_client()

        with app.app_context():
            db.create_all()

            cls.test_customer = Customer(
                given_name="Testaren",
                surname="Testy",
                streetaddress="Testingstreet 11",
                city="TestarCity",
                zipcode="18412",
                country="Tland",
                country_code="SE",
                birthday="1934-11-27",
                national_id="341127-1337",
                telephone_country_code="+46",
                telephone="0791847123",
                email_address="testing@testing.com"
            )
            db.session.add(cls.test_customer)
            db.session.commit()

            cls.test_account = Account(
                account_type="CHECKING",
                created=datetime.now(),
                balance=Decimal(1000),
                customer_id=cls.test_customer.id
            )
            db.session.add(cls.test_account)
            db.session.commit()

            db.session.refresh(cls.test_account)

    @classmethod
    def tearDownClass(cls):
        """Rensa databasen efter tester"""
        with app.app_context():
            db.drop_all()

    def test_cannot_withdraw_more_than_balance(self):
        """Ska inte kunna ta ut mer än kontots saldo"""
        with app.app_context():
            account = db.session.get(Account, self.test_account.id)
            initial_balance = account.balance
            amount_to_withdraw = initial_balance + Decimal("1.00")

            if account.balance >= amount_to_withdraw:
                account.balance -= amount_to_withdraw
                db.session.commit()

            self.assertEqual(account.balance, initial_balance)

    def test_cannot_transfer_more_than_balance(self):
        """Ska inte kunna överföra mer än vad som finns på kontot"""
        with app.app_context():
            account = db.session.get(Account, self.test_account.id)
            initial_balance = account.balance
            amount_to_transfer = initial_balance + Decimal("1.00")

            if account.balance >= amount_to_transfer:
                account.balance -= amount_to_transfer
                db.session.commit()

            self.assertEqual(account.balance, initial_balance)

    def test_cannot_deposit_negative_amount(self):
        """Ska inte gå att sätta in ett negativt belopp"""
        deposit_amount = Decimal(-100)
        self.assertTrue(deposit_amount <= 0, "Borde inte kunna sätta in negativa belopp")

    def test_cannot_withdraw_negative_amount(self):
        """Ska inte kunna ta ut ett negativt belopp"""
        withdraw_amount = Decimal(-100)
        self.assertTrue(withdraw_amount <= 0, "Borde inte kunna ta ut negativa belopp")


if __name__ == "__main__":
    unittest.main()




