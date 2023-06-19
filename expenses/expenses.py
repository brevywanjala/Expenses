from datetime import datetime
from flask import  *
import os


import sqlite3
from werkzeug.local import Local
def file_extension(value):
    return value.rsplit('.', 1)[-1].lower() if '.' in value else None


from difflib import SequenceMatcher

from werkzeug.utils import secure_filename
from fuzzywuzzy import fuzz
db = Local()
db.connection = sqlite3.connect('grades.db')
db.cursor = db.connection.cursor()


db.cursor.execute("DROP TABLE IF EXISTS expenses")
db.cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        amount REAL,
        receipt TEXT,
        timestamp  DEFAULT CURRENT_TIMESTAMP
    )
""")

app = Flask(__name__)
app.jinja_env.filters['file_extension'] = file_extension
app.secret_key ='dahdjii/@h'
UPLOAD_FOLDER = os.path.join('static', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db():
    if not hasattr(db, 'connection'):
        db.connection = sqlite3.connect('grades.db')
    if not hasattr(db, 'cursor'):
        db.cursor = db.connection.cursor()
    return db

@app.route('/add', methods=['GET', 'POST'])
def add_ex():
    if request.method == 'POST':
        conn = sqlite3.connect('grades.db')
        c = conn.cursor()
        item = request.form['item']
        amount = float(request.form['amount'])
        receipt = request.files['receipt']
        
        # Check for duplicate expense
        c.execute("SELECT item, amount, receipt FROM expenses")
        expenses = c.fetchall()
        for expense in expenses:
            stored_item = expense[0]
            stored_amount = expense[1]
            stored_receipt = expense[2]
            
            similarity_ratio_item = SequenceMatcher(None, stored_item, item).ratio()
            similarity_ratio_amount = SequenceMatcher(None, str(stored_amount), str(amount)).ratio()
            similarity_ratio_receipt = SequenceMatcher(None, stored_receipt, receipt.filename).ratio()
            print(similarity_ratio_receipt)
            
            if similarity_ratio_item >= 0.8 and similarity_ratio_amount >= 0.8 and similarity_ratio_receipt >= 0.8:
                flash('Item already added. Adding it again may interfere with your monthly expenses.', 'error')
                return redirect(url_for('add_ex'))
       
        # Save the receipt file
        if receipt:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            filename = f"{timestamp}_{secure_filename(receipt.filename)}"
            filename = filename.replace(':', '_')
            receipt.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = None
        
        c.execute("INSERT INTO expenses (item, amount, receipt) VALUES (?, ?, ?)",
                    (item, amount, filename))
        conn.commit()
        
        return redirect('/expenses')
    
    return render_template('expenses/add_ex.html')
@app.route('/download_receipt/<filename>', methods=['GET'])
def download_receipt(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
# ... Existing code ...
from difflib import SequenceMatcher
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
@app.route('/edit/<int:expense_id>', methods=['GET', 'POST'])
def edit_ex(expense_id):
    
    

    conn = get_db().connection
    c = get_db().cursor
    c.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    expense = c.fetchone()

    if request.method == 'POST':
        item = request.form['item']
        amount = float(request.form['amount'])
        receipt = request.files['receipt']
        
        # Check if receipt name is 70% or above match
        if receipt and fuzz.ratio(receipt.filename, expense[3]) >= 30:
            # Save the receipt file
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            filename = f"{timestamp}_{secure_filename(receipt.filename)}"
            filename = filename.replace(':', '_')
            receipt.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            flash('Invalid receipt name. Please upload a receipt with a matching name.', 'error')
            return redirect(url_for('edit_ex', expense_id=expense[0]))
        
        c.execute("UPDATE expenses SET item = ?, amount = ?, receipt = ? WHERE id = ?",
                (item, amount, filename, expense_id))
        conn.commit()
        
        return redirect('/expenses')
    
    return render_template('expenses/edit_ex.html', expense=expense)


import difflib

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    conn = get_db().connection
    c = get_db().cursor
    c.execute("SELECT receipt FROM expenses WHERE id = ?", (expense_id,))
    result = c.fetchone()

    if result:
        stored_receipt_name = result[0]
        uploaded_receipt = request.files.get('receipt')

        if uploaded_receipt and uploaded_receipt.filename:
            similarity_ratio = difflib.SequenceMatcher(None, stored_receipt_name, uploaded_receipt.filename).ratio()
            if similarity_ratio >= 0.3:
                c.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                conn.commit()
                flash('Expense deleted successfully.')
            else:
                flash('Invalid receipt. Deletion not allowed.')
        else:
            flash('No receipt uploaded. Deletion not allowed.')

    return redirect(url_for('expenses'))


@app.route('/expenses')
def expenses():
    conn = get_db().connection
    c = get_db().cursor
    c.execute("SELECT * FROM expenses")
    expenses = c.fetchall()
    return render_template('expenses/expenses.html', expenses=expenses )


@app.route('/total_expenses', methods=['POST', 'GET'])
def total_expenses():
    if request.method == 'POST':
        month = request.form.get('month')
        if month:
            conn = sqlite3.connect('grades.db')
            c = conn.cursor()
            c.execute("SELECT * FROM expenses WHERE strftime('%Y-%m', timestamp) = ?", (month,))
            expenses = c.fetchall()

            total_amount = sum(expense[2] for expense in expenses)

            return render_template('expenses/expenses.html', expenses=expenses, month=month, total_amount=total_amount)
    
    flash('Invalid request. Please provide a valid month.')
    return render_template('expenses/expenses.html')



    
if __name__ == '__main__':
    app.run(debug=True)