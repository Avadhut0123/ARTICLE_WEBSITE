from flask import (
    Flask,
    render_template,
    flash,
    redirect,
    url_for,
    session,
    logging,
    request,
)

# from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


app = Flask(__name__)

# Config MySQL
app.config["MYSQL_HOST"] = "{{SQL HOST}}"
app.config["MYSQL_USER"] = "{{SQL ROOT}}"
app.config["MYSQL_PASSWORD"] = "{{SQL Pass}}"
app.config["MYSQL_DB"] = "{{SQL DB_NAME}}"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

# Initiate MySQL
mysql = MySQL(app)

# Articles = Articles()


# Index
@app.route("/")
def index():
    return render_template("home.html")


# About
@app.route("/about")
def about():
    return render_template("about.html")


# Articles
@app.route("/articles")
def articles():
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get Articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template("articles.html", articles=articles)
    else:
        msg = "No articles"
        return render_template("articles.html", msg=msg)

    # Close Cursor
    cur.close()


# Single Articles
@app.route("/article/<string:id>")
def article(id):
    # Create Cursor
    cur = mysql.connection.cursor()
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get Article
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    return render_template("article.html", article=article)


# Register Form Class
class RegisterForm(Form):
    name = StringField("Name", validators=[validators.Length(min=1, max=50)])
    username = StringField("Username", validators=[validators.Length(min=4, max=25)])
    email = StringField("Email", validators=[validators.Length(min=1, max=110)])
    password = PasswordField(
        "Password",
        [
            validators.DataRequired(),
            validators.Length(min=1, max=150),
            validators.EqualTo("confirm", message="Password do not match"),
        ],
    )
    confirm = PasswordField("Confirm Password")


# User Register
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)
    if (request.method == "POST") and (form.validate()):
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # create cursor
        cur = mysql.connection.cursor()

        # Execute query
        cur.execute(
            "INSERT INTO users(name,email,username,password) VALUES (%s,%s,%s,%s)",
            (name, email, username, password),
        )

        # commit to DB
        mysql.connection.commit()

        # Close connection
        cur.close()

        flash("You are now registered and log in ", "Success")

        return redirect((url_for("login")))
    return render_template("register.html", form=form)


# User Login
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # Get form Fields
        username = request.form["username"]
        password_candidate = request.form["password"]

        # Create cursor
        cur = mysql.connection.cursor()

        # get user by username
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            # get stored hash
            data = cur.fetchone()
            password = data["password"]

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # passed
                session["logged_in"] = True
                session["username"] = username

                flash("You are now logged in", "success")
                return redirect(url_for("dashboard"))
            else:
                error = "Invalid Login"
                return render_template("login.html", error=error)
            # Close connection
            cur.close()
        else:
            error = "Username not found"
            return render_template("login.html", error=error)

    return render_template("login.html")


# Check if the user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized,Please login", "danger")
            return redirect(url_for("login"))

    return wrap


# Logout
@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for("login"))


# Dashboard
@app.route("/dashboard")
@is_logged_in
def dashboard():
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get Articles
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template("dashboard.html", articles=articles)
    else:
        msg = "No articles"
        return render_template("dashboard.html", msg=msg)

    # Close Cursor
    cur.close()


# Article Form Class
class ArticleForm(Form):
    title = StringField("Title", validators=[validators.Length(min=1, max=200)])
    body = TextAreaField("Body", validators=[validators.Length(min=30)])


# Add Article
@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        body = form.body.data

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute(
            "INSERT INTO articles (title, body,author) values (%s, %s, %s)",
            (title, body, session["username"]),
        )

        # Commit to DB
        mysql.connection.commit()

        # close Connection
        cur.close()

        flash("Article created successfully", "success")
        return redirect(url_for("dashboard"))

    return render_template("add_article.html", form=form)


# Edit Article
@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
    # Create Cursor
    cur = mysql.connection.cursor()

    # Get User by Id
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = article["title"]
    form.body.data = article["body"]

    if request.method == "POST" and form.validate():
        title = request.form["title"]
        body = request.form["body"]

        # Create Cursor
        cur = mysql.connection.cursor()

        # Execute
        cur.execute(
            "UPDATE articles SET title=%s,body=%s WHERE id = %s", (title, body, id)
        )

        # Commit to DB
        mysql.connection.commit()

        # close Connection
        cur.close()

        flash("Article Updated successfully", "success")
        return redirect(url_for("dashboard"))

    return render_template("edit_article.html", form=form)


# Delete Article
@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    # Create Cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    # close Connection
    cur.close()

    flash("Article Deleted successfully", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.secret_key = "secret123"
    app.run(debug=True, port=78)
