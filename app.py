import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'gruz_secret_key_2025'

# Инициализация базы данных
def init_db():
    with sqlite3.connect('gruz.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                login TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                cargo_weight REAL NOT NULL,
                cargo_type TEXT NOT NULL,
                pickup_address TEXT NOT NULL,
                delivery_address TEXT NOT NULL,
                date_time TEXT NOT NULL,
                status TEXT DEFAULT 'Новая',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                review_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO users (full_name, phone, email, login, password)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Администратор', '+7(000)000-00-00', 'admin@gruz.ru', 'admin', 'gruzovik2024'))
        conn.commit()

# Валидация данных
def validate_phone(phone):
    return bool(re.match(r'^\+7\(9\d{2}\)-\d{3}-\d{2}-\d{2}$', phone))

def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email))

def validate_password(password):
    return len(password) >= 6

def validate_full_name(full_name):
    return bool(re.match(r'^[А-Яа-я\s]+$', full_name))

def get_db():
    conn = sqlite3.connect('gruz.db')
    conn.row_factory = sqlite3.Row
    return conn

# Главная страница
@app.route('/')
def index():
    return redirect(url_for('login'))

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        phone = request.form['phone'].strip()
        email = request.form['email'].strip()
        login = request.form['login'].strip()
        password = request.form['password'].strip()

        errors = []
        if not validate_full_name(full_name):
            errors.append('ФИО должно содержать только кириллицу и пробелы')
        if not validate_phone(phone):
            errors.append('Телефон должен быть в формате +7(XXX)XXX-XX-XX')
        if not validate_email(email):
            errors.append('Некорректный формат email')
        if not validate_password(password):
            errors.append('Пароль должен содержать минимум 6 символов')
        if not login:
            errors.append('Логин обязателен')

        if errors:
            for error in errors:
                flash(error)
            return render_template('register.html', form_data=request.form)

        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (full_name, phone, email, login, password) VALUES (?, ?, ?, ?, ?)',
                             (full_name, phone, email, login, password))
                conn.commit()
            flash('Регистрация успешна! Войдите в систему.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Логин или email уже заняты')
            return render_template('register.html', form_data=request.form)
    
    return render_template('register.html', form_data={})

# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login'].strip()
        password = request.form['password'].strip()
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE login = ? AND password = ?', (login, password))
            user = cursor.fetchone()
        
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = login == 'admin'
            flash('Вход успешен!')
            return redirect(url_for('requests'))
        else:
            flash('Неверный логин или пароль')
            return render_template('login.html', form_data=request.form)
    
    return render_template('login.html', form_data={})

# Список заявок и отзывы
@app.route('/requests', methods=['GET', 'POST'])
def requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Добавление отзыва
    if request.method == 'POST':
        review_text = request.form.get('review_text', '').strip()
        request_id = request.form.get('request_id')
        if review_text and request_id:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO reviews (request_id, user_id, review_text, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (request_id, session['user_id'], review_text, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
            flash('Отзыв добавлен!')

    with get_db() as conn:
        cursor = conn.cursor()
        if session.get('is_admin'):
            cursor.execute('''
                SELECT r.*, u.full_name FROM requests r
                JOIN users u ON r.user_id = u.id
                ORDER BY r.id DESC
            ''')
        else:
            cursor.execute('''
                SELECT r.*, u.full_name FROM requests r
                JOIN users u ON r.user_id = u.id
                WHERE r.user_id = ?
                ORDER BY r.id DESC
            ''', (session['user_id'],))
        requests_list = cursor.fetchall()

        # Получаем отзывы для всех заявок, теперь с login вместо full_name
        cursor.execute('''
            SELECT reviews.*, users.login FROM reviews
            JOIN users ON reviews.user_id = users.id
            ORDER BY reviews.created_at DESC
        ''')
        reviews = cursor.fetchall()
        reviews_by_request = {}
        for review in reviews:
            reviews_by_request.setdefault(review['request_id'], []).append(review)

    return render_template('requests.html', requests=requests_list, reviews_by_request=reviews_by_request)

# Формирование заявки на перевозку груза
@app.route('/create_request', methods=['GET', 'POST'])
def create_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        cargo_weight = request.form['cargo_weight'].strip()
        cargo_type_select = request.form.get('cargo_type_select', '').strip()
        cargo_type = request.form.get('cargo_type', '').strip()
        pickup_address = request.form['pickup_address'].strip()
        delivery_address = request.form['delivery_address'].strip()
        date_time = request.form['date_time']

        # Выбор типа груза
        if cargo_type_select == 'Другое':
            cargo_type_final = cargo_type
        else:
            cargo_type_final = cargo_type_select

        errors = []
        try:
            weight = float(cargo_weight)
            if weight <= 0:
                errors.append('Вес груза должен быть положительным числом')
        except ValueError:
            errors.append('Вес груза должен быть числом')
        if not cargo_type_final:
            errors.append('Тип груза обязателен')
        if not pickup_address:
            errors.append('Адрес отправления обязателен')
        if not delivery_address:
            errors.append('Адрес доставки обязателен')
        try:
            selected_time = datetime.strptime(date_time, '%Y-%m-%dT%H:%M')
            if selected_time < datetime.now():
                errors.append('Дата и время не могут быть в прошлом')
        except ValueError:
            errors.append('Некорректный формат даты и времени')

        if errors:
            for error in errors:
                flash(error)
            # Передаем выбранный тип груза обратно в форму
            form_data = dict(request.form)
            if cargo_type_select != 'Другое':
                form_data['cargo_type'] = cargo_type_select
            return render_template('create_request.html', form_data=form_data)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO requests (user_id, cargo_weight, cargo_type, pickup_address, delivery_address, date_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session['user_id'], weight, cargo_type_final, pickup_address, delivery_address, date_time, 'Новая'))
            conn.commit()
        flash('Заявка на перевозку создана!')
        return redirect(url_for('requests'))
    
    return render_template('create_request.html', form_data={})

# Обновление статуса заявки (админ)
@app.route('/admin/update_request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    status = request.form['status']

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', (status, request_id))
        conn.commit()
    
    flash('Статус заявки обновлен!')
    return redirect(url_for('requests'))

# Выход из системы
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)