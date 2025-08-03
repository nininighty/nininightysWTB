# aggregate_scores.py
import traceback
from collections import defaultdict
from db_utils import db_cursor

def aggregate_scores_for_today():
    try:
        with db_cursor() as (conn, cursor):
            cursor.execute("""
                SELECT user_id, wtb_id, wrong_topic_id, accuracy
                FROM review_logs
                WHERE DATE(review_time) = CURDATE()
                ORDER BY user_id, wrong_topic_id, wtb_id
            """)
            logs = cursor.fetchall()
            print(f"今天复习记录总数: {len(logs)}")

            reviewed_topics_per_user = defaultdict(set)
            review_counter = defaultdict(int)

            for log in logs:
                user_id = log['user_id']
                wtb_id = log['wtb_id']
                wrong_topic_id = log['wrong_topic_id']
                score_ratio = log['accuracy']

                # 更新错题正确率
                if score_ratio is not None:
                    cursor.execute("""
                        SELECT current_correct_rate FROM wrong_topic WHERE id = %s
                    """, (wrong_topic_id,))
                    row = cursor.fetchone()
                    old_rate = row['current_correct_rate'] if row and row['current_correct_rate'] is not None else 0.0
                    new_rate = min(1.0, 0.6 * old_rate + 0.4 * score_ratio)

                    cursor.execute("""
                        UPDATE wrong_topic
                        SET current_correct_rate = %s, last_review_date = NOW()
                        WHERE id = %s
                    """, (new_rate, wrong_topic_id))

                    print(f"更新错题ID={wrong_topic_id}，旧得分={old_rate}，新得分={new_rate}")

                if wrong_topic_id not in reviewed_topics_per_user[user_id]:
                    reviewed_topics_per_user[user_id].add(wrong_topic_id)

                review_counter[(user_id, wtb_id)] += 1

            # 写入 daily_review_stats
            for (user_id, wtb_id), count in review_counter.items():
                update_daily_review_stats(cursor, user_id, wtb_id, count)

            conn.commit()

    except Exception as e:
        print("汇总得分失败：", e)
        traceback.print_exc()


def update_daily_review_stats(cursor, user_id, wtb_id, count):
    cursor.execute("""
        SELECT id FROM daily_review_stats
        WHERE user_id = %s AND wtb_id = %s AND date = CURDATE()
    """, (user_id, wtb_id))
    row = cursor.fetchone()

    if row:
        cursor.execute("""
            UPDATE daily_review_stats
            SET review_count = review_count + %s
            WHERE id = %s
        """, (count, row['id']))
    else:
        cursor.execute("""
            INSERT INTO daily_review_stats (user_id, wtb_id, date, review_count)
            VALUES (%s, %s, CURDATE(), %s)
        """, (user_id, wtb_id, count))


if __name__ == "__main__":
    aggregate_scores_for_today()
