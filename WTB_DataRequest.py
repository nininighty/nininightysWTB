import os
import traceback
from datetime import datetime
from flask import Blueprint, jsonify, session, redirect, url_for, request
from werkzeug.utils import secure_filename
from db_utils import db_cursor
import config
import json
from io import BytesIO
from PIL import Image
import io
from natsort import natsorted

WTB_DataRequest = Blueprint('wtb', __name__)
WTBs_path = "./WTBs"
MySQL_PSW = config.MySQL_PSW
IMAGE_BASE_URL = config.IMAGE_BASE_URL
MEMORY_FACTOR = config.MemoryFactor


# 侧边栏请求=================================================
# 创建错题本
@WTB_DataRequest.route("/create_wtb", methods=["POST"])
def create_wtb():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    username = session['username']

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"success": False, "message": "用户不存在"})
        user_id = result['id']

        # 限制最多5个 WTB
        cursor.execute("SELECT COUNT(*) AS count FROM wtbs WHERE user_id = %s", (user_id,))
        count = cursor.fetchone()['count']
        if count >= 10:
            return jsonify({"success": False, "message": "最多只能创建 5 个错题本"})

        data = request.get_json()
        title = data.get('title')
        if not title:
            return jsonify({"success": False, "message": "标题不能为空"})

        cursor.execute(
            "INSERT INTO wtbs (user_id, title, create_time) VALUES (%s, %s, %s)",
            (user_id, title, datetime.now())
        )
        conn.commit()

    return jsonify({"success": True, "message": "错题本创建成功", "title": title})


# 重命名错题本
@WTB_DataRequest.route("/rename_wtb", methods=["POST"])
def rename_wtb():
    data = request.get_json()
    wtb_id = data.get('id')
    new_title = data.get('new_title')
    if not wtb_id or not new_title:
        return jsonify(success=False, message="参数缺失")

    try:
        with db_cursor() as (conn, cursor):
            sql_code = "UPDATE wtbs SET title = %s WHERE id = %s"
            cursor.execute(sql_code, (new_title, wtb_id))
            conn.commit()
            return jsonify(success=True)
    except Exception as e:
        print("修改错题本名称错误:", e)
        return jsonify(success=False, message="数据库操作失败")

# 删除错题本
@WTB_DataRequest.route("/delete_wtb", methods=["POST"])
def delete_wtb():
    data = request.get_json()
    wtb_id = data.get('id')

    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    try:
        with db_cursor() as (conn, cursor):
            # 获取与该错题本相关的所有错题文件路径
            cursor.execute("SELECT file_path, answer_file_path FROM wrong_topic WHERE wtb_id = %s", (wtb_id,))
            files = cursor.fetchall()

            # 遍历文件路径，删除文件
            for f in files:
                for path in (f['file_path'], f['answer_file_path']):
                    if path:
                        full_path = os.path.join(WTBs_path, path)
                        # 如果是用户上传的文件，才进行删除
                        if not path.startswith("Official/") and os.path.exists(full_path):
                            os.remove(full_path)

            # 删除错题本相关的所有记录
            cursor.execute("DELETE FROM chapters WHERE wtb_id = %s", (wtb_id,))
            cursor.execute("DELETE FROM daily_review_stats WHERE wtb_id = %s", (wtb_id,))
            cursor.execute("DELETE FROM review_logs WHERE wtb_id = %s", (wtb_id,))
            cursor.execute("DELETE FROM wrong_topic WHERE wtb_id = %s", (wtb_id,))
            cursor.execute("DELETE FROM wtb_notes WHERE wtb_id = %s", (wtb_id,))
            cursor.execute("DELETE FROM wtbs WHERE id = %s", (wtb_id,))

            conn.commit()

            return jsonify({"success": True})
    except Exception as e:
        print("删除错误:", e)
        return jsonify({"success": False, "message": "数据库操作失败"})


