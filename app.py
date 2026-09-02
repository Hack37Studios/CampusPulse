from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import date, datetime, timedelta
import sqlite3
import os
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'campus_pulse_secret_key_2024'
DATABASE = 'campus_pulse.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    """Initialize database with schema"""
    db = get_db()
    cursor = db.cursor()
    
    # Schools table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            total_school_days INTEGER DEFAULT 180,
            current_school_day INTEGER DEFAULT 1,
            end_of_year_date TEXT,
            announcement TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT,
            school_id INTEGER NOT NULL,
            role TEXT DEFAULT 'student',
            grade INTEGER,
            graduation_year INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        )
    ''')
    
    # Classes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            period INTEGER NOT NULL,
            name TEXT NOT NULL,
            room TEXT NOT NULL,
            teacher TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            min_grade INTEGER,
            max_grade INTEGER,
            created_by INTEGER,
            is_user_created INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # Class Notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    ''')

    # Student Classes (Enrollment) table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            class_id INTEGER NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (class_id) REFERENCES classes(id),
            UNIQUE(user_id, class_id)
        )
    ''')

    # School Periods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS school_periods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id INTEGER NOT NULL,
            period_number INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (school_id) REFERENCES schools(id),
            UNIQUE(school_id, period_number)
        )
    ''')

    school_columns = {row['name'] for row in cursor.execute('PRAGMA table_info(schools)').fetchall()}
    if 'last_school_day_date' not in school_columns:
        cursor.execute('ALTER TABLE schools ADD COLUMN last_school_day_date TEXT')
        cursor.execute('UPDATE schools SET last_school_day_date = ?', (date.today().isoformat(),))
    
    db.commit()
    # Friend Requests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id),
            UNIQUE(sender_id, receiver_id)
        )
    ''')

    # Friends table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id_1 INTEGER NOT NULL,
            user_id_2 INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id_1) REFERENCES users(id),
            FOREIGN KEY (user_id_2) REFERENCES users(id),
            UNIQUE(user_id_1, user_id_2)
        )
    ''')

    db.commit()
    db.close()

def update_school_day_counters():
    """Advance each school's counter once for every missed weekday."""
    today = date.today()
    db = get_db()
    schools = db.execute('SELECT id, current_school_day, total_school_days, last_school_day_date FROM schools').fetchall()

    for school in schools:
        last_date = date.fromisoformat(school['last_school_day_date']) if school['last_school_day_date'] else today
        if last_date >= today:
            continue

        missed_weekdays = 0
        check_date = last_date + timedelta(days=1)
        while check_date <= today:
            if check_date.weekday() < 5:
                missed_weekdays += 1
            check_date += timedelta(days=1)

        new_day = min(school['total_school_days'], school['current_school_day'] + missed_weekdays)
        db.execute('''
            UPDATE schools
            SET current_school_day = ?, last_school_day_date = ?
            WHERE id = ?
        ''', (new_day, today.isoformat(), school['id']))

    db.commit()
    db.close()

@app.before_request
def refresh_school_day_counters():
    update_school_day_counters()

