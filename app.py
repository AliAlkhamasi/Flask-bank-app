from flask import Flask, render_template, request, url_for, redirect, flash
from flask_migrate import Migrate, upgrade
from flask_security import Security, login_required, roles_required
from dotenv import load_dotenv
import os
from sqlalchemy.orm import joinedload
from models import db, seedData, Customer, Account, Transaction, user_datastore, seed_users, TransactionType, TransactionOperation
from flask_security import logout_user
from flask_login import current_user
from decimal import Decimal
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config["SECURITY_LOGIN_USER_TEMPLATE"] = "security/login_user.html"
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")  
app.config['SECURITY_PASSWORD_SALT'] = os.getenv("SECURITY_PASSWORD_SALT")
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:password@localhost/Bank'

security = Security(app, user_datastore)
db.app = app
db.init_app(app)
migrate = Migrate(app, db)

@app.route("/logout")
def logout():
    logout_user()  
    flash("Du har loggats ut!", "info")
    return redirect(url_for("security.login"))

@app.route("/")
@login_required #både admin och cashier
def startpage():
    with app.app_context():
        num_customers = Customer.query.count()
        num_accounts = Account.query.count()
        total_balance = db.session.query(db.func.sum(Account.balance)).scalar() or 0
    
    return render_template("index.html", num_customers=num_customers, num_accounts=num_accounts, total_balance=total_balance)

@app.route("/search_customer", methods=["POST"])
def search_customer():
    customer_id = request.form.get("customer_id")

    if not customer_id or not customer_id.isdigit(): 
        flash("Felaktigt kundnummer! Endast positiva siffror är tillåtna.", "error")
        return redirect(url_for("all_customers"))

    customer_id = int(customer_id) 

    if customer_id <= 0: 
        flash("Kundnummer måste vara större än 0.", "error")
        return redirect(url_for("all_customers"))

    if customer_id > 500: 
        flash("Kundnummer får inte vara större än 500.", "error")
        return redirect(url_for("all_customers"))

    return redirect(url_for("customer_details", customer_id=customer_id))

@app.route("/account/<int:account_id>")
@login_required #både admin och cashier
def account_details(account_id):
    with app.app_context():
        account = Account.query.get_or_404(account_id) 
        transactions = Transaction.query.filter_by(account_id=account.id).order_by(Transaction.date.desc()).all()  
    return render_template("account_details.html", account=account, transactions=transactions)

@app.route("/all_accounts")
def all_accounts():
    with app.app_context():
        accounts = Account.query.all()
    return render_template("accounts.html", accounts=accounts)

@app.route("/deposit/<int:account_id>", methods=["POST"])
@roles_required("Cashier")  
def deposit(account_id):
    amount = request.form.get("amount", type=Decimal)
    
    if amount is None or amount <= 0:
        flash("Felaktigt belopp. Insättning måste vara större än 0.", "error")
        return redirect(url_for("account_details", account_id=account_id))

    with app.app_context():
        account = Account.query.get_or_404(account_id)
        new_balance = account.balance + amount

        new_transaction = Transaction(
            type=TransactionType.CREDIT,
            operation=TransactionOperation.DEPOSIT_CASH,
            amount=amount,
            new_balance=new_balance,
            account_id=account.id,
            date=datetime.now()
        )

        account.balance = new_balance 
        db.session.add(new_transaction)
        db.session.commit()

    flash(f"{amount:.2f} kr sattes in på konotnummer: {account_id}.", "slutfört")
    return redirect(url_for("account_details", account_id=account_id))

@app.route("/withdraw/<int:account_id>", methods=["POST"])
@roles_required("Cashier")  
def withdraw(account_id):
    amount = request.form.get("amount", type=Decimal)

    if amount is None or amount <= 0:
        flash("Uttag måste vara större än 0.", "Fel")
        return redirect(url_for("account_details", account_id=account_id))

    with app.app_context():
        account = Account.query.get_or_404(account_id)

        if account.balance < amount:
            flash("Otillräckligt saldo!", "Fel")
            return redirect(url_for("account_details", account_id=account_id))

        new_balance = account.balance - amount

        new_transaction = Transaction(
            type=TransactionType.DEBIT,
            operation=TransactionOperation.ATM_WITHDRAWL,
            amount=amount,
            new_balance=new_balance,
            account_id=account.id,
            date=datetime.now()
        )

        account.balance = new_balance
        db.session.add(new_transaction)
        db.session.commit()

    flash(f"{amount:.2f} kr togs ut från konto: {account_id}.", "slutfört")
    return redirect(url_for("account_details", account_id=account_id))

