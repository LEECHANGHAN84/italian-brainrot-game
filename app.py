import itertools
import logging
import os
import random
import sys
import traceback
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', stream=sys.stdout)
app.debug = True
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///characters.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

db = SQLAlchemy(app)

# Prevent browser caching during development
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# New Character Model
class Character(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name_ko = db.Column(db.String(100), nullable=False, unique=True)
    name_en = db.Column(db.String(100), nullable=True)
    image_file = db.Column(db.String(100), nullable=False)
    question1 = db.Column(db.String(200), nullable=True)
    question2 = db.Column(db.String(200), nullable=True)
    question3 = db.Column(db.String(200), nullable=True)
    question4 = db.Column(db.String(200), nullable=True)
    question5 = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"Character('{self.name_ko}', '{self.image_file}')"

# Visitor and Game Log Models
class VisitorLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    visit_date = db.Column(db.Date, nullable=False, default=date.today)

class GameLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mode = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    play_date = db.Column(db.Date, nullable=False, default=date.today)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/')
def index():
    # Log unique visitor for the day
    visitor_ip = request.remote_addr
    today = date.today()
    existing_visitor = VisitorLog.query.filter_by(ip_address=visitor_ip, visit_date=today).first()
    if not existing_visitor:
        new_visitor = VisitorLog(ip_address=visitor_ip)
        db.session.add(new_visitor)
        db.session.commit()
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if 'image' not in request.files:
            flash('이미지 파일이 없습니다.', 'danger')
            return redirect(request.url)
        file = request.files['image']
        if file.filename == '':
            flash('파일을 선택하지 않았습니다.', 'danger')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                img = Image.open(file.stream)
                if img.height > 800 or img.width > 800:
                    img.thumbnail((800, 800))
                img.save(file_path)
            except Exception as e:
                flash(f'이미지 처리 중 오류 발생: {e}', 'danger')
                return redirect(request.url)

            new_character = Character(
                name_ko=request.form['name_ko'],
                name_en=request.form['name_en'],
                image_file=filename,
                question1=request.form.get('question1'),
                question2=request.form.get('question2'),
                question3=request.form.get('question3'),
                question4=request.form.get('question4'),
                question5=request.form.get('question5')
            )
            db.session.add(new_character)
            db.session.commit()
            flash('캐릭터가 성공적으로 추가되었습니다!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('허용되는 파일 확장자: png, jpg, jpeg, webp', 'danger')
            return redirect(request.url)

    characters = Character.query.order_by(Character.id).all()
    today = date.today()
    today_visitors = VisitorLog.query.filter_by(visit_date=today).count()
    today_games = db.session.query(GameLog).filter(db.func.date(GameLog.timestamp) == today).count()
    return render_template('admin.html', characters=characters, today_visitors=today_visitors, today_games=today_games)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_character(id):
    character = Character.query.get_or_404(id)
    if request.method == 'POST':
        character.name_ko = request.form['name_ko']
        character.name_en = request.form['name_en']
        character.question1 = request.form.get('question1')
        character.question2 = request.form.get('question2')
        character.question3 = request.form.get('question3')
        character.question4 = request.form.get('question4')
        character.question5 = request.form.get('question5')

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], character.image_file))
                except OSError:
                    pass
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                character.image_file = filename

        db.session.commit()
        flash('캐릭터 정보가 성공적으로 수정되었습니다!', 'success')
        return redirect(url_for('admin'))

    return render_template('edit_character.html', character=character)

