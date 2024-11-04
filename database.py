from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, Float, exc, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from flask_login import UserMixin

# DB classes
class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_hash: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    profile_pic: Mapped[str] = mapped_column(String(255), nullable=True)
    user_bio: Mapped[str] = mapped_column(String(255), nullable=True)
    user_games_saved: Mapped[str] = mapped_column(JSON, nullable=True)
    saved_game_data: Mapped[str] = mapped_column(JSON, nullable=True)

class IGDBData(db.Model):
    __tablename__ = "igdb_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game: Mapped[str] = mapped_column(JSON, unique=True, nullable=False)
