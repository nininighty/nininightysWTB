import math
from contextlib import contextmanager
from datetime import datetime

import pymysql
import config

MEMORY_FACTOR = config.MemoryFactor

@contextmanager
def db_cursor():
    conn = pymysql.connect(
        host="localhost",
        user="root",
        password=config.MySQL_PSW,
        database="user_system",
        cursorclass=pymysql.cursors.DictCursor,
        charset='utf8mb4'
    )
    cursor = conn.cursor()
    try:
        yield conn, cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def select_weighted_wrong_topics(user_id, wtb_id, chapter_id=None):
    with db_cursor() as (conn, cursor):
        params = [user_id, wtb_id]
        chapter_filter = ""
        if chapter_id:
            chapter_filter = "AND wt.unit_id=%s"
            params.append(chapter_id)

        sql = f"""
            SELECT wt.id, wt.title, wt.init_score, wt.is_flippable, wt.file_path, wt.answer_file_path,
                   wt.last_review_date, wt.current_correct_rate, wt.is_reviewed,
                   COALESCE(SUM(t.weight), 0) AS weight
            FROM wrong_topic wt
            LEFT JOIN wrong_topic_tag_rel rel ON rel.wrong_topic_id = wt.id
            LEFT JOIN wrong_topic_tags t ON t.id = rel.tag_id AND t.user_id = %s
            WHERE wt.wtb_id = %s
            {chapter_filter}
            GROUP BY wt.id, wt.title, wt.init_score, wt.is_flippable, 
                     wt.file_path, wt.answer_file_path, wt.last_review_date, wt.current_correct_rate, wt.is_reviewed
        """

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            if row['last_review_date']:
                delta = datetime.now() - row['last_review_date']
                days_since_review = round(delta.total_seconds() / 86400, 2)
            else:
                days_since_review = None
            if days_since_review is None:
                memory_weight = 1.0
            else:
                memory_weight = MemoryCalculate(days_since_review)
            correct_rate = row['current_correct_rate'] or 0
            correct_weight = 2 - 1.2 * correct_rate
            is_reviewed = row['is_reviewed']
            tag_weight = 1 + (row['weight'] / (1 + abs(row['weight'])))
            total_weight = memory_weight * tag_weight * correct_weight * (1.5 - 0.75*row['init_score']) * (2 - is_reviewed)
            result.append({
                "id": row['id'],
                "weight": total_weight,
                "is_flippable": row['is_flippable'],
                "title": row['title']
            })
        return result

def MemoryCalculate(days_since_review):
    denominator = (
            79.323 * math.exp(-0.409 * days_since_review) +
            15.098 * math.exp(-0.52 * days_since_review) +
            5.5
    )
    return (100 / denominator) ** MEMORY_FACTOR
