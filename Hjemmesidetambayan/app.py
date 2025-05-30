from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
import os


app = Flask(__name__)

load_dotenv()  

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        
        
    )
    return conn



# Get employee data
def get_employees():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, first_name || ' ' || last_name, job_title FROM employees ORDER BY first_name;")
    employees = cur.fetchall()
    cur.close()
    conn.close()
    return employees

# Index route
@app.route('/')
def index():
    return render_template('index.html')

# Inventory route
@app.route('/inventory')
def inventory():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Ingredients;')
    ingredients = cur.fetchall()
    cur.close()
    conn.close()

    ingredient_status = []
    for ingredient in ingredients:
        status = 'red' if ingredient[2] < ingredient[5] else 'green'
        ingredient_status.append({
            'id': ingredient[0],
            'name': ingredient[1],
            'quantity': ingredient[2],
            'unit': ingredient[3],
            'threshold': ingredient[5],
            'status': status
        })

    return render_template('inventory.html', ingredients=ingredient_status)

# Add quantity
@app.route('/add_quantity/<int:ingredient_id>', methods=['POST'])
def add_quantity(ingredient_id):
    quantity_to_add = float(request.form['amount'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE Ingredients SET Quantity = Quantity + %s WHERE IngredientID = %s', (quantity_to_add, ingredient_id))
    conn.commit()
    cur.close()
    conn.close()
    flash('Quantity added successfully!')
    return redirect(url_for('inventory'))

# Deduct quantity
@app.route('/deduct_quantity/<int:ingredient_id>', methods=['POST'])
def deduct_quantity(ingredient_id):
    quantity_to_deduct = float(request.form['amount'])
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('UPDATE Ingredients SET Quantity = Quantity - %s WHERE IngredientID = %s', (quantity_to_deduct, ingredient_id))
    conn.commit()
    cur.close()
    conn.close()
    flash('Quantity deducted successfully!')
    return redirect(url_for('inventory'))

# Remove dishes and deduct ingredients
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM Menu;')
    dishes = cur.fetchall()

    if request.method == 'POST':
        selected_dishes = request.form.getlist('dishes')
        quantity_to_deduct = int(request.form['quantity'])

        for dish_id in selected_dishes:
            cur.execute('''SELECT mi.IngredientID, mi.QuantityNeeded, mi.Unit FROM MenuIngredients mi WHERE mi.MenuID = %s;''', (dish_id,))
            ingredients_needed = cur.fetchall()

            for ingredient_id, quantity_needed, unit in ingredients_needed:
                cur.execute('''UPDATE Ingredients SET Quantity = Quantity - %s WHERE IngredientID = %s;''', (quantity_needed * quantity_to_deduct, ingredient_id))

        conn.commit()
        cur.close()
        conn.close()
        flash("Deduction successful!")
        return redirect(url_for('remove'))

    cur.close()
    conn.close()
    return render_template('remove.html', dishes=dishes)

# Vagtskema (schedule) route
@app.route('/vagtskema', methods=['GET', 'POST'])
def vagtskema():
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    employees = get_employees()

    times = []
    hour, minute = 7, 0
    while hour < 20 or (hour == 20 and minute == 0):
        times.append(f"{hour:02d}:{minute:02d}")
        minute += 30
        if minute == 60:
            hour += 1
            minute = 0

    durations = [str(dur) for dur in [x * 0.5 for x in range(1, 27)]]

    if request.method == 'POST':
        try:
            conn = get_db_connection()
            cur = conn.cursor()

            for i in range(5):
                emp_id = request.form.get(f'employee_{i}')
                day = request.form.get(f'day_{i}')
                start_time = request.form.get(f'start_{i}')
                duration = request.form.get(f'duration_{i}')
                print(f"Received: employee={emp_id}, day={day}, start_time={start_time}, duration={duration}")  # Debug

                if emp_id and day and start_time and duration:
                    cur.execute("""
                        INSERT INTO employee_hours (employee_id, day, start_time, duration)
                        VALUES (%s, %s, %s, %s)
                    """, (int(emp_id), day, start_time, float(duration)))

            conn.commit()

        except Exception as e:
            print("Database error:", e)
            flash("An error occurred while saving the schedule.")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('vagtskema'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT eh.employee_id, e.first_name || ' ' || e.last_name, e.job_title, eh.day, eh.start_time, eh.duration
        FROM employee_hours eh
        JOIN employees e ON eh.employee_id = e.id
        ORDER BY eh.day, eh.start_time    
    """)
    rows = cur.fetchall()

    schedule_dict = {}
    for row in rows:
        emp_id, name, job_title, day, start_time, duration = row
        key = (emp_id, day)
        schedule_dict.setdefault(key, []).append({
            'employee_id': emp_id,
            'employee_name': name,
            'job_title': job_title,
            'day': day,
            'start_time': start_time,
            'duration': duration
        })
    cur.close()
    conn.close()

    return render_template('vagtskema.html', employees=employees, days=days,
                           times=times, durations=durations, schedule_dict=schedule_dict)

# Other pages
@app.route('/medarbejder')
def medarbejder():
    return render_template('medarbejder.html')

@app.route('/Beskeder')
def beskeder():
    return render_template('beskeder.html')

@app.route('/Dine_oplysninger')
def dine_oplysninger():
    return render_template('dine_oplysninger.html')


if __name__ == '__main__':
    app.run(debug=True)
