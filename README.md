# 🎓 Future Proof Learning for Everyone

A full-stack web application for online learning with courses, mentors, gamification, AI risk prediction, and certificates.

## Features

- 🔐 User registration, login, logout with session management
- 📊 Personal dashboard with progress, streaks, and AI risk analysis
- 📚 Course catalog with enrollment and lesson tracking
- 🧑‍🏫 Mentor directory with mentorship request forms
- 🔥 Daily login streaks and points system
- 🤖 AI-based learning risk prediction (Low/Medium/High)
- 🏆 Certificate generation on course completion (printable)
- 📁 Admin panel (add/edit/delete courses, view users)
- 🔔 Notification system for key events

## Requirements

- Python 3.7+
- Flask

## Installation & Setup

```bash
# 1. Install Flask
pip install flask

# 2. Run the app
python app.py

# 3. Open in browser
# http://localhost:5000
```

## Default Admin Account

- **Email:** admin@example.com
- **Password:** admin123

## Folder Structure

```
├── app.py              # Main Flask application
├── database.db         # SQLite database (auto-created)
├── README.md
├── static/
│   ├── css/style.css   # Stylesheet
│   └── js/main.js      # Client-side JavaScript
└── templates/
    ├── base.html        # Base template
    ├── home.html        # Landing page
    ├── login.html       # Login page
    ├── register.html    # Registration page
    ├── dashboard.html   # User dashboard
    ├── courses.html     # Course listing
    ├── course_detail.html  # Course detail + lessons
    ├── mentors.html     # Mentor listing
    ├── mentor_detail.html  # Mentor profile + request
    ├── certificate.html # Certificate page
    └── admin/
        ├── dashboard.html  # Admin overview
        ├── course_form.html # Add/edit course
        └── users.html      # User management
```

## Database Tables

- `users` - User accounts
- `courses` - Course catalog
- `enrollments` - User-course enrollments
- `progress` - Lesson completion tracking
- `mentors` - Mentor profiles
- `mentor_requests` - Mentorship requests
- `streaks` - Daily login streaks
- `notifications` - User notifications
