from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, URLField
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
