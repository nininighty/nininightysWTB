import hashlib
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
from db_utils import db_cursor

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        if session.get('logged_in'):
            return redirect(url_for('user.user_home'))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        try:
            with db_cursor() as (conn, cursor):
                cursor.execute(
                    "SELECT id, password_hash, nickname, avatar_url FROM users WHERE username=%s",
                    (username,)
                )
                result = cursor.fetchone()

                if not result:
                    flash("账户错误", "username_error")
                    return redirect(url_for("auth.home"))

                user_id, db_password_hash, nickname, avatar_url = (
                    result['id'],
                    result['password_hash'],
                    result['nickname'],
                    result['avatar_url']
                )

                if password_hash == db_password_hash:
                    session['logged_in'] = True
                    session['username'] = username
                    session['user_id'] = user_id
                    session['nickname'] = nickname if nickname else username
                    session['avatar_url'] = avatar_url if avatar_url else '/static/images/Pic_DefaultAvatar.jpg'

                    if request.form.get("remember_me"):
                        session.permanent = True
                    else:
                        session.permanent = False

                    return redirect(url_for("user.user_home"))
                else:
                    flash("密码错误", "password_error")
                    return redirect(url_for("auth.home"))
        except Exception as err:
            return f"数据库错误: {err}"

    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template("home.html", version_time=now_time)

@auth_bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template("register.html")
    elif request.method == "POST":
        nickname = request.form.get("nickname")
        avatar_url = '/Pic_DefaultAvatar.jpg'
        username = request.form.get("username")
        password = request.form.get("password")
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        if not nickname or not username or not password:
            flash("所有字段均为必填", "error")
            return redirect(url_for("auth.register"))

        try:
            with db_cursor() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
                if cursor.fetchone():
                    flash("该账户已被注册", "error")
                    return redirect(url_for("auth.register"))

                cursor.execute(
                    "INSERT INTO users (username, password_hash, nickname, avatar_url) VALUES (%s, %s, %s, %s)",
                    (username, password_hash, nickname, avatar_url)
                )
                conn.commit()
        except Exception as e:
            print(f"注册出错：{e}")
            flash("注册失败，内部错误", "error")
            return render_template("register.html")

        return redirect(url_for("auth.register_success"))

@auth_bp.route("/register_success")
def register_success():
    return render_template("register_success.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.home"))
