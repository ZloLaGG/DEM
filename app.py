import sqlite3
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'moynesam_secret_key_2025'

# Инициализация базы данных
def init_db():
    with sqlite3.connect('moynesam.db') as conn:
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
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                service_type TEXT NOT NULL,
                other_service TEXT,
                date_time TEXT NOT NULL,
                payment_type TEXT NOT NULL,
                status TEXT DEFAULT 'Новая',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cancel_reasons (
                request_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id)
            )
        ''')
        cursor.execute('''
            INSERT OR IGNORE INTO users (full_name, phone, email, login, password)
            VALUES (?, ?, ?, ?, ?)
        ''', ('Администратор', '+7(000)000-00-00', 'admin@moynesam.ru', 'adminka', 'password'))
        conn.commit()

# Валидация данных
def validate_phone(phone):
    return bool(re.match(r'^\+7\(\d{3}\)\d{3}-\d{2}-\d{2}$', phone))

def validate_email(email):
    return bool(re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email))

def validate_password(password):
    return len(password) >= 6

def validate_full_name(full_name):
    return bool(re.match(r'^[А-Яа-я\s]+$', full_name))

def get_db():
    conn = sqlite3.connect('moynesam.db')
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
            session['is_admin'] = login == 'adminka'
            flash('Вход успешен!')
            return redirect(url_for('requests'))
        else:
            flash('Неверный логин или пароль')
            return render_template('login.html', form_data=request.form)
    
    return render_template('login.html', form_data={})

# Список заявок
@app.route('/requests')
def requests():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as conn:
        cursor = conn.cursor()
        if session.get('is_admin'):
            cursor.execute('SELECT r.*, u.full_name FROM requests r JOIN users u ON r.user_id = u.id ORDER BY r.id DESC')
        else:
            cursor.execute('SELECT r.*, u.full_name FROM requests r JOIN users u ON r.user_id = u.id WHERE r.user_id = ? ORDER BY r.id DESC',
                         (session['user_id'],))
        requests = cursor.fetchall()
        
        reasons = {}
        cursor.execute('SELECT * FROM cancel_reasons')
        for row in cursor.fetchall():
            reasons[row['request_id']] = row['reason']
    
    return render_template('requests.html', requests=requests, reasons=reasons)

# Формирование заявки
@app.route('/create_request', methods=['GET', 'POST'])
def create_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        address = request.form['address'].strip()
        phone = request.form['phone'].strip()
        service_type = request.form['service_type']
        other_service = request.form.get('other_service', '').strip()
        date_time = request.form['date_time']
        payment_type = request.form['payment_type']

        errors = []
        if not address:
            errors.append('Адрес обязателен')
        if not validate_phone(phone):
            errors.append('Телефон должен быть в формате +7(XXX)-XXX-XX-XX')
        if service_type not in ['Общий клининг', 'Генеральная уборка', 'После строительная уборка', 'Химчистка ковров и мебели', 'Иная услуга']:
            errors.append('Некорректный тип услуги')
        if service_type == 'Иная услуга' and not other_service:
            errors.append('Укажите описание иной услуги')
        try:
            selected_time = datetime.strptime(date_time, '%Y-%m-%dT%H:%M')
            if selected_time < datetime.now():
                errors.append('Дата и время не могут быть в прошлом')
        except ValueError:
            errors.append('Некорректный формат даты и времени')
        if payment_type not in ['Наличные', 'Банковская карта']:
            errors.append('Некорректный тип оплаты')

        if errors:
            for error in errors:
                flash(error)
            return render_template('create_request.html', form_data=request.form)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO requests (user_id, address, phone, service_type, other_service, date_time, payment_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (session['user_id'], address, phone, service_type, other_service, date_time, payment_type, 'Новая'))
            conn.commit()
        flash('Заявка создана!')
        return redirect(url_for('requests'))
    
    return render_template('create_request.html', form_data={})

# Обновление статуса заявки (админ)
@app.route('/admin/update_request/<int:request_id>', methods=['POST'])
def update_request(request_id):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    status = request.form['status']
    reason = request.form.get('reason', '').strip()

    if status == 'Отменено' and not reason:
        flash('Укажите причину отмены')
        return redirect(url_for('requests'))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE requests SET status = ? WHERE id = ?', (status, request_id))
        if status == 'Отменено':
            cursor.execute('INSERT OR REPLACE INTO cancel_reasons (request_id, reason) VALUES (?, ?)', (request_id, reason))
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