# 获取错题本主界面
@WTB_DataRequest.route("/get_wtb_content", methods=['GET'])
def get_wtb_content():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    show_top_n = request.args.get('show_top_n', default=5, type=int)

    with db_cursor() as (conn, cursor):
        # 获取用户ID
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "用户不存在"}), 404
        user_id = user['id']

        # 标题
        cursor.execute("SELECT title FROM wtbs WHERE id = %s", (wtb_id,))
        title = cursor.fetchone()['title']

        # 总题量
        cursor.execute("SELECT COUNT(*) AS total_questions FROM wrong_topic WHERE wtb_id = %s", (wtb_id,))
        total_questions = cursor.fetchone()['total_questions']

        # 复习率（已复习题目数量 / 总题目数量）
        cursor.execute("SELECT COUNT(*) AS reviewed_count FROM wrong_topic WHERE wtb_id = %s AND is_reviewed = 1",
                       (wtb_id,))
        reviewed_count = cursor.fetchone()['reviewed_count']
        review_rate = reviewed_count / total_questions if total_questions else 0

        # 今日复习量
        today = datetime.now().date()
        cursor.execute("""
            SELECT COUNT(DISTINCT wrong_topic_id) AS today_finished
            FROM review_logs
            WHERE user_id=%s AND wtb_id=%s AND DATE(review_time) = %s
        """, (user_id, wtb_id, today))
        today_finished = cursor.fetchone()['today_finished']

        # 章节统计
        cursor.execute("""
            SELECT
                q.unit_id,
                c.name AS chapter_name,
                COUNT(*) AS question_count,
                AVG(q.current_correct_rate) AS avg_accuracy
            FROM wrong_topic q
            LEFT JOIN chapters c ON c.id = q.unit_id
            WHERE q.wtb_id = %s
            GROUP BY q.unit_id, c.name
            ORDER BY avg_accuracy ASC
            LIMIT %s;
        """, (wtb_id, show_top_n))
        chapter_stats = cursor.fetchall()

        data = {
            "title": title,
            "total_questions": total_questions,
            "review_rate": review_rate,
            "today_finished": today_finished,
            "chapter_stats": chapter_stats,
        }
        return jsonify(data)


# 日历学习量
@WTB_DataRequest.route("/get_monthly_review_stats", methods=['GET'])
def get_monthly_review_stats():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401
    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    date_str = request.args.get('date')  # 格式 "YYYY-MM"
    if not wtb_id or not date_str:
        return jsonify({"success": False, "message": "参数缺失"}), 400

    try:
        year, month = map(int, date_str.split('-'))
    except Exception:
        return jsonify({"success": False, "message": "日期格式错误，应为YYYY-MM"}), 400

    with db_cursor() as (conn, cursor):
        # 获取用户id
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "用户不存在"}), 404
        user_id = user['id']

        # 计算当月起止日期
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"

        # 查询复习量
        cursor.execute("""
            SELECT date, review_count
            FROM daily_review_stats
            WHERE wtb_id=%s AND user_id=%s AND date BETWEEN %s AND %s
        """, (wtb_id, user_id, start_date, end_date))

        rows = cursor.fetchall()
        data = {row['date'].strftime("%Y-%m-%d"): row['review_count'] for row in rows}

        return jsonify({"success": True, "data": data})


# 随机获取备注文本
@WTB_DataRequest.route("/get_random_note_with_topic", methods=['GET'])
def get_random_note_with_topic():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "参数缺失"}), 400

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "用户不存在"}), 404
        user_id = user['id']

        # 随机获取一条对应 wtb_id 的备注，并关联 wrong_topic 获取题目标题
        cursor.execute("""
            SELECT wn.note_text, wt.title AS topic_title
            FROM wtb_notes wn
            LEFT JOIN wrong_topic wt ON wn.wrong_topic_id = wt.id
            WHERE wn.wtb_id = %s
            ORDER BY RAND()
            LIMIT 1
        """, (wtb_id,))
        row = cursor.fetchone()

        if row:
            note_text = row["note_text"]
            topic_title = row["topic_title"] if row["topic_title"] else "未知题目"
            return jsonify({"success": True, "note_text": note_text, "topic_title": topic_title})
        else:
            return jsonify({"success": True, "note_text": "暂无备注", "topic_title": ""})


