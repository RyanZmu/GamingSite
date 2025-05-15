from crypt import methods
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
import re
from dotenv import load_dotenv
import requests
from flask_wtf.csrf import CSRFProtect
from forms import RegisterForm, LoginForm, DiscoverForm, SearchForm
from database import db
from database import User
from flask_ckeditor import CKEditor
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
import psycopg2
from random import randint
from datetime import datetime
# import requests_cache
# from requests_cache import CachedSession

app = Flask(__name__)

load_dotenv()

TWITCH_CLIENT = os.environ.get("TWITCH_CLIENT")
TWITCH_SECRET = os.environ.get("TWITCH_SECRET")
BANNED_NAMES = os.environ.get("BANNED_NAMES")
SECRET_WTF_KEY = os.environ.get("WTF_CSRF_SECRET_KEY")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY")

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

# API global return vars
igdb_queries = {
    "igdb_top": [],
    "igdb_random": [],
    "igdb_upcoming": [],
    "igdb_searched": [],
}

def get_twitch_token():
    # Get token from Twitch
    # TODO Change logic so a token is requested only when expired - maybe move back into its own function
    token_request = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={TWITCH_CLIENT}"
                                  f"&client_secret={TWITCH_SECRET}&grant_type=client_credentials")
    print(token_request.json())
    token = token_request.json()["access_token"]

    return token

def igdb_api(**kwargs):
    global igdb_queries
    print("api called")
    # Default limit for api call, override with kwargs
    limit = 100

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

    # if current_user.is_authenticated and kwargs:
    #     game_ids = kwargs["game_ids"]
    #     igdb_request_by_id = requests.post(
    #         url=f"{igdb_endpoint}/games",
    #         headers=headers,
    #         data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where id=({game_ids});")
    #     igdb_request_by_id_data = igdb_request_by_id.json()
    #     # print(igdb_request_by_id_data)

        #
        # igdb_queries["user_game_data"] = igdb_request_by_id_data
        # # # print(igdb_queries["user_game_data"])
        #
        # redirect(url_for("home"))
        # return igdb_request_by_id_data

    # # Discover Games
    if kwargs and kwargs["request_type"] == "discover":
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
    # print(len(igdb_random_data))
    if len(igdb_random_data) == 0:
        igdb_request = requests.post(
            url=f"{igdb_endpoint}/games",
            headers=headers,
            data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where rating > {randint(60, 70)} & rating < {randint(80, 100)}; limit {limit}; sort rating desc;")
        igdb_random_data = igdb_request.json()
    # print(igdb_random_data)

    # Get Upcoming games
    current_date = round(datetime.timestamp(datetime.now()))
    print(current_date)
    # TODO get game's timestamp for release date and convert it with date time to get more accurate readings
    # via datetime.fromtimestamp(timestamp).<month/day/year>

    # TODO Work on getting more relevant new releases to display and no duplicates
    igdb_upcoming_request = requests.post(
        url=f"{igdb_endpoint}/release_dates",
        headers=headers,
        data=f"fields *, game.*, game.cover.*, game.release_dates.*, game.first_release_date, game.screenshots.*, game.platforms.*, game.genres.*; where game.first_release_date >= {current_date} & game.hypes >= 10; limit 300; sort date asc;")
    igdb_upcoming_data = igdb_upcoming_request.json()
    # print(igdb_upcoming_data)

    # Remove duplicate games from the upcoming game data post api call
    # Empty array to hold game data and names, due to many duplicate records
    filtered_upcoming_data = []
    game_names = []

    for game in igdb_upcoming_data:
        # Check for unique game name each loop to ensure no duplicates are displayed
        if game["game"]["name"] not in game_names:
            filtered_upcoming_data.append(game)
            game_names.append(game["game"]["name"])

    # Get Top 10 most popular games
    igdb_top_request = requests.post(
            url=f"{igdb_endpoint}/games",
            headers=headers,
            data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where aggregated_rating > {randint(85, 99)}; limit 10; sort aggregated_rating;")
    igdb_top_data = igdb_top_request.json()
    # print(igdb_top_data)

    # TODO: Look into making one large query for everything and cache it
    # Bundle all queries into a single object - igdb_searched empty until a user searches for a game
    igdb_queries = {
        "igdb_top": igdb_top_data,
        "igdb_random": igdb_random_data,
        "igdb_upcoming": filtered_upcoming_data,
        "igdb_searched": []
    }
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
    global igdb_queries

    # Check if the random games list is filled, if not then call the API
    # TODO still consider caching API data instead of relying on this logic
    if len(igdb_queries["igdb_random"]) == 0:
        igdb_api()

    # Get 10 random games to display on homepage for users to check out
    random_games = igdb_queries["igdb_random"]
    # print(random_games)

    # Get the upcoming games for this year (lots of dupes currently)
    upcoming_games = igdb_queries["igdb_upcoming"]
    # print(upcoming_games)

    top_games = igdb_queries["igdb_top"]
    # print(igdb_top)

    # Search
    # TODO work this out so this logic works for any page and the search bar eventually will go into the nav bar
    search_form = SearchForm()

    if search_form.validate_on_submit():
        # Call api and get results, redirect to the results route
        game_query = search_form.data.get("search")
        print(game_query)

        return redirect(url_for("search", game_query=game_query))


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
        discover_form=discover_form,
        search_bar=search_form
    )

# Use this route to let the user Update the games shown and eventually set API update intervals
@app.route(rule="/update", methods=["GET"])
def update_api_data():
    # API call to update DB with new games
    igdb_api()
    flash("Games Updated")
    return redirect(url_for("home"))

@app.route(rule="/results<game_query>", methods=["GET"])
def search(game_query):
    global igdb_queries
    print(game_query)

    igdb_endpoint = "https://api.igdb.com/v4"
    token = get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT,
        "Authorization": f"Bearer {token}",
    }

    # API Call
    game_data_request = requests.post(
        url=f"{igdb_endpoint}/games",
        headers=headers,
        data=f'fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; search "{game_query}"; limit 50;)'
    )
    game_data = game_data_request.json()
    print(game_data)

    igdb_queries["igdb_searched"] = game_data

    return render_template(template_name_or_list="search_results.html", results=game_data)

