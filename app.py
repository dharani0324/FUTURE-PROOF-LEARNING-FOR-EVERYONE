import os
import sqlite3
import csv
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
import string
import random
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.units import inch
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = 'super_secret_key_future_proof'
DB_PATH = 'database.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    # Create tables
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'student',
            streak INTEGER DEFAULT 0,
            last_login DATE,
            tenth_marks REAL DEFAULT 0,
            twelfth_marks REAL DEFAULT 0,
            ug_marks REAL DEFAULT 0,
            mock_test_score REAL DEFAULT 0,
            attendance REAL DEFAULT 0,
            skills TEXT DEFAULT '',
            resume_strength INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            mentor_name TEXT NOT NULL,
            duration TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            course_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES courses (id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS mentors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            expertise TEXT NOT NULL,
            email TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS placement_drives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            salary REAL NOT NULL,
            min_10th REAL NOT NULL,
            min_12th REAL NOT NULL,
            min_ug REAL NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS drive_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drive_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'Applied',
            FOREIGN KEY (drive_id) REFERENCES placement_drives(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Pre-populate data if empty
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO courses (title, description, mentor_name, duration) VALUES ('Full Stack Web Dev', 'Learn HTML, CSS, JS, Python, Flask', 'Alice', '3 months')")
        c.execute("INSERT INTO courses (title, description, mentor_name, duration) VALUES ('Data Science 101', 'Intro to ML and Data Analytics', 'Bob', '2 months')")
        c.execute("INSERT INTO mentors (name, expertise, email) VALUES ('Alice', 'Web Development', 'alice@example.com')")
        c.execute("INSERT INTO mentors (name, expertise, email) VALUES ('Bob', 'Data Science', 'bob@example.com')")
        
        # Admin user
        c.execute("INSERT INTO users (name, email, password, role) VALUES ('Admin', 'admin@example.com', ?, 'admin')", (generate_password_hash('admin123'),))

    try:
        c.execute("ALTER TABLE enrollments ADD COLUMN completed INTEGER DEFAULT 0")
        c.execute("ALTER TABLE enrollments ADD COLUMN completed_date TEXT")
    except sqlite3.OperationalError:
        pass # Already exists

    try:
        c.execute("ALTER TABLE courses ADD COLUMN degree TEXT DEFAULT 'General'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
        c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except sqlite3.OperationalError:
        pass

    # Give all existing users a random referral code if they don't have one
    users = c.execute("SELECT id FROM users WHERE referral_code IS NULL").fetchall()
    for u in users:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        c.execute("UPDATE users SET referral_code = ? WHERE id = ?", (code, u['id']))

    # Seed 80 courses if there are few courses
    c.execute("SELECT COUNT(*) FROM courses")
    if c.fetchone()[0] < 20: 
        degrees_map = {
            'Engineering': ['Python Programming', 'Data Structures', 'Circuit Analysis', 'Thermodynamics', 'Fluid Mechanics', 'Robotics', 'AutoCAD', 'VLSI Design', 'Software Engineering', 'Machine Learning', 'Computer Networks', 'Control Systems', 'Microprocessors', 'Digital Signal Processing', 'Heat Transfer', 'Manufacturing Processes', 'Power Systems', 'Embedded Systems', 'Artificial Intelligence', 'Cyber Security'],
            'Arts': ['Modern History', 'English Literature', 'Psychology 101', 'Sociology', 'Political Science', 'Economics', 'Philosophy', 'World Religions', 'Creative Writing', 'Art History', 'Music Theory', 'Theatre Arts', 'Cultural Studies', 'Anthropology', 'Linguistics', 'Human Geography', 'International Relations', 'Ethics', 'Gender Studies', 'Media Studies'],
            'Science': ['Quantum Physics', 'Organic Chemistry', 'Molecular Biology', 'Genetics', 'Earth Science', 'Astronomy', 'Environmental Science', 'Inorganic Chemistry', 'Physical Chemistry', 'Microbiology', 'Botany', 'Zoology', 'Ecology', 'Biochemistry', 'Neuroscience', 'Calculus I', 'Linear Algebra', 'Statistics', 'Thermodynamics', 'Optics'],
            'BSc': ['Advanced Mathematics', 'Applied Physics', 'Applied Chemistry', 'Computer Science', 'Information Technology', 'Data Analytics', 'Actuarial Science', 'Geology', 'Bioinformatics', 'Forensic Science', 'Nutrition', 'Sports Science', 'Marine Biology', 'Agriculture', 'Forestry', 'Horticulture', 'Biotechnology', 'Food Technology', 'Genomics', 'Materials Science']
        }
        for deg, c_list in degrees_map.items():
            for title in c_list:
                c.execute("INSERT INTO courses (title, description, mentor_name, duration, degree) VALUES (?, ?, ?, ?, ?)",
                          (title, f"Comprehensive guide to {title}", "Expert Mentor", "3 months", deg))

    # Seed 20 mentors if there are few mentors
    c.execute("SELECT COUNT(*) FROM mentors")
    if c.fetchone()[0] < 20:
        mentors_list = [
            ('Dr. Sarah Connor', 'Artificial Intelligence', 'sarah@example.com'),
            ('Prof. John Smith', 'Data Science', 'john.smith@example.com'),
            ('Emily Chen', 'Software Engineering', 'emily.chen@example.com'),
            ('Michael Johnson', 'Machine Learning', 'michael.j@example.com'),
            ('Dr. Alice Roberts', 'Arts & Humanities', 'alice.r@example.com'),
            ('Robert Brown', 'Economics', 'rbrown@example.com'),
            ('Jessica Williams', 'Psychology', 'jwilliams@example.com'),
            ('David Jones', 'Physics', 'djones@example.com'),
            ('Dr. Richard Davis', 'Chemistry', 'rdavis@example.com'),
            ('Prof. Linda Miller', 'Biology', 'lmiller@example.com'),
            ('James Wilson', 'Mathematics', 'jwilson@example.com'),
            ('Mary Moore', 'Statistics', 'mmoore@example.com'),
            ('William Taylor', 'Marketing', 'wtaylor@example.com'),
            ('Barbara Anderson', 'Business Management', 'banderson@example.com'),
            ('Richard Thomas', 'Finance', 'rthomas@example.com'),
            ('Susan Jackson', 'Human Resources', 'sjackson@example.com'),
            ('Dr. Joseph White', 'Cyber Security', 'jwhite@example.com'),
            ('Margaret Harris', 'UI/UX Design', 'mharris@example.com'),
            ('Thomas Martin', 'Cloud Computing', 'tmartin@example.com'),
            ('Prof. Dorothy Thompson', 'Philosophy', 'dthompson@example.com')
        ]
        for m in mentors_list:
            c.execute("INSERT INTO mentors (name, expertise, email) VALUES (?, ?, ?)", m)

    mentors_in_db = [m['name'] for m in c.execute("SELECT name FROM mentors").fetchall()]
    if mentors_in_db:
        expert_courses = c.execute("SELECT id FROM courses WHERE mentor_name = 'Expert Mentor'").fetchall()
        for course in expert_courses:
            c.execute("UPDATE courses SET mentor_name = ? WHERE id = ?", (random.choice(mentors_in_db), course['id']))

    conn.commit()
    conn.close()

# Initialize DB on startup
with app.app_context():
    init_db()

def create_notification(user_id, message):
    conn = get_db()
    conn.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (user_id, message))
    conn.commit()
    conn.close()

def predict_placement(user):
    # Simple logic-based prediction
    score = 0
    if user['mock_test_score'] >= 80: score += 3
    elif user['mock_test_score'] >= 60: score += 2
    else: score += 1

    if user['attendance'] >= 90: score += 3
    elif user['attendance'] >= 75: score += 2
    else: score += 1

    if user['resume_strength'] >= 8: score += 3 # out of 10
    elif user['resume_strength'] >= 5: score += 2
    else: score += 1
    
    if score >= 8: return 'High'
    elif score >= 5: return 'Medium'
    else: return 'Low'

@app.before_request
def update_streak():
    if 'user_id' in session:
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if user:
            today = date.today().isoformat()
            last_login = user['last_login']
            if last_login != today:
                streak = user['streak']
                if last_login:
                    try:
                        last_login_date = datetime.strptime(last_login, '%Y-%m-%d').date()
                        if date.today() - last_login_date == timedelta(days=1):
                            streak += 1
                        else:
                            streak = 1
                    except ValueError:
                        streak = 1
                else:
                    streak = 1
                conn.execute("UPDATE users SET streak = ?, last_login = ? WHERE id = ?", (streak, today, session['user_id']))
                conn.commit()
                session['streak'] = streak
        conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        ref_code = request.form.get('referral_code', '')
        
        conn = get_db()
        try:
            user_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            referrer_id = None
            if ref_code:
                referrer = conn.execute("SELECT id, streak FROM users WHERE referral_code = ?", (ref_code,)).fetchone()
                if referrer:
                    referrer_id = referrer['id']
                    # Bonus
                    conn.execute("UPDATE users SET streak = streak + 5 WHERE id = ?", (referrer_id,))
                    # create_notification logic without duplicate connection opening
                    conn.execute("INSERT INTO notifications (user_id, message) VALUES (?, ?)", (referrer_id, f"Someone registered using your referral code! You got +5 streak bonus."))
                    
            conn.execute("INSERT INTO users (name, email, password, referral_code, referred_by) VALUES (?, ?, ?, ?, ?)", 
                         (name, email, password, user_code, referrer_id))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            session['streak'] = user['streak']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    if user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))

    # Get enrolled courses
    courses = conn.execute("""
        SELECT c.*, e.completed, e.completed_date FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.user_id = ?
    """, (session['user_id'],)).fetchall()
    
    notifications = conn.execute("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (session['user_id'],)).fetchall()
    
    placement_chance = predict_placement(user)
    conn.close()
    
    return render_template('dashboard.html', user=user, courses=courses, notifications=notifications, placement_chance=placement_chance)

@app.route('/courses')
def courses():
    if 'user_id' not in session: return redirect(url_for('login'))
    degree = request.args.get('degree', 'All')
    conn = get_db()
    if degree != 'All':
        all_courses = conn.execute("SELECT * FROM courses WHERE degree = ?", (degree,)).fetchall()
    else:
        all_courses = conn.execute("SELECT * FROM courses").fetchall()
    enrolled = [row['course_id'] for row in conn.execute("SELECT course_id FROM enrollments WHERE user_id = ?", (session['user_id'],)).fetchall()]
    conn.close()
    return render_template('courses.html', courses=all_courses, enrolled=enrolled, selected_degree=degree)

@app.route('/enroll/<int:course_id>')
def enroll(course_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    try:
        conn.execute("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", (session['user_id'], course_id))
        conn.commit()
        create_notification(session['user_id'], 'Successfully enrolled in course!')
        flash('Enrolled successfully.', 'success')
    except Exception as e:
        flash('Error enrolling.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('courses'))

@app.route('/mentors')
def mentors():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    mentors_list = conn.execute("SELECT * FROM mentors").fetchall()
    conn.close()
    return render_template('mentors.html', mentors=mentors_list)

@app.route('/placements')
def placements():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    drives = conn.execute("SELECT * FROM placement_drives").fetchall()
    applications = [row['drive_id'] for row in conn.execute("SELECT drive_id FROM drive_applications WHERE user_id = ?", (session['user_id'],)).fetchall()]
    conn.close()
    return render_template('placements.html', drives=drives, user=user, applications=applications)

@app.route('/apply_drive/<int:drive_id>')
def apply_drive(drive_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    drive = conn.execute("SELECT * FROM placement_drives WHERE id = ?", (drive_id,)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    
    if user['tenth_marks'] >= drive['min_10th'] and user['twelfth_marks'] >= drive['min_12th'] and user['ug_marks'] >= drive['min_ug']:
        conn.execute("INSERT INTO drive_applications (drive_id, user_id) VALUES (?, ?)", (drive_id, session['user_id']))
        conn.commit()
        create_notification(session['user_id'], f"Applied for {drive['company_name']} drive")
        flash('Applied successfully!', 'success')
    else:
        flash('Not eligible for this drive.', 'danger')
    conn.close()
    return redirect(url_for('placements'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    if request.method == 'POST':
        tenth = request.form.get('tenth_marks', 0)
        twelfth = request.form.get('twelfth_marks', 0)
        ug = request.form.get('ug_marks', 0)
        skills = request.form.get('skills', '')
        mock = request.form.get('mock_test_score', 0)
        attendance = request.form.get('attendance', 0)
        resume = request.form.get('resume_strength', 0)
        
        conn.execute("""
            UPDATE users SET tenth_marks=?, twelfth_marks=?, ug_marks=?, skills=?, mock_test_score=?, attendance=?, resume_strength=? WHERE id=?
        """, (tenth, twelfth, ug, skills, mock, attendance, resume, session['user_id']))
        conn.commit()
        flash('Profile updated!', 'success')
        
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin': return redirect(url_for('index'))
    
    conn = get_db()
    if request.method == 'POST':
        # Create Drive
        company = request.form['company_name']
        salary = request.form['salary']
        m10 = request.form['min_10th']
        m12 = request.form['min_12th']
        mug = request.form['min_ug']
        conn.execute("INSERT INTO placement_drives (company_name, salary, min_10th, min_12th, min_ug) VALUES (?, ?, ?, ?, ?)", (company, salary, m10, m12, mug))
        conn.commit()
        flash('Drive created successfully.', 'success')
        
    stats = {
        'users': conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        'courses': conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        'drives': conn.execute("SELECT COUNT(*) FROM placement_drives").fetchone()[0]
    }
    
    applications = conn.execute("""
        SELECT a.id, a.status, u.name as student_name, p.company_name as company
        FROM drive_applications a
        JOIN users u ON a.user_id = u.id
        JOIN placement_drives p ON a.drive_id = p.id
    """).fetchall()
    
    drives = conn.execute("SELECT * FROM placement_drives").fetchall()
    
    conn.close()
    return render_template('admin.html', stats=stats, applications=applications, drives=drives)

@app.route('/admin/download_csv/<int:drive_id>')
def download_csv(drive_id):
    if 'user_id' not in session or session.get('role') != 'admin': return redirect(url_for('index'))
    conn = get_db()
    drive = conn.execute("SELECT * FROM placement_drives WHERE id=?", (drive_id,)).fetchone()
    users = conn.execute("""
        SELECT name, email, tenth_marks, twelfth_marks, ug_marks 
        FROM users 
        WHERE role='student' AND tenth_marks >= ? AND twelfth_marks >= ? AND ug_marks >= ?
    """, (drive['min_10th'], drive['min_12th'], drive['min_ug'])).fetchall()
    
    def generate():
        yield 'Name,Email,10th,12th,UG\n'
        for u in users:
            yield f"{u['name']},{u['email']},{u['tenth_marks']},{u['twelfth_marks']},{u['ug_marks']}\n"
            
    conn.close()
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename=eligible_{drive_id}.csv'})

@app.route('/complete/<int:course_id>', methods=['POST'])
def complete_course(course_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    today = date.today().isoformat()
    conn.execute("UPDATE enrollments SET completed = 1, completed_date = ? WHERE user_id = ? AND course_id = ?", (today, session['user_id'], course_id))
    conn.commit()
    conn.close()
    flash('Course marked as completed!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/certificates')
def certificates():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    completed_courses = conn.execute("""
        SELECT c.*, e.completed_date FROM courses c
        JOIN enrollments e ON c.id = e.course_id
        WHERE e.user_id = ? AND e.completed = 1
    """, (session['user_id'],)).fetchall()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('certificates.html', courses=completed_courses, user=user)

@app.route('/download_certificate/<int:course_id>')
def download_certificate(course_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db()
    course = conn.execute("SELECT c.title, e.completed_date FROM courses c JOIN enrollments e ON c.id = e.course_id WHERE e.user_id = ? AND c.id = ? AND e.completed = 1", (session['user_id'], course_id)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    
    if not course:
        flash('Invalid certificate request.', 'danger')
        return redirect(url_for('certificates'))

    buffer = BytesIO()
    try:
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Draw border
        c.setLineWidth(5)
        c.rect(20, 20, width - 40, height - 40)
        c.setLineWidth(1)
        c.rect(26, 26, width - 52, height - 52)
        
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(width / 2.0, height - 100, "Certificate of Completion")
        
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2.0, height - 160, "This is to certify that")
        
        c.setFont("Helvetica-Bold", 32)
        c.drawCentredString(width / 2.0, height - 220, user['name'])
        
        c.setFont("Helvetica", 18)
        c.drawCentredString(width / 2.0, height - 280, "has successfully completed the course")
        
        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(width / 2.0, height - 340, course['title'])
        
        c.setFont("Helvetica", 14)
        c.drawCentredString(width / 2.0, height - 400, f"Date of Completion: {course['completed_date']}")
        
        c.setFont("Helvetica-Oblique", 14)
        c.drawString(width - 250, 100, "Future Proof Learning")
        c.line(width - 250, 95, width - 50, 95)
        c.drawString(width - 220, 80, "Authorized Signature")
        
        c.save()
    except Exception as e:
        flash('Error generating PDF. Please contact support.', 'danger')
        return redirect(url_for('certificates'))

    buffer.seek(0)
    return Response(buffer.getvalue(), mimetype='application/pdf', headers={'Content-Disposition': f'attachment; filename=Certificate_{course_id}.pdf'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