# ========================   管理错题本   ==========================================
# 修改wtb情况
@WTB_DataRequest.route('/submit_WTBEdit', methods=['POST'])
def submit_WTBEdit():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    try:
        data = request.get_json(force=True)
        # 只处理非标签相关字段，标签单独接口提交
        daily_topic_num = data.get('daily_num')
        label_color = data.get('theme_color')

        with db_cursor() as (conn, cursor):
            # 获取当前用户id
            cursor.execute("SELECT id FROM users WHERE username=%s", (session['username'],))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})
            user_id = user['id']

            # 检查错题本归属
            cursor.execute("SELECT user_id FROM wtbs WHERE id=%s", (wtb_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"success": False, "message": "错题本不存在"})
            if row['user_id'] != user_id:
                return jsonify({"success": False, "message": "无权限修改此错题本"})

            # 更新字段
            update_fields = []
            params = []
            if daily_topic_num is not None:
                update_fields.append("daily_topic_num=%s")
                params.append(daily_topic_num)
            if label_color is not None:
                update_fields.append("label_color=%s")
                params.append(label_color)

            if not update_fields:
                return jsonify({"success": False, "message": "无更新内容"})

            params.append(wtb_id)
            sql = f"UPDATE wtbs SET {', '.join(update_fields)} WHERE id=%s"
            cursor.execute(sql, params)
            conn.commit()
        return jsonify({"success": True, "message": "错题本信息更新成功"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})

# 获取wtb情况
@WTB_DataRequest.route('/get_WTB_detail')
def get_WTB_detail():
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT label_color, daily_topic_num FROM wtbs WHERE id = %s", (wtb_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "错题本不存在"})

        return jsonify({
            "success": True,
            "theme_color": row['label_color'] or "#00A573",
            "daily_topic_num": row['daily_topic_num'] or 5
        })



# 获取标签情况
@WTB_DataRequest.route('/get_Label_list', methods=["GET"])
def get_Label_list():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    with db_cursor() as (conn, cursor):
        sql_code = "SELECT id, tag_name, weight, color FROM wrong_topic_tags WHERE wtb_id = %s ORDER BY id"
        cursor.execute(sql_code, (wtb_id,))
        rows = cursor.fetchall()
        label_list = [{
            "id": row["id"],
            "tag_name": row["tag_name"],
            "weight": row["weight"],
            "color": row["color"]
        } for row in rows]
        return jsonify({"success": True, "labels": label_list})


# 修改标签情况
@WTB_DataRequest.route('/submit_LabelEdit', methods=['POST'])
def submit_LabelEdit():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']

    data = request.get_json()
    wtb_id = data.get('wtb_id')
    newLabels = data.get('newLabels', [])
    deletedLabels = data.get('deletedLabels', [])
    changedLabels = data.get('changedLabels', {})
    MaxLabels = data.get('MaxLabels', 10)

    if not wtb_id:
        return jsonify({"success": False, "message": "参数错误"})
    if not isinstance(newLabels, list) or not isinstance(deletedLabels, list):
        return jsonify({"success": False, "message": "标签格式错误"})
    try:
        with db_cursor() as (conn, cursor):
            # 获取当前已有标签数量
            cursor.execute(
                "SELECT COUNT(*) AS count FROM wrong_topic_tags WHERE user_id = (SELECT id FROM users WHERE username=%s) AND wtb_id = %s",
                (username, wtb_id)
            )
            existing_count = cursor.fetchone()['count']
            # 限制标签数量
            net_count = existing_count - len(deletedLabels) + len(newLabels)
            if net_count > MaxLabels:
                return jsonify({"success": False, "message": f"标签总数不能超过 {MaxLabels} 个"})

            # 插入新标签
            for label in newLabels:
                name = label.get("name", "").strip()
                color = label.get("color", "#000000")
                weight = label.get("weight", 0.0)

                try:
                    weight = float(weight)
                except:
                    weight = 0.0
                weight = max(-1.0, min(1.0, weight))

                if name:
                    cursor.execute(
                        "INSERT INTO wrong_topic_tags (user_id, wtb_id, tag_name, color, weight, created_at) "
                        "VALUES ((SELECT id FROM users WHERE username=%s), %s, %s, %s, %s, NOW())",
                        (username, wtb_id, name, color, weight)
                    )

            # 删除标签
            for label_id in deletedLabels:
                cursor.execute(
                    "DELETE FROM wrong_topic_tags WHERE id = %s AND user_id = (SELECT id FROM users WHERE username=%s)",
                    (label_id, username)
                )

            # 修改标签
            for label_id, updates in changedLabels.items():
                fields = []
                values = []

                if "name" in updates:
                    fields.append("tag_name = %s")
                    values.append(updates["name"].strip())

                if "color" in updates:
                    fields.append("color = %s")
                    values.append(updates["color"])

                if "weight" in updates:
                    try:
                        weight = float(updates["weight"])
                    except:
                        weight = 0.0
                    weight = max(-1.0, min(1.0, weight))
                    fields.append("weight = %s")
                    values.append(weight)

                if fields:
                    values.extend([label_id, username])
                    cursor.execute(
                        f"UPDATE wrong_topic_tags SET {', '.join(fields)} "
                        "WHERE id = %s AND user_id = (SELECT id FROM users WHERE username=%s)",
                        values
                    )

            conn.commit()
    except Exception as e:
        traceback.print_exc()  # 打印完整异常栈到控制台
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})
    return jsonify({"success": True})


