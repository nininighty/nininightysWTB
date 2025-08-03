import os
import re
import traceback
from flask import Blueprint, jsonify, session, request
import config
from db_utils import db_cursor

WTB_Official = Blueprint('WTB_Official', __name__)

OFFICIAL_PATH = config.OFFICIAL_PATH

def natural_key(s):
    """用于自然排序，如 Chapter2 排在 Chapter10 前"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

@WTB_Official.route('/get_Collection_list', methods=['GET'])
def get_collection_list():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']
    try:
        if not os.path.exists(OFFICIAL_PATH):
            return jsonify({"success": False, "message": "官方错题集路径不存在"})

        subjects = []
        for subject_name in sorted(os.listdir(OFFICIAL_PATH)):
            subject_path = os.path.join(OFFICIAL_PATH, subject_name)
            if not os.path.isdir(subject_path):
                continue

            books = []
            for book_name in sorted(os.listdir(subject_path)):
                book_path = os.path.join(subject_path, book_name)
                if not os.path.isdir(book_path):
                    continue

                chapters = []
                for chapter_name in sorted(os.listdir(book_path), key=natural_key):
                    chapter_path = os.path.join(book_path, chapter_name)
                    if os.path.isdir(chapter_path):
                        chapters.append({
                            "chapter_name": chapter_name
                        })

                books.append({
                    "collection_name": book_name,
                    "chapters": chapters
                })

            subjects.append({
                "subject_name": subject_name,
                "books": books
            })

        return jsonify({
            "success": True,
            "collections": subjects
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


@WTB_Official.route('/get_topics_for_chapter', methods=['GET'])
def get_topics_for_chapter():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})

    try:
        subject = request.args.get('subject')
        collection = request.args.get('collection')
        chapter = request.args.get('chapter')
        if not subject or not collection or not chapter:
            return jsonify({"success": False, "message": "缺少 subject、collection 或 chapter 参数"})

        chapter_dir = os.path.join(OFFICIAL_PATH, subject, collection, chapter)
        if not os.path.exists(chapter_dir):
            return jsonify({"success": False, "message": "章节文件夹不存在"})

        pattern = re.compile(
            r"^(?P<collection>.+)_Chapter(?P<chapter>\d+)_Q(?P<question>.+)\.webp$",
            re.IGNORECASE
        )

        topics = []
        for filename in sorted(os.listdir(chapter_dir), key=natural_key):
            full_path = os.path.join(chapter_dir, filename)
            if os.path.isfile(full_path):
                match = pattern.match(filename)
                if match:
                    collection_name = match.group('collection')
                    chapter_num = match.group('chapter')
                    question_num = match.group('question')

                    title = f"《{collection_name}》  {chapter_num}.{question_num}"
                    relative_path = f"{subject}/{collection}/{chapter}/{filename}"
                    url = f"Official/{relative_path}"

                    topics.append({
                        "topic_name": title,
                        "topic_img_url": url,
                        "filename": filename
                    })

        return jsonify({"success": True, "topics": topics})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": "服务器错误：" + str(e)})


@WTB_Official.route('/import_official_topics', methods=['POST'])
def import_official_topic():
    if 'username' not in session:
        return jsonify({"success": False, "message": "请先登录"})
    username = session['username']

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "请求体为空或格式错误"})

        wtb_id = data.get('wtb_id')
        chapter_id = data.get('chapter_id')
        chapter_name = data.get('chapter_name', '').strip()
        tag_ids = data.get('tags', [])
        topics = data.get('topics', [])

        if not wtb_id or not topics:
            return jsonify({"success": False, "message": "缺少必要参数"})

        with db_cursor() as (conn, cursor):
            cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"success": False, "message": "用户不存在"})
            user_id = user["id"]
            print(data)
            # 章节处理
            unit_id = None
            print("ChapterName", chapter_name)
            if chapter_id and chapter_id.strip().lower() != 'none':
                try:
                    unit_id = int(chapter_id)
                except ValueError:
                    return jsonify({"success": False, "message": "章节ID格式错误"})
            else:
                # 检查章节名称，若无则尝试从图片路径中提取
                if not chapter_name or chapter_name.strip() == '*新建对应章节':
                    if topics:
                        first_topic = topics[0]
                        question_path = first_topic.get('img_url', '')
                        path_parts = question_path.split('/')
                        if len(path_parts) > 3:
                            chapter_name = path_parts[-2]
                        else:
                            return jsonify({"success": False, "message": "无法提取章节名"})
                print("insert c name:",chapter_name)
                # 查找是否已存在该章节名
                cursor.execute(
                    "SELECT id FROM chapters WHERE wtb_id = %s AND LOWER(name) = %s",
                    (wtb_id, chapter_name.lower())
                )
                existing_chapter = cursor.fetchone()
                if existing_chapter:
                    unit_id = existing_chapter['id']
                else:
                    # 创建新章节
                    cursor.execute(
                        "INSERT INTO chapters (wtb_id, name) VALUES (%s, %s)",
                        (wtb_id, chapter_name)
                    )
                    unit_id = cursor.lastrowid

            # 遍历题目批量插入或更新
            for topic in topics:
                title = topic.get('title', '').strip()
                question_path = topic.get('img_url', '').strip()
                init_score = topic.get('score', 1)
                # 验证题目路径合法性
                if not question_path.startswith("Official/") and not is_official_path(question_path):
                    continue  # 跳过不合法路径

                cursor.execute(
                    "SELECT id FROM wrong_topic WHERE wtb_id = %s AND title = %s",
                    (wtb_id, title)
                )
                existing = cursor.fetchone()
                if existing:
                    topic_id = existing["id"]
                    cursor.execute(""" 
                        UPDATE wrong_topic
                        SET unit_id=%s, init_score=%s, current_correct_rate=%s, explanation_url='',
                            file_path=%s, last_review_date=NOW()
                        WHERE id=%s
                    """, (unit_id, init_score, init_score, question_path, topic_id))
                    cursor.execute("DELETE FROM wrong_topic_tag_rel WHERE wrong_topic_id=%s", (topic_id,))
                else:
                    cursor.execute(""" 
                        INSERT INTO wrong_topic
                        (wtb_id, unit_id, title, init_score, current_correct_rate, is_flippable, explanation_url,
                        file_path, answer_file_path, created_at, last_review_date, is_reviewed)
                        VALUES (%s, %s, %s, %s, %s, 0, '',
                        %s, '', NOW(), NOW(), 0)
                    """, (wtb_id, unit_id, title, init_score, init_score, question_path))
                    topic_id = cursor.lastrowid

                for tag_id in tag_ids:
                    cursor.execute(
                        "INSERT INTO wrong_topic_tag_rel (wrong_topic_id, tag_id) VALUES (%s, %s)",
                        (topic_id, tag_id)
                    )

            conn.commit()
            return jsonify({"success": True, "message": "官方错题批量导入成功"})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"服务器错误：{str(e)}"})


def is_official_path(path: str, base_dir="WTBs/Official") -> bool:
    if not path.startswith("__official__/"):
        return False
    rel_path = path.replace("__official__/", "")
    abs_path = os.path.abspath(os.path.join(base_dir, rel_path))
    return os.path.commonpath([abs_path, os.path.abspath(base_dir)]) == os.path.abspath(base_dir) and os.path.isfile(abs_path)

