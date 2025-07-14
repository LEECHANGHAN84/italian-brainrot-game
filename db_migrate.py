from app import db, GodLeaderboard
import sqlite3
import os

# 데이터베이스 파일 경로
DB_PATH = 'characters.db'

def check_if_table_exists():
    """테이블이 존재하는지 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='god_leaderboard'")
    result = cursor.fetchone()
    conn.close()
    return result is not None

def check_if_column_exists():
    """country 컬럼이 이미 존재하는지 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(god_leaderboard)")
        columns = cursor.fetchall()
        conn.close()
        return any(column[1] == 'country' for column in columns)
    except sqlite3.OperationalError:
        conn.close()
        return False

def check_if_time_taken_exists():
    """time_taken 컬럼이 존재하는지 확인"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(god_leaderboard)")
        columns = cursor.fetchall()
        conn.close()
        return any(column[1] == 'time_taken' for column in columns)
    except sqlite3.OperationalError:
        conn.close()
        return False

def backup_database():
    """데이터베이스 백업"""
    if os.path.exists(DB_PATH):
        backup_path = DB_PATH + '.bak'
        with open(DB_PATH, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        print(f"데이터베이스 백업 완료: {backup_path}")
    else:
        print("데이터베이스 파일이 존재하지 않습니다.")

def migrate_database():
    """데이터베이스 마이그레이션 수행"""
    # 테이블이 존재하는지 확인
    table_exists = check_if_table_exists()
    
    if not table_exists:
        # 테이블이 없으면 새로 생성
        print("god_leaderboard 테이블이 존재하지 않습니다. 새로 생성합니다.")
        db.create_all()
        print("테이블 생성 완료!")
        return
    
    # country 컬럼이 이미 존재하는지 확인
    column_exists = check_if_column_exists()
    
    if column_exists:
        print("country 컬럼이 이미 존재합니다. 마이그레이션이 필요하지 않습니다.")
        return
    
    # time_taken 컬럼이 존재하는지 확인
    time_taken_exists = check_if_time_taken_exists()
    
    # 백업 생성
    backup_database()
    
    # 기존 테이블의 데이터 가져오기
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if time_taken_exists:
        cursor.execute("SELECT id, school, nickname, score, time_taken, timestamp FROM god_leaderboard")
    else:
        cursor.execute("SELECT id, school, nickname, score, timestamp FROM god_leaderboard")
    
    old_data = cursor.fetchall()
    
    # 임시 테이블 생성 (time_taken 컬럼 유무에 따라 다르게 처리)
    if time_taken_exists:
        cursor.execute("""
        CREATE TABLE god_leaderboard_new (
            id INTEGER PRIMARY KEY,
            country TEXT NOT NULL DEFAULT 'South Korea',
            school TEXT NOT NULL,
            nickname TEXT NOT NULL,
            score INTEGER NOT NULL,
            time_taken FLOAT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
    else:
        cursor.execute("""
        CREATE TABLE god_leaderboard_new (
            id INTEGER PRIMARY KEY,
            country TEXT NOT NULL DEFAULT 'South Korea',
            school TEXT NOT NULL,
            nickname TEXT NOT NULL,
            score INTEGER NOT NULL,
            time_taken FLOAT NOT NULL DEFAULT 0.0,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
    
    # 데이터 이전
    for row in old_data:
        if time_taken_exists:
            cursor.execute("""
            INSERT INTO god_leaderboard_new (id, country, school, nickname, score, time_taken, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (row[0], 'South Korea', row[1], row[2], row[3], row[4], row[5]))
        else:
            cursor.execute("""
            INSERT INTO god_leaderboard_new (id, country, school, nickname, score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (row[0], 'South Korea', row[1], row[2], row[3], row[4]))
    
    # 기존 테이블 삭제 및 새 테이블로 교체
    cursor.execute("DROP TABLE god_leaderboard")
    cursor.execute("ALTER TABLE god_leaderboard_new RENAME TO god_leaderboard")
    
    # 변경사항 저장
    conn.commit()
    conn.close()
    
    print("마이그레이션 완료! country 컬럼이 추가되었습니다.")
    if not time_taken_exists:
        print("time_taken 컬럼도 추가되었습니다. 기본값은 0.0입니다.")

if __name__ == "__main__":
    migrate_database()
