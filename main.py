from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
app = Flask(__name__)
app.secret_key ='Secret_key'

# Dummy data for demonstration purposes
#gym_packages = [{'name': 'Package 1', 'price': 50}, {'name': 'Package 2', 'price': 75}]
# ... other dummy data ...

import mysql.connector
import re

#members = []
mydbcon = mysql.connector.connect(host="localhost", user="root", password="", database="gymdb")


# mycursor = mysql.cursor()

# mysql = MySQL(app)
mycursor = mydbcon.cursor()

# Routes for Guest Users
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact_us')
def contact_us():
    return render_template('contact_us.html')

@app.route('/trainers_equipment')
def trainers_equipment():
    return render_template('trainers_equipment.html')

# Routes for Registered Users
@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        mycursor.execute('SELECT * FROM users WHERE name = %s', (username,))
        account = mycursor.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'name must contain only characters and numbers !'
        else:
            mycursor.execute('INSERT INTO users VALUES (NULL, %s, %s, %s)',(username, email, password,))
            mydbcon.commit()
            msg = 'You have successfully registered !'
            return redirect("/login")
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg=msg)


@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username and password:
            if username == 'admin' and password == 'admin':
                session['loggedin'] = True
                session['username'] = 'admin'
                return redirect(url_for('admin'))

            try:
                # Using a with statement for cursor to ensure proper resource management
                with mydbcon.cursor() as mycursor:
                    # Execute the query to check user credentials
                    mycursor.execute('SELECT * FROM users WHERE name = %s AND password = %s', (username, password))
                    account = mycursor.fetchone()
                    mycursor.fetchall()  # Clear any remaining results

                    if account:
                        session['loggedin'] = True
                        session['id'] = account[0]
                        session['username'] = account[1]
                        msg = 'Logged in successfully!'

                        # Execute the query to check if the user has a package
                        mycursor.execute('SELECT package FROM booking WHERE name = %s', (username,))
                        booking_info = mycursor.fetchone()
                        mycursor.fetchall()  # Clear any remaining results

                        has_package = booking_info is not None
                        package = booking_info[0] if booking_info else None

                        # Render the profile page with the user's information
                        return render_template('profile.html', msg=msg, account=account, has_package=has_package, package=package)
                    else:
                        msg = 'Incorrect username or password!'
            except mysql.connector.Error as err:
                msg = f"Database error: {err}"
                print(f"Error: {err}")
        else:
            msg = 'Please enter both username and password!'

    # Render the login page with any messages
    return render_template('login.html', msg=msg)

@app.route('/subscribe')
def subscribe():
    if 'loggedin' in session:
        date = datetime.date.today()
        package_selected = str(request.args.get('package'))
        username = session['username']
        session['package'] = True
        mycursor.execute('INSERT INTO booking VALUES (%s, %s, %s)', (username, package_selected, date))
        mydbcon.commit()
        return redirect('/dashboard')  # Redirect after POST to avoid resubmission
    return render_template('index.html')

@app.route("/display")
def profile():
    if 'loggedin' in session:
        mycursor.execute('SELECT * FROM users WHERE id = % s', (session['id'],))
        account = mycursor.fetchone()
        return render_template("display.html", account=account)
    return redirect(url_for('login'))

@app.route('/booking_history')
def booking_history():
    # Logic to fetch user's booking history from the database
    return render_template('booking_history.html')


@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        # Fetch user information
        mycursor.execute('SELECT * FROM users WHERE id = %s', (session['id'],))
        account = mycursor.fetchone()
        
        # Fetch booking history
        mycursor.execute('SELECT package_name, booking_date FROM bookings WHERE user_id = %s ORDER BY booking_date DESC', (session['id'],))
        bookings = mycursor.fetchall()
        
        return render_template('profile.html', account=account, bookings=bookings)
    return redirect(url_for('login'))

@app.route('/packages')
def packages():
    if 'loggedin' in session:
        return render_template('packages.html')
    return redirect(url_for('login'))

@app.route('/update_package', methods=['POST'])
def update_package():
    if 'loggedin' in session:
        package = request.form['package']
        user_id = session['id']
        booking_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # Update user's package in the users table
            mycursor.execute('UPDATE users SET package = %s WHERE id = %s', (package, user_id))
            
            # Insert into bookings table
            mycursor.execute('INSERT INTO bookings (user_id, package_name, booking_date) VALUES (%s, %s, %s)', 
                             (user_id, package, booking_date))
            
            mydbcon.commit()
            flash('Package updated successfully!')
        except mysql.connector.Error as err:
            mydbcon.rollback()
            flash(f'An error occurred: {err}')
        
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Routes for Admin
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'loggedin' in session and session.get('username') == 'admin':
        # Count queries for overview
        mycursor.execute('SELECT COUNT(*) FROM bookings')
        booking_count = mycursor.fetchone()[0]

        mycursor.execute('SELECT COUNT(*) FROM packages')
        package_count = mycursor.fetchone()[0]

        mycursor.execute('SELECT COUNT(*) FROM categories')
        category_count = mycursor.fetchone()[0]

        mycursor.execute('SELECT COUNT(*) FROM package_types')
        package_type_count = mycursor.fetchone()[0]

        # User count and recent users query
        mycursor.execute('SELECT COUNT(name) FROM users')
        user_count = mycursor.fetchone()[0]

        mycursor.execute('SELECT * FROM users LIMIT 5')
        users = mycursor.fetchall()

        # Render the template with all gathered data
        return render_template('admin.html',
                               booking_count=booking_count,
                               package_count=package_count,
                               category_count=category_count,
                               package_type_count=package_type_count,
                               user_count=user_count,
                               users=users)
    else:
        return redirect(url_for('login'))


