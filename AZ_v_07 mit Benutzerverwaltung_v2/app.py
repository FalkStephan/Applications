# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Employee, WorkingHoursChange, Holiday, DepartmentTask, EmployeeTask, Settings, User, Log
from datetime import datetime
import csv
from io import TextIOWrapper
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a_very_secret_key_change_it' # Unbedingt ändern!

db.init_app(app)
migrate = Migrate(app, db)

# Flask-Login Initialisierung
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Bitte melden Sie sich an, um diese Seite aufzurufen."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Datenbanktabellen erstellen und Standard-Admin anlegen
with app.app_context():
    db.create_all()
    if not Settings.query.first():
        db.session.add(Settings())
        db.session.commit()
    if not User.query.filter_by(is_admin=True).first():
        admin_user = User(username='admin', oe_number='GLOBAL', is_admin=True)
        admin_user.set_password('admin')
        db.session.add(admin_user)
        db.session.commit()
        print("Default admin user 'admin' with password 'admin' created.")

# --- Hilfsfunktionen & Decorators ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Für diese Aktion sind Administratorrechte erforderlich.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action, description):
    """Manuelle Funktion zum Erstellen von Log-Einträgen."""
    try:
        log = Log(
            user_id=current_user.id if current_user.is_authenticated else None,
            username=current_user.username if current_user.is_authenticated else 'System',
            action=action,
            description=description
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Fehler beim Schreiben ins Logbuch: {e}")
        db.session.rollback()

# --- Authentifizierung & Hauptrouten ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            log_action("Login", f"Benutzer '{user.username}' hat sich angemeldet.")
            return redirect(url_for('index'))
        flash('Ungültiger Benutzername oder Passwort.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action("Logout", f"Benutzer '{current_user.username}' hat sich abgemeldet.")
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

# --- Admin-Routen ---
@app.route('/admin/users')
@login_required
@admin_required
def user_list():
    users = User.query.order_by(User.username).all()
    return render_template('user_list.html', users=users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form['username']
        if User.query.filter_by(username=username).first():
            flash('Benutzername existiert bereits.', 'danger')
            return redirect(url_for('add_user'))
        new_user = User(username=username, oe_number=request.form['oe_number'], is_admin='is_admin' in request.form)
        new_user.set_password(request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        log_action("Erstellen", f"Neuer Benutzer '{username}' wurde angelegt.")
        flash('Benutzer erfolgreich hinzugefügt.', 'success')
        return redirect(url_for('user_list'))
    return render_template('add_user.html')

@app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.oe_number = request.form['oe_number']
        user.is_admin = 'is_admin' in request.form
        password = request.form.get('password')
        if password:
            user.set_password(password)
        db.session.commit()
        log_action("Bearbeiten", f"Benutzer '{user.username}' (ID: {user_id}) wurde aktualisiert.")
        flash('Benutzer erfolgreich aktualisiert.', 'success')
        return redirect(url_for('user_list'))
    return render_template('edit_user.html', user=user)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin and User.query.filter_by(is_admin=True).count() == 1:
        flash('Der letzte Administrator kann nicht gelöscht werden.', 'danger')
        return redirect(url_for('user_list'))
    username = user.username
    db.session.delete(user)
    db.session.commit()
    log_action("Löschen", f"Benutzer '{username}' (ID: {user_id}) wurde gelöscht.")
    flash('Benutzer erfolgreich gelöscht.', 'success')
    return redirect(url_for('user_list'))

@app.route('/admin/logbook')
@login_required
@admin_required
def logbook():
    page = request.args.get('page', 1, type=int)
    logs = Log.query.order_by(Log.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template('logbook.html', logs=logs)

# --- Mitarbeiterverwaltung ---
@app.route('/employees')
@login_required
def employees():
    query = Employee.query
    if not current_user.is_admin:
        query = query.filter_by(oe_number=current_user.oe_number)
    return render_template('employees.html', employees=query.order_by(Employee.name).all())

@app.route('/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if request.method == 'POST':
        oe_number = request.form.get('oe_number') if current_user.is_admin else current_user.oe_number
        new_employee = Employee(name=request.form['name'], job_title=request.form['job_title'], team=request.form.get('team'), oe_number=oe_number)
        db.session.add(new_employee)
        db.session.commit()
        log_action("Erstellen", f"Neuer Mitarbeiter '{new_employee.name}' wurde angelegt.")
        flash('Mitarbeiter erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('employees'))
    return render_template('add_employee.html')

@app.route('/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if not current_user.is_admin and employee.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('employees'))
    if request.method == 'POST':
        employee.name = request.form['name']
        employee.job_title = request.form['job_title']
        employee.team = request.form.get('team')
        if current_user.is_admin:
            employee.oe_number = request.form.get('oe_number')
        db.session.commit()
        log_action("Bearbeiten", f"Mitarbeiter '{employee.name}' (ID: {employee_id}) wurde aktualisiert.")
        flash('Mitarbeiter erfolgreich aktualisiert!', 'success')
        return redirect(url_for('employees'))
    return render_template('edit_employee.html', employee=employee)

@app.route('/employees/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if not current_user.is_admin and employee.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('employees'))
    name = employee.name
    db.session.delete(employee)
    db.session.commit()
    log_action("Löschen", f"Mitarbeiter '{name}' (ID: {employee_id}) wurde gelöscht.")
    flash('Mitarbeiter erfolgreich gelöscht!', 'success')
    return redirect(url_for('employees'))

# --- Abteilungsaufgaben ---
@app.route('/department_tasks')
@login_required
def department_tasks():
    query = DepartmentTask.query
    if not current_user.is_admin:
        query = query.filter_by(oe_number=current_user.oe_number)
    return render_template('department_tasks.html', tasks=query.order_by(DepartmentTask.name).all())

@app.route('/department_tasks/add', methods=['GET', 'POST'])
@login_required
def add_department_task():
    if current_user.is_admin:
        flash('Administratoren können keine neuen Abteilungsaufgaben anlegen.', 'danger')
        return redirect(url_for('department_tasks'))
    if request.method == 'POST':
        new_task = DepartmentTask(name=request.form['name'], description=request.form['description'], oe_number=current_user.oe_number)
        db.session.add(new_task)
        db.session.commit()
        log_action("Erstellen", f"Neue Aufgabe '{new_task.name}' wurde angelegt.")
        flash('Aufgabe erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('department_tasks'))
    return render_template('add_department_task.html')

@app.route('/department_tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_department_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if not current_user.is_admin and task.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('department_tasks'))
    if request.method == 'POST':
        task.name = request.form['name']
        task.description = request.form['description']
        if current_user.is_admin:
            task.oe_number = request.form.get('oe_number')
        db.session.commit()
        log_action("Bearbeiten", f"Aufgabe '{task.name}' (ID: {task_id}) wurde aktualisiert.")
        flash('Aufgabe erfolgreich aktualisiert!', 'success')
        return redirect(url_for('department_tasks'))
    return render_template('edit_department_task.html', task=task)

@app.route('/department_tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_department_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if not current_user.is_admin and task.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('department_tasks'))
    name = task.name
    db.session.delete(task)
    db.session.commit()
    log_action("Löschen", f"Aufgabe '{name}' (ID: {task_id}) wurde gelöscht.")
    flash('Aufgabe erfolgreich gelöscht!', 'success')
    return redirect(url_for('department_tasks'))

# --- Arbeitszeiten ---
@app.route('/working_hours_changes')
@login_required
def working_hours_changes():
    employees_query = Employee.query
    changes_query = WorkingHoursChange.query
    if not current_user.is_admin:
        employees_query = employees_query.filter_by(oe_number=current_user.oe_number)
        employee_ids = [e.id for e in employees_query.all()]
        changes_query = changes_query.filter(WorkingHoursChange.employee_id.in_(employee_ids))
    
    employees = employees_query.order_by(Employee.name).all()
    changes = changes_query.join(Employee).order_by(WorkingHoursChange.change_date.desc(), Employee.name).all()
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('working_hours_changes.html', changes=changes, employees=employees, today=today)

@app.route('/add_working_hours_change', methods=['POST'])
@login_required
def add_working_hours_change():
    employee = Employee.query.get_or_404(request.form['employee_id'])
    if not current_user.is_admin and employee.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('working_hours_changes'))
    
    try:
        new_hours = float(request.form['new_hours'])
        change_date = datetime.strptime(request.form['change_date'], '%Y-%m-%d').date()
        old_hours = employee.weekly_working_hours or 0.0
        employee.weekly_working_hours = new_hours
        new_change = WorkingHoursChange(employee_id=employee.id, old_hours=old_hours, new_hours=new_hours, change_date=change_date, reason=request.form['reason'])
        db.session.add(employee)
        db.session.add(new_change)
        db.session.commit()
        log_action("Erstellen", f"Arbeitszeit für '{employee.name}' wurde auf {new_hours}h hinzugefügt.")
        flash('Arbeitszeitänderung erfolgreich hinzugefügt!', 'success')
    except Exception as e:
        db.session.rollback(); flash(f'Ein Fehler ist aufgetreten: {e}', 'danger')
    return redirect(url_for('working_hours_changes'))

@app.route('/edit_working_hours_change/<int:change_id>', methods=['GET', 'POST'])
@login_required
def edit_working_hours_change(change_id):
    change = WorkingHoursChange.query.get_or_404(change_id)
    if not current_user.is_admin and change.employee.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('working_hours_changes'))
    
    employees_query = Employee.query
    if not current_user.is_admin:
        employees_query = employees_query.filter_by(oe_number=current_user.oe_number)
    employees = employees_query.order_by(Employee.name).all()
    
    if request.method == 'POST':
        try:
            change.employee_id = request.form['employee_id']
            change.new_hours = float(request.form['new_hours'])
            change.change_date = datetime.strptime(request.form['change_date'], '%Y-%m-%d').date()
            change.reason = request.form['reason']
            db.session.commit()
            log_action("Bearbeiten", f"Arbeitszeitänderung (ID: {change_id}) für '{change.employee.name}' wurde aktualisiert.")
            flash('Arbeitszeitänderung erfolgreich aktualisiert!', 'success')
        except Exception as e:
            db.session.rollback(); flash(f'Ein Fehler ist aufgetreten: {e}', 'danger')
        return redirect(url_for('working_hours_changes'))
    return render_template('edit_working_hours_change.html', change=change, employees=employees)

@app.route('/delete_working_hours_change/<int:change_id>', methods=['POST'])
@login_required
def delete_working_hours_change(change_id):
    change = WorkingHoursChange.query.get_or_404(change_id)
    if not current_user.is_admin and change.employee.oe_number != current_user.oe_number:
        flash('Keine Berechtigung.', 'danger'); return redirect(url_for('working_hours_changes'))
    
    employee_name = change.employee.name
    db.session.delete(change)
    db.session.commit()
    log_action("Löschen", f"Arbeitszeitänderung (ID: {change_id}) für '{employee_name}' wurde gelöscht.")
    flash('Arbeitszeitänderung erfolgreich gelöscht!', 'success')
    return redirect(url_for('working_hours_changes'))

# --- Feiertage, Zuordnungen & Einstellungen ---
@app.route('/assign_tasks', methods=['GET', 'POST'])
@login_required
def assign_tasks():
    employees_query = Employee.query
    tasks_query = DepartmentTask.query
    if not current_user.is_admin:
        employees_query = employees_query.filter_by(oe_number=current_user.oe_number)
        tasks_query = tasks_query.filter_by(oe_number=current_user.oe_number)
    
    employees = employees_query.order_by(Employee.name).all()
    tasks = tasks_query.order_by(DepartmentTask.name).all()

    if request.method == 'POST':
        employee_ids = [e.id for e in employees]
        EmployeeTask.query.filter(EmployeeTask.employee_id.in_(employee_ids)).delete(synchronize_session=False)
        for employee in employees:
            for task in tasks:
                assignment_type = request.form.get(f'assignment_type_{employee.id}_{task.id}')
                if assignment_type:
                    percentage_str = request.form.get(f'percentage_{employee.id}_{task.id}')
                    new_assignment = EmployeeTask(employee_id=employee.id, task_id=task.id, assignment_type=assignment_type, percentage=float(percentage_str) if percentage_str else None)
                    db.session.add(new_assignment)
        db.session.commit()
        log_action("Bearbeiten", f"Aufgabenzuordnungen für OE '{current_user.oe_number}' wurden aktualisiert.")
        flash('Aufgaben erfolgreich zugeordnet!', 'success')
        return redirect(url_for('assign_tasks'))
    
    # Restliche Logik zum Anzeigen der Seite
    assignment_types = {'v': 'Haupt-Verantwortlich', 'v1': 'Vertretung 1', 'v2': 'Vertretung 2', 'o': 'Mitwirkung'}
    assigned_tasks_data = {e.id: {} for e in employees}
    total_percentages = {e.id: 0.0 for e in employees}
    all_assignments = EmployeeTask.query.filter(EmployeeTask.employee_id.in_([e.id for e in employees])).all()
    for assign in all_assignments:
        assigned_tasks_data[assign.employee_id][assign.task_id] = {'type': assign.assignment_type, 'percentage': assign.percentage}
        if assign.percentage:
            total_percentages[assign.employee_id] += assign.percentage
    
    return render_template('assign_tasks.html', employees=employees, tasks=tasks, assigned_tasks_data=assigned_tasks_data, assignment_types=assignment_types, total_percentages_per_employee=total_percentages, settings=Settings.query.first())

@app.route('/holidays')
@login_required
@admin_required
def holidays():
    return render_template('holidays.html', holidays=Holiday.query.order_by(Holiday.holiday_date.asc()).all())

@app.route('/holidays/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_holiday():
    if request.method == 'POST':
        try:
            date_str = request.form['holiday_date']
            desc = request.form['description']
            new_holiday = Holiday(holiday_date=datetime.strptime(date_str, '%Y-%m-%d').date(), description=desc)
            db.session.add(new_holiday)
            db.session.commit()
            log_action("Erstellen", f"Feiertag '{desc}' am {date_str} wurde hinzugefügt.")
            flash('Feiertag erfolgreich hinzugefügt!', 'success')
        except Exception as e:
            db.session.rollback(); flash(f'Fehler beim Hinzufügen: {e}', 'danger')
        return redirect(url_for('holidays'))
    return render_template('add_holiday.html')

@app.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
@login_required
@admin_required
def delete_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    date = holiday.holiday_date.strftime('%Y-%m-%d')
    db.session.delete(holiday)
    db.session.commit()
    log_action("Löschen", f"Feiertag am {date} wurde gelöscht.")
    flash('Feiertag erfolgreich gelöscht!', 'success')
    return redirect(url_for('holidays'))


@app.route('/holidays/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_holidays():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt!', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt!', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            # Datei als Textdatei lesen
            csv_file = TextIOWrapper(file.stream.read(), 'utf-8')
            reader = csv.reader(csv_file)
            
            imported_count = 0
            skipped_count = 0
            errors = []

            for i, row in enumerate(reader):
                if i == 0: # Kopfzeile überspringen
                    continue
                
                if len(row) >= 1: # Mindestens das Datum muss vorhanden sein
                    date_str = row[0].strip()
                    description = row[1].strip() if len(row) > 1 else ''

                    try:
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Prüfen, ob Feiertag bereits existiert (optional, aber gut gegen Duplikate)
                        existing_holiday = Holiday.query.filter_by(holiday_date=holiday_date).first()
                        if existing_holiday:
                            skipped_count += 1
                            errors.append(f"Zeile {i+1}: Feiertag am {date_str} existiert bereits und wurde übersprungen.")
                            continue

                        new_holiday = Holiday(holiday_date=holiday_date, description=description)
                        db.session.add(new_holiday)
                        imported_count += 1
                    except ValueError:
                        skipped_count += 1
                        errors.append(f"Zeile {i+1}: Ungültiges Datumsformat '{date_str}'. Erwartet YYYY-MM-DD. Zeile übersprungen.")
                    except Exception as e:
                        skipped_count += 1
                        errors.append(f"Zeile {i+1}: Fehler beim Importieren: {e}. Zeile übersprungen.")
            
            db.session.commit() # Alle importierten Feiertage auf einmal speichern
            
            flash(f'{imported_count} Feiertage erfolgreich importiert.', 'success')
            if skipped_count > 0:
                flash(f'{skipped_count} Feiertage übersprungen oder mit Fehlern.', 'warning')
            for error in errors:
                flash(error, 'danger')
            
            return redirect(url_for('holidays'))
        else:
            flash('Ungültiger Dateityp. Bitte eine CSV-Datei hochladen.', 'danger')
    
    return render_template('import_holidays.html')



@app.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    current_settings = Settings.query.first()
    if request.method == 'POST':
        current_settings.red_threshold = float(request.form['red_threshold'])
        current_settings.green_min_threshold = float(request.form['green_min_threshold'])
        current_settings.yellow_max_threshold = float(request.form['yellow_max_threshold'])
        db.session.commit()
        log_action("Bearbeiten", "Die Schwellenwerte für die Prozent-Summen wurden geändert.")
        flash('Einstellungen erfolgreich gespeichert!', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', settings=current_settings)