def hash_password(password):
    """Hash password"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        db = get_db()
        user = db.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        db.close()
        if not user or user['role'] != 'admin':
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes

@app.route('/')
def index():
    """Redirect to login or dashboard based on session"""
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        if user and user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user:
            return redirect(url_for('student_dashboard'))
        else:
            session.clear()
            return redirect(url_for('login'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        db.close()
        
        if user and user['password'] == hash_password(password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['school_id'] = user['school_id']
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    error = None
    success = None
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        school_id = request.form.get('school_id')
        grade = request.form.get('grade')
        graduation_year = request.form.get('graduation_year')
        
        # Validation
        if not all([username, password, confirm_password, full_name, email, school_id, grade, graduation_year]):
            error = 'All fields are required'
        elif password != confirm_password:
            error = 'Passwords do not match'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters'
        else:
            db = get_db()
            existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            
            if existing_user:
                error = 'Username already exists'
            else:
                try:
                    cursor = db.cursor()
                    cursor.execute('''
                        INSERT INTO users (username, password, full_name, email, school_id, role, grade, graduation_year)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (username, hash_password(password), full_name, email, school_id, 'student', grade, graduation_year))
                    db.commit()
                    success = 'Registration successful! Please log in.'
                except sqlite3.IntegrityError as e:
                    error = f'Registration failed: {str(e)}'
            
            db.close()
    
    # Get list of schools
    db = get_db()
    schools = db.execute('SELECT id, name FROM schools ORDER BY name').fetchall()
    db.close()
    
    return render_template('register.html', error=error, success=success, schools=schools)

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (session['school_id'],)).fetchone()
    db.close()
    
    if not user or not school:
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user, school=school)

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET full_name = ?, email = ?
        WHERE id = ?
    ''', (data['full_name'], data['email'], session['user_id']))
    
    db.commit()
    db.close()
    
    session['full_name'] = data['full_name']
    return jsonify({'success': True})

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Change password"""
    data = request.get_json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
    
    db = get_db()
    user = db.execute('SELECT password FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user['password'] != hash_password(old_password):
        db.close()
        return jsonify({'success': False, 'error': 'Current password is incorrect'}), 400
    
    cursor = db.cursor()
    cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(new_password), session['user_id']))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/notes/class/<int:class_id>', methods=['GET'])
@login_required
def get_class_notes(class_id):
    """Get notes for a specific class"""
    db = get_db()
    notes = db.execute('''
        SELECT * FROM class_notes 
        WHERE user_id = ? AND class_id = ?
        ORDER BY created_at DESC
    ''', (session['user_id'], class_id)).fetchall()
    db.close()
    
    return jsonify([dict(n) for n in notes])

@app.route('/api/notes/add', methods=['POST'])
@login_required
def add_note():
    """Add a note for a class"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO class_notes (user_id, class_id, title, content)
        VALUES (?, ?, ?, ?)
    ''', (session['user_id'], data['class_id'], data['title'], data['content']))
    
    db.commit()
    note_id = cursor.lastrowid
    db.close()
    
    return jsonify({'success': True, 'id': note_id})

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    """Delete a note"""
    db = get_db()
    # Verify ownership
    note = db.execute('SELECT user_id FROM class_notes WHERE id = ?', (note_id,)).fetchone()
    
    if not note or note['user_id'] != session['user_id']:
        db.close()
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    cursor = db.cursor()
    cursor.execute('DELETE FROM class_notes WHERE id = ?', (note_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/student')
@login_required
def student_dashboard():
    """Student dashboard - CarPlay style"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (session['school_id'],)).fetchone()
    
    if not user or not school:
        db.close()
        session.clear()
        return redirect(url_for('login'))
    
    # Get only enrolled classes
    classes = db.execute('''
        SELECT c.* FROM classes c
        JOIN student_classes sc ON c.id = sc.class_id
        WHERE sc.user_id = ? AND c.school_id = ?
        ORDER BY c.period
    ''', (session['user_id'], session['school_id'])).fetchall()
    db.close()
    
    return render_template('student_dashboard.html', user=user, school=school, classes=classes)

@app.route('/api/schedule')
@login_required
def get_schedule():
    """Get school schedule for current user (enrolled classes only)"""
    db = get_db()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (session['school_id'],)).fetchone()
    classes = db.execute('''
        SELECT c.* FROM classes c
        JOIN student_classes sc ON c.id = sc.class_id
        WHERE sc.user_id = ? AND c.school_id = ?
        ORDER BY c.period
    ''', (session['user_id'], session['school_id'])).fetchall()
    db.close()
    
    return jsonify({
        'total_school_days': school['total_school_days'],
        'current_school_day': school['current_school_day'],
        'end_of_year_date': school['end_of_year_date'],
        'announcement': school['announcement'],
        'classes': [dict(c) for c in classes]
    })

