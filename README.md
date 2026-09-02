# CampusPulse 🎓

A comprehensive school schedule management system with a beautiful, modern interface. CampusPulse helps students and administrators manage school schedules, classes, and announcements with real-time countdowns and multi-school support.

## Features ✨

### Student Dashboard
- **Real-time Clock & Date** - Always know what time it is
- **Current Period Display** - See which class is happening now
- **Live Countdown Timer** - Watch the minutes tick down until class ends
- **Full Schedule View** - See all classes for the day with times and rooms
- **School Day Counter** - Track progress through the school year
- **Automatic School Day Counter** - Advances once per weekday and stops at the school's total day count
- **Summer Countdown** - Days remaining until summer break
- **Announcements** - Stay updated with school announcements
- **Active Class Highlight** - Current class is visually distinguished
- **Theme Toggle** - Switch between dark and light modes (preference saved)
- **User Profile** - View and edit profile information
- **Password Management** - Change password securely
- **Friends & Schedule Sharing** - Send, accept, and decline requests; view accepted friends' enrolled schedules

### Authentication System
- **User Registration** - Self-service registration for new students
- **Secure Login** - Username and password authentication
- **Role-Based Access** - Separate admin and student interface
- **Password Security** - Minimum 6 characters, hashed storage
- **Multi-School Support** - Each user belongs to a specific school

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Security**: Password hashing with SHA-256
- **API**: RESTful endpoints for data management

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   cd CampusPulse
   ```

2. **Install dependencies**
   ```bash
   pip install flask
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   - Open your browser and navigate to `http://localhost:5000`
   - You'll be redirected to the login page

## Getting Started

### Initial Setup
The application requires at least one school to be created before users can register:

1. **Create your first school**:
   - Use Python to add a school directly to the database, or
   - Modify `app.py` to temporarily add demo data in `init_db()`, or
   - Start the app and manually insert a school using a SQLite client

2. **Register your first account**:
   - Go to the login page and click "Register here"
   - Fill in your details and select your school
   - Use a password with at least 6 characters
   - Submit to create your account

3. **Access features**:
   - **Students**: Login to view your schedule, toggle themes, manage your profile
   - **Admins**: Login and navigate to Admin Dashboard to manage schools, classes, and users

## Project Structure

```
CampusPulse/
├── app.py                          # Main Flask application
├── campus_pulse.db                 # SQLite database (auto-created)
├── templates/                      # HTML templates
│   ├── login.html                 # Login page
│   ├── student_dashboard.html     # Student dashboard
│   ├── admin_dashboard.html       # Admin home dashboard
│   ├── admin_school_edit.html     # School settings & class management
│   └── admin_users.html           # User management page
├── README.md                       # This file
└── requirements.txt                # Python dependencies
```

## Database Schema

### Schools Table
- `id`: Primary key
- `name`: School name
- `total_school_days`: Total days in school year
- `current_school_day`: Current day of year
- `last_school_day_date`: Date through which the counter has been updated
- `end_of_year_date`: Date school ends
- `announcement`: School announcement

### Users Table
- `id`: Primary key
- `username`: Unique username
- `password`: Hashed password (SHA-256)
- `full_name`: User's full name
- `email`: User email
- `school_id`: Foreign key to schools
- `role`: 'student' or 'admin'
- `grade`: Student grade level
- `graduation_year`: Expected graduation year

### Friend Requests and Friends Tables
- Friend requests track sender, receiver, status, and timestamp
- Accepted friendships are stored separately with a unique user pair
- Friend connections are limited to users in the same school

### Classes Table
- `id`: Primary key
- `school_id`: Foreign key to schools
- `period`: Class period number
- `name`: Class name
- `room`: Room number
- `start_time`: Class start time (HH:MM)
- `end_time`: Class end time (HH:MM)

## Usage Guide

### For New Users

1. **Register an Account**
   - Click "Register here" on the login page
   - Enter your full name, username, email, and select your school
   - Create a password (minimum 6 characters)
   - Confirm your password matches
   - Submit to create your account
   - Login with your new credentials

### For Students

1. **Login** - Enter your username and password
2. **View Dashboard** - See your current class, remaining time, and full schedule
3. **Check Schedule** - Scroll to see all classes for the day
4. **Track Progress** - See school day counter and summer countdown
5. **Receive Announcements** - Check school announcements at the top
6. **Manage Your Profile**
   - Click the 👤 button in the top-right corner
   - Edit your full name and email
   - Change your password (requires old password verification)
   - View your account information
