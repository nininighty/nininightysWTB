import traceback
from datetime import datetime
from urllib.parse import quote
from flask import make_response, Blueprint, render_template, session, redirect, url_for, request, jsonify
from db_utils import db_cursor
from config import IMAGE_BASE_URL
from weasyprint import HTML
import io, random
from db_utils import select_weighted_wrong_topics
from natsort import natsorted

WTB_WrongTopicPaper = Blueprint('wtb_detail', __name__)


# 错题卷=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
@WTB_WrongTopicPaper.route('/generate_wrong_topic_paper', methods=['POST'])
def generate_wrong_topic_paper():
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
            data = request.get_json()
            wtb_id = data.get("wtb_id")
            chapter_id = data.get("chapter_id")
            from datetime import datetime

            input_title = data.get("title", "").strip()
            today_str = datetime.now().strftime('%m-%d')
            if input_title:
                cursor.execute("""
                    SELECT COUNT(*) AS cnt FROM wrong_topic_paper
                    WHERE user_id=%s AND wtb_id=%s AND DATE(created_at) = CURDATE()
                """, (user_id, wtb_id))
                count = cursor.fetchone()['cnt'] or 0
                suffix = count + 1
                suffix = int_to_chinese(suffix)
                title = f"{today_str} 自定义卷{suffix}"
            else:
                title = f"{today_str} 每日错题卷"
            # 如果指定了章节 ID，附加章节名
            if chapter_id:
                cursor.execute("SELECT name FROM chapters WHERE id = %s", (chapter_id,))
                chapter = cursor.fetchone()
                if chapter and chapter['name']:
                    title += f" {chapter['name']}专题"

            topic_num = data.get("topic_num")

            if not wtb_id:
                return jsonify({"success": False, "message": "缺少错题本参数"})

            wrong_topics = select_weighted_wrong_topics(user_id, wtb_id, chapter_id)
            if not wrong_topics:
                return jsonify({"success": False, "message": "没有找到符合条件的错题！"})

            topic_num = min(max(topic_num, 1), len(wrong_topics))
            selected_topics = []
            pool = wrong_topics[:]
            while len(selected_topics) < topic_num:
                pick = random.choices(pool, weights=[t['weight'] for t in pool], k=1)[0]
                selected_topics.append(pick)
                pool.remove(pick)

            # 排序
            selected_topics = natsorted(selected_topics, key=lambda x: x['title'])

            cursor.execute("""
                INSERT INTO wrong_topic_paper (user_id, wtb_id, created_at, question_count, title)
                VALUES (%s, %s, NOW(), %s, %s)
            """, (user_id, wtb_id, topic_num, title))
            paper_id = cursor.lastrowid

            for topic in selected_topics:
                flip_flag = 0
                if topic.get('is_flippable', 0) == 1:
                    flip_flag = 1 if random.random() < 0.5 else 0
                cursor.execute("""
                    INSERT INTO wrong_topic_paper_rel (wrong_topic_paper_id, wrong_topic_id, score_ratio, is_flippable)
                    VALUES (%s, %s, %s, %s)
                """, (paper_id, topic['id'], None, flip_flag))

            conn.commit()

            return jsonify({
                "success": True,
                "message": f"成功生成 {topic_num} 道错题的错题卷",
                "paper_id": paper_id,
                "topic_ids": [t['id'] for t in selected_topics]
            })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 获取错题卷列表
