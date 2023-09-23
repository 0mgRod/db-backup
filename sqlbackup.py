import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
import mysql.connector
import os
import gzip
import base64
import csv
import hashlib
from cryptography.fernet import Fernet
from plyer import notification

# Initialize the encryption key
encryption_key = Fernet.generate_key()
cipher_suite = Fernet(encryption_key)

# Function to check if login information is remembered
def is_remembered():
    return os.path.exists("logins.csv")

# Function to get remembered login information
def get_remembered_logins():
    logins = []
    if os.path.exists("logins.csv"):
        with open("logins.csv", "rb") as csv_file:
            csv_data = gzip.decompress(base64.b64decode(csv_file.read())).decode("utf-8")
            csv_reader = csv.reader(csv_data.splitlines())
            for row in csv_reader:
                if len(row) == 2:
                    login_data = row[1]
                    logins.append(login_data)
    return logins

# Function to save logins to a CSV file
def save_logins(logins):
    csv_data = "\n".join([f", {login}" for login in logins])
    compressed_csv_data = base64.b64encode(gzip.compress(csv_data.encode("utf-8")))
    with open("logins.csv", "wb") as csv_file:
        csv_file.write(compressed_csv_data)

# Function to set login values
def set_login_values(url_entry, db_username_entry, username_entry, password_entry, login):
    url, db_username, username, password = login.split(":")
    url_entry.delete(0, tk.END)
    db_username_entry.delete(0, tk.END)
    username_entry.delete(0, tk.END)
    password_entry.delete(0, tk.END)
    url_entry.insert(0, url)
    db_username_entry.insert(0, db_username)
    username_entry.insert(0, username)
    password_entry.insert(0, password)

# Function to create a custom "Remember Login" dialog
def remember_login():
    remember = simpledialog.askstring("Remember Login", "Do you want to remember login information? (yes/no)")
    return remember and remember.lower() == "yes"

# Function to handle the backup process
def backup_database():
    url, db_username, username, password = url_entry.get(), db_username_entry.get(), username_entry.get(), password_entry.get()

    try:
        conn = mysql.connector.connect(host=url, user=db_username, password=password, database=username)
        cursor = conn.cursor(buffered=True)

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        progress_var.set(0)
        total_tables = len(tables)
        progress_step = 100 / total_tables

        backup_location = backup_location_var.get()
        backup_filename = os.path.join(backup_location, "backup.sql")

        with open(backup_filename, "w", encoding="utf-8") as backup_file:
            for index, table in enumerate(tables):
                table_name = table[0]
                cursor.execute(f"SHOW CREATE TABLE {table_name}")
                create_table_sql = cursor.fetchone()[1]
                backup_file.write(f"{create_table_sql};\n")

                cursor.execute(f"SELECT * FROM {table_name}")
                data = cursor.fetchall()

                backup_file.write(f"\n-- Table: {table_name}\n")
                for row in data:
                    row_values = ", ".join([f"'{value}'" if isinstance(value, str) else str(value) for value in row])
                    backup_file.write(f"INSERT INTO {table_name} VALUES ({row_values});\n")

                progress_var.set(min(100, int((index + 1) * progress_step)))

        conn.close()
        messagebox.showinfo("Backup Complete", "Database backup completed successfully!")

        # Save login information if "Remember Login" is checked
        if remember_login_var.get():
            logins = get_remembered_logins()
            login_data = f"{url}:{db_username}:{username}:{password}"
            if login_data not in logins:
                logins.append(login_data)
                save_logins(logins)

        # Compress backup if compression is enabled
        if compress_backup_var.get():
            compressed_filename = os.path.join(backup_location, "backup.sql.gz")
            with open(backup_filename, "rb") as backup_file:
                with gzip.open(compressed_filename, "wb") as compressed_file:
                    compressed_file.writelines(backup_file)

        # Send desktop notification
        if desktop_notification_var.get():
            send_notification("Database backup completed successfully!")

    except mysql.connector.Error as e:
        messagebox.showerror("Database Error", str(e))
        progress_var.set(0)

# Function to choose backup location
def choose_backup_location():
    backup_dir = filedialog.askdirectory()
    if backup_dir:
        backup_location_var.set(backup_dir)

# Function to send desktop notification
def send_notification(message):
    notification.notify(
        title="Backup Complete",
        message=message,
        app_name="DB Backup App",
    )

# Create the GUI window
window = tk.Tk()
window.title("DB Backup")

# Check if login information is remembered
logins = get_remembered_logins()

# Checkbutton for "Remember Login" feature
remember_login_var = tk.BooleanVar()
remember_login_var.set(False)

def toggle_remember_login():
    remember_login_var.set(not remember_login_var.get())

remember_login_checkbox = ttk.Checkbutton(window, text="Remember Login", variable=remember_login_var)
remember_login_checkbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")

# Label and Entry widgets for user input
tk.Label(window, text="DB URL:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
url_entry = ttk.Entry(window)
url_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Label(window, text="DB Username:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
db_username_entry = ttk.Entry(window)
db_username_entry.grid(row=2, column=1, padx=10, pady=5)

tk.Label(window, text="DB Name:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
username_entry = ttk.Entry(window)
username_entry.grid(row=3, column=1, padx=10, pady=5)

tk.Label(window, text="Password:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
password_entry = ttk.Entry(window, show="*")
password_entry.grid(row=4, column=1, padx=10, pady=5)

# Progress Bar
progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(window, variable=progress_var, mode='determinate')
progress_bar.grid(row=5, column=0, columnspan=2, padx=10, pady=10)

# Backup Location
backup_location_label = ttk.Label(window, text="Backup Location:")
backup_location_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
backup_location_var = tk.StringVar()
backup_location_entry = ttk.Entry(window, textvariable=backup_location_var)
backup_location_entry.grid(row=6, column=1, padx=10, pady=5)
choose_location_button = ttk.Button(window, text="Choose Location", command=choose_backup_location)
choose_location_button.grid(row=6, column=2, padx=10, pady=5)

# Checkbutton for "Compress Backup" feature
compress_backup_var = tk.BooleanVar()
compress_backup_var.set(False)
compress_backup_checkbox = ttk.Checkbutton(window, text="Compress Backup", variable=compress_backup_var)
compress_backup_checkbox.grid(row=7, column=0, padx=10, pady=5, sticky="w")

# Checkbutton for desktop notifications
desktop_notification_var = tk.BooleanVar()
desktop_notification_var.set(False)
desktop_notification_checkbox = ttk.Checkbutton(window, text="Desktop Notifications", variable=desktop_notification_var)
desktop_notification_checkbox.grid(row=8, column=0, padx=10, pady=5, sticky="w")

# Button to initiate the backup process
backup_button = ttk.Button(window, text="Backup DB", command=backup_database)
backup_button.grid(row=9, column=0, columnspan=2, padx=10, pady=10)

# Listbox for saved logins
login_listbox = tk.Listbox(window, selectmode=tk.SINGLE)
login_listbox.grid(row=1, column=3, rowspan=8, padx=10, pady=5, sticky="ns")

# Populate the listbox with saved logins
for login in logins:
    login_listbox.insert(tk.END, login)

# Function to handle login selection from the listbox
def on_login_select(event):
    selected_login_index = login_listbox.curselection()
    if selected_login_index:
        selected_login = logins[selected_login_index[0]]
        set_login_values(url_entry, db_username_entry, username_entry, password_entry, selected_login)

login_listbox.bind('<<ListboxSelect>>', on_login_select)

# Start the GUI main loop
window.mainloop()
