import sqlite3

from flask import Flask, redirect, render_template, request, url_for, jsonify
from flask_session import Session
from flask_paginate import Pagination, get_page_parameter
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *

app = Flask(__name__)

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = sqlite3.connect("sqlite:///safersubstance.db")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/info", methods=["GET","POST"])
def info():

    if request.method == "GET":
        substance = request.args.get("substance")
        advice = None

    elif request.method == "POST":
        substance = request.form.get("substance")
        advice = request.form.get("advice")


    if not substance:
        return render_template("index.html")

    # check if txt file with advice exists
    elif supported(substance):

        # add new advice to the page
        if advice and session.get('user_id'):
            add_advice(substance,advice)

        info = get_adviceData(substance)

        page = request.args.get(get_page_parameter(), type=int, default=1)
        per_page = 5
        offset = (page - 1) * per_page

        pagination = Pagination(page=page,per_page=per_page,total=len(info),css_framework='bootstrap4')

        info = info[offset: offset + per_page]

        return render_template("info.html",pagination=pagination,substance=substance,info=info)

    else:
        return render_template("index.html",notify="Sorry, could not find any advice for your substance. Try another?")


@app.route("/voteAdvice", methods=["GET","POST"])
@login_required
def voteAdvice():

    if request.method == "POST":

        data = request.get_json()

        vote = db.execute("SELECT vote FROM votes WHERE user=:user AND advice=:advice",user=data['user'],advice=data['advice'])

        # New Vote
        if not vote:
            db.execute("INSERT INTO votes ('user','advice','vote') VALUES (:user,:advice,:v)",v=data['vote'],user=data['user'],advice=data['advice'])
            db.execute("UPDATE advice SET votes = votes + :v WHERE id=:id",id=data['advice'],v=data['vote'])
            return jsonify({"type": "new"})

        # Change Vote
        elif (vote[0]['vote'] != data['vote']):
            db.execute("UPDATE votes SET vote = :v, datetime = CURRENT_TIMESTAMP WHERE user=:user AND advice=:advice",v=data['vote'],user=data['user'],advice=data['advice'])
            db.execute("UPDATE advice SET votes = votes + :v * 2 WHERE id=:id",id=data['advice'],v=data['vote'])
            return jsonify({"type": "change"})

        # Unvote
        else:
            db.execute("DELETE FROM votes WHERE user=:user AND advice=:advice",user=data['user'],advice=data['advice'])
            db.execute("UPDATE advice SET votes = votes - :v WHERE id=:id",id=data['advice'],v=data['vote'])
            return jsonify({"type": "unvote"})

    else:
        return redirect(url_for("index"))


@app.route("/voteSuggestion", methods=["GET","POST"])
@login_required
def voteSuggestion():

    if request.method == "POST":

        data = request.get_json()

        vote = db.execute("SELECT vote FROM suggestions WHERE user=:user AND substance=:substance",user=data['user'],substance=data['substance'])

        # New Vote
        if not vote:
            db.execute("INSERT INTO suggestions ('user','substance','vote') VALUES (:user,:substance,:v)",v=data['vote'],user=data['user'],substance=data['substance'])
            return jsonify({"type": "new"})

        # Change Vote
        elif (vote[0]['vote'] != data['vote']):
            db.execute("UPDATE suggestions SET vote = :v, datetime = CURRENT_TIMESTAMP WHERE user=:user AND substance=:substance",v=data['vote'],user=data['user'],substance=data['substance'])
            return jsonify({"type": "change"})

        # Unvote
        else:
            db.execute("DELETE FROM suggestions WHERE user=:user AND substance=:substance",user=data['user'],substance=data['substance'])
            return jsonify({"type": "unvote"})

    else:
        return redirect(url_for("index"))


@app.route("/suggestions", methods=['GET','POST'])
@login_required
def suggestions():

    suggestions = []

    totalVotes= db.execute("SELECT substance, SUM(vote) FROM suggestions GROUP BY substance")
    userVotes = db.execute("SELECT substance, vote FROM suggestions WHERE user=:id",id=session['user_id'])

    for substance1 in totalVotes:
        uservote = 0

        for substance2 in userVotes:
            if substance1['substance'] == substance2['substance']:
                uservote = substance2['vote']

        suggestions.append({'substance':substance1['substance'], 'votes':substance1['SUM(vote)'], 'uservote':uservote})

    if request.method == "POST":

        suggestion = request.form.get("suggestion")

        if suggestion:
            db.execute("INSERT INTO suggestions ('user','substance','vote') VALUES (:user,:substance,1)",user=session['user_id'],substance=suggestion)
            suggestions.append({'substance':suggestion, 'votes':1, 'uservote':1})

    suggestions.sort(key=lambda k: k['votes'], reverse=True)   # Thanks to Dave Lasley from stackoverflow

    return render_template("suggestions.html",suggestions=suggestions)

@app.route("/profile")
@login_required
def profile():

    username = db.execute("SELECT username FROM users WHERE id=:id",id=session['user_id'])[0]['username']

    userdata = get_userdata()

    # calculate total karma
    karma = 0
    for k,v in userdata.items():
        for advice in v:
            karma += advice['votes']

    return render_template("profile.html",username=username,userdata=userdata,karma=karma)

@app.route("/login", methods=["GET","POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("login.html",notify="Must provide a username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return render_template("login.html",notify="Must provide a password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username =:username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return render_template("login.html",notify="Sorry, invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("index"))

@app.route("/signup", methods=["GET","POST"])
def signup():
    """Register user."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return render_template("signup.html",notify="must provide username")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username does not already exist
        if len(rows) > 0:
            return render_template("signup.html",notfy="username already taken")

        # ensure password was submitted
        elif not request.form.get("password") or not request.form.get("password_control"):
            return render_template("signup.html",notify="must provide password")

        # ensure passwords match
        elif request.form.get("password") != request.form.get("password_control"):
            return render_template("signup.html",notify="passwords must match")

        else:
            # hash password with CryptContext function
            hash = pwd_context.hash(request.form.get("password"))

            # insert new user into database
            db.execute("INSERT INTO users (username, hash) VALUES (:name,:hash)",name=request.form.get("username"),hash=hash)

            return render_template("login.html")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("signup.html")

@app.route("/mission")
def mission():
    return render_template("mission.html")

if __name__ == "main":
    app.run()