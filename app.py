from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime, timedelta



app = Flask(__name__)
app.secret_key = '136bbad7ffbcea6d3b679dbaefc108aeab09f3f7c9c6d332'


def calculate_rank(signins):
    """Calculate the rank of a user based on the number of sign-ins."""
    RANKS = {
        'Member': 1,
        'Bonk': 120,
        'Dorm': 200,
        'Area': 250,
        'City': 320,
        'State': 400,
        'Zonal': 500,
        'National': 600,
        'Regional': 700,
        'Global': 1000,
        'Universal': 1500
    }
    for rank, threshold in sorted(RANKS.items(), key=lambda x: x[1], reverse=True):
        if signins >= threshold:
            return rank
    return 'Unranked'


# Database connection
def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user_id():
    """Retrieve the current user's ID from the session."""
    return session.get('user_id')


@app.route('/')
def index():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, country FROM Users').fetchall()
    conn.close()
    return render_template('index.html', users=users)


@app.route('/user_details/<int:user_id>')
def user_detail(user_id):
    """Display the user details, their rank, tasks, and the remaining time for sign-in if applicable."""
    conn = get_db_connection()
    
    # Fetch user details
    user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        conn.close()
        return "User not found", 404
    
    # Fetch user rank
    rank = conn.execute('SELECT * FROM Ranks WHERE user_id = ?', (user_id,)).fetchone()
    referral_link = f"https://yourdomain.com/register/{user_id}"
    
    # Calculate remaining time for sign-in
    last_signin = conn.execute(
        "SELECT date, time FROM Attendance WHERE user_id = ? ORDER BY date DESC, time DESC LIMIT 1", 
        (user_id,)
    ).fetchone()

    if last_signin:
        last_signin_time = datetime.strptime(f"{last_signin['date']} {last_signin['time']}", "%Y-%m-%d %H:%M:%S")
        time_diff = datetime.now() - last_signin_time
        if time_diff < timedelta(hours=12):
            remaining_time = timedelta(hours=12) - time_diff
            remaining_time_str = str(remaining_time).split('.')[0]  # Format the remaining time as "H:MM:SS"
        else:
            remaining_time_str = None
    else:
        remaining_time_str = None
    
    conn.close()
    
    return render_template('user_detail.html', user=user, rank=rank, remaining_time=remaining_time_str, referral_link=referral_link)


@app.route('/update_country/<int:user_id>', methods=['GET', 'POST'])
def update_country(user_id):
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_country = request.form['country']
        
        # Update the user's country
        conn.execute('UPDATE Users SET country = ? WHERE id = ?', (new_country, user_id))
        
        # Increment the user's sign-ins by 5
        conn.execute('UPDATE Ranks SET signins = signins + 5 WHERE user_id = ?', (user_id,))
        
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('user_detail', user_id=user_id))
    

    user = conn.execute('SELECT country_updated FROM Users WHERE id = ?', (user_id,)).fetchone()

    if user and not user['country_updated']:
            # Perform country update logic here

            # Update the state to mark the button as clicked
            conn.execute('UPDATE Users SET country_updated = 1 WHERE id = ?', (user_id,))
            conn.commit()
    
    # Fetch current country for display and any other needed information
    user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()
    conn.close()

    if user is None:
        return "User not found", 404

    countries = ["USA", "Canada", "UK", "Germany", "France", "India"]  # Add more as needed
    return render_template('update_country.html', user_id=user_id, user=user, countries=countries, current_country=user['country'])



