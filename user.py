import os
import traceback
from datetime import datetime
from flask import render_template, Blueprint, jsonify, session, redirect, url_for, request, send_from_directory
from db_utils import db_cursor
import config
from WTB_DataRequest import compress_image

user_bp = Blueprint('user', __name__)
WTBs_path = "./WTBs"
MySQL_PSW = config.MySQL_PSW
IMAGE_BASE_URL = config.IMAGE_BASE_URL
LOCAL_PATH = config.LOCAL_PATH

# =-=-=-= 用户主页
@user_bp.route("/user_home")
def user_home():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    username = session['username']

    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id, nickname, avatar_url FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        if not result:
            return redirect(url_for("auth.home"))

        user_id = result['id']
        session['user_id'] = user_id
        session['nickname'] = result.get('nickname', '未命名')
        session['avatar_url'] = result.get('avatar_url') or '/static/images/Pic_DefaultAvatar.jpg'

        cursor.execute("SELECT id, title, create_time, label_color FROM wtbs WHERE user_id=%s", (user_id,))
        wtbs_list = cursor.fetchall()
        wtb_count = len(wtbs_list)

    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return render_template(
        "user_home.html",
        version_time=now_time,
        wtbs_list=wtbs_list,
        wtb_count=wtb_count
    )


# 个人信息
@user_bp.route("/get_user_info")
def get_user_info():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    username = session['username']
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT username, nickname, avatar_url FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"success": False, "message": "用户不存在"}), 404

        return jsonify({
            "success": True,
            "username": row["username"],
            "nickname": row["nickname"],
            "avatar_url": row["avatar_url"] or "/static/default_avatar.png"
        })

@user_bp.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return jsonify(success=False, message="未登录"), 401

    user_id = session['user_id']

    if 'avatar' not in request.files:
        return jsonify(success=False, message="未找到上传文件"), 400

    file = request.files['avatar']
    if file.filename == '':
        return jsonify(success=False, message="文件名为空"), 400

    compressed_img_buf = compress_image(file)
    if not compressed_img_buf:
        return jsonify(success=False, message="图片压缩失败"), 500

    user_dir = os.path.join(LOCAL_PATH, "WTBs", str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    filename = "avatar.webp"
    save_path = os.path.join(user_dir, filename)

    with open(save_path, 'wb') as f:
        f.write(compressed_img_buf.read())

    avatar_db_path = f"/{user_id}/{filename}"
    try:
        with db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE users SET avatar_url=%s WHERE id=%s",
                (avatar_db_path, user_id)
            )
            conn.commit()
    except Exception as e:
        return jsonify(success=False, message=f"数据库更新失败: {e}"), 500

    return jsonify(success=True, avatar_url=avatar_db_path)


# 今日复习错题量
@user_bp.route("/count_today_reviewed_topics", methods=["GET"])
def count_today_reviewed_topics():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    username = session['username']
    wtb_id = request.args.get('wtb_id', type=int)
    if not wtb_id:
        return jsonify({"success": False, "message": "缺少错题本ID参数"}), 400

    with db_cursor() as (conn, cursor):
        # 获取用户ID
        cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"success": False, "message": "用户不存在"}), 404

        user_id = user['id']

        cursor.execute("""
            SELECT COUNT(DISTINCT wrong_topic_id) AS reviewed_count
            FROM review_logs
            WHERE user_id = %s AND wtb_id = %s AND DATE(review_time) = CURDATE()
        """, (user_id, wtb_id))
        row = cursor.fetchone()
        count = row['reviewed_count'] if row else 0

    return jsonify({"success": True, "count": count})


# ========================   管理章节   ==========================================
# 获取章节情况
@user_bp.route('/get_chapter_list', methods=["GET"])
def get_chapter_list():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    wtb_id = request.args.get('wtb_id', type=int)

    with db_cursor() as (conn, cursor):
        sql_code = "SELECT id, name FROM chapters WHERE wtb_id = %s ORDER BY id"
        cursor.execute(sql_code, (wtb_id,))
        rows = cursor.fetchall()
        chapter_list = [{"id": row["id"], "name": row["name"]} for row in rows]
        return jsonify(chapter_list)


