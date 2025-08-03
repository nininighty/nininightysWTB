# Timer_generate_daily_papers.py
# 用于定时运行，生成每个用户每个错题本的一套错题卷的脚本，题量由MySQL中的wtbs表"daily_topic_num"决定

import random
import traceback
from datetime import datetime
from db_utils import db_cursor, select_weighted_wrong_topics
from natsort import natsorted


def generate_wrong_topic_paper_for_user(user_id, wtb_id, chapter_id=None):
    try:
        with db_cursor() as (conn, cursor):
            # 获取每日题量配置
            cursor.execute("SELECT daily_topic_num FROM wtbs WHERE id = %s", (wtb_id,))
            res = cursor.fetchone()
            if not res or not res.get("daily_topic_num"):
                print(f"错题本 {wtb_id} 未设置 daily_topic_num，跳过")
                return False

            topic_num = res["daily_topic_num"]
            wrong_topics = select_weighted_wrong_topics(user_id, wtb_id, chapter_id)
            if not wrong_topics:
                print(f"用户 {user_id} 错题本 {wtb_id} 无错题，跳过")
                return False

            topic_num = min(max(topic_num, 1), len(wrong_topics))
            selected_topics = []
            pool = wrong_topics[:]
            while len(selected_topics) < topic_num:
                pick = random.choices(pool, weights=[t['weight'] for t in pool], k=1)[0]
                selected_topics.append(pick)
                pool.remove(pick)

            today_str = datetime.now().strftime('%m-%d')
            # 排序
            selected_topics = natsorted(selected_topics, key=lambda x: x['title'])

            # 读取已有每日卷数量（必须fetch结果）
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM wrong_topic_paper
                WHERE user_id=%s AND wtb_id=%s AND DATE(created_at) = CURDATE()
            """, (user_id, wtb_id))
            count_res = cursor.fetchone()

            title = f"{today_str} 每日错题卷"

            cursor.execute("""
                INSERT INTO wrong_topic_paper (user_id, wtb_id, created_at, question_count, title)
                VALUES (%s, %s, NOW(), %s, %s)
            """, (user_id, wtb_id, topic_num, title))
            paper_id = cursor.lastrowid

            for topic in selected_topics:
                flip_flag = 1 if topic.get('is_flippable', 0) == 1 and random.random() < 0.5 else 0
                cursor.execute("""
                    INSERT INTO wrong_topic_paper_rel (wrong_topic_paper_id, wrong_topic_id, score_ratio, is_flippable)
                    VALUES (%s, %s, %s, %s)
                """, (paper_id, topic['id'], None, flip_flag))

            conn.commit()
            print(f"用户 {user_id} 错题本 {wtb_id} 生成错题卷 {paper_id}，共 {topic_num} 题")
            return True

    except Exception as e:
        print(f"生成用户 {user_id} 错题本 {wtb_id} 错题卷失败：{e}")
        traceback.print_exc()
        return False


def generate_all_users_daily_papers():
    with db_cursor() as (conn, cursor):
        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()

    for user in users:
        user_id = user['id']
        with db_cursor() as (conn, cursor):
            cursor.execute("SELECT id FROM wtbs WHERE user_id = %s", (user_id,))
            user_wtbs = cursor.fetchall()

        for wtb in user_wtbs:
            print(f"生成每日卷：user_id={user_id}, wtb_id={wtb['id']}")
            generate_wrong_topic_paper_for_user(user_id, wtb['id'])

if __name__ == "__main__":
    generate_all_users_daily_papers()
