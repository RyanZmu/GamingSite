from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, URLField, SelectField, RadioField, SelectMultipleField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import DataRequired, Email, Length
from flask_ckeditor import CKEditorField


class RegisterForm(FlaskForm):
    username = StringField(label="Username", validators=[DataRequired()])
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=8)])
    # render_kw sets a keyword for the button, can be used to ID which button is primary if many are on a page
    submit = SubmitField(label="Sign Up!", render_kw={'btn-primary': 'True'})


class LoginForm(FlaskForm):
    email = StringField(label='Email', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=8)])
    # render_kw sets a keyword for the button, can be used to ID which button is primary if many are on a page
    submit = SubmitField(label="Sign In!", render_kw={'btn-primary': 'True'})

class SearchForm(FlaskForm):
    search = StringField(label="Search", validators=[DataRequired()])
    submit = SubmitField(label="Submit", render_kw={'btn-secondary': 'True'})

class DiscoverForm(FlaskForm):
    platform = RadioField(
        label="Platforms",
        choices=["PlayStation", "PlayStation 2", "PlayStation 3", "PlayStation 4", "PlayStation 5", "PlayStation Vita",
                 "PC (Microsoft Windows)", "Xbox", "Xbox 360", "Xbox One", "Xbox Series X", "NES", "SNES", "Wii",
                 "Nintendo Switch", "Nintendo DS", "Sega Dreamcast", "Sega Saturn", "Sega Genesis", "Android", "iOS"],
        validate_choice=False
    )
    genre = RadioField(
        label="Genres",
        choices=['Point-and-click',
                 'Fighting',
                 'Shooter',
                 'Music',
                 'Platform',
                 'Puzzle',
                 'Racing',
                 'Real Time Strategy (RTS)',
                 'Role-playing (RPG)',
                 'Simulator'
                 ],
        validate_choice=False
    )

    submit = SubmitField(
        label="Submit",
        render_kw={'btn-primary': 'True'})