@app.route('/delete/<int:id>')
def delete_character(id):
    character_to_delete = Character.query.get_or_404(id)
    try:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], character_to_delete.image_file)
        if os.path.exists(image_path):
            os.remove(image_path)
        db.session.delete(character_to_delete)
        db.session.commit()
        flash('캐릭터가 삭제되었습니다!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'캐릭터 삭제 중 오류 발생: {e}', 'danger')
    return redirect(url_for('admin'))

@app.route('/super_beginner_mode')
def super_beginner_mode():
    db.session.add(GameLog(mode='super_beginner'))
    db.session.commit()
    return render_template('super_beginner.html')

@app.route('/api/quiz/super_beginner')
def api_quiz_super_beginner():
    all_characters = Character.query.all()
    
    if not all_characters:
        return jsonify({'error': '퀴즈 데이터가 없습니다. 관리자 페이지에서 캐릭터를 추가해주세요.'}), 404

    num_questions = min(10, len(all_characters))
    quiz_characters = random.sample(all_characters, num_questions)

    questions = [{'name': char.name_ko, 'image': char.image_file} for char in quiz_characters]
    
    return jsonify(questions)

@app.route('/beginner')
def beginner_mode():
    db.session.add(GameLog(mode='beginner'))
    db.session.commit()
    return render_template('beginner.html')

@app.route('/api/quiz/beginner')
def api_quiz_beginner():
    characters = Character.query.all()
    if len(characters) < 2:
        return jsonify({'error': '퀴즈를 만들려면 최소 2명의 캐릭터가 필요합니다.'}), 404

    num_questions = min(10, len(characters))
    quiz_characters = random.sample(characters, num_questions)

    quiz_data = []
    for char in quiz_characters:
        options = [char.name_ko] # Correct answer
        # Add one random wrong answer
        wrong_answers = [c.name_ko for c in characters if c.id != char.id]
        options.extend(random.sample(wrong_answers, 1))
        random.shuffle(options)
        quiz_data.append({'image': char.image_file, 'options': options, 'answer': char.name_ko})
    
    random.shuffle(quiz_data) # Shuffle the entire quiz
    return jsonify(quiz_data)

@app.route('/intermediate')
def intermediate_mode():
    db.session.add(GameLog(mode='intermediate'))
    db.session.commit()
    return render_template('intermediate.html')

@app.route('/api/quiz/intermediate')
def api_quiz_intermediate():
    app.logger.debug('--- Intermediate Quiz API Start ---')
    try:
        all_characters = Character.query.all()
        app.logger.debug(f'Total characters fetched: {len(all_characters)}')
        if not all_characters:
            app.logger.warning('No characters found in DB.')

        if len(all_characters) < 4:
            app.logger.warning(f'Not enough characters for intermediate quiz. Found {len(all_characters)}, need 4.')
            return jsonify({'error': '퀴즈를 만들려면 최소 4명의 캐릭터가 필요합니다.'}), 404

        num_questions = min(20, len(all_characters))
        app.logger.debug(f'Number of questions to generate: {num_questions}')
        quiz_characters = random.sample(all_characters, num_questions)
        app.logger.debug(f'Selected characters for quiz: {[c.name_ko for c in quiz_characters]}')

        quiz_data = []
        for i, char in enumerate(quiz_characters):
            app.logger.debug(f'Processing character #{i+1}: {char.name_ko} (ID: {char.id})')
            options = [char.name_ko]
            
            other_names = [c.name_ko for c in all_characters if c.id != char.id]
            
            num_options_to_add = 3
            num_to_sample = min(num_options_to_add, len(other_names))
            wrong_answers = random.sample(other_names, num_to_sample)
            app.logger.debug(f'  Wrong answers for {char.name_ko}: {wrong_answers}')

            options.extend(wrong_answers)
            random.shuffle(options)
            app.logger.debug(f'  Shuffled options: {options}')
            
            question_item = {
                'image': char.image_file,
                'options': options,
                'answer': char.name_ko
            }
            app.logger.debug(f'  Generated question item: {question_item}')
            quiz_data.append(question_item)
        
        app.logger.debug(f'--- Final quiz data (before jsonify): {quiz_data} ---')
        response = jsonify(quiz_data)
        app.logger.debug('--- Intermediate Quiz API End (Success) ---')
        return response

    except Exception as e:
        app.logger.error(f'An error occurred in /api/quiz/intermediate: {e}', exc_info=True)
        return jsonify({'error': '서버 내부 오류가 발생했습니다.'}), 500

@app.route('/advanced_mode')
def advanced_mode():
    db.session.add(GameLog(mode='advanced'))
    db.session.commit()
    return render_template('advanced.html')

@app.route('/api/quiz/advanced')
def api_quiz_advanced():
    all_characters = Character.query.all()
    if len(all_characters) < 4:
        return jsonify({'error': '퀴즈를 만들려면 최소 4명의 캐릭터가 필요합니다.'}), 404

    num_questions = min(20, len(all_characters))
    quiz_characters = random.sample(all_characters, num_questions)

    quiz_data = []
    for char in quiz_characters:
        options = [char.name_ko]  # Correct answer
        wrong_answers = [c.name_ko for c in all_characters if c.id != char.id]
        options.extend(random.sample(wrong_answers, 3))
        random.shuffle(options)
        quiz_data.append({'image': char.image_file, 'options': options, 'answer': char.name_ko})

    random.shuffle(quiz_data)
    return jsonify(quiz_data)

@app.route('/expert')
def expert():
    db.session.add(GameLog(mode='expert'))
    db.session.commit()
    return render_template('expert.html')



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/super_advanced_mode')
def super_advanced_mode():
    db.session.add(GameLog(mode='super_advanced'))
    db.session.commit()
    return render_template('super_advanced.html')

@app.route('/api/quiz/super_advanced')
def api_quiz_super_advanced():
    all_characters = Character.query.all()
    if len(all_characters) < 4:
        return jsonify({'error': '퀴즈를 만들려면 최소 4명의 캐릭터가 필요합니다.'}), 404

    num_questions = min(20, len(all_characters))
    quiz_characters = random.sample(all_characters, num_questions)

    quiz_data = []
    for char in quiz_characters:
        options = [char.name_ko]  # Correct answer
        wrong_answers = [c.name_ko for c in all_characters if c.id != char.id]
        options.extend(random.sample(wrong_answers, 3))
        random.shuffle(options)
        quiz_data.append({'image': char.image_file, 'options': options, 'answer': char.name_ko})
    
    return jsonify(quiz_data)

# Leaderboard Model
class Leaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Leaderboard('{self.nickname}', '{self.score}')"







# God Leaderboard Model
class GodLeaderboard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    school = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    time_taken = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"GodLeaderboard('{self.nickname}', '{self.score}')"


@app.route('/divine_power')
def divine_power_page():
    # DEBUG: Returning a simple string to isolate the error.
    return "This is a test. If you see this, the route is working."




@app.route('/god_mode')
def god_mode():
    db.session.add(GameLog(mode='god'))
    db.session.commit()
    return render_template('god_mode.html')


@app.route('/api/quiz/god')
def god_quiz():
    # 모든 캐릭터 가져오기
    all_characters = Character.query.all()
    
    # 총 25개의 문제 생성 (10개는 이미지 크롭, 10개는 마스킹된 텍스트, 5개는 메모리 게임)
    questions = []
    
    # 이미지 크롭 문제 10개 생성
    for _ in range(10):
        # 정답이 될 캐릭터 랜덤 선택
        correct_character = random.choice(all_characters)
        
        # 오답이 될 캐릭터 3개 랜덤 선택 (정답 제외)
        other_characters = [c for c in all_characters if c.id != correct_character.id]
        wrong_characters = random.sample(other_characters, 3)
        
        # 모든 선택지 (정답 1개 + 오답 3개)
        options = [{
            'id': correct_character.id,
            'name': correct_character.name_ko,
            'image': correct_character.image_file
        }]
        
        for wrong in wrong_characters:
            options.append({
                'id': wrong.id,
                'name': wrong.name_ko,
                'image': wrong.image_file
            })
        
        # 선택지 섞기
        random.shuffle(options)
        
        # 문제 생성
        question = {
            'id': len(questions) + 1,
            'type': 'image_crop',  # 이미지 크롭 타입
            'character_id': correct_character.id,
            'image': correct_character.image_file,
            'correct_answer': correct_character.name_ko,  # 정답 캐릭터 이름 명시적 전달
            'options': options
        }
        
        questions.append(question)
    
    # 마스킹된 텍스트 문제 10개 생성
    for _ in range(10):
        # 정답이 될 캐릭터 랜덤 선택
        correct_character = random.choice(all_characters)
        
        # 오답이 될 캐릭터 3개 랜덤 선택 (정답 제외)
        other_characters = [c for c in all_characters if c.id != correct_character.id]
        wrong_characters = random.sample(other_characters, 3)
        
        # 모든 선택지 (정답 1개 + 오답 3개)
        options = [{
            'id': correct_character.id,
            'name': correct_character.name_ko,
            'image': correct_character.image_file
        }]
        
        for wrong in wrong_characters:
            options.append({
                'id': wrong.id,
                'name': wrong.name_ko,
                'image': wrong.image_file
            })
        
        # 선택지 섞기
        random.shuffle(options)
        
        # 문제 생성
        question = {
            'id': len(questions) + 1,
            'type': 'masked_text',  # 마스킹된 텍스트 타입
            'character_id': correct_character.id,
            'image': correct_character.image_file,
            'correct_answer': correct_character.name_ko,  # 정답 캐릭터 이름 명시적 전달
            'options': options
        }
        
        questions.append(question)
    
    # 메모리 게임 문제 5개 생성
    for _ in range(5):
        # 서로 다른 캐릭터 2개 랜덤 선택
        selected_characters = random.sample(all_characters, 2)
        character1 = selected_characters[0]
        character2 = selected_characters[1]
        
        # 메모리 게임은 2개의 서로 다른 캐릭터 이미지를 각각 2장씩 사용
        cards = [{
            'id': f"{character1.id}_1",
            'character_id': character1.id,
            'name': character1.name_ko,
            'image': character1.image_file,
            'pair_id': 1  # 페어 식별자 추가
        }, {
            'id': f"{character1.id}_2",
            'character_id': character1.id,
            'name': character1.name_ko,
            'image': character1.image_file,
            'pair_id': 1  # 같은 페어 식별자
        }, {
            'id': f"{character2.id}_1",
            'character_id': character2.id,
            'name': character2.name_ko,
            'image': character2.image_file,
            'pair_id': 2  # 다른 페어 식별자
        }, {
            'id': f"{character2.id}_2",
            'character_id': character2.id,
            'name': character2.name_ko,
            'image': character2.image_file,
            'pair_id': 2  # 같은 페어 식별자
        }]
        
        # 카드 섞기
        random.shuffle(cards)
        
        # 문제 생성
        question = {
            'id': len(questions) + 1,
            'type': 'memory_game',  # 메모리 게임 타입
            'character_id': correct_character.id,
            'correct_answer': character1.name_ko,  # 첫 번째 캐릭터를 정답으로 명시적 전달
            'cards': cards
        }
        
        questions.append(question)
    
    # 문제 섞기
    random.shuffle(questions)
    
    # 문제 ID 재할당
    for i, q in enumerate(questions):
        q['id'] = i + 1
    
    return jsonify(questions)


@app.route('/api/leaderboard/add', methods=['POST'])
def add_score():
    data = request.get_json()
    
    if not data or 'school' not in data or 'nickname' not in data or 'score' not in data or 'time_taken' not in data:
        return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
    
    new_score = Leaderboard(
        school=data['school'],
        nickname=data['nickname'],
        score=data['score'],
        time_taken=data['time_taken']
    )
    
    db.session.add(new_score)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '점수가 성공적으로 추가되었습니다.'}), 201


@app.route('/god_leaderboard')
def god_leaderboard():
    leaderboard_entries = GodLeaderboard.query.order_by(GodLeaderboard.score.desc(), GodLeaderboard.time_taken).limit(100).all()
    return render_template('god_leaderboard.html', leaderboard=leaderboard_entries)


@app.route('/api/god_leaderboard/add', methods=['POST'])
def add_god_score():
    data = request.get_json()
    
    if not data or 'school' not in data or 'nickname' not in data or 'score' not in data or 'time_taken' not in data:
        return jsonify({'error': '필수 필드가 누락되었습니다.'}), 400
    
    new_score = GodLeaderboard(
        school=data['school'],
        nickname=data['nickname'],
        score=data['score'],
        time_taken=data['time_taken']
    )
    
    db.session.add(new_score)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '점수가 성공적으로 추가되었습니다.'}), 201




# This block ensures that the database tables are created when the app starts.
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
