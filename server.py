from types import NoneType
import dotenv
import hashlib
from urllib.parse import urlencode
import sqlalchemy
from sqlalchemy import exc, insert, values
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap5
import os
import time
from dotenv import load_dotenv
import requests
from flask_wtf.csrf import CSRFProtect
from forms import RegisterForm, LoginForm, DiscoverForm
from database import db
from database import User, IGDBData
from flask_ckeditor import CKEditor
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
import psycopg2
from random import randint
from datetime import datetime

app = Flask(__name__)

load_dotenv()

TWITCH_CLIENT = os.environ.get("TWITCH_CLIENT")
TWITCH_SECRET = os.environ.get("TWITCH_SECRET")
BANNED_NAMES = os.environ.get("BANNED_NAMES")
SECRET_WTF_KEY = os.environ.get("WTF_CSRF_SECRET_KEY")

# Enable CSRF for flask forms
csrf = CSRFProtect(app)
# Config app for CSFR with a secret key
app.config["SECRET_KEY"] = SECRET_WTF_KEY
app.secret_key = os.environ.get("APP_SECRET_KEY")

# Load DB
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DB_URI", "sqlite:///main.db")
app.config['BOOTSTRAP_BOOTSWATCH_THEME'] = 'slate'
# init app with extension
db.init_app(app)

# Create the db tables
with app.app_context():
    db.create_all()

# Load bootstrap
bootstrap = Bootstrap5(app)

# Load login manager
login_manager = LoginManager()
login_manager.init_app(app)

