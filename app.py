from flask import Flask, render_template, send_file, request, redirect, url_for, flash, session
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import pytz
import pandas as pd
from io import BytesIO


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client.RealEstate  # Your database name
users_collection = db.users  # Your users collection name
properties_collection = db.properties  # Your properties collection name


# Authentication Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('You need to log in first!', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users_collection.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('welcome'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/welcome')
@login_required
def welcome():
    username = session.get('username')
    return render_template('welcome.html', username=username)


@app.route('/logout')
@login_required
def logout():
    session.clear()  # Clears the entire session
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        if users_collection.find_one({'username': username}):
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        users_collection.insert_one({'username': username, 'password': hashed_password})
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/')
@login_required
def index():
    try:
        properties = list(properties_collection.find())
    except Exception as e:
        print(f"Error fetching properties: {str(e)}")
        properties = []
    return render_template('index.html', properties=properties)


@app.route('/search', methods=['GET'])
@login_required
def search_properties():
    try:
        search_query = request.args.get('search_query', '')
        transaction_type = request.args.get('transaction_type', '')
        price_order = request.args.get('price_order', '')
        status = request.args.get('status', '')

        query = {}
        if search_query:
            query['$or'] = [
                {'address': {'$regex': search_query, '$options': 'i'}},
                {'city': {'$regex': search_query, '$options': 'i'}}
            ]
        if transaction_type:
            query['transaction_type'] = transaction_type
        if status:
            query['status'] = status

        sort_key = 'price'
        sort_direction = 1
        if price_order == 'High to Low':
            sort_direction = -1

        properties = list(properties_collection.find(query).sort(sort_key, sort_direction))
    
    except Exception as e:
        print(f"Error fetching properties: {str(e)}")
        properties = []

    return render_template('search_properties.html', properties=properties)


@app.route('/add_property', methods=['GET'])
@login_required
def add_property():
    return render_template('add_property.html')

@app.route('/add_property', methods=['POST'])
@login_required
def add_property_action():
    try:
        address = request.form.get('address')
        city = request.form.get('city')
        price = int(request.form.get('price'))
        bedrooms = int(request.form.get('bedrooms'))
        bathrooms = str(request.form.get('bathrooms'))
        transaction_type = request.form.get('transaction_type')
        status = request.form.get('status')
        listing_date = request.form.get('listing_date')
        rent_or_sale_date = request.form.get('rent_or_sale_date')

        # Convert dates to ISO format
        listing_date = datetime.strptime(listing_date, '%Y-%m-%d') if listing_date else None
        rent_or_sale_date = datetime.strptime(rent_or_sale_date, '%Y-%m-%d') if rent_or_sale_date else None

        property_data = {
            'address': address,
            'city': city,
            'price': price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'transaction_type': transaction_type,
            'status': status,
            'listing_date': listing_date,
            'rent_or_sale_date': rent_or_sale_date
        }
        properties_collection.insert_one(property_data)
        flash('Property added successfully!', 'success')
        
    except Exception as e:
        flash(f'Error adding property: {str(e)}', 'danger')
    return redirect(url_for('index'))


@app.route('/delete/<id>', methods=['POST'])
@login_required
def delete_property(id):
    try:
        properties_collection.delete_one({'_id': ObjectId(id)})
    
    except Exception as e:
        flash(f'Error deleting property: {str(e)}', 'danger')
    return redirect(url_for('index'))





@app.route('/edit_property/<id>', methods=['GET'])
@login_required
def edit_property(id):
    try:
        property = properties_collection.find_one({'_id': ObjectId(id)})
        if property:
            # Convert dates to string format for the form
            if property.get('listing_date'):
                property['listing_date'] = property['listing_date'].strftime('%Y-%m-%d')
            if property.get('rent_or_sale_date'):
                property['rent_or_sale_date'] = property['rent_or_sale_date'].strftime('%Y-%m-%d')
            return render_template('edit_property.html', property=property)
        else:
            flash('Property not found!', 'danger')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error fetching property: {str(e)}', 'danger')
        return redirect(url_for('index'))