@app.route(rule="/add_game/<game_id>")
@login_required
def add_game(game_id):
    global igdb_queries
    # Get user's current game list
    game_list = db.session.execute(db.select(User.user_games_saved).where(User.id == current_user.id)).scalar()
    saved_games = db.session.execute(db.select(User.saved_game_data).where(User.id == current_user.id)).scalar()

    # Boolean for if a game is found in one of the lists
    game_found = False

    # Update the list if game is not already in list
    # Update added_games with ID
    if game_id not in game_list["added_games"]:
        game_list["added_games"].append(int(game_id))

    # TODO Add the populates the game_page instead of using the query object - add a way to know if an add
    #  is from game_page
    # Loops through both top and random games, will need on for upcoming
    # TODO Condense this down into as few loops as possible to avoid 2-3 loops at once - performance
    # TODO refactor to handle data as cache instead of vars
    if game_found is False:
        for game in igdb_queries["igdb_random"]:
            print(f"found {game['name']} in random")
            if int(game["id"]) == int(game_id):
                print(f"adding {game['name']}")
                saved_games["game_data"].append(game)
                game_found = True
                flash(f"{game['name']} added to library")

    if game_found is False:
        for game in igdb_queries["igdb_top"]:
            print(f"found {game['name']} in top")
            if int(game["id"]) == int(game_id):
                print(f"adding {game['name']}")
                saved_games["game_data"].append(game)
                game_found = True
                flash(f"{game['name']} added to library")

    if game_found is False and len(igdb_queries["igdb_searched"]) > 0:
        for game in igdb_queries["igdb_searched"]:
            print(f"found {game['name']} in searched")
            if int(game["id"]) == int(game_id):
                print(f"adding {game['name']}")
                saved_games["game_data"].append(game)
                game_found = True
                flash(f"{game['name']} added to library")

    if game_found is False:
        # game ID must be set for upcoming section
        for game in igdb_queries["igdb_upcoming"]:
            print(f"found {game['game']['name']} in upcoming")
            if int(game['game']["id"]) == int(game_id):
                print(f"adding {game['game']['name']}")
                saved_games["game_data"].append(game['game'])
                game_found = True
                flash(f"{game['game']['name']} added to library")

    if game_found:
        # Add the updated list to the DB and commit
        db.session.execute(db.update(User).where(User.id == current_user.id).values(user_games_saved=game_list))
        db.session.execute(db.update(User).where(User.id == current_user.id).values(saved_game_data=saved_games))
        db.session.commit()

    return redirect(url_for(endpoint="home"))

