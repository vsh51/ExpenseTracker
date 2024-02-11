import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime
import random


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def usd(value):
    """Format value as USD"""
    return f"${value:,.2f}"


def dateFormater(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime('%a %d/%m/%y')


def timeFormater(s):
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S').strftime('%H:%M')


def colorGen(n, c_seed):
    colors_list = []

    for i in range(0, n):
        random.seed(i + c_seed)
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        color = f"rgb({r}, {g}, {b})"
        colors_list.append(color)

    return colors_list


def sortPicker(db, data, param: str, title: str):
    response = db.execute("SELECT t.id, t.user_id, t.amount, t.type, t.time, c.title AS category_title " +
                                      "FROM transactions AS t JOIN categories AS c ON t.category_id = c.id " +
                                      "WHERE strftime('%Y', t.time) = (?) " +
                                      f"AND strftime('{param}', t.time) = (?) " +
                                      "AND t.user_id = (?) " +
                                      "ORDER BY t.time DESC",
                                      data[len(data) - 1]["year"],
                                      data[len(data) - 1][title],
                                      session["user_id"])

    return response