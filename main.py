import os
from datetime import timedelta
from flask import Flask

import config
from auth import auth_bp
from user import user_bp
from WTB_DataRequest import WTB_DataRequest
from WTB_WrongTopicPaper import WTB_WrongTopicPaper
from WTB_OfficialRequest import WTB_Official

base_dir = os.path.abspath(os.path.dirname(__file__))
template_path = os.path.join(base_dir, 'templates')
static_path = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_path, static_folder=static_path)
app.secret_key = config.SESSION_KEY
app.permanent_session_lifetime = timedelta(days=7)

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(user_bp)
app.register_blueprint(WTB_DataRequest)
app.register_blueprint(WTB_WrongTopicPaper)
app.register_blueprint(WTB_Official)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

# 通用函数==================================================================
