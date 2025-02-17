import psycopg2
import random
import time
from faker import Faker

# Database connection parameters
RETAIL_DB_PARAMS = {
    "dbname": "retail",
    "user": "postgres",
    "password": "Delta_12345678",
    "host": "localhost",
    "port": 5432
}

LOGISTICS_DB_PARAMS = {
    "dbname": "logistics",
    "user": "postgres",
    "password": "Delta_12345678",
    "host": "localhost",
    "port": 5432
}

ACCOUNTS_DB_PARAMS = {
    "dbname": "accounts",
    "user": "postgres",
    "password": "Delta_12345678",
    "host": "localhost",
    "port": 5432
}

# Initialize Faker
fake = Faker()
settings = []

# Function to get load settings from retail database
def get_settings(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name, value FROM settings")
    settings = cursor.fetchall()
    return settings    

# Function to load customer IDs from the Customers table
def get_customers(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT customer_id FROM Customers")
    rows = cursor.fetchall()
    customer_ids = [row[0] for row in rows]
    return customer_ids

# Function to load warehouse IDs from the Warehouses table
def get_warehouses(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT warehouse_id FROM Warehouses")
    rows = cursor.fetchall()
    warehouse_ids = [row[0] for row in rows]
    return warehouse_ids

# Function to populate Cities table
def populate_cities(conn):
    cursor = conn.cursor()
    cities = [
        "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
        "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
    ]
    for city in cities:
        cursor.execute(
            "INSERT INTO Cities (city_name) VALUES (%s) ON CONFLICT (city_name) DO NOTHING",
            (city,)
        )
    conn.commit()
    print("Cities table populated.")

# Function to populate payment methods
def populate_payment_methods(conn):
    cursor = conn.cursor()
    pay_methods = ["Credit Card", "PayPal", "Bank Transfer", "Bitcoin", "Debit Card"]
    for method in pay_methods:
        cursor.execute(
            "INSERT INTO paymentmethods (method_name) VALUES (%s) ON CONFLICT (method_name) DO NOTHING",
            (method,)
        )
    conn.commit()
    print("Payment Methods table populated.")

# Function to populate Warehouses table
def populate_warehouses(conn):
    cursor = conn.cursor()
    warehouse_ids = []
    for _ in range(10):  # Insert 10 warehouses
        location = fake.city()
        capacity = random.randint(100, 10000)
        cursor.execute(
            "INSERT INTO Warehouses (location, capacity) VALUES (%s, %s) RETURNING warehouse_id",
            (location, capacity)
        )
        warehouse_id = cursor.fetchone()[0]
        warehouse_ids.append(warehouse_id)
    conn.commit()
    print("Warehouses table populated.")
    return warehouse_ids

# Function to populate Customers table
def populate_customers(conn):
    cursor = conn.cursor()
    customer_ids = []
    used_emails = set()
    for _ in range(1000):  # Insert exactly 1000 customers
        name = fake.name()
        email = fake.email()
        while email in used_emails:  # Ensure email is unique
            email = fake.email()
        used_emails.add(email)
        address = fake.address()
        phone = fake.phone_number()[:15]  # Truncate to 15 characters
        cursor.execute(
            "INSERT INTO Customers (name, email, address, phone) VALUES (%s, %s, %s, %s) RETURNING customer_id",
            (name, email, address, phone)
        )
        customer_id = cursor.fetchone()[0]
        customer_ids.append(customer_id)
    conn.commit()
    print("1000 Customers inserted successfully.")
    return customer_ids

# Function to populate Orders and Shipments, and record transactions
def populate_orders_and_shipments(retail_conn, logistics_conn, accounts_conn, customer_ids, warehouse_ids, settings_dict):
    retail_cursor = retail_conn.cursor()
    logistics_cursor = logistics_conn.cursor()
    accounts_cursor = accounts_conn.cursor()
    
    # Note: Autocommit is now set in main, so we remove it from here.
    
    for i in range(settings_dict.get("batch_size")):
        customer_id = random.choice(customer_ids)
        order_date = fake.date_time_this_year()
        total_amount = round(random.uniform(20, 1000), 2)
        
        try:
            # Insert into Orders and retrieve generated order_id
            retail_cursor.execute(
                "INSERT INTO Orders (customer_id, order_date, total_amount) VALUES (%s, %s, %s) RETURNING order_id",
                (customer_id, order_date, total_amount)
            )
            order_id = retail_cursor.fetchone()
            if order_id is None:
                print("ERROR: Failed to retrieve order_id!")
                continue
            order_id = order_id[0]          
        
            warehouse_id = random.choice(warehouse_ids)
            city_id = random.randint(1, 10)  # Assuming 10 predefined cities
            shipment_date = fake.date_time_this_year()
            delivery_date = fake.future_date()
        
            logistics_cursor.execute(
                "INSERT INTO Shipments (order_id, warehouse_id, shipment_date, delivery_date, total_amount, city_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, warehouse_id, shipment_date, delivery_date, total_amount, city_id)
            )            
        
            payment_method_id = random.randint(1, 5)  # Assuming 5 predefined payment methods            
            accounts_cursor.execute(
                "INSERT INTO transactions (order_id, customer_id, payment_method_id, transaction_date, amount) VALUES (%s, %s, %s, %s, %s)",
                (order_id, customer_id, payment_method_id, order_date, total_amount)
            )
            
        
        except Exception as e:
            print(f"Database Error: {e}")
            continue
        
        retail_conn.commit()
        logistics_conn.commit()
        accounts_conn.commit()
        if i % 1000 == 0:
            print(f"Processed {i} orders and shipments.")
    
    print(f'{settings_dict.get("batch_size")} orders and shipments added.')
        

# Main execution
if __name__ == "__main__":
    retail_conn = None
    logistics_conn = None
    accounts_conn = None
    try:
        print("Connecting to Retail, Logistics, and Accounts Databases...")
        retail_conn = psycopg2.connect(**RETAIL_DB_PARAMS)
        logistics_conn = psycopg2.connect(**LOGISTICS_DB_PARAMS)
        accounts_conn = psycopg2.connect(**ACCOUNTS_DB_PARAMS)
        
        # Set autocommit on each connection immediately after connecting.
        retail_conn.autocommit = True
        logistics_conn.autocommit = True
        accounts_conn.autocommit = True
        
        # Retrieve settings from the retail database.
        settings_list = get_settings(retail_conn)
        settings_dict = {name: value for name, value in settings_list}
        
        # Check if the "first_load" setting is 1.
        if settings_dict.get("first_load") == 1:
            populate_cities(logistics_conn)
            populate_payment_methods(accounts_conn)
            warehouse_ids = populate_warehouses(logistics_conn)
            customer_ids = populate_customers(retail_conn)
        else:
            # If not the first load, fetch existing IDs.
            warehouse_ids = get_warehouses(logistics_conn)
            customer_ids = get_customers(retail_conn)
        
        while settings_dict.get("continous_loading") == 1:            
            populate_orders_and_shipments(retail_conn, logistics_conn, accounts_conn, customer_ids, warehouse_ids, settings_dict)
            time.sleep(settings_dict.get("pause_seconds"))
            settings_list = ()
            settings_dict = []
            settings_list = get_settings(retail_conn)
            settings_dict = {name: value for name, value in settings_list}
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if retail_conn:
            retail_conn.close()
        if logistics_conn:
            logistics_conn.close()
        if accounts_conn:
            accounts_conn.close()