@app.route('/friends')
@login_required
def friends_page():
    """Show friends and pending friend requests."""
    return render_template('friends.html', user=session.get('full_name'))

@app.route('/api/friends')
@login_required
def get_friends():
    """Return accepted friends and pending requests for the current user."""
    user_id = session['user_id']
    db = get_db()
    friends = db.execute('''
        SELECT u.id, u.username, u.full_name, u.grade
        FROM friends f
        JOIN users u ON u.id = CASE WHEN f.user_id_1 = ? THEN f.user_id_2 ELSE f.user_id_1 END
        WHERE f.user_id_1 = ? OR f.user_id_2 = ?
        ORDER BY u.full_name
    ''', (user_id, user_id, user_id)).fetchall()
    incoming = db.execute('''
        SELECT r.id, u.id AS user_id, u.username, u.full_name, r.created_at
        FROM friend_requests r
        JOIN users u ON u.id = r.sender_id
        WHERE r.receiver_id = ? AND r.status = 'pending'
        ORDER BY r.created_at DESC
    ''', (user_id,)).fetchall()
    outgoing = db.execute('''
        SELECT r.id, u.id AS user_id, u.username, u.full_name, r.created_at
        FROM friend_requests r
        JOIN users u ON u.id = r.receiver_id
        WHERE r.sender_id = ? AND r.status = 'pending'
        ORDER BY r.created_at DESC
    ''', (user_id,)).fetchall()
    db.close()
    return jsonify({
        'friends': [dict(friend) for friend in friends],
        'incoming': [dict(request) for request in incoming],
        'outgoing': [dict(request) for request in outgoing]
    })

@app.route('/api/friends/search')
@login_required
def search_users():
    """Search students in the current user's school."""
    search = request.args.get('q', '').strip()
    if len(search) < 2:
        return jsonify({'users': []})

    db = get_db()
    users = db.execute('''
        SELECT id, username, full_name, grade
        FROM users
        WHERE school_id = ? AND id != ?
          AND (full_name LIKE ? OR username LIKE ?)
        ORDER BY full_name
        LIMIT 20
    ''', (session['school_id'], session['user_id'], f'%{search}%', f'%{search}%')).fetchall()
    db.close()
    return jsonify({'users': [dict(user) for user in users]})