@app.route("/transfer/<int:account_id>", methods=["POST"])
@roles_required("Cashier")  
def transfer(account_id):
    target_account_id = request.form.get("target_account", type=int)
    amount = request.form.get("amount", type=Decimal)

    if amount is None or amount <= 0:
        flash("Överföring måste vara större än 0!", "FEL")
        return redirect(url_for("account_details", account_id=account_id))

    with app.app_context():
        source_account = Account.query.get_or_404(account_id)
        target_account = Account.query.get_or_404(target_account_id)

        if source_account.balance < amount:
            flash("Otillräckligt saldo för överföring!", "FEL")
            return redirect(url_for("account_details", account_id=account_id))

        source_new_balance = source_account.balance - amount
        source_transaction = Transaction(
            type=TransactionType.DEBIT,
            operation=TransactionOperation.TRANSFER,
            amount=amount,
            new_balance=source_new_balance,
            account_id=source_account.id,
            date=datetime.now()
        )

        target_new_balance = target_account.balance + amount
        target_transaction = Transaction(
            type=TransactionType.CREDIT,
            operation=TransactionOperation.TRANSFER,
            amount=amount,
            new_balance=target_new_balance,
            account_id=target_account.id,
            date=datetime.now()
        )

        source_account.balance = source_new_balance
        target_account.balance = target_new_balance

        db.session.add(source_transaction)
        db.session.add(target_transaction)
        db.session.commit()

    flash(f"{amount:.2f} kr överfördes till konto: {target_account_id}.", "slutfört")
    return redirect(url_for("account_details", account_id=account_id))

@app.route("/customer/<int:customer_id>")
@login_required #både admin och cashier
def customer_details(customer_id):
    with app.app_context():
        customer = db.session.query(Customer).options(db.joinedload(Customer.accounts)).filter(Customer.id == customer_id).first_or_404()
        accounts = Account.query.filter_by(customer_id=customer.id).all()
        total_balance = db.session.query(db.func.sum(Account.balance)).filter(Account.customer_id == customer.id).scalar() or 0
    return render_template("customer_details.html", customer=customer, accounts=accounts, total_balance=total_balance)


@app.route("/transactions")
@roles_required("Cashier") #annars login_required om admin också ska få se? fråga Sebastian
def transactions():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template("transactions.html", transactions=transactions)


@app.route("/all_customers")
@login_required #både admin och cashier
def all_customers():
    sort_order = request.args.get("sort_order", "asc")  
    sort_column = request.args.get("sort_column", "id")  
    search_word = request.args.get("q", "")  
    page = request.args.get("page", 1, type=int)  
    per_page = 50  

    search_customers = Customer.query.filter(
        Customer.given_name.ilike(f"%{search_word}%") |
        Customer.surname.ilike(f"%{search_word}%") |
        Customer.city.ilike(f"%{search_word}%")
    )

    order_by = Customer.id
    if sort_column == "given_name":
        order_by = Customer.given_name
    elif sort_column == "surname":
        order_by = Customer.surname
    elif sort_column == "city":
        order_by = Customer.city

    order_by = order_by.asc() if sort_order == 'asc' else order_by.desc()

    all_customers = search_customers.order_by(order_by)
    pagination_object = all_customers.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "customers.html",
        customers=pagination_object.items,  
        has_prev=pagination_object.has_prev,
        has_next=pagination_object.has_next,
        pages=pagination_object.pages,
        iter_pages=pagination_object.iter_pages,
        sort_column=sort_column,
        sort_order=sort_order,
        page=page,
        q=search_word
    )


if __name__ == "__main__":
    with app.app_context():
        seed_users()
        seedData(db) 

    app.run(debug=True)