7. **Connect with Friends**
   - Open the 👥 Friends button from the dashboard
   - Search classmates by name or username
   - Send and respond to friend requests
   - Open an accepted friend's schedule
8. **Toggle Theme**
   - Click the 🌙 button in the top-right corner
   - Switch between dark and light modes
   - Your preference is saved automatically

### For Administrators

1. **Login with Admin Account** - Use your admin credentials
2. **Manage Schools**
   - View all schools from the dashboard
   - Click "Edit School" to modify school settings (name, school year dates, announcement)
   
3. **Manage Classes**
   - Go to school edit page
   - Add new classes with period, name, room, and times
   - Edit existing classes inline
   - Delete classes as needed
   
4. **Manage Users**
   - Go to users section
   - Add new students or admins
   - Edit user information and roles
   - Delete users
   
5. **Update Announcements** - Modify school announcements in real-time

## API Endpoints

### Authentication & Account Management
- `POST /login` - User login
- `GET /logout` - User logout
- `GET/POST /register` - Register new user account
- `GET /profile` - View user profile
- `POST /api/profile/update` - Update full name and email
- `POST /api/profile/change-password` - Change password (requires old password verification)

### Student Routes
- `GET /student` - Student dashboard
- `GET /friends` - Friends and schedule-sharing page
- `GET /api/schedule` - Get school schedule (JSON)
- `GET /api/notes/class/<id>` - Get notes for a specific class
- `POST /api/notes/add` - Create a new note
- `DELETE /api/notes/<id>` - Delete a note

### Friends API Endpoints
- `GET /api/friends` - List friends and pending requests
- `GET /api/friends/search?q=<name>` - Search same-school users
- `POST /api/friends/request` - Send a friend request
- `PUT /api/friends/request/<id>` - Accept or decline a request
- `DELETE /api/friends/<id>` - Remove a friend
- `GET /api/friends/<id>/schedule` - View an accepted friend's enrolled schedule

### Admin Routes
- `GET /admin` - Admin dashboard
- `GET /admin/school/<id>` - Edit school settings
- `GET /admin/users/<id>` - Manage users

### Admin API Endpoints
- `POST /api/admin/school/<id>` - Update school (name, dates, announcement)
- `POST /api/admin/class` - Add new class
- `PUT /api/admin/class/<id>` - Update class details
- `DELETE /api/admin/class/<id>` - Delete class
- `POST /api/admin/user` - Add new user
- `PUT /api/admin/user/<id>` - Update user (optional password change)
- `DELETE /api/admin/user/<id>` - Delete user

## Customization

### Changing the App Title
Edit the `<title>` tags in HTML templates to customize the page title.

### Modifying Color Scheme
Edit the CSS variables in the `<style>` sections:
```css
:root {
    --primary-bg: #0f172a;
    --card-bg: #1e293b;
    --accent-blue: #38bdf8;
    --accent-green: #22c55e;
    ...
}
```

### Adding New Schools
1. Login as admin
2. Click "Add School" button (if implemented)
3. Or use Flask shell:
   ```python
   from app import get_db
   db = get_db()
   db.execute('INSERT INTO schools (name, total_school_days, current_school_day, end_of_year_date, announcement) VALUES (?, ?, ?, ?, ?)',
              ('My School', 180, 1, '2027-06-15', 'Welcome!'))
   db.commit()
   ```

## Features Coming Soon

- [ ] Full school creation in admin panel
- [ ] Calendar view for the entire school year
- [ ] Student schedule export (PDF/iCal)
- [ ] Email notifications for announcements
- [ ] Mobile app version
- [ ] Class notes display on student dashboard
- [ ] Timetable sync with Google Calendar

## Troubleshooting

### Database Issues
If you encounter database errors, delete `campus_pulse.db` and restart the app. It will be recreated automatically.

### Login Issues
- Ensure you're using correct username and password
- Check browser console for errors (F12)
- Try clearing browser cache and cookies

### Display Issues
- Ensure JavaScript is enabled in your browser
- Try refreshing the page
- Check that you're using a modern browser (Chrome, Firefox, Safari, Edge)

## Security Considerations

⚠️ **Important**: This is a demo application. For production use:
- Use a proper authentication system (JWT, OAuth, etc.)
- Implement HTTPS/SSL
- Use a production-grade database
- Add rate limiting on login attempts
- Implement password requirements and validation
- Add audit logging
- Use environment variables for secrets

## Support & Contributing

For issues, suggestions, or contributions, please open an issue or pull request on the GitHub repository.

## License

This project is open source and available under the MIT License.

---

**Enjoy using CampusPulse! 🚀**