@WTB_WrongTopicPaper.route('/get_wrong_topic_paper_list', methods=['GET'])
def get_wrong_topic_paper_list():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']
    wtb_id = request.args.get("wtb_id", type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少错题本参数wtb_id"})
    try:
        with db_cursor() as (conn, cursor):
            # 获取用户 ID
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})

            cursor.execute("""
                SELECT id, title, created_at, question_count 
                FROM wrong_topic_paper 
                WHERE user_id=%s AND wtb_id=%s
                ORDER BY created_at DESC
                LIMIT 100
            """, (user['id'], wtb_id))

            papers = cursor.fetchall()
            result = []
            for p in papers:
                result.append({
                    "id": p['id'],
                    "title": p['title'],
                    "created_at": p['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                    "question_count": p['question_count']
                })

        return jsonify({"success": True, "data": result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 获取错题卷详情
@WTB_WrongTopicPaper.route('/get_wrong_topic_paper_detail', methods=['GET'])
def get_wrong_topic_paper_detail():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']
    wtp_id = request.args.get("wtp_id", type=int)
    if not wtp_id:
        return jsonify({"success": False, "message": "缺少错题卷参数wtp_id"})
    try:
        with db_cursor() as (conn, cursor):
            # 获取用户ID
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})
            user_id = user['id']

            # 查询错题卷基本信息，确保属于当前用户
            cursor.execute("""
                SELECT id, title, created_at, question_count 
                FROM wrong_topic_paper
                WHERE id=%s AND user_id=%s
            """, (wtp_id, user_id))
            paper = cursor.fetchone()
            if not paper:
                return jsonify({"success": False, "message": "错题卷不存在或无权限查看"})

            cursor.execute("""
                SELECT wtp_rel.id as rel_id,
                       wt.id as topic_id,
                       wt.title as topic_title,
                       wtp_rel.is_flippable,
                       wtp_rel.score_ratio
                FROM wrong_topic_paper_rel wtp_rel
                JOIN wrong_topic wt ON wt.id = wtp_rel.wrong_topic_id
                WHERE wtp_rel.wrong_topic_paper_id=%s
            """, (wtp_id,))
            topics = cursor.fetchall()

            topic_list = []
            for t in topics:
                topic_list.append({
                    "rel_id": t["rel_id"],
                    "topic_id": t["topic_id"],
                    "topic_title": t["topic_title"],
                    "is_flippable": t["is_flippable"],
                    "score_ratio": t["score_ratio"]
                })

            return jsonify({
                "success": True,
                "title": paper["title"],
                "question_count": paper["question_count"],
                "data": topic_list
            })


    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


@WTB_WrongTopicPaper.route('/wrong_topic_detail_page')
def wrong_topic_detail_page():
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return "缺少错题本ID (wtb_id)", 400
    topic_id = request.args.get('topic_id', type=int)  # 可选
    return render_template('wrong_topic_detail.html', wtb_id=wtb_id, topic_id=topic_id)


# 错题卷提交得分
@WTB_WrongTopicPaper.route('/submit_score_ratio', methods=['POST'])
def submit_score_ratio():
    if 'username' not in session:
        return redirect(url_for("auth.home"))

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "请求体为空"}), 400

    wtb_id = data.get('wtb_id')
    wtp_id = data.get('wtp_id')
    topic_id = data.get('topic_id')
    score_ratio = data.get('score_ratio')

    if wtp_id is None:
        return jsonify({"success": False, "message": "缺少错题卷 ID"}), 400
    if topic_id is None:
        return jsonify({"success": False, "message": "缺少题目 ID"}), 400
    if score_ratio is None:
        return jsonify({"success": False, "message": "缺少得分数据"}), 400

    username = session['username']

    with db_cursor() as (conn, cursor):
        try:
            # 获取 user_id
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user_row = cursor.fetchone()
            if not user_row:
                return jsonify({"success": False, "message": "用户不存在"}), 400
            user_id = user_row['id']

            now = datetime.now()
            today_date = now.date()

            # 先查询当天是否有review_logs记录
            cursor.execute("""
                SELECT id FROM review_logs
                WHERE user_id=%s AND wtp_id=%s AND wrong_topic_id=%s AND DATE(review_time) = %s
                LIMIT 1
            """, (user_id, wtp_id, topic_id, today_date))
            log = cursor.fetchone()

            if log:
                # 更新当天已有记录
                cursor.execute("""
                    UPDATE review_logs SET accuracy=%s, review_time=NOW()
                    WHERE id=%s
                """, (score_ratio, log['id']))
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO review_logs (user_id, wtp_id, wtb_id, wrong_topic_id, review_time, accuracy, source, remark)
                    VALUES (%s, %s, %s, %s, NOW(), %s, 'daily_set', '')
                """, (user_id, wtp_id, wtb_id, topic_id, score_ratio))

            # 更新错题卷中的得分率（直接更新）
            cursor.execute("""
                UPDATE wrong_topic_paper_rel
                SET score_ratio=%s
                WHERE wrong_topic_paper_id=%s AND wrong_topic_id=%s
            """, (score_ratio, wtp_id, topic_id))

            # 更新错题最后复习时间
            cursor.execute("""
                UPDATE wrong_topic
                SET last_review_date=NOW(), is_reviewed=1
                WHERE id=%s
            """, (topic_id,))

            conn.commit()
            return jsonify({"success": True, "message": "提交成功"})

        except Exception as e:
            traceback.print_exc()
            conn.rollback()
            return jsonify({"success": False, "message": f"数据库错误: {repr(e)}"}), 500


# 生成错题卷PDF
@WTB_WrongTopicPaper.route('/wrong_topic_paper_pdf')
def wrong_topic_paper_pdf():
    if 'username' not in session:
        return redirect(url_for("auth.home"))

    wtp_id = request.args.get('wtp_id', type=int)
    if not wtp_id:
        return "缺少错题卷ID", 400

    username = session['username']
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return "用户不存在", 403
        user_id = user['id']

    with db_cursor() as (conn, cursor):
        cursor.execute("""
            SELECT wt.id as topic_id 
            FROM wrong_topic_paper_rel wtp_rel
            JOIN wrong_topic wt ON wt.id = wtp_rel.wrong_topic_id
            WHERE wtp_rel.wrong_topic_paper_id=%s
        """, (wtp_id,))
        topic_rows = cursor.fetchall()

    if not topic_rows:
        return "该错题卷无错题", 404

    topics_detail = []
    for row in topic_rows:
        topic_detail = fetch_wrong_topic_detail(row['topic_id'])
        if topic_detail:
            topics_detail.append(topic_detail)

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT title FROM wrong_topic_paper WHERE id=%s AND user_id=%s", (wtp_id, user_id))
        paper = cursor.fetchone()
        if not paper:
            return "错题卷不存在或无权限", 404

    # pdf渲染的网页模板
    base_url = request.host_url.rstrip('/')
    wtb_id_for_template = topics_detail[0]['wtb_id'] if topics_detail else None
    html_str = render_template('WrongTopicPaper_PDF.html',
                               title=paper['title'],
                               topics=topics_detail,
                               base_url=base_url,
                               wtb_id=wtb_id_for_template)

    pdf_io = io.BytesIO()
    HTML(string=html_str, base_url=request.host_url).write_pdf(target=pdf_io)

    pdf_data = pdf_io.getvalue()

    response = make_response(pdf_data)
    response.headers["Content-Type"] = "application/pdf"
    filename = f"{paper['title']}.pdf"
    filename_encoded = quote(filename)
    response.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{filename_encoded}"
    return response


def fetch_wrong_topic_detail(topic_id):
    def full_url(path):
        if not path:
            return ""
        return IMAGE_BASE_URL + path.replace("\\", "/")

    with db_cursor() as (conn, cursor):
        # 主信息查询，附带章节和错题本名称
        cursor.execute("""
            SELECT wt.*, c.name AS chapter_name, wtb.title AS wtb_name
            FROM wrong_topic wt
            LEFT JOIN chapters c ON wt.unit_id = c.id
            LEFT JOIN wtbs wtb ON wt.wtb_id = wtb.id
            WHERE wt.id = %s
        """, (topic_id,))
        row = cursor.fetchone()
        if not row:
            return None

        # 标签（含颜色）
        cursor.execute("""
            SELECT t.tag_name, t.color
            FROM wrong_topic_tag_rel r
            JOIN wrong_topic_tags t ON r.tag_id = t.id
            WHERE r.wrong_topic_id = %s
        """, (topic_id,))
        tags = [{"name": r['tag_name'], "color": r['color']} for r in cursor.fetchall()]

        return {
            "id": row['id'],
            "title": row['title'],
            "wtb_id": row['wtb_id'],
            "wtb_name": row['wtb_name'] or "",
            "chapter_name": row['chapter_name'] or "",
            "created_at": row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else "",
            "tags": tags,
            "question_img_url": full_url(row['file_path']),
            "answer_img_url": full_url(row['answer_file_path']),
            "explanation_url": row['explanation_url'] or "",
            "is_flippable": bool(row['is_flippable']),
            "last_review_date": row['last_review_date'].strftime('%Y-%m-%d') if row.get('last_review_date') else None,
            "current_correct_rate": row.get('current_correct_rate', 0.0),
        }


# 错题卷生成

# 复习记录=========================================================
# 添加复习记录（用于手动添加，不包含 wtp_id）
@WTB_WrongTopicPaper.route('/add_review_log', methods=['POST'])
def add_review_log_api():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    data = request.get_json()
    required_fields = ['wtb_id', 'wrong_topic_id', 'score_ratio', 'source']
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "message": f"缺少参数 {field}"}), 400

    username = session['username']
    wtb_id = data['wtb_id']
    wrong_topic_id = data['wrong_topic_id']
    score_ratio = data['score_ratio']
    source = data['source']
    remark = data.get('remark', "")

    try:
        with db_cursor() as (conn, cursor):
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user_row = cursor.fetchone()
            if not user_row:
                return jsonify({"success": False, "message": "用户不存在"}), 400
            user_id = user_row['id']

            sql = """
                INSERT INTO review_logs
                (user_id, wtb_id, wrong_topic_id, review_time, accuracy, source, remark)
                VALUES (%s, %s, %s, NOW(), %s, %s, %s)
            """
            cursor.execute(sql, (user_id, wtb_id, wrong_topic_id, score_ratio, source, remark))
            conn.commit()

        return jsonify({"success": True, "message": "添加复习记录成功"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)}), 500


#     查看复习记录
@WTB_WrongTopicPaper.route("/get_wrong_topic_ReviewDetail", methods=['GET'])
def get_wrong_topic_ReviewDetail():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    # 获取用户ID
    username = session['username']
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            return jsonify({"success": False, "message": "用户不存在"}), 400
        user_id = user_row['id']

    topic_id = request.args.get("topic_id", type=int)
    if not topic_id:
        return jsonify({"success": False, "message": "缺少参数 topic_id"}), 400

    today = datetime.now().date()

    try:
        with db_cursor() as (conn, cursor):
            sql = """
                SELECT id, user_id, wtb_id, wrong_topic_id, review_time, accuracy, source, remark
                FROM review_logs
                WHERE user_id = %s AND wrong_topic_id = %s AND DATE(review_time) < %s
                ORDER BY review_time ASC
            """
            cursor.execute(sql, (user_id, topic_id, today))
            rows = cursor.fetchall()

            data_list = []
            for row in rows:
                data_list.append({
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "wtb_id": row["wtb_id"],
                    "wrong_topic_id": row["wrong_topic_id"],
                    "review_time": row["review_time"].strftime('%Y-%m-%d %H:%M:%S') if row["review_time"] else None,
                    "accuracy": float(row["accuracy"]) if row["accuracy"] is not None else 0,
                    "source": row["source"],
                    "remark": row["remark"] or "",
                })

            return jsonify({"success": True, "data": data_list})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)}), 500


# 通用函数==============================================================
def full_url(path):
    if not path:
        return ""
    return IMAGE_BASE_URL + path.replace("\\", "/")


# 数字转中文
def int_to_chinese(num):
    digits = '零一二三四五六七八九'
    units = ['', '十', '百', '千']
    result = ''
    num_str = str(num)
    length = len(num_str)

    for i, ch in enumerate(num_str):
        digit = int(ch)
        unit_index = length - i - 1
        if digit != 0:
            result += digits[digit] + units[unit_index]
        else:
            if not result.endswith('零') and i != length - 1:
                result += '零'

    result = result.rstrip('零')
    result = result.replace('一十', '十') if result.startswith('一十') else result
    return result or '零'