@app.route(rule="/remove_game/<game_id>")
@login_required
def remove_game(game_id):
    # Get user's current game list
    game_list = db.session.execute(db.select(User.user_games_saved).where(User.id == current_user.id)).scalar()

    if int(game_id) in game_list["added_games"]:
        print(f"Removing {game_id}")
        game_list["added_games"].pop(game_list["added_games"].index(int(game_id)))
        flash(f"Game removed from library")

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


# Game Page
@app.route(rule="/game/<game_id>", methods=["GET"])
def game_page(game_id):
    global igdb_queries

    # TODO in future avoid API call if the game's data is present in igdb query data
    igdb_endpoint = "https://api.igdb.com/v4"
    token = get_twitch_token()

    headers = {
        "Client-ID": TWITCH_CLIENT,
        "Authorization": f"Bearer {token}",
    }

    # API Call to IGDB for game info
    game_data_request = requests.post(
        url=f"{igdb_endpoint}/games",
        headers=headers,
        data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*, "
             f"age_ratings.*, artworks.*, dlcs.*, expansions.*, external_games.*, "
             f"involved_companies.company.*, involved_companies.company.logo.*, similar_games.*, themes.*, language_supports.*, collections.*; where id=({game_id});")
    game_data = game_data_request.json()
    # print(game_data[0])

    # Get Game's news - comment out when testing to avoid excessive api calls
    try:
        # GNEWS API
        gnews_key = os.environ.get("GNEWS_API_KEY")
        gnews_baseurl = "https://gnews.io/api/v4/"

        # remove special chars and then any double spaces left behind when chars are removed - clunky solution.
        game_name = re.sub("[^A-Za-z0-9]|[\s]", " ", game_data[0]["name"])
        # If 2 or more spaces, replace with a SINGLE space to avoid query errors
        game_name_final = re.sub("\s{2,}", " ", game_name)
        print(f"{game_name_final} {game_data[0]['platforms'][0]['abbreviation']}")

        # Add platform abbreviation to help results avoid irrelevant articles
        gnews_params = {
            "apikey": gnews_key,
            "q": f"{game_name_final} {game_data[0]['platforms'][0]['abbreviation']}",
            "lang": "en",
            "country": "us",
            "sortby": "publishedAt",
            "max": 10,
        }

        gnews_search = requests.get(f"{gnews_baseurl}/search", params=gnews_params)
        gnews_data = gnews_search.json()
        print(gnews_data)

        news_articles = gnews_data["articles"]

    except KeyError as e:
        print("Error: news api data missing - possible rate limit hit or query error")
        print(e)
        news_articles = []
    else:
        print("news api data found")

    # news_articles = []

    return render_template( template_name_or_list="game_page.html", game=game_data[0], game_news=news_articles)

# Search Route here to lead to game pages
# First user searches then sees a results page, clicks name of game and then the id is passed that way
# Just like with Movie DB project

# Use this route to test page layouts and other ideas
@app.route(rule="/test", methods=["GET"])
def test():
    # # Test caching data from API
    # requests_cache.install_cache('games_cache', backend='sqlite', expire_after=180)
    # print("creating cache")
    # # create a cached session
    #
    # # Default limit for api call, override with kwargs
    # limit = 20
    #
    # igdb_endpoint = "https://api.igdb.com/v4"
    #
    # # Get token from Twitch
    # # TODO Change logic so a token is requested only when expired - maybe move back into its own function
    # token_request = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={TWITCH_CLIENT}"
    #                               f"&client_secret={TWITCH_SECRET}&grant_type=client_credentials")
    # print(token_request.json())
    # token = token_request.json()["access_token"]
    #
    # headers = {
    #     "Client-ID": TWITCH_CLIENT,
    #     "Authorization": f"Bearer {token}",
    # }
    #
    # igdb_request = requests.post(
    #     url=f"{igdb_endpoint}/games",
    #     headers=headers,
    #     data=f"fields *, cover.*, platforms.*, release_dates.*, screenshots.*, videos.*, genres.*; where rating > {randint(60, 70)} & rating < {randint(80, 100)}; limit {limit}; sort rating desc;")
    # # igdb_random_data = igdb_request.json()
    # requests_cache.get_cache().save_response(igdb_request)
    #
    # print(igdb_request.)

    return render_template(template_name_or_list="test.html")


if __name__ == "__main__":
    app.run(debug=True)