# 修改章节情况
@user_bp.route('/submit_ChapterEdit', methods=["POST"])
def submit_ChapterEdit():
    if 'username' not in session:
        return redirect(url_for("auth.home"))
    data = request.get_json()
    wtb_id = data.get('wtb_id')
    newChapters = data.get('newChapters')
    deletedChapters = data.get("deleteChapters", [])
    renamedChapters = data.get("renameChapters", {})
    deletedTopics = data.get("deleteTopics", [])
    max_chapters = 40
    # print(f"deletedChapters: {deletedChapters}, type: {type(deletedChapters)}")
    if not wtb_id:
        return jsonify({"success": False, "message": "参数错误"})

    try:
        with db_cursor() as (conn, cursor):
            # 先查已有章节名集合
            cursor.execute("SELECT name FROM chapters WHERE wtb_id = %s", (wtb_id,))
            existing_names = {row['name'].strip().lower() for row in cursor.fetchall()}

            # 插入新章节，跳过重复的
            cursor.execute("SELECT COUNT(*) AS count FROM chapters WHERE wtb_id = %s", (wtb_id,))
            result = cursor.fetchone()
            current_count = result["count"] if result else 0
            available_slots = max_chapters - current_count
            if available_slots <= 0:
                return jsonify({"success": False, "message": "章节数量已达上限，无法添加更多章节"})
            # 只保留允许插入的章节
            chapters_to_insert = newChapters[:available_slots]
            for chapter in chapters_to_insert:
                name = chapter.get('name', '').strip()
                if not name or name.lower() in existing_names:
                    return jsonify({"success": False, "message": f"章节 '{name}' 已存在"})
                cursor.execute("INSERT INTO chapters (wtb_id, name) VALUES (%s, %s)", (wtb_id, name))

            # 删除章节及其错题（根据错题地址判断删除）
            if deletedChapters:
                deletedChapters = [int(cid) for cid in deletedChapters]
                placeholders = ",".join(["%s"] * len(deletedChapters))

                cursor.execute(
                    f"SELECT id, file_path, answer_file_path FROM wrong_topic WHERE unit_id IN ({placeholders})",
                    tuple(deletedChapters)
                )
                topics = cursor.fetchall()

                topic_ids = []
                for topic in topics:
                    topic_ids.append(topic['id'])
                    for p in [topic['file_path'], topic['answer_file_path']]:
                        if p and not p.startswith("Official/"):
                            full_path = os.path.join(WTBs_path, p)
                            if os.path.exists(full_path):
                                os.remove(full_path)

                # 删除所有相关错题数据库记录（官方或非官方一视同仁）
                if topic_ids:
                    topic_placeholders = ",".join(["%s"] * len(topic_ids))
                    cursor.execute(f"DELETE FROM wrong_topic WHERE id IN ({topic_placeholders})", tuple(topic_ids))

                # 删除章节
                cursor.execute(f"DELETE FROM chapters WHERE id IN ({placeholders})", tuple(deletedChapters))

            # 处理删除错题逻辑
            if deletedTopics:
                for file_path in deletedTopics:
                    if file_path.startswith("Official/"):
                        # 解除官方题目与章节的绑定
                        cursor.execute("UPDATE wrong_topic SET unit_id = NULL WHERE file_path = %s", (file_path,))
                    else:
                        # 删除用户上传的错题
                        cursor.execute("DELETE FROM wrong_topic WHERE file_path = %s", (file_path,))

            # 重命名章节
            # 先查出章节id对应旧名，方便比较
            cursor.execute("SELECT id, name FROM chapters WHERE wtb_id = %s", (wtb_id,))
            rows = cursor.fetchall()
            existing_names = {row['name'].strip().lower() for row in rows}
            id_to_name = {row['id']: row['name'].strip() for row in rows}

            # 重命名检查
            for chapter_id, new_name in renamedChapters.items():
                chapter_id = int(chapter_id)
                new_name_lower = new_name.strip().lower()
                old_name_lower = id_to_name.get(chapter_id, "").lower()
                if new_name_lower in existing_names and new_name_lower != old_name_lower:
                    return jsonify({"success": False, "message": f"章节名 '{new_name}' 已存在"})

            # 执行更新
            for chapter_id, new_name in renamedChapters.items():
                chapter_id = int(chapter_id)
                cursor.execute(
                    "UPDATE chapters SET name = %s WHERE id = %s AND wtb_id = %s",
                    (new_name, chapter_id, wtb_id)
                )

            conn.commit()
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})

    return jsonify({"success": True})