@app.route('/edit_property/<id>', methods=['POST'])
@login_required
def edit_property_action(id):
    from datetime import datetime  # Make sure datetime is imported

    try:
        address = request.form.get('address')
        city = request.form.get('city')
        price = int(request.form.get('price'))
        bedrooms = int(request.form.get('bedrooms'))
        bathrooms = str(request.form.get('bathrooms'))
        transaction_type = request.form.get('transaction_type')
        status = request.form.get('status')
        listing_date_str = request.form.get('listing_date')
        rent_or_sale_date_str = request.form.get('rent_or_sale_date')

        # Convert date strings to datetime objects
        listing_date = datetime.strptime(listing_date_str, '%Y-%m-%d') if listing_date_str else None
        rent_or_sale_date = datetime.strptime(rent_or_sale_date_str, '%Y-%m-%d') if rent_or_sale_date_str else None

        property_data = {
            'address': address,
            'city': city,
            'price': price,
            'bedrooms': bedrooms,
            'bathrooms': bathrooms,
            'transaction_type': transaction_type,
            'status': status,
            'listing_date': listing_date,
            'rent_or_sale_date': rent_or_sale_date
        }
        properties_collection.update_one({'_id': ObjectId(id)}, {'$set': property_data})
        
        flash('Property updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating property: {str(e)}', 'danger')
    return redirect(url_for('index'))



@app.route('/generate_report', methods=['GET', 'POST'])
@login_required
def generate_report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        # Default values for price range
        min_price = request.form.get('min_price', None)
        max_price = request.form.get('max_price', None)

        try:
            # Convert date strings to datetime objects
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            # Build query based on report type
            query = {
                'listing_date': {'$gte': start_date, '$lte': end_date}
            }

            if report_type == 'listed':
                properties = list(properties_collection.find(query).sort('listing_date', 1))  # Sort by listing_date ascending

            elif report_type == 'sold_out_rented':
                query['status'] = {'$in': ['Sold out', 'Rented']}
                properties = list(properties_collection.find(query).sort('listing_date', 1))  # Sort by listing_date ascending

            elif report_type == 'price':
                if min_price:
                    query['price'] = {'$gte': float(min_price)}
                if max_price:
                    query.setdefault('price', {})['$lte'] = float(max_price)
                properties = list(properties_collection.find(query).sort('listing_date', 1))  # Sort by listing_date ascending

            else:
                flash('Invalid report type selected.', 'danger')
                return render_template('generate_report.html')

            return render_template('report.html', properties=properties, report_type=report_type, start_date=start_date_str, end_date=end_date_str)

        except ValueError as ve:
            flash(f'Value Error: {str(ve)}', 'danger')
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')

    return render_template('generate_report.html')



@app.route('/export_report', methods=['POST'])
@login_required
def export_report():
    if request.method == 'POST':
        report_type = request.form.get('report_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        min_price = request.form.get('min_price', None)
        max_price = request.form.get('max_price', None)

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            query = {
                'listing_date': {'$gte': start_date, '$lte': end_date}
            }

            if report_type == 'listed':
                properties = list(properties_collection.find(query).sort('listing_date', 1))

            elif report_type == 'sold_out_rented':
                query['status'] = {'$in': ['Sold out', 'Rented']}
                properties = list(properties_collection.find(query).sort('listing_date', 1))

            elif report_type == 'price':
                if min_price:
                    query['price'] = {'$gte': float(min_price)}
                if max_price:
                    query.setdefault('price', {})['$lte'] = float(max_price)
                properties = list(properties_collection.find(query).sort('listing_date', 1))

            else:
                flash('Invalid report type selected.', 'danger')
                return redirect(url_for('generate_report'))

            # Convert properties data to DataFrame
            df = pd.DataFrame(properties)
            if df.empty:
                flash('No data available for the selected criteria.', 'info')
                return redirect(url_for('generate_report'))

            # Create a BytesIO buffer to hold the Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Report')
            
            # Seek to the beginning of the BytesIO buffer
            output.seek(0)
            return send_file(output, download_name='report.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'danger')
            return redirect(url_for('generate_report'))

    return redirect(url_for('generate_report'))





if __name__ == '__main__':
    app.run(debug=True)