@app.route('/api/friends/request', methods=['POST'])
@login_required
def send_friend_request():
    """Send or re-send a friend request to a same-school user."""
    data = request.get_json() or {}
    receiver_id = data.get('user_id')
    db = get_db()
    receiver = db.execute('SELECT id FROM users WHERE id = ? AND school_id = ?',
                          (receiver_id, session['school_id'])).fetchone()
    if not receiver or receiver_id == session['user_id']:
        db.close()
        return jsonify({'success': False, 'error': 'User is not available'}), 400

    first_id, second_id = sorted((session['user_id'], receiver_id))
    friendship = db.execute('SELECT id FROM friends WHERE user_id_1 = ? AND user_id_2 = ?',
                            (first_id, second_id)).fetchone()
    if friendship:
        db.close()
        return jsonify({'success': False, 'error': 'You are already friends'}), 400

    existing = db.execute('''
        SELECT id, status FROM friend_requests
        WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
        ORDER BY id DESC LIMIT 1
    ''', (session['user_id'], receiver_id, receiver_id, session['user_id'])).fetchone()
    if existing and existing['status'] == 'pending':
        db.close()
        return jsonify({'success': False, 'error': 'Request already pending'}), 400

    if existing:
        db.execute('''
            UPDATE friend_requests SET sender_id = ?, receiver_id = ?, status = 'pending', created_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session['user_id'], receiver_id, existing['id']))
    else:
        db.execute('INSERT INTO friend_requests (sender_id, receiver_id) VALUES (?, ?)',
                   (session['user_id'], receiver_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/friends/request/<int:request_id>', methods=['PUT'])
@login_required
def respond_to_friend_request(request_id):
    """Accept or decline an incoming friend request."""
    action = (request.get_json() or {}).get('action')
    if action not in ('accept', 'decline'):
        return jsonify({'success': False, 'error': 'Invalid response'}), 400

    db = get_db()
    friend_request = db.execute('''
        SELECT sender_id, receiver_id FROM friend_requests
        WHERE id = ? AND receiver_id = ? AND status = 'pending'
    ''', (request_id, session['user_id'])).fetchone()
    if not friend_request:
        db.close()
        return jsonify({'success': False, 'error': 'Request not found'}), 404

    new_status = 'accepted' if action == 'accept' else 'declined'
    db.execute('UPDATE friend_requests SET status = ? WHERE id = ?', (new_status, request_id))
    if action == 'accept':
        first_id, second_id = sorted((friend_request['sender_id'], friend_request['receiver_id']))
        db.execute('INSERT OR IGNORE INTO friends (user_id_1, user_id_2) VALUES (?, ?)',
                   (first_id, second_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/friends/<int:friend_id>', methods=['DELETE'])
@login_required
def remove_friend(friend_id):
    """Remove an accepted friend."""
    first_id, second_id = sorted((session['user_id'], friend_id))
    db = get_db()
    db.execute('DELETE FROM friends WHERE user_id_1 = ? AND user_id_2 = ?', (first_id, second_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@app.route('/api/friends/<int:friend_id>/schedule')
@login_required
def friend_schedule(friend_id):
    """Return a friend's enrolled schedule when friendship is accepted."""
    first_id, second_id = sorted((session['user_id'], friend_id))
    db = get_db()
    friend = db.execute('''
        SELECT u.id, u.full_name, u.username
        FROM friends f JOIN users u ON u.id = ?
        WHERE f.user_id_1 = ? AND f.user_id_2 = ?
    ''', (friend_id, first_id, second_id)).fetchone()
    if not friend:
        db.close()
        return jsonify({'success': False, 'error': 'You are not friends with this user'}), 403
    classes = db.execute('''
        SELECT c.period, c.name, c.room, c.teacher, c.start_time, c.end_time
        FROM student_classes sc JOIN classes c ON c.id = sc.class_id
        WHERE sc.user_id = ? AND c.school_id = ?
        ORDER BY c.period
    ''', (friend_id, session['school_id'])).fetchall()
    db.close()
    return jsonify({'success': True, 'friend': dict(friend), 'classes': [dict(item) for item in classes]})

@app.route('/classes')
@login_required
def view_classes():
    """View and manage class enrollment"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (session['school_id'],)).fetchone()
    
    if not user or not school:
        db.close()
        session.clear()
        return redirect(url_for('login'))
    
    # Get all available classes filtered by user's grade (only approved classes)
    available_classes = db.execute('''
        SELECT c.* FROM classes c
        WHERE c.school_id = ?
        AND c.is_approved = 1
        AND (c.min_grade IS NULL OR c.min_grade <= ?)
        AND (c.max_grade IS NULL OR c.max_grade >= ?)
        ORDER BY c.period
    ''', (session['school_id'], user['grade'], user['grade'])).fetchall()
    
    # Get enrolled classes
    enrolled_ids = db.execute('''
        SELECT class_id FROM student_classes WHERE user_id = ?
    ''', (session['user_id'],)).fetchall()
    enrolled_class_ids = [e['class_id'] for e in enrolled_ids]
    
    db.close()
    
    return render_template('student_classes.html', user=dict(user) if user else None, school=dict(school) if school else None, classes=[dict(c) for c in available_classes], enrolled_class_ids=enrolled_class_ids)

@app.route('/api/student/enroll', methods=['POST'])
@login_required
def enroll_class():
    """Enroll in a class"""
    data = request.get_json()
    class_id = data.get('class_id')
    
    db = get_db()
    
    # Verify class exists and user's grade is eligible
    user = db.execute('SELECT grade FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    class_info = db.execute('SELECT * FROM classes WHERE id = ? AND school_id = ?', 
                           (class_id, session['school_id'])).fetchone()
    
    if not class_info:
        db.close()
        return jsonify({'success': False, 'error': 'Class not found'}), 404
    
    # Check grade eligibility
    if (class_info['min_grade'] and user['grade'] < class_info['min_grade']) or \
       (class_info['max_grade'] and user['grade'] > class_info['max_grade']):
        db.close()
        return jsonify({'success': False, 'error': 'You are not eligible for this class'}), 403
    
    # Check if already enrolled
    existing = db.execute('SELECT id FROM student_classes WHERE user_id = ? AND class_id = ?',
                         (session['user_id'], class_id)).fetchone()
    
    if existing:
        db.close()
        return jsonify({'success': False, 'error': 'Already enrolled in this class'}), 400
    
    try:
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO student_classes (user_id, class_id)
            VALUES (?, ?)
        ''', (session['user_id'], class_id))
        db.commit()
        db.close()
        return jsonify({'success': True})
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/student/enroll/<int:class_id>', methods=['DELETE'])
@login_required
def drop_class(class_id):
    """Drop a class"""
    db = get_db()
    
    # Verify enrollment exists
    enrollment = db.execute('SELECT id FROM student_classes WHERE user_id = ? AND class_id = ?',
                           (session['user_id'], class_id)).fetchone()
    
    if not enrollment:
        db.close()
        return jsonify({'success': False, 'error': 'Not enrolled in this class'}), 404
    
    cursor = db.cursor()
    cursor.execute('DELETE FROM student_classes WHERE user_id = ? AND class_id = ?',
                   (session['user_id'], class_id))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/student/create-class', methods=['POST'])
