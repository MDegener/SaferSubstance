import csv, os
import urllib.request

from cs50 import SQL
from flask import redirect, render_template, request, session
from functools import wraps

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///safersubstance.db")

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def get_adviceData(substance, filtered=False):

    path = "{}/info/{}.txt".format(os.getcwd(),substance)

    try:
        f = open(path,"r")
    except IOError:
        return None

    _temp = ""
    adviceData = []
    IDs = []

    for line in f:

        #  sequence of "~.~." is the separator between advice entries
        if "~.~." in line:

            # extract advice and author id from file
            # (both are embedded in the separator line -> "~.~.advice_id/author_id\n")
            c = line.lstrip("~.~.").rstrip("\n").split("/")

            id = c[0]
            author = c[1]

            # check if extracted characters are infact numeric IDs
            if id.isnumeric() and author.isnumeric():

                # check for author equality if filtered == True
                if filtered == False or int(author) == session['user_id']:

                    # fill list with adivce IDs for easy access
                    IDs.append(int(id))

                    # save all relevant advice data to list
                    adviceData.append({'id':int(id),'author':int(author),'advice':_temp,'votes':0,'uservote':0})

                # clear temporary string
                _temp = ""

            else:
                _temp += line
        else:
            _temp += line

    f.close()

    if IDs:
        get_votes(adviceData, IDs)

    # sort advice entries based on amount of votes
    adviceData.sort(key=lambda k: k['votes'], reverse=True)   # Thanks to Dave Lasley from stackoverflow

    return adviceData

# get total amount of votes and selected uservote (if logged in)
def get_votes(info, IDs):

    if len(IDs) > 1:
        votes = db.execute("SELECT votes FROM advice WHERE id IN {} ORDER BY id".format(tuple(IDs)))
    else:
        votes = db.execute("SELECT votes FROM advice WHERE id=:id ORDER BY id",id=IDs[0])

    uservotes = {}

    # get uservotes only if the user is logged in
    if session.get('user_id') is not None:

        if len(IDs) > 1:
            q = db.execute("SELECT vote, advice FROM votes WHERE user=:user AND advice IN {} ORDER BY advice".format(tuple(IDs)),user=session['user_id'])
        else:
            q = db.execute("SELECT vote, advice FROM votes WHERE user=:user AND advice=:advice ORDER BY advice",advice=IDs[0],user=session['user_id'])

        # Translate SQL output to a dict with k=advice_id and v=vote
        for e in q:
            uservotes[e['advice']] = e['vote']

    # save data in dict object
    for i, advice in enumerate(info):
        advice['votes'] = votes[i]['votes']

        if advice['id'] in uservotes:
            advice['uservote'] = uservotes[advice['id']]
        else:
            advice['uservote'] = 0

# get all contributed advice from current user
def get_userdata():

    userdata = {}
    substances = []

    q = db.execute("SELECT DISTINCT substance FROM advice WHERE author=:author",author=session['user_id'])

    for e in q:
        substances.append(e['substance'])

    for substance in substances:
        userdata[substance] = get_adviceData(substance, filtered=True)

    return userdata

# add new advice to the txt file and database
def add_advice(substance,advice):

    path = "{}/info/{}.txt".format(os.getcwd(),substance)

    try:
        f = open(path,"a") #append data

    except IOError:
        return False

    db.execute("INSERT INTO advice ('author','substance') VALUES (:id,:name)",id=session['user_id'],name=substance)
    advice_id = db.execute("SELECT id FROM advice WHERE substance=:substance ORDER BY id DESC",substance=substance)

    f.write("{}\n~.~.{}/{}\n".format(advice,advice_id[0]['id'],session['user_id']))
    f.close()

    return True

# check for txt file existence
def supported(substance):

    path = "{}/info/{}.txt".format(os.getcwd(),substance)

    if os.path.isfile(path):
        return True
    else:
        return False