@app.route('/admin/categories', methods=['GET', 'POST'])
def manage_categories():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            category_name = request.form['category_name']
            mycursor.execute('INSERT INTO categories (name) VALUES (%s)', (category_name,))
            mydbcon.commit()
            return redirect(url_for('manage_categories'))

        mycursor.execute('SELECT * FROM categories')
        categories = mycursor.fetchall()
        return render_template('admin_categories.html', categories=categories)
    else:
        return redirect(url_for('login'))

@app.route('/admin/package_types', methods=['GET', 'POST'])
def manage_package_types():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            package_type_name = request.form['package_type_name']
            mycursor.execute('INSERT INTO package_types (name) VALUES (%s)', (package_type_name,))
            mydbcon.commit()
            return redirect(url_for('manage_package_types'))

        mycursor.execute('SELECT * FROM package_types')
        package_types = mycursor.fetchall()
        return render_template('admin_package_types.html', package_types=package_types)
    else:
        return redirect(url_for('login'))

@app.route('/admin/packages', methods=['GET', 'POST'])
def manage_packages():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            package_name = request.form['package_name']
            package_type = request.form['package_type']
            price = request.form['price']
            mycursor.execute('INSERT INTO packages (name, package_type, price) VALUES (%s, %s, %s)',
                             (package_name, package_type, price))
            mydbcon.commit()
            return redirect(url_for('manage_packages'))

        mycursor.execute('SELECT * FROM packages')
        packages = mycursor.fetchall()
        return render_template('admin_packages.html', packages=packages)
    else:
        return redirect(url_for('login'))

@app.route('/admin/bookings', methods=['GET', 'POST'])
def manage_bookings():
    if 'loggedin' in session and session.get('username') == 'admin':
        mycursor.execute('SELECT * FROM bookings')
        bookings = mycursor.fetchall()
        return render_template('admin_bookings.html', bookings=bookings)
    else:
        return redirect(url_for('login'))


@app.route('/admin/reports', methods=['GET', 'POST'])
def generate_reports():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            start_date = request.form['start_date']
            end_date = request.form['end_date']

            # Example report for bookings within a date range
            mycursor.execute('SELECT * FROM bookings WHERE booking_date BETWEEN %s AND %s',
                             (start_date, end_date))
            bookings = mycursor.fetchall()

            # Example report for registered users within a date range
            mycursor.execute('SELECT * FROM users WHERE registration_date BETWEEN %s AND %s',
                             (start_date, end_date))
            users = mycursor.fetchall()

            return render_template('admin_reports.html', bookings=bookings, users=users)
        return render_template('admin_generate_reports.html')
    else:
        return redirect(url_for('login'))


@app.route('/admin/profile', methods=['GET', 'POST'])
def admin_profile():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            mycursor.execute('UPDATE users SET name=%s, email=%s, password=%s WHERE name=%s',
                             (username, email, password, 'admin'))
            mydbcon.commit()
            return redirect(url_for('admin_profile'))

        mycursor.execute('SELECT * FROM users WHERE name = %s', ('admin',))
        admin_info = mycursor.fetchone()
        return render_template('admin_profile.html', admin_info=admin_info)
    else:
        return redirect(url_for('login'))


@app.route('/admin/change_password', methods=['GET', 'POST'])
def change_admin_password():
    if 'loggedin' in session and session.get('username') == 'admin':
        if request.method == 'POST':
            old_password = request.form['old_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            # Verify old password
            mycursor.execute('SELECT * FROM users WHERE name = %s AND password = %s',
                             ('admin', old_password))
            admin_info = mycursor.fetchone()

            if admin_info and new_password == confirm_password:
                mycursor.execute('UPDATE users SET password=%s WHERE name=%s',
                                 (new_password, 'admin'))
                mydbcon.commit()
                return redirect(url_for('admin_profile'))
            else:
                msg = "Password change failed. Please check your input."
                return render_template('admin_change_password.html', msg=msg)

        return render_template('change_password.html')
    else:
        return redirect(url_for('login'))


@app.route('/editprofile', methods=['GET', 'POST'])
def editProfile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        selected_package = request.form.get('membership')

        mycursor.execute('UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s', (username, email, password, session['id']))
        mydbcon.commit()

        if selected_package:
            mycursor.execute('UPDATE booking SET package=%s WHERE name=%s', (selected_package, username))
            mydbcon.commit()

        return redirect('/dashboard')  # Redirect to avoid form resubmission

    mycursor.execute('SELECT * FROM users WHERE id=%s', (session['id'],))
    account = mycursor.fetchone()
    return render_template('editProfile.html', user=account)


@app.route('/users')
def users():
    mycursor.execute('SELECT * FROM users')
    users = mycursor.fetchall()
    return render_template('users.html',users = users)

@app.route('/deleteusers', methods=['POST','GET'])
def delete_user():
    user = request.args.getlist('user')
    user_id = user[0]
    mycursor.execute('DELETE FROM users WHERE id=%s',(user_id,))
    mydbcon.commit()
    return redirect(url_for('users'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