# 主页调用动态图表
@WTB_DataRequest.route('/get_chapter_stats', methods=["GET"])
def get_chapter_stats():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    limit = request.args.get('limit', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    with db_cursor() as (conn, cursor):
        sql = """
        SELECT 
            c.id AS chapter_id,
            c.name AS chapter_name,
            t.id AS tag_id,
            t.tag_name,
            t.color,
            COUNT(w.id) AS question_count
        FROM chapters c
        LEFT JOIN wrong_topic w ON w.unit_id = c.id AND w.wtb_id = %s
        LEFT JOIN wrong_topic_tag_rel rel ON rel.wrong_topic_id = w.id
        LEFT JOIN wrong_topic_tags t ON t.id = rel.tag_id AND t.wtb_id = %s
        WHERE c.wtb_id = %s
        GROUP BY c.id, t.id
        ORDER BY c.id, t.id
        LIMIT %s
        """
        cursor.execute(sql, (wtb_id, wtb_id, wtb_id, limit or 30))
        rows = cursor.fetchall()

        chapters = {}
        for row in rows:
            cid = row["chapter_id"]
            if cid not in chapters:
                chapters[cid] = {
                    "chapter_name": row["chapter_name"],
                    "tags": []
                }
            chapters[cid]["tags"].append({
                "tag_id": row["tag_id"],
                "tag_name": row["tag_name"],
                "color": row["color"],
                "question_count": row["question_count"]
            })
        return jsonify({"success": True, "data": chapters})


# 获取错题本体量
@WTB_DataRequest.route('/get_wrong_topic_count_by_chapter', methods=["GET"])
def get_wrong_topic_count_by_chapter():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    chapter_id_raw = request.args.get('chapter_id')

    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    chapter_id = None if chapter_id_raw == "none" else int(chapter_id_raw)

    with db_cursor() as (conn, cursor):
        if chapter_id is None:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM wrong_topic WHERE wtb_id = %s AND unit_id IS NULL",
                (wtb_id,))
        else:
            cursor.execute(
                "SELECT COUNT(*) AS count FROM wrong_topic WHERE wtb_id = %s AND unit_id = %s",
                (wtb_id, chapter_id))

        row = cursor.fetchone()
        count = row['count'] if row else 0

    return jsonify({"success": True, "count": count})


# 图片压缩
def compress_image(file_storage, max_width=1920, quality=90):
    try:
        img = Image.open(file_storage)

        # 检查宽度是否超限，等比例缩放
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.LANCZOS)

        # 转换为RGB，防止PNG透明图报错
        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality)
        buf.seek(0)
        return buf
    except Exception as e:
        print("图片压缩失败：", e)
        return None


def safe_official_path(sub_path: str) -> str:
    base_path = os.path.abspath(os.path.join(WTBs_path, "Official"))
    abs_path = os.path.abspath(os.path.join(base_path, sub_path))
    if not abs_path.startswith(base_path):
        raise ValueError("非法路径访问")
    if not os.path.isfile(abs_path):
        raise FileNotFoundError("文件不存在")
    return abs_path

