from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Numeric, Boolean
from datetime import datetime, timedelta
from faker import Faker
from decimal import Decimal
from flask_security import SQLAlchemyUserDatastore, hash_password
from flask_security.models import fsqla_v3 as fsqla

db = SQLAlchemy()

import random
import enum

MAX_NR_OF_CUSTOMERS = 500 
MAX_NR_OF_ACCOUNTS = 4
MINIMUM_NR_OF_ACCOUNTS = 1
MAX_NR_OF_TRANSACTIONS = 30
MINIMUM_NR_OF_TRANSACTIONS = 3

db = SQLAlchemy()

roles_users = db.Table(
    "roles_users",
    db.Column("user_id", db.Integer(), db.ForeignKey("User.id")),
    db.Column("role_id", db.Integer(), db.ForeignKey("Role.id")),
)

class Role(db.Model, fsqla.FsRoleMixin):
    __tablename__ = "Role"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    users = relationship("User", secondary=roles_users, back_populates="roles")

class User(db.Model, fsqla.FsUserMixin):
    __tablename__ = "User"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    fs_uniquifier: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    roles: Mapped[list[Role]] = relationship("Role", secondary=roles_users, back_populates="users")


class Customer(db.Model):
    __tablename__ = "Customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    given_name: Mapped[str] = mapped_column(String(50), nullable=False)
    surname: Mapped[str] = mapped_column(String(50), nullable=False)
    streetaddress: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(70), nullable=False)
    zipcode: Mapped[str] = mapped_column(String(15), nullable=False)
    country: Mapped[str] = mapped_column(String(60), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    birthday: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    national_id: Mapped[str] = mapped_column(String(20), nullable=False)
    telephone_country_code: Mapped[str] = mapped_column(String(10), nullable=False)
    telephone: Mapped[str] = mapped_column(String(30), nullable=False)
    email_address: Mapped[str] = mapped_column(String(50), nullable=False)

    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="customer", lazy="select"
    )

class AccountType(enum.Enum):
    PERSONAL = "Personal"
    CHECKING = "Checking"
    SAVINGS = "Savings"


class Account(db.Model):
    __tablename__ = "Accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=True, create_constraint=True),
        nullable=False
    )
    created: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=2), nullable=False, default=Decimal(0))
    customer_id: Mapped[int] = mapped_column(ForeignKey("Customers.id"), nullable=False)

    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="accounts", lazy="select"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="account", lazy="select"
    )


class TransactionType(enum.Enum):
    DEBIT = "Debit"
    CREDIT = "Credit"

class TransactionOperation(enum.Enum):
    SALARY = "Salary"
    TRANSFER = "Transfer"
    DEPOSIT_CASH = "Deposit cash"
    ATM_WITHDRAWL = "ATM withdrawal"
    PAYMENT = "Payment"
    BANK_WITHDRAWL = "Bank withdrawal"

class Transaction(db.Model):
    __tablename__ = "Transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=True, create_constraint=True), nullable=False)
    
    operation:Mapped[TransactionOperation] = mapped_column(
        Enum(TransactionOperation, native_enum=True, create_constraint=True), nullable=False)
    
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    new_balance: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    account_id: Mapped[int] = mapped_column(ForeignKey("Accounts.id"), nullable=False)

    account: Mapped["Account"] = relationship(
        "Account", back_populates="transactions", lazy="select"
    )

def seedData(db):

    fake = Faker()
    list_of_account_types = list(AccountType)

    number_of_customers_in_db =  Customer.query.count()
    while number_of_customers_in_db < MAX_NR_OF_CUSTOMERS:

        new_customer:Customer = Customer(
            given_name=fake.first_name(),
            surname=fake.last_name(),
            streetaddress=fake.street_address(),
            city=fake.city(),
            zipcode=fake.postcode(),
            country=fake.country(),
            country_code=fake.country_code(),
            birthday=fake.date_of_birth(),
            national_id=fake.ssn(),
            telephone_country_code=fake.country_calling_code(),
            telephone=fake.phone_number(),
            email_address=fake.email()
        )
        
        ## Create fake accounts for new customer
        number_of_accounts = random.randint(MINIMUM_NR_OF_ACCOUNTS, MAX_NR_OF_ACCOUNTS)
        
        for _ in range(number_of_accounts):
            account_type = random.choice(list_of_account_types)
            account_created_at = datetime.now() + timedelta(days=-random.randint(365,3650))        

            new_account:Account = Account(
                account_type=account_type,
                created = account_created_at,
                balance = Decimal('0.00'),
                customer_id=new_customer.id                
            )

            new_customer.accounts.append(new_account)

            ### Create fake transaktions for new account
            number_of_transactions = random.randint(MINIMUM_NR_OF_TRANSACTIONS, MAX_NR_OF_TRANSACTIONS)
            start_date = account_created_at

            for _ in range(number_of_transactions):
                new_transaction = Transaction()

                trans_amount = Decimal(random.randint(0,30)*100)
                new_transaction.amount = trans_amount

                fake_transaction_date = fake.date_time_between_dates(
                    datetime_start=start_date, datetime_end=start_date + timedelta(days=10))
                new_transaction.date = fake_transaction_date

                new_account.transactions.append(new_transaction)

                if new_account.balance - trans_amount < 0:
                    new_transaction.type = TransactionType.DEBIT
                else:
                    new_transaction.type = TransactionType.DEBIT if random.randint(0,100) > 70 else TransactionType.CREDIT

                random_roll = random.randint(0,100)
                if new_transaction.type == TransactionType.DEBIT:
                    new_account.balance += trans_amount

                    if random_roll < 20:
                        new_transaction.operation = TransactionOperation.DEPOSIT_CASH
                    elif random_roll < 66:
                        new_transaction.operation = TransactionOperation.SALARY
                    else:
                        new_transaction.operation = TransactionOperation.TRANSFER
                        
                else:
                    new_account.balance -= trans_amount

                    if random_roll < 40:
                        new_transaction.operation = TransactionOperation.ATM_WITHDRAWL
                    elif random_roll < 75:
                        new_transaction.operation = TransactionOperation.PAYMENT
                    elif random_roll < 85:
                        new_transaction.operation = TransactionOperation.BANK_WITHDRAWL
                    else:
                        new_transaction.operation = TransactionOperation.TRANSFER

                new_transaction.new_balance = new_account.balance
                start_date = fake_transaction_date
                    
            db.session.add(new_customer)
            db.session.commit()

        number_of_customers_in_db += 1
user_datastore = SQLAlchemyUserDatastore(db, User, Role)

def seed_users():
    with db.session.begin():
        if not Role.query.first():
            db.session.add_all([
                Role(name="Admin", description="Master"),
                Role(name="Cashier", description="Hantera kunder"),
            ])
        
        if not User.query.first():
            db.session.add_all([
                user_datastore.create_user(email="sebastian.ohman@systementor.se", password=hash_password("Hejsan123#"), roles=["Admin"]),
                user_datastore.create_user(email="sebastian.ohman@teknikhögskolan.se", password=hash_password("Hejsan123#"), roles=["Cashier"]),
            ])
        
        db.session.commit()


