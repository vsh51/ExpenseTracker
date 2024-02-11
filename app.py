import os
import json

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, usd, dateFormater, timeFormater, colorGen, sortPicker

# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///financeTracker.db")

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Custom filter
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["format"] = dateFormater
app.jinja_env.filters["time"] = timeFormater


def incExpTemplate(tp):
    """Template for incomes and expenses separately"""

    if request.method == "GET":
        # Function to create id for sorting transactions daily
        def sort_id_creator(string):
            splt = string.split("-")
            a = splt[1]
            b = str(splt[2]).split(" ", 1)[0]
            return int(a + b)

        # Set up pagination
        weeks_to_be_shown_raw = db.execute("SELECT strftime('%Y', time) AS year, strftime('%W', time) AS week FROM transactions WHERE type=(?) AND user_id=(?) GROUP BY year, week", tp, session["user_id"])
        pg = request.args.get("page")

        if pg != None:
            try:
                pg = int(pg)
            except:
                return apology("Not found", 404)
            if pg - 1 < 0 or pg > len(weeks_to_be_shown_raw):
                return apology("Not found", 404)
        else:
            pg = 1

        # Check if user has any records
        if weeks_to_be_shown_raw != []:
            transactions_raw = db.execute("SELECT t.id, t.user_id, t.amount, t.type, t.time, c.title AS category_title " +
                                      "FROM transactions AS t JOIN categories AS c ON t.category_id = c.id " +
                                      "WHERE strftime('%Y', t.time) = (?) " +
                                      "AND strftime('%W', t.time) = (?) " +
                                      "AND t.user_id = (?) " +
                                      "AND type = (?) "
                                      "ORDER BY t.time DESC",
                                      weeks_to_be_shown_raw[len(weeks_to_be_shown_raw) - pg]["year"],
                                      weeks_to_be_shown_raw[len(weeks_to_be_shown_raw) - pg]["week"],
                                      session["user_id"], tp)

            if pg != None:
                if pg == 1:
                    pagination = {"previous_page": str(pg) + "#", "next_page": pg + 1}
                elif pg == len(weeks_to_be_shown_raw):
                    pagination = {"previous_page": pg - 1, "next_page": str(pg) + "#"}
                else:
                    pagination = {"previous_page": pg - 1, "next_page": pg + 1}
            else:
                pg = 1
                pagination = {"previous_page": str(pg) + "#", "next_page": pg + 1}



            # Create 2 level's list sorted by days
            sort_id = sort_id_creator(transactions_raw[0]["time"])
            transactions = []
            local_daily_list = []
            for transaction in transactions_raw:
                local_sort_id = sort_id_creator(transaction["time"])
                if sort_id == local_sort_id:
                    local_daily_list.append(transaction)
                else:
                    transactions.append(local_daily_list)
                    local_daily_list = []
                    local_daily_list.append(transaction)
                    sort_id = local_sort_id
            transactions.append(local_daily_list)

            return render_template(f"{tp}.html", transactions=transactions, pagination=pagination)
        else:
            pagination = ""
            return render_template(f"{tp}.html", pagination=pagination)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Home page"""

    if request.method == "GET":
        # Function to create id for sorting transactions daily
        def sort_id_creator(string):
            splt = string.split("-")
            a = splt[1]
            b = str(splt[2]).split(" ", 1)[0]
            return int(a + b)

        categ_list = db.execute(
            "SELECT * FROM categories WHERE user_id=(?) OR user_id=(-115)", session["user_id"])

        # Set up pagination
        weeks_to_be_shown_raw = db.execute(
            "SELECT strftime('%Y', time) AS year, strftime('%W', time) AS week FROM transactions WHERE user_id=(?) GROUP BY year, week", session["user_id"])
        if weeks_to_be_shown_raw:
            pg = request.args.get("page")

            if pg != None:
                try:
                    pg = int(pg)
                except:
                    return apology("Not found", 404)
                if pg - 1 < 0 or pg > len(weeks_to_be_shown_raw):
                    return apology("Not found", 404)
            else:
                pg = 1

            transactions_raw = db.execute("SELECT t.id, t.user_id, t.amount, t.type, t.time, c.title AS category_title " +
                                        "FROM transactions AS t JOIN categories AS c ON t.category_id = c.id " +
                                        "WHERE strftime('%Y', t.time) = (?) " +
                                        "AND strftime('%W', t.time) = (?) " +
                                        "AND t.user_id = (?) " +
                                        "ORDER BY t.time DESC",
                                        weeks_to_be_shown_raw[len(weeks_to_be_shown_raw) - pg]["year"],
                                        weeks_to_be_shown_raw[len(weeks_to_be_shown_raw) - pg]["week"],
                                        session["user_id"])

            # Check if user has any records
            if transactions_raw != []:

                if pg != None:
                    if pg == 1:
                        if len(weeks_to_be_shown_raw) == 1:
                            pagination = {"previous_page": str(pg) + "#", "next_page": str(pg) + "#"}
                        else:
                            pagination = {"previous_page": str(pg) + "#", "next_page": pg + 1}
                    elif pg == len(weeks_to_be_shown_raw):
                        pagination = {"previous_page": pg - 1, "next_page": str(pg) + "#"}
                    else:
                        pagination = {"previous_page": pg - 1, "next_page": pg + 1}
                else:
                    pg = 1
                    pagination = {"previous_page": str(pg) + "#", "next_page": pg + 1}

                # Create 2 level's list sorted by days
                sort_id = sort_id_creator(transactions_raw[0]["time"])
                transactions = []
                local_daily_list = []
                total_inDay_counter = {"income": 0, "expense": 0}
                for transaction in transactions_raw:
                    local_sort_id = sort_id_creator(transaction["time"])
                    if sort_id == local_sort_id:
                        local_daily_list.append(transaction)

                        # Count day volume
                        if transaction["type"] == "income":
                            total_inDay_counter["income"] += transaction["amount"]
                        else:
                            total_inDay_counter["expense"] += transaction["amount"]
                    else:
                        local_daily_list.append(json.loads(str(total_inDay_counter).replace("'", '"')))
                        transactions.append(local_daily_list)
                        total_inDay_counter["income"] = 0
                        total_inDay_counter["expense"] = 0
                        local_daily_list = []
                        local_daily_list.append(transaction)
                        sort_id = local_sort_id

                        # Count day volume
                        if transaction["type"] == "income":
                            total_inDay_counter["income"] += transaction["amount"]
                        else:
                            total_inDay_counter["expense"] += transaction["amount"]

                local_daily_list.append(json.loads(str(total_inDay_counter).replace("'", '"')))
                transactions.append(local_daily_list)
            else:
                pagination = ""

            return render_template("index.html", categ_list=categ_list, transactions=transactions, pagination=pagination)
        else:
            pagination = ""
            return render_template("index.html", categ_list=categ_list, pagination=pagination)
    else:
        db.execute("DELETE FROM transactions WHERE id=(?) AND user_id=(?)",
                   request.form.get("id"), session["user_id"])
        return redirect("/")


@app.route("/incomes", methods=["GET"])
@login_required
def incomes():
    """Incomes"""

    return incExpTemplate('income')


@app.route("/expenses", methods=["GET"])
@login_required
def expenses():
    """Expenses"""

    return incExpTemplate('expense')


@app.route("/statistics", methods=["GET"])
@login_required
def statistics():
    """Statistics"""

    def distributionAdj(tr_type, param, title, c_seed):
        weeks_to_be_shown_raw = db.execute(
                f"SELECT strftime('%Y', time) AS year, strftime('{param}', time) AS {title} FROM transactions WHERE user_id=(?) GROUP BY year, {title}", session["user_id"])
        if weeks_to_be_shown_raw != []:
            transactions_raw = sortPicker(db, weeks_to_be_shown_raw, param, title)
            weeklyPieData = {"labels": {}, "colors": []}
            for transaction in transactions_raw:
                if transaction["type"] == tr_type:
                    if transaction["category_title"] not in weeklyPieData["labels"]:
                        weeklyPieData["labels"][transaction["category_title"]] = transaction["amount"]
                    else:
                        weeklyPieData["labels"][transaction["category_title"]] += transaction["amount"]
            weeklyPieData["colors"] = colorGen(len(weeklyPieData["labels"]), c_seed)
            return json.dumps(weeklyPieData)
        else:
            return False

    # Adjust data for weekly expense distribution chart
    weeklyPieDataExp = distributionAdj("expense", "%W", "week", 993)

    # Adjust data for weekly income distribution chart
    weeklyPieDataInc = distributionAdj("income", "%W", "week", 69)

    # Adjust data for daily expenses chart
    months_to_be_shown_raw = db.execute(
            "SELECT strftime('%Y', time) AS year, strftime('%m', time) AS month FROM transactions WHERE user_id=(?) GROUP BY year, month", session["user_id"])
    # return months_to_be_shown_raw
    if months_to_be_shown_raw:
        transactions_month_raw = sortPicker(db, months_to_be_shown_raw, "%m", "month")
        dailyExpData = {"data": {}}
        for transaction in transactions_month_raw:
            if transaction["type"] == "expense":
                if datetime.strptime(transaction["time"], '%Y-%m-%d %H:%M:%S').strftime('%d') not in dailyExpData["data"]:
                    dailyExpData["data"][datetime.strptime(transaction["time"], '%Y-%m-%d %H:%M:%S').strftime('%d')] = transaction["amount"]
                else:
                    dailyExpData["data"][datetime.strptime(transaction["time"], '%Y-%m-%d %H:%M:%S').strftime('%d')] += transaction["amount"]
        dailyExpDataMonth = datetime.strptime(transactions_month_raw[0]["time"], '%Y-%m-%d %H:%M:%S').strftime('%B')
        dailyExpData = json.dumps(dailyExpData)
    else:
        dailyExpDataMonth = None
        dailyExpData = None

    return render_template('statistics.html', weeklyPieDataExp=weeklyPieDataExp, weeklyPieDataInc=weeklyPieDataInc, dailyExpData=dailyExpData, dailyExpDataMonth=dailyExpDataMonth)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Settings"""

    if request.method == "POST":
        # Deleting category
        if request.form.get("category2del"):
            db.execute("DELETE FROM transactions WHERE category_id=(?) AND user_id=(?)", db.execute("SELECT * FROM categories WHERE title=(?)", request.form.get("category2del"))[0]["id"], session["user_id"])
            db.execute("DELETE FROM categories WHERE user_id=(?) AND title=(?)", session["user_id"], request.form.get("category2del"))

        # Adding category
        elif request.form.get("category"):
            existing_categories_raw = db.execute("SELECT title FROM categories WHERE user_id=(?) OR user_id=(-115)", session["user_id"])
            existing_categories = []
            for category in existing_categories_raw:
                existing_categories.append(category["title"])
            if request.form.get("category") not in existing_categories:
                db.execute("INSERT INTO categories (user_id, title) VALUES (?, ?)",  session["user_id"], request.form.get("category"))
            else:
                return apology("Category already in use", 418)

        # Changing password
        elif request.form.get("oldPassword") and request.form.get("newPassword") and request.form.get("confirmation"):
            user = db.execute("SELECT * FROM users WHERE id = (?)", session["user_id"])

            # Checking if password and confirmation matches
            if request.form.get("newPassword") == request.form.get("confirmation"):

                # Checking if old password is correct
                if check_password_hash(user[0]["hash"], request.form.get("oldPassword")):
                    db.execute("UPDATE users SET hash=(?) WHERE id=(?)", generate_password_hash(request.form.get("newPassword")), session["user_id"])
                else:
                    return apology("Incorect old password", 422)
            else:
                return apology("Passwords do not match", 422)
        else:
            return apology("Invalid input", 422)

    categ_list = db.execute("SELECT * FROM categories WHERE user_id=(?)", session["user_id"])

    return render_template("settings.html", categ_list=categ_list)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    try:
        if session["user_id"]:
            return redirect("/")
    except:

        # Forget any user_id
        session.clear()

        # User reached route via POST (as by submitting a form via POST)
        if request.method == "POST":

            # Ensure username was submitted
            if not request.form.get("username"):
                return apology("must provide username", 403)

            # Ensure password was submitted
            elif not request.form.get("password"):
                return apology("must provide password", 403)

            # Query database for username
            user = db.execute(
                "SELECT * FROM users WHERE username = ?", request.form.get("username"))

            # Ensure username exists and password is correct
            if len(user) != 1 or not check_password_hash(user[0]["hash"], request.form.get("password")):
                return apology("invalid username and/or password", 403)

            # Remember which user has logged in
            session["user_id"] = user[0]["id"]

            # Redirect user to home page
            return redirect("/")

        # User reached route via GET (as by clicking a link or via redirect)
        else:
            return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    try:
        if session["user_id"]:
            return redirect("/")
    except:

        if request.method == "POST":
            # Checking if inputs are not blank
            if not request.form.get("username"):
                return apology("type username")
            if not request.form.get("password"):
                return apology("type password")
            if not request.form.get("confirmation"):
                return apology("type confirmation")

            # Check if password and confirmation are the same
            if request.form.get("password") != request.form.get("confirmation"):
                return apology("password and confirmation does not match")
            else:
                username = request.form.get("username")
                password = request.form.get("password")

                # Checking if username exists in the database
                row = db.execute(
                    "SELECT * FROM users WHERE username = (?)", username)
                if len(row) == 1:
                    return apology("Sorry, username already exists", 400)

                db.execute("INSERT INTO users (username, hash) VALUES (?, ?)",
                           username, generate_password_hash(password))
                user = db.execute(
                    "SELECT * FROM users WHERE username = ?", username)

                session["user_id"] = user[0]["id"]

                return redirect("/")

        else:
            return render_template("register.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/record", methods=["GET", "POST"])
@login_required
def record():
    """Add record into db"""

    if request.method == "POST":
        if request.form.get("amount") and request.form.get("type") and request.form.get("category") and request.form.get("date"):
            # Save input
            r_amount = request.form.get("amount")
            r_category = request.form.get("category")
            r_type = request.form.get("type")

            # Format time for storing
            r_date_raw = request.form.get("date")
            r_date = datetime.strptime(
                r_date_raw, '%d/%m/%Y %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")

            # Db request
            r_catID = db.execute(
                "SELECT * FROM categories WHERE title=(?) AND (user_id=(?) OR user_id=(-115))", r_category, session["user_id"])[0]["id"]
            if r_catID == []:
                return apology("Invalid input", 422)
            else:
                db.execute("INSERT INTO transactions (user_id, amount, time, category_id, type) VALUES (?, ?, ?, ?, ?)",
                           session["user_id"], r_amount, r_date, r_catID, r_type)
            return redirect("/")
        else:
            return apology("Invalid input", 422)
    else:
        return redirect("/")