# 修改错题
@WTB_DataRequest.route('/update_wrong_topic_detail', methods=['POST'])
def update_wrong_topic_detail():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']

    try:
        with db_cursor() as (conn, cursor):
            # 获取用户 ID
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})
            user_id = user["id"]

            # 提取参数
            wrong_topic_id = request.form.get('wrong_topic_id', type=int)
            note = request.form.get('note', '').strip()
            explanation_url = request.form.get('explanation_url', '').strip()
            flippable_str = request.form.get('flippable', '0').lower()
            is_flippable = 1 if flippable_str in ['1', 'true', 'yes', 'on'] else 0
            review_logs = json.loads(request.form.get('review_logs', '[]'))
            question_file = request.files.get('question_image')
            answer_file = request.files.get('answer_image')
            tags_json = request.form.get('tags', '[]')
            tags = json.loads(tags_json)

            if not wrong_topic_id:
                return jsonify({"success": False, "message": "缺少错题ID"})

            # 查询错题
            cursor.execute("SELECT * FROM wrong_topic WHERE id = %s", (wrong_topic_id,))
            wrong_topic = cursor.fetchone()

            if not wrong_topic:
                return jsonify({"success": False, "message": "错题不存在"})

            # 插入备注记录（如果有新备注）
            if note:
                cursor.execute(
                    """INSERT INTO wtb_notes (wtb_id, wrong_topic_id, note_text, user, created_at)
                       VALUES (%s, %s, %s, %s, NOW())""",
                    (wrong_topic['wtb_id'], wrong_topic_id, note, username)
                )

            # 更新错题的备注和讲解链接
            cursor.execute(
                """UPDATE wrong_topic SET  explanation_url = %s, is_flippable = %s, last_review_date = NOW()
                   WHERE id = %s""",
                (explanation_url, is_flippable, wrong_topic_id)
            )

            if question_file:
                processed_q = compress_image(question_file)
                if processed_q:
                    q_filename = f"{wrong_topic['wtb_id']}_{wrong_topic['unit_id']}_{wrong_topic_id}_question.webp"
                    question_dir = os.path.join(WTBs_path, str(user_id))
                    os.makedirs(question_dir, exist_ok=True)
                    question_path = os.path.join(question_dir, q_filename)
                    with open(question_path, "wb") as f:
                        f.write(processed_q.read())
                    cursor.execute(
                        "UPDATE wrong_topic SET file_path = %s WHERE id = %s",
                        (os.path.join(str(user_id), q_filename), wrong_topic_id)
                    )

            if answer_file:
                processed_a = compress_image(answer_file)
                if processed_a:
                    a_filename = f"{wrong_topic['wtb_id']}_{wrong_topic['unit_id']}_{wrong_topic_id}_answer.webp"
                    answer_dir = os.path.join(WTBs_path, str(user_id))
                    os.makedirs(answer_dir, exist_ok=True)
                    answer_path = os.path.join(answer_dir, a_filename)
                    with open(answer_path, "wb") as f:
                        f.write(processed_a.read())
                    cursor.execute(
                        "UPDATE wrong_topic SET answer_file_path = %s WHERE id = %s",
                        (os.path.join(str(user_id), a_filename), wrong_topic_id)
                    )

            # 先删除所有旧标签
            cursor.execute("DELETE FROM wrong_topic_tag_rel WHERE wrong_topic_id = %s", (wrong_topic_id,))

            # 再插入新标签（如果有）
            for tag_id in tags:
                cursor.execute(
                    "INSERT INTO wrong_topic_tag_rel (wrong_topic_id, tag_id) VALUES (%s, %s)",
                    (wrong_topic_id, int(tag_id))
                )

            # 处理复习记录并更新正确率
            if review_logs:
                if wrong_topic['is_reviewed'] == 0:
                    cursor.execute("UPDATE wrong_topic SET is_reviewed = 1 WHERE id = %s", (wrong_topic_id,))

                for log in review_logs:
                    # 计算新的正确率
                    current_score = wrong_topic['current_correct_rate']
                    for log in review_logs:
                        new_score = log['accuracy']
                        current_score = current_score * 0.6 + new_score * 0.4
                        cursor.execute(
                            "UPDATE wrong_topic SET current_correct_rate = %s WHERE id = %s",
                            (current_score, wrong_topic_id)
                        )

                    # 插入 review_logs 表
                    cursor.execute(
                        """INSERT INTO review_logs (user_id, wtb_id, wtp_id, wrong_topic_id, review_time, accuracy, source, remark)
                           VALUES (%s, %s, %s, %s, NOW(), %s, 'manual', %s)""",
                        (user_id, wrong_topic['wtb_id'], wrong_topic['unit_id'], wrong_topic_id, log['accuracy'],
                         log.get('remark', ''))
                    )

            conn.commit()
            return jsonify({"success": True, "message": "错题修改成功"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 添加错题
@WTB_DataRequest.route('/add_wrong_topic', methods=['POST'])
def add_wrong_topic():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']

    try:
        with db_cursor() as (conn, cursor):
            # 获取用户 ID
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})
            user_id = user["id"]

            # 提取参数
            wtb_id = request.form.get('wtb_id', type=int)
            unit_id = request.form.get('chapter_id', type=int)
            title = request.form.get('title', '').strip()
            if "《" in title or "》" in title:
                return jsonify({"success": False, "message": "不能含有书名号"})

            is_flippable = request.form.get('is_flippable', type=int, default=0)
            explanation_url = request.form.get('explanation_url', '').strip()
            tag_ids = json.loads(request.form.get('tag_ids', '[]') or '[]')

            init_score = request.form.get('init_score', type=float)
            init_score = 0.0 if init_score is None else max(-1.0, min(1.0, init_score))

            # 查询当前 WTB 是否已有同名错题
            cursor.execute("""
                SELECT id FROM wrong_topic 
                WHERE wtb_id = %s AND title = %s
            """, (wtb_id, title))
            existing = cursor.fetchone()
            if existing:
                return jsonify({"success": False, "message": "该错题本中已存在同名题目，请修改标题"})

            if not wtb_id or not title:
                return jsonify({"success": False, "message": "缺少必要参数"})

            # 处理题干图片（question_file）
            question_file = request.files.get('question_file')

            if not question_file:
                return jsonify({"success": False, "message": "必须上传题目图片"})

            # 处理答案图片（answer_file）
            answer_file = request.files.get('answer_file')
            answer_file_path = request.form.get('answer_file', '').strip()

            if not answer_file and answer_file_path.startswith("__official__/"):
                try:
                    sub_path = answer_file_path.replace("__official__/", "")
                    abs_path = safe_official_path(sub_path)
                    with open(abs_path, 'rb') as f:
                        answer_file = BytesIO(f.read())
                        answer_file.name = os.path.basename(abs_path)
                except (ValueError, FileNotFoundError) as e:
                    return jsonify({"success": False, "message": f"答案图片路径错误：{str(e)}"})

            if is_flippable and not answer_file:
                return jsonify({"success": False, "message": "翻转题必须上传答案图片"})

            # 创建用户目录
            user_folder = os.path.join(WTBs_path, str(user_id))
            os.makedirs(user_folder, exist_ok=True)

            # 计算题号序列号
            import re
            existing_files = os.listdir(user_folder)
            pattern = re.compile(rf"{wtb_id}_(?:{unit_id}|None)_(\d+)_question")
            existing_nums = [
                int(match.group(1)) for f in existing_files
                if (match := pattern.match(f))
            ]
            seq_num = max(existing_nums, default=0) + 1

            def make_filename(prefix, ext):
                filename = f"{wtb_id}_{unit_id}_{seq_num}_{prefix}{ext}"
                return secure_filename(filename)

            # 压缩并保存题干图片
            question_path = None
            processed_q = compress_image(question_file)
            if processed_q:
                q_filename = make_filename("question", ".webp")
                with open(os.path.join(user_folder, q_filename), "wb") as f:
                    f.write(processed_q.read())
                question_path = os.path.join(str(user_id), q_filename)
            else:
                return jsonify({"success": False, "message": "题目图片压缩失败"})

            # 压缩并保存答案图片
            answer_path = None
            if answer_file:
                processed_a = compress_image(answer_file)
                if processed_a:
                    a_filename = make_filename("answer", ".webp")
                    with open(os.path.join(user_folder, a_filename), "wb") as f:
                        f.write(processed_a.read())
                    answer_path = os.path.join(str(user_id), a_filename)

            # 写入数据库
            cursor.execute(
                """INSERT INTO wrong_topic
                (wtb_id, unit_id, title, init_score, current_correct_rate, is_flippable, explanation_url,
                 file_path, answer_file_path, created_at, last_review_date, is_reviewed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 0)""",
                (wtb_id, unit_id, title, init_score, init_score, is_flippable, explanation_url,
                 question_path, answer_path)
            )
            wrong_topic_id = cursor.lastrowid

            # 插入标签关联
            for tag_id in tag_ids:
                cursor.execute(
                    "INSERT INTO wrong_topic_tag_rel (wrong_topic_id, tag_id) VALUES (%s, %s)",
                    (wrong_topic_id, tag_id)
                )

            conn.commit()
            return jsonify({"success": True, "message": "错题添加成功"})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