@login_required
def create_class_user():
    """User creates a class suggestion"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO classes (school_id, period, name, room, teacher, start_time, end_time, 
                                min_grade, max_grade, created_by, is_user_created, is_approved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0)
        ''', (
            session['school_id'],
            data.get('period'),
            data.get('name'),
            data.get('room', ''),
            data.get('teacher', ''),
            data.get('start_time'),
            data.get('end_time'),
            data.get('min_grade'),
            data.get('max_grade'),
            session['user_id']
        ))
        
        db.commit()
        class_id = cursor.lastrowid
        db.close()
        return jsonify({'success': True, 'id': class_id, 'message': 'Class submitted for admin approval'})
    except Exception as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin')
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    db = get_db()
    schools = db.execute('SELECT * FROM schools').fetchall()
    db.close()
    
    return render_template('admin_dashboard.html', schools=schools)

@app.route('/admin/school/<int:school_id>')
@admin_required
def edit_school(school_id):
    """Edit school settings"""
    db = get_db()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (school_id,)).fetchone()
    classes = db.execute('''
        SELECT c.*, u.full_name as creator_name 
        FROM classes c 
        LEFT JOIN users u ON c.created_by = u.id 
        WHERE c.school_id = ? 
        ORDER BY c.period
    ''', (school_id,)).fetchall()
    users = db.execute('SELECT * FROM users WHERE school_id = ?', (school_id,)).fetchall()
    db.close()
    
    if not school:
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_school_edit.html', school=dict(school) if school else None, classes=[dict(c) for c in classes], users=[dict(u) for u in users])

@app.route('/api/admin/school/<int:school_id>', methods=['POST'])
@admin_required
def update_school(school_id):
    """Update school data"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        UPDATE schools 
        SET name = ?, total_school_days = ?, current_school_day = ?, end_of_year_date = ?, announcement = ?
        WHERE id = ?
    ''', (data['name'], data['total_school_days'], data['current_school_day'], data['end_of_year_date'], data['announcement'], school_id))
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/class', methods=['POST'])
@admin_required
def add_class():
    """Add new class"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO classes (school_id, period, name, room, teacher, start_time, end_time, min_grade, max_grade)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['school_id'], data['period'], data['name'], data['room'], data.get('teacher'), 
          data['start_time'], data['end_time'], data.get('min_grade'), data.get('max_grade')))
    
    db.commit()
    class_id = cursor.lastrowid
    db.close()
    
    return jsonify({'success': True, 'id': class_id})

@app.route('/api/admin/class/<int:class_id>', methods=['PUT'])
@admin_required
def update_class(class_id):
    """Update class"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE classes 
        SET period = ?, name = ?, room = ?, teacher = ?, start_time = ?, end_time = ?, min_grade = ?, max_grade = ?
        WHERE id = ?
    ''', (data['period'], data['name'], data['room'], data.get('teacher'), 
          data['start_time'], data['end_time'], data.get('min_grade'), data.get('max_grade'), class_id))
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/class/<int:class_id>', methods=['DELETE'])
@admin_required
def delete_class(class_id):
    """Delete class"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/periods/<int:school_id>', methods=['GET'])
@admin_required
def get_periods(school_id):
    """Get all periods for a school"""
    db = get_db()
    periods = db.execute('''
        SELECT * FROM school_periods WHERE school_id = ? ORDER BY period_number
    ''', (school_id,)).fetchall()
    db.close()
    
    return jsonify([dict(p) for p in periods])

@app.route('/api/admin/periods', methods=['POST'])
@admin_required
def add_period():
    """Add a period to a school"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO school_periods (school_id, period_number, start_time, end_time)
            VALUES (?, ?, ?, ?)
        ''', (data['school_id'], data['period_number'], data['start_time'], data['end_time']))
        
        db.commit()
        period_id = cursor.lastrowid
        db.close()
        return jsonify({'success': True, 'id': period_id})
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'success': False, 'error': 'Period already exists'}), 400

@app.route('/api/admin/periods/<int:period_id>', methods=['PUT'])
@admin_required
def update_period(period_id):
    """Update a period"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        UPDATE school_periods 
        SET period_number = ?, start_time = ?, end_time = ?
        WHERE id = ?
    ''', (data['period_number'], data['start_time'], data['end_time'], period_id))
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/periods/<int:period_id>', methods=['DELETE'])
@admin_required
def delete_period(period_id):
    """Delete a period"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM school_periods WHERE id = ?', (period_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/admin/users/<int:school_id>')
@admin_required
def manage_users(school_id):
    """Manage users for school"""
    db = get_db()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (school_id,)).fetchone()
    users = db.execute('SELECT * FROM users WHERE school_id = ?', (school_id,)).fetchall()
    db.close()
    
    return render_template('admin_users.html', school=dict(school) if school else None, users=[dict(u) for u in users])

@app.route('/api/admin/user', methods=['POST'])
@admin_required
def add_user():
    """Add new user"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, password, full_name, email, school_id, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['username'], hash_password(data['password']), data['full_name'], data['email'], data['school_id'], data['role']))
        
        db.commit()
        user_id = cursor.lastrowid
        db.close()
        return jsonify({'success': True, 'id': user_id})
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({'success': False, 'error': 'Username already exists'}), 400

