# wsgi.py
# Flask项目的入口文件，供gunicorn调用
from main import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)