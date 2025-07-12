import sqlite3

# 데이터베이스 연결
conn = sqlite3.connect('characters.db')
cursor = conn.cursor()

# 테이블 정보 확인
cursor.execute("PRAGMA table_info(game_log)")
columns = cursor.fetchall()
column_names = [col[1] for col in columns]

# timestamp 컬럼이 없으면 추가
if 'timestamp' not in column_names:
    try:
        cursor.execute("ALTER TABLE game_log ADD COLUMN timestamp DATETIME")
        print("timestamp 컬럼이 성공적으로 추가되었습니다.")
    except sqlite3.Error as e:
        print(f"오류 발생: {e}")
else:
    print("timestamp 컬럼이 이미 존재합니다.")

# 변경사항 저장 및 연결 종료
conn.commit()
conn.close()

print("데이터베이스 업데이트 완료!")