@app.route('/api/admin/user/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user"""
    data = request.get_json()
    
    db = get_db()
    cursor = db.cursor()
    
    if data.get('password'):
        cursor.execute('''
            UPDATE users 
            SET full_name = ?, email = ?, role = ?, password = ?
            WHERE id = ?
        ''', (data['full_name'], data['email'], data['role'], hash_password(data['password']), user_id))
    else:
        cursor.execute('''
            UPDATE users 
            SET full_name = ?, email = ?, role = ?
            WHERE id = ?
        ''', (data['full_name'], data['email'], data['role'], user_id))
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    db.close()
    
    return jsonify({'success': True})

def get_user_by_id(user_id):
    """Get user by ID"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    db.close()
    return user

@app.route('/admin/enrollment/<int:school_id>')
@admin_required
def manage_enrollment(school_id):
    """Manage student enrollments for school"""
    db = get_db()
    school = db.execute('SELECT * FROM schools WHERE id = ?', (school_id,)).fetchone()
    
    if not school:
        return redirect(url_for('admin_dashboard'))
    
    # Get all students in school
    students = db.execute(
        'SELECT id, full_name, grade, graduation_year FROM users WHERE school_id = ? AND role = ? ORDER BY full_name',
        (school_id, 'student')
    ).fetchall()
    
    # Get all classes in school with enrollment counts
    classes = db.execute(
        'SELECT c.*, COUNT(sc.id) as enrolled_count FROM classes c LEFT JOIN student_classes sc ON c.id = sc.class_id WHERE c.school_id = ? GROUP BY c.id ORDER BY c.period',
        (school_id,)
    ).fetchall()
    
    # Get all enrollments with student and class info
    enrollments = db.execute('''
        SELECT sc.id, sc.user_id, sc.class_id, u.full_name, u.grade, c.name as class_name, c.period
        FROM student_classes sc
        JOIN users u ON sc.user_id = u.id
        JOIN classes c ON sc.class_id = c.id
        WHERE u.school_id = ?
        ORDER BY c.period, u.full_name
    ''', (school_id,)).fetchall()
    
    db.close()
    
    return render_template('admin_enrollment.html', 
        school=dict(school) if school else None, 
        students=[dict(s) for s in students],
        classes=[dict(c) for c in classes],
        enrollments=[dict(e) for e in enrollments])

@app.route('/api/admin/enrollment/add', methods=['POST'])
@admin_required
def admin_add_enrollment():
    """Admin adds student to class"""
    data = request.get_json()
    user_id = data.get('user_id')
    class_id = data.get('class_id')
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # Check if enrollment already exists
        existing = db.execute(
            'SELECT id FROM student_classes WHERE user_id = ? AND class_id = ?',
            (user_id, class_id)
        ).fetchone()
        
        if existing:
            db.close()
            return jsonify({'success': False, 'error': 'Student already enrolled in this class'}), 400
        
        # Insert enrollment
        cursor.execute(
            'INSERT INTO student_classes (user_id, class_id) VALUES (?, ?)',
            (user_id, class_id)
        )
        
        db.commit()
        db.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError as e:
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/enrollment/remove/<int:class_id>/<int:user_id>', methods=['DELETE'])
@admin_required
def admin_remove_enrollment(class_id, user_id):
    """Admin removes student from class"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'DELETE FROM student_classes WHERE class_id = ? AND user_id = ?',
        (class_id, user_id)
    )
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/class/<int:class_id>/approve', methods=['PUT'])
@admin_required
def approve_class(class_id):
    """Admin approves a user-created class"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'UPDATE classes SET is_approved = 1 WHERE id = ?',
        (class_id,)
    )
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/class/<int:class_id>/reject', methods=['DELETE'])
@admin_required
def reject_class(class_id):
    """Admin rejects a user-created class"""
    db = get_db()
    cursor = db.cursor()
    
    # Delete any enrollments first
    cursor.execute('DELETE FROM student_classes WHERE class_id = ?', (class_id,))
    
    # Delete the class
    cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
    
    db.commit()
    db.close()
    
    return jsonify({'success': True})

if __name__ == "__main__":
    # Initialize database on startup
    if not os.path.exists(DATABASE):
        init_db()
    else:
        # Create tables if they don't exist (in case of update)
        init_db()
    
    app.run(debug=True, host='0.0.0.0', port=5000)