@WTB_DataRequest.route("/get_wrong_topics", methods=["GET"])
def get_wrong_topics():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    wtb_id = request.args.get("wtb_id", type=int)
    chapter_id_raw = request.args.get("chapter_id")

    if not wtb_id:
        return jsonify({"success": False, "message": "缺少参数 wtb_id"})

    if chapter_id_raw in (None, "none"):
        chapter_id = None
    else:
        try:
            chapter_id = int(chapter_id_raw)
        except:
            return jsonify({"success": False, "message": "chapter_id 格式错误"})

    try:
        with db_cursor() as (conn, cursor):
            if chapter_id is None:
                sql = """
                    SELECT 
                      w.id, w.wtb_id, w.unit_id, w.title, w.file_path, w.init_score, w.quality_weight,
                      w.created_at, w.is_reviewed, w.answer_file_path, w.is_flippable, w.explanation_url,
                      w.last_review_date, w.current_correct_rate,
                      c.name AS chapter_name,
                      GROUP_CONCAT(t.tag_name) AS tags
                    FROM wrong_topic w
                    LEFT JOIN chapters c ON w.unit_id = c.id
                    LEFT JOIN wrong_topic_tag_rel rel ON rel.wrong_topic_id = w.id
                    LEFT JOIN wrong_topic_tags t ON t.id = rel.tag_id
                    WHERE w.wtb_id = %s
                    GROUP BY 
                      w.id, w.wtb_id, w.unit_id, w.title, w.file_path, w.init_score, w.quality_weight,
                      w.created_at, w.is_reviewed, w.answer_file_path, w.is_flippable, w.explanation_url,
                      w.last_review_date, w.current_correct_rate,
                      c.name
                    ORDER BY w.created_at DESC
                """
                cursor.execute(sql, (wtb_id,))
            else:
                sql = """
                    SELECT 
                      w.id, w.wtb_id, w.unit_id, w.title, w.file_path, w.init_score, w.quality_weight,
                      w.created_at, w.is_reviewed, w.answer_file_path, w.is_flippable, w.explanation_url,
                      w.last_review_date, w.current_correct_rate,
                      c.name AS chapter_name,
                      GROUP_CONCAT(t.tag_name) AS tags
                    FROM wrong_topic w
                    LEFT JOIN chapters c ON w.unit_id = c.id
                    LEFT JOIN wrong_topic_tag_rel rel ON rel.wrong_topic_id = w.id
                    LEFT JOIN wrong_topic_tags t ON t.id = rel.tag_id
                    WHERE w.wtb_id = %s AND w.unit_id = %s
                    GROUP BY 
                      w.id, w.wtb_id, w.unit_id, w.title, w.file_path, w.init_score, w.quality_weight,
                      w.created_at, w.is_reviewed, w.answer_file_path, w.is_flippable, w.explanation_url,
                      w.last_review_date, w.current_correct_rate,
                      c.name
                    ORDER BY w.created_at DESC
                """
                cursor.execute(sql, (wtb_id, chapter_id))

            rows = cursor.fetchall()

            result = []
            for row in rows:
                tags = row['tags'].split(',') if row['tags'] else []
                result.append({
                    "id": row['id'],
                    "title": row['title'],
                    "unit_id": row['unit_id'],
                    "chapter_name": row['chapter_name'],
                    "tags": tags,
                    "file_path": row['file_path'],
                    "answer_file_path": row['answer_file_path'],
                    "is_flippable": bool(row['is_flippable']),
                    "explanation_url": row['explanation_url'],
                    "created_at": row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                })
            result = natsorted(result, key=lambda x: x['title'])
            return jsonify({"success": True, "data": result})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


@WTB_DataRequest.route("/get_wrong_topic_ReviewLogs", methods=['GET'])
def get_wrong_topic_ReviewLogs():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    username = session['username']
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"success": False, "message": "用户不存在"}), 400
        user_id = user_row['id']

    topic_id = request.args.get("topic_id", type=int)
    if not topic_id:
        return jsonify({"success": False, "message": "缺少参数 topic_id"}), 400

    try:
        with db_cursor() as (conn, cursor):
            sql = """
                SELECT id, review_time, accuracy, source, remark
                FROM review_logs
                WHERE user_id = %s AND wrong_topic_id = %s
                ORDER BY review_time ASC
            """
            cursor.execute(sql, (user_id, topic_id))
            rows = cursor.fetchall()

            data_list = []
            for row in rows:
                data_list.append({
                    "id": row["id"],
                    "review_time": row["review_time"].strftime('%Y-%m-%d %H:%M:%S') if row["review_time"] else None,
                    "accuracy": float(row["accuracy"]) if row["accuracy"] is not None else 0,
                    "source": row["source"],
                    "remark": row["remark"] or "",
                })

            return jsonify({"success": True, "data": data_list})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)}), 500