def igdb_api(**kwargs):
    print("api called")
    # Default limit for api call, override with kwargs
    limit = 200

    igdb_endpoint = "https://api.igdb.com/v4"

    # Get token from Twitch
    # TODO Change logic so a token is requested only when expired - maybe move back into its own function
    token_request = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={TWITCH_CLIENT}"
                                  f"&client_secret={TWITCH_SECRET}&grant_type=client_credentials")
    print(token_request.json())
    token = token_request.json()["access_token"]

    headers = {
        "Client-ID": TWITCH_CLIENT,
        "Authorization": f"Bearer {token}",
    }

    igdb_random_data = {}

    if kwargs:
        # limit = kwargs["limit"]
        request_type = kwargs["request_type"]

        # TODO Fix this so when a user adds a game, we just pass the data from the DB games table to the user table
        # TODO and add the game data this way there is no need for an api as the data will be saved always
        # TODO Remove this API call after doing the above!
        # Just call API and get user's games info after adding new ones
        if request_type == "user_games":
            game_ids = kwargs["game_ids"]
            igdb_request_by_id = requests.post(
                url=f"{igdb_endpoint}/games",
                headers=headers,
                data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where id=({game_ids});")
            igdb_request_by_id_data = igdb_request_by_id.json()
            # print(igdb_request_by_id_data)

            # Add game data to user's saved_game_data
            user_saved_games = db.session.execute(db.select(User.saved_game_data).where(User.id == current_user.id)).scalar()

            # Data to add
            data = {"game_data": igdb_request_by_id_data}

            if not user_saved_games["game_data"]:
                print("create saved game data")
                user_saved_games = data
            else:
                print("append data")
                print(user_saved_games["game_data"])
                user_saved_games["game_data"].append(igdb_request_by_id_data[0])

            db.session.execute(db.update(User).where(User.id == current_user.id).values(saved_game_data=user_saved_games))
            db.session.commit()

            redirect(url_for("home"))
            return igdb_request_by_id_data

        # Discover Games
        elif request_type == "discover":
            user_choices = kwargs["user_choices"]
            platform = user_choices["platform"]
            genre = user_choices["genre"]
            print(user_choices)
            igdb_request_discover = requests.post(
                url=f"{igdb_endpoint}/games",
                headers=headers,
                data=f'fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where platforms.name = "{platform}" & genres.name = "{genre}"; limit {limit}; sort date desc;'),

            igdb_random_data = igdb_request_discover[0].json()
            # print(igdb_random_data)

    # TODO: Make this more random and varied if possible
    print(len(igdb_random_data))
    if len(igdb_random_data) == 0:
        igdb_request = requests.post(
            url=f"{igdb_endpoint}/games",
            headers=headers,
            data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where rating > {randint(60, 70)} & rating < {randint(80, 100)}; limit {limit}; sort rating desc;")
        igdb_random_data = igdb_request.json()
    # print(igdb_random_data)

    # Get Upcoming games
    # current_year = str(datetime.year)
    # print({"current_year": current_year})

    # TODO Work on getting more relevant new releases to display and no duplicates
    igdb_upcoming_request = requests.post(
        url=f"{igdb_endpoint}/release_dates",
        headers=headers,
        data=f"fields *, game.*, game.cover.*, game.release_dates.*; where y = 2024 & m=(11,12) & game.hypes >= 10; limit 300; sort date asc;")
    igdb_upcoming_data = igdb_upcoming_request.json()
    # print(igdb_upcoming_data)

    # Remove duplicate games from the upcoming game data
    current_game_name = ""
    filtered_upcoming_data = []
    for game in igdb_upcoming_data:
        print(game['game']['name'])

        if game["game"] and game['game']['name'] != current_game_name:
            current_game_name = game["game"]['name']
            filtered_upcoming_data.append(game)
            # print(current_game_name)



    # Get Top 10 most popular games
    igdb_top_request = requests.post(
            url=f"{igdb_endpoint}/games",
            headers=headers,
            data=f"fields *, cover.*, platforms.*, release_dates.*; where aggregated_rating > {randint(85, 99)}; limit 10; sort aggregated_rating;")
    igdb_top_data = igdb_top_request.json()
    # print(igdb_top_data)

    # TODO: Look into making one large query for everything and sort it nicely in the DB
    # Bundle all queries into a single object
    igdb_queries = {
        "igdb_top": igdb_top_data,
        "igdb_random": igdb_random_data,
        "igdb_upcoming": filtered_upcoming_data
    }

    data = IGDBData(
        game=igdb_queries
    )

    db.session.execute(db.select(IGDBData))

    try:
        db.session.add(data)
        db.session.commit()
    except exc.IntegrityError:
        print("DB DATA UPDATE NOT NEEDED")
    else:
        print("DB DATA UPDATED")

    return igdb_queries

# User Routes
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    requested_email = login_form.data.get("email")
    requested_password = login_form.data.get("password")

    if login_form.validate_on_submit():
        requested_user = db.session.execute(db.select(User).where(User.email == requested_email)).scalar()
        if requested_user is not None:
            if check_password_hash(requested_user.password, requested_password):
                login_user(requested_user)
                flash(f"Welcome {current_user.username}!")
                return redirect(url_for("home"))
            else:
                flash("Wrong Credentials please try again!")
        else:
            flash("Wrong Credentials please try again!")

    return render_template(
        template_name_or_list="user_forms.html",
        form=login_form
    )

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged Out")
    return redirect(url_for("home"))

@app.route("/register", methods=["POST", "GET"])
def register_user():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        db.session.execute(db.select(User))

        # Encoded email for gravatar usage
        email_encoded = register_form.data.get("email").lower().encode('utf-8')

        # noinspection PyArgumentList
        new_user = User(
            username=register_form.data.get("username"),
            email=register_form.data.get("email"),
            email_hash=hashlib.sha256(email_encoded).hexdigest(),
            password=generate_password_hash(register_form.data.get("password"), method="scrypt", salt_length=10),
            user_games_saved={"added_games": []},
            saved_game_data={"game_data": []}
        )

        # Add a default profile pic after email is hashed
        new_user.profile_pic = f"https://gravatar.com/avatar/{new_user.email_hash}?d=retro&s=40"

        try:
            db.session.add(new_user)
            db.session.commit()
        except exc.IntegrityError:
            # Add flash
            flash("User exists with this email or username!")
        else:
            login_user(new_user)
            flash(f"Thanks for joining SavePoint! {current_user.username}!")
            return redirect(url_for("home"))

    return render_template(
        template_name_or_list="user_forms.html",
        form=register_form
    )

# Main Site Routes
@app.route(rule="/", methods=["GET", "POST"])
def home(**kwargs):
    # Grab games from DB instead of API call
    game_data = db.session.execute(db.select(IGDBData)).scalars().all()
    igdb_calls = {}
    for game in game_data:
        igdb_calls = {
            "igdb_top": game.game["igdb_top"],
            "igdb_random": game.game["igdb_random"],
            "igdb_upcoming": game.game["igdb_upcoming"]
        }


    # Get 10 random games to display on homepage for users to check out
    random_games = igdb_calls["igdb_random"]
    # print(random_games)

    # Get the upcoming games for this year (lots of dupes currently)
    upcoming_games = igdb_calls["igdb_upcoming"]
    # print(upcoming_games)

    top_games = igdb_calls["igdb_top"]
    # print(igdb_top)

    # Discovery Form
    discover_form = DiscoverForm()

    # TODO currently will get games from platforms, however page needs to reload for games to display
    # TODO Find all the ways IGDB names platforms and correct the form choices
    if discover_form.validate_on_submit():
        platform = discover_form.data.get("platform")
        genre = discover_form.data.get("genre")

        user_choices = {
            "platform": platform,
            "genre": genre,
        }
        igdb_api(request_type="discover", user_choices=user_choices)
        return redirect(url_for("home"))


    return render_template(
        template_name_or_list="main.html",
        random_games=random_games,
        upcoming_games=upcoming_games,
        top_games=top_games,
        api_call=igdb_api,
        date=datetime.now(),
        time=time.time(),
        add_game=add_game,
        random_number=randint(0, len(random_games)-1),
        discover_form=discover_form,
    )

# Use this route to let the user Update the games shown and eventually set API update intervals
@app.route(rule="/update", methods=["GET"])
def update_api_data():
    # API call to update DB with new games
    igdb_api()
    flash("Games Updated")
    return redirect(url_for("home"))

# TODO: Add a Remove game route as well
@app.route(rule="/add_game/<game_id>")
@login_required
def add_game(game_id):
    # Get user's current game list
    game_list = db.session.execute(db.select(User.user_games_saved).where(User.id == current_user.id)).scalar()
    # Update the list if game is not already in list
    # Update added_games with ID
    if game_id not in game_list["added_games"]:
        game_list["added_games"].append(int(game_id))
        # TODO: Change this flash to display game names instead of ID numbers
        flash(f"{game_id} added to library")

        # Add the updated list to the DB and commit
        db.session.execute(db.update(User).where(User.id == current_user.id).values(user_games_saved=game_list))
        db.session.commit()

        # Do an API call to just update user's games using Kwargs
        # Call on API for newest game data
        igdb_api(request_type="user_games", game_ids=int(game_id))

    return redirect(url_for(endpoint="home"))

@app.route(rule="/remove_game/<game_id>")
@login_required
def remove_game(game_id):
    # Get user's current game list
    game_list = db.session.execute(db.select(User.user_games_saved).where(User.id == current_user.id)).scalar()

    print(game_list)
    print(game_id)

    if int(game_id) in game_list["added_games"]:
        print(f"Removing {game_id}")
        game_list["added_games"].pop(game_list["added_games"].index(int(game_id)))
        # TODO: Change this flash to display game names instead of ID numbers
        flash(f"{game_id} removed from library")

        # Add the updated list to the DB and commit
        db.session.execute(db.update(User).where(User.id == current_user.id).values(user_games_saved=game_list))
        db.session.commit()

    # Remove game data
    user_saved_games = db.session.execute(db.select(User.saved_game_data).where(User.id == current_user.id)).scalar()

    for game in user_saved_games["game_data"]:
        current_id = game["id"]
        if int(game_id) == current_id:
            print("found saved game data")
            user_saved_games["game_data"].pop(user_saved_games["game_data"].index(game))

            db.session.execute(db.update(User).where(User.id == current_user.id).values(saved_game_data=user_saved_games))
            db.session.commit()

    return redirect(url_for(endpoint="home"))


# Use this route to test page layouts
@app.route(rule="/test", methods=["GET"])
def test():
    return render_template(template_name_or_list="test.html")


if __name__ == "__main__":
    app.run(debug=True)