# ============================================================
# 返回错题详情信息
@user_bp.route("/get_wrong_topic_detail", methods=["GET"])
def get_wrong_topic_detail():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    topic_id = request.args.get("topic_id", type=int)
    if not topic_id:
        return jsonify({"success": False, "message": "缺少参数 topic_id"}), 400

    try:
        with db_cursor() as (conn, cursor):
            # 先查错题详情
            cursor.execute("""
                SELECT wt.*, c.name AS chapter_name, wtb.title AS wtb_name
                FROM wrong_topic wt
                LEFT JOIN chapters c ON wt.unit_id = c.id
                LEFT JOIN wtbs wtb ON wt.wtb_id = wtb.id
                WHERE wt.id = %s
            """, (topic_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify({"success": False, "message": "错题不存在"}), 404

            # 查该错题的标签
            cursor.execute("""
                SELECT tag_id
                FROM wrong_topic_tag_rel
                WHERE wrong_topic_id = %s
            """, (topic_id,))
            tag_rows = cursor.fetchall()
            tag_ids = [str(row['tag_id']) for row in tag_rows]

            # 查该错题本全部备注
            cursor.execute("""
                SELECT id, note_text, user, created_at
                FROM wtb_notes
                WHERE wrong_topic_id = %s
                ORDER BY created_at ASC
            """, (topic_id,))
            notes = cursor.fetchall()

            def full_url(path):
                if not path:
                    return ""
                return IMAGE_BASE_URL + path.replace("\\", "/")

            data = {
                "id": row['id'],
                "title": row['title'],
                "wtb_name": row['wtb_name'] or "",
                "chapter_name": row['chapter_name'] or "",
                "created_at": row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                "tags": tag_ids,  # 使用标签 ID 数组
                "question_img_url": full_url(row['file_path']),
                "answer_img_url": full_url(row['answer_file_path']),
                "explanation_url": row['explanation_url'] or "",
                "flippable": bool(row['is_flippable']),
                "review_status": "已复习" if row.get("is_reviewed") else "未复习",
                "last_review_date": row['last_review_date'].strftime('%Y-%m-%d') if row.get(
                    'last_review_date') else None,
                "review_count": row.get('review_count', 0),
                "current_correct_rate": row.get('current_correct_rate') or 0.0,
                "notes": [
                    {
                        "id": n["id"],
                        "note_text": n["note_text"],
                        "user": n["user"],
                        "created_at": n["created_at"].strftime('%Y-%m-%d %H:%M:%S') if n["created_at"] else None,
                    }
                    for n in notes
                ]
            }
            return jsonify({"success": True, "data": data})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 删除备注
@user_bp.route('/delete_note', methods=['DELETE'])
def delete_note():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"}), 401

    note_id = request.args.get('note_id', type=int)
    if not note_id:
        return jsonify({"success": False, "message": "缺少备注ID"}), 400

    try:
        with db_cursor() as (conn, cursor):
            # 查询该备注是否存在
            cursor.execute("SELECT * FROM wtb_notes WHERE id = %s", (note_id,))
            note = cursor.fetchone()

            if not note:
                return jsonify({"success": False, "message": "备注不存在"}), 404

            # 删除该备注
            cursor.execute("DELETE FROM wtb_notes WHERE id = %s", (note_id,))
            conn.commit()

            return jsonify({"success": True, "message": "备注删除成功"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 删除错题
@user_bp.route("/deleteWrongTopic", methods=['GET'])
def deleteWrongTopic():
    if 'username' not in session:
        return jsonify({"success": False, "message": "未登录"}), 401

    topic_id = request.args.get("topic_id", type=int)
    if not topic_id:
        return jsonify({"success": False, "message": "缺少参数 topic_id"})

    try:
        with db_cursor() as (conn, cursor):
            # 查找错题的文件路径
            cursor.execute("SELECT file_path, answer_file_path FROM wrong_topic WHERE id = %s", (topic_id,))
            file_info = cursor.fetchone()

            if not file_info:
                return jsonify({"success": False, "message": "错题不存在"})

            # 判断并删除错题文件
            for path in (file_info['file_path'], file_info['answer_file_path']):
                if path:
                    full_path = os.path.join(WTBs_path, path)
                    # 如果是用户上传的文件，才进行删除
                    if not path.startswith("Official/") and os.path.exists(full_path):
                        os.remove(full_path)

            # 删除错题记录
            cursor.execute("DELETE FROM wrong_topic WHERE id = %s", (topic_id,))
            conn.commit()

            return jsonify({"success": True})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


# 通用函数==============================================================
# 本地调试
@user_bp.route('/img/<path:filename>')
def uploaded_file(filename):
    print("Request for :",filename)
    return send_from_directory(os.path.join(config.LOCAL_PATH, 'WTBs'), filename)