@app.route('/signin/<int:user_id>', methods=['POST'])
def signin(user_id):
    """Handle user sign-in and manage sign-in limits and bonuses."""
    with get_db_connection() as conn:
        last_signin = conn.execute('''
            SELECT date, time FROM Attendance
            WHERE user_id = ?
            ORDER BY date DESC, time DESC LIMIT 1
        ''', (user_id,)).fetchone()

        if last_signin:
            last_signin_time = datetime.strptime(f"{last_signin['date']} {last_signin['time']}", "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_signin_time
            if time_diff < timedelta(hours=12):
                remaining_time = timedelta(hours=12) - time_diff
                remaining_time_str = str(remaining_time).split('.')[0]
                return jsonify({"message": f"Please wait {remaining_time_str} before signing in again."}), 400
        
        # Record the sign-in
        now = datetime.now()
        conn.execute('''
            INSERT INTO Attendance (user_id, date, time)
            VALUES (?, ?, ?)
        ''', (user_id, now.date(), now.strftime("%H:%M:%S")))
        
        # Update sign-ins and rank
        conn.execute('UPDATE Ranks SET signins = signins + 5 WHERE user_id = ?', (user_id,))
        signins = conn.execute('SELECT signins FROM Ranks WHERE user_id = ?', (user_id,)).fetchone()['signins']
        rank = calculate_rank(signins)
        conn.execute('UPDATE Ranks SET rank = ? WHERE user_id = ?', (rank, user_id))
        
        conn.commit()

    return redirect(url_for('user_detail', user_id=user_id))


    

@app.route('/user_signins/<int:user_id>')
def user_signins(user_id):
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row  # Set row_factory to sqlite3.Row to access rows like dicts

        # Fetch user's details (username and country)
        user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()

        if user:
            username = user['username']
            user_country = user['country']

            # Fetch national sign-ins (sign-ins from the user's country)
            c = conn.cursor()
            c.execute("""
                SELECT SUM(Ranks.signins) 
                FROM Ranks 
                JOIN Users ON Ranks.user_id = Users.id 
                WHERE Users.country = ?
            """, (user_country,))
            national_signins = c.fetchone()[0] or 0

            # Fetch total sign-ins (sign-ins from all countries)
            c.execute("""
                SELECT SUM(Ranks.signins) 
                FROM Ranks
            """)
            total_signins = c.fetchone()[0] or 0

            # Fetch total number of national users
            c.execute("""
                SELECT COUNT(*) 
                FROM Users 
                WHERE country = ?
            """, (user_country,))
            total_national_users = c.fetchone()[0] or 0

            # Fetch total number of global users (including the user's country)
            c.execute("""
                SELECT COUNT(*) 
                FROM Users
            """)
            total_global_users = c.fetchone()[0] or 0

            return render_template(
                'user_signins.html',
                user=user,  # This will pass the full user object
                user_id=user_id,
                username=username,
                user_country=user_country,
                national_signins=national_signins,
                total_signins=total_signins,
                total_national_users=total_national_users,
                total_global_users=total_global_users
            )
        else:
            return "User not found", 404




@app.route('/referral_stats/<int:user_id>')
def referral_stats(user_id):
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row  # This allows fetching rows as dictionary-like objects
    c = conn.cursor()

    # Fetch referral statistics
    c.execute('''
        SELECT COUNT(*), SUM(R.signins) 
        FROM Referrals AS Rf
        JOIN Ranks AS R ON Rf.referred_id = R.user_id
        WHERE Rf.referrer_id = ?
    ''', (user_id,))
    result = c.fetchone()

    user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()

    if result is None:
        total_referrals = 0
        total_signins_from_referrals = 0
    else:
        total_referrals, total_signins_from_referrals = result

        # Handle the case where SUM could be None
        total_signins_from_referrals = total_signins_from_referrals or 0

    conn.close()

    referral_link = f"https://t.me/ubicentbot?start={user_id}"
    
    return render_template(
        'referral_stats.html', 
        user=user,
        user_id=user_id,
        referral_link=referral_link, 
        total_referrals=total_referrals, 
        total_signins_from_referrals=total_signins_from_referrals
    )




@app.route('/admin/activity', methods=['GET', 'POST'])
def global_activity():
    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        points = request.form['points']

        with get_db_connection() as conn:
            conn.execute('INSERT INTO Activities (title, url, points) VALUES (?, ?, ?)',
                         (title, url, points))
            conn.commit()

        return redirect(url_for('global_activity'))  # Redirect back to the form or to an admin dashboard

    return render_template('global_activity.html')


@app.route('/user/<int:user_id>/activities')
def user_activities(user_id):
    with get_db_connection() as conn:
        # Fetch activities that the user has not yet completed
        activities = conn.execute('''
            SELECT * FROM Activities 
            WHERE id NOT IN (
                SELECT activity_id FROM UserCompletedActivities WHERE user_id = ?
            )
        ''', (user_id,)).fetchall()
        
        # Fetch user information for display
        user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()

    return render_template('tasks.html', user=user, activities=activities)

@app.route('/user/<int:user_id>/activity/<int:activity_id>/complete', methods=['POST'])
def complete_activity(user_id, activity_id):
    with get_db_connection() as conn:
        # Fetch points for the activity
        activity = conn.execute('SELECT points FROM Activities WHERE id = ?', (activity_id,)).fetchone()
        if activity is None:
            return "Activity not found", 404
        
        points = activity['points']
        
        # Check if the user has already completed the activity
        existing_completion = conn.execute('SELECT * FROM UserCompletedActivities WHERE user_id = ? AND activity_id = ?', (user_id, activity_id)).fetchone()
        
        if existing_completion is None:
            # Record the completion of the activity
            conn.execute('INSERT INTO UserCompletedActivities (user_id, activity_id) VALUES (?, ?)', (user_id, activity_id))
            
            # Update user's sign-ins or rewards
            conn.execute('UPDATE Ranks SET signins = signins + ? WHERE user_id = ?', (points, user_id))
        
        conn.commit()

    return redirect(url_for('user_activities', user_id=user_id))


@app.route('/admin/upload', methods=['GET', 'POST'])
def upload_activity():
    if request.method == 'POST':
        title = request.form['title']
        url = request.form['url']
        points = request.form['points']
        country = request.form['country']

        with get_db_connection() as conn:
            conn.execute('INSERT INTO NationalActivities (title, url, points, country) VALUES (?, ?, ?, ?)',
                         (title, url, points, country))
            conn.commit()

        return redirect(url_for('upload_activity'))  # Redirect back to the form or to an admin dashboard

    return render_template('upload_activity.html')


@app.route('/user/<int:user_id>/nationalactivities/<int:nationalactivities_id>/complete', methods=['POST'])
def complete_national_activity(user_id, nationalactivities_id):
    with get_db_connection() as conn:
        # Fetch the user's country
        user = conn.execute('SELECT country FROM Users WHERE id = ?', (user_id,)).fetchone()
        if user is None:
            return "User not found", 404
        
        user_country = user['country']
        
        # Fetch the activity and ensure it matches the user's country
        nationalactivities = conn.execute('SELECT * FROM NationalActivities WHERE id = ? AND country = ?', (nationalactivities_id, user_country)).fetchone()
        if nationalactivities is None:
            return "Activity not found or not available for your country", 404
        
        points = nationalactivities['points']

        # Update user's sign-ins or rewards
        conn.execute('UPDATE Ranks SET signins = signins + ? WHERE user_id = ?', (points, user_id))

        # Record the completion of the activity
        try:
            conn.execute('INSERT INTO UserCompletedActivitiesNational (user_id, nationalactivities_id) VALUES (?, ?)', (user_id, nationalactivities_id))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Activity already completed", 400

        return redirect(url_for('list_national_activities', user=user, user_id=user_id))


@app.route('/user/<int:user_id>/nationalactivities', methods=['GET'])
def list_national_activities(user_id):
    with get_db_connection() as conn:
        # Fetch the user's country
        user = conn.execute('SELECT country FROM Users WHERE id = ?', (user_id,)).fetchone()
        if user is None:
            return "User not found", 404
        
        user_country = user['country']

        # Fetch all activities available for the user's country
        nationalactivities = conn.execute('SELECT * FROM NationalActivities WHERE country = ?', (user_country,)).fetchall()

        # Fetch activities that the user has already completed
        completed_activities = conn.execute('SELECT nationalactivities_id FROM UserCompletedActivitiesNational WHERE user_id = ?', (user_id,)).fetchall()
        completed_activity_ids = [activity['nationalactivities_id'] for activity in completed_activities]

        user = conn.execute('SELECT * FROM Users WHERE id = ?', (user_id,)).fetchone()

    return render_template('national_activities.html', user=user, nationalactivities=nationalactivities, completed_activity_ids=completed_activity_ids)





@app.route('/admin/dashboard')
def admin_dashboard():
    conn = get_db_connection()
    
    # Fetch all users
    users = conn.execute('SELECT id, username, country FROM Users').fetchall()

    # Fetch total sign-ins globally
    total_signins = conn.execute('SELECT SUM(signins) FROM Ranks').fetchone()[0] or 0
    
    # Fetch total number of users
    total_users = conn.execute('SELECT COUNT(*) FROM Users').fetchone()[0]
    
    # Fetch total referrals globally
    total_referrals = conn.execute('SELECT COUNT(*) FROM Referrals').fetchone()[0]
    
    # Fetch national activities
    activities = conn.execute('SELECT * FROM Activities').fetchall()
    
    # Fetch pending national activities
    national_activities = conn.execute('SELECT * FROM NationalActivities').fetchall()
    
    conn.close()

    return render_template(
        'admin_dashboard.html',
        users=users,
        total_signins=total_signins,
        total_users=total_users,
        total_referrals=total_referrals,
        activities=activities,
        national_activities=national_activities
    )



if __name__ == '__main__':
    app.run(debug=True)



