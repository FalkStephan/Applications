# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
import locale
from models import db, Employee, WorkingHoursChange, Holiday, DepartmentTask, EmployeeTask, Settings, User, Log, Status, Prioritaet, Einzelaufgabe, EinzelaufgabeMitarbeiter
from datetime import datetime, date, timedelta
import csv
from io import TextIOWrapper
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from sqlalchemy import func, or_
from dateutil.relativedelta import relativedelta

# Setzt die Sprache für Zeit- und Datumsformate auf Deutsch
try:
    locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')
except locale.Error:
    print("Warnung: Deutsches locale 'de_DE.UTF-8' nicht gefunden. Monatsnamen könnten auf Englisch sein.")
    try:
        locale.setlocale(locale.LC_TIME, 'de_DE')
    except locale.Error:
        print("Warnung: Fallback auf 'de_DE' ebenfalls fehlgeschlagen.")
        locale.setlocale(locale.LC_TIME, '')


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a_very_secret_key_change_it'

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Bitte melden Sie sich an, um diese Seite aufzurufen."

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
    if not Status.query.first():
        default_stati = [
            Status(name='Offen', reihenfolge=10),
            Status(name='In Bearbeitung', reihenfolge=20),
            Status(name='Erledigt', reihenfolge=30)
        ]
        db.session.bulk_save_objects(default_stati)
        db.session.commit()
        print("Default status values created.")
    if not Prioritaet.query.first():
        default_priorities = [
            Prioritaet(name='Hoch', reihenfolge=10),
            Prioritaet(name='Mittel', reihenfolge=20),
            Prioritaet(name='Niedrig', reihenfolge=30)
        ]
        db.session.bulk_save_objects(default_priorities)
        db.session.commit()
        print("Default priority values created.")


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

def get_workdays(start_date, end_date):
    if not start_date or not end_date or start_date > end_date:
        return 0
    workdays = 0
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() < 5:
            workdays += 1
        current_date += timedelta(days=1)
    return workdays

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
        
        last_change = WorkingHoursChange.query.filter(
            WorkingHoursChange.employee_id == employee.id
        ).order_by(WorkingHoursChange.change_date.desc()).first()
        old_hours = last_change.new_hours if last_change else 0.0

        employee.weekly_working_hours = new_hours

        new_change = WorkingHoursChange(employee_id=employee.id, old_hours=old_hours, new_hours=new_hours, change_date=change_date, reason=request.form.get('reason'))
        db.session.add(new_change)
        db.session.commit()
        log_action("Erstellen", f"Arbeitszeit für '{employee.name}' wurde auf {new_hours}h geändert.")
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
            csv_file = TextIOWrapper(file.stream, 'utf-8')
            reader = csv.reader(csv_file)
            
            imported_count = 0
            skipped_count = 0
            errors = []

            next(reader, None) 
            
            for row in reader:
                if len(row) >= 1: 
                    date_str = row[0].strip()
                    description = row[1].strip() if len(row) > 1 else ''

                    try:
                        holiday_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        existing_holiday = Holiday.query.filter_by(holiday_date=holiday_date).first()
                        if existing_holiday:
                            skipped_count += 1
                            errors.append(f"Feiertag am {date_str} existiert bereits und wurde übersprungen.")
                            continue

                        new_holiday = Holiday(holiday_date=holiday_date, description=description)
                        db.session.add(new_holiday)
                        imported_count += 1
                    except ValueError:
                        skipped_count += 1
                        errors.append(f"Ungültiges Datumsformat '{date_str}'. Erwartet YYYY-MM-DD. Zeile übersprungen.")
                    except Exception as e:
                        skipped_count += 1
                        errors.append(f"Fehler beim Importieren: {e}. Zeile übersprungen.")
            
            try:
                db.session.commit() 
                log_action("Import", f"{imported_count} Feiertage importiert, {skipped_count} übersprungen.")
                flash(f'{imported_count} Feiertage erfolgreich importiert.', 'success')
                if skipped_count > 0:
                    flash(f'{skipped_count} Feiertage übersprungen oder mit Fehlern.', 'warning')
                for error in errors:
                    flash(error, 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f"Fehler beim Speichern der importierten Feiertage: {e}", "danger")

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
        if 'save_order' in request.form:
            for status in Status.query.all():
                new_order = request.form.get(f'status_order_{status.id}')
                if new_order is not None:
                    status.reihenfolge = int(new_order)
            for prio in Prioritaet.query.all():
                new_order = request.form.get(f'prio_order_{prio.id}')
                if new_order is not None:
                    prio.reihenfolge = int(new_order)
            db.session.commit()
            log_action("Bearbeiten", "Reihenfolge für Status/Prioritäten aktualisiert.")
            flash('Reihenfolge erfolgreich gespeichert!', 'success')
        elif 'red_threshold' in request.form:
            current_settings.red_threshold = float(request.form['red_threshold'])
            current_settings.green_min_threshold = float(request.form['green_min_threshold'])
            current_settings.yellow_max_threshold = float(request.form['yellow_max_threshold'])
            db.session.commit()
            log_action("Bearbeiten", "Die Schwellenwerte für die Prozent-Summen wurden geändert.")
            flash('Schwellenwerte erfolgreich gespeichert!', 'success')
        elif 'new_status_name' in request.form and request.form['new_status_name']:
            if not Status.query.filter_by(name=request.form['new_status_name']).first():
                new_status = Status(name=request.form['new_status_name'], reihenfolge=int(request.form.get('new_status_order', 0)))
                db.session.add(new_status)
                db.session.commit()
                log_action("Erstellen", f"Neuer Status '{new_status.name}' hinzugefügt.")
                flash('Neuer Status hinzugefügt.', 'success')
            else:
                flash('Dieser Status existiert bereits.', 'warning')
        elif 'new_prio_name' in request.form and request.form['new_prio_name']:
            if not Prioritaet.query.filter_by(name=request.form.get('new_prio_name')).first():
                new_prio = Prioritaet(name=request.form.get('new_prio_name'), reihenfolge=int(request.form.get('new_prio_order', 0)))
                db.session.add(new_prio)
                db.session.commit()
                log_action("Erstellen", f"Neue Priorität '{new_prio.name}' hinzugefügt.")
                flash('Neue Priorität hinzugefügt.', 'success')
            else:
                flash('Diese Priorität existiert bereits.', 'warning')
        return redirect(url_for('settings'))
    
    stati = Status.query.order_by(Status.reihenfolge, Status.name).all()
    priorities = Prioritaet.query.order_by(Prioritaet.reihenfolge, Prioritaet.name).all()
    return render_template('settings.html', settings=current_settings, stati=stati, priorities=priorities)

@app.route('/settings/status/delete/<int:status_id>', methods=['POST'])
@login_required
@admin_required
def delete_status(status_id):
    status = Status.query.get_or_404(status_id)
    if status.einzelaufgaben:
        flash(f'Status "{status.name}" wird noch von Aufgaben verwendet und kann nicht gelöscht werden.', 'danger')
    else:
        name = status.name
        db.session.delete(status)
        db.session.commit()
        log_action("Löschen", f"Status '{name}' wurde gelöscht.")
        flash(f'Status "{name}" wurde gelöscht.', 'success')
    return redirect(url_for('settings'))

@app.route('/settings/priority/delete/<int:prio_id>', methods=['POST'])
@login_required
@admin_required
def delete_priority(prio_id):
    prio = Prioritaet.query.get_or_404(prio_id)
    if prio.einzelaufgaben:
        flash(f'Priorität "{prio.name}" wird noch von Aufgaben verwendet und kann nicht gelöscht werden.', 'danger')
    else:
        name = prio.name
        db.session.delete(prio)
        db.session.commit()
        log_action("Löschen", f"Priorität '{name}' wurde gelöscht.")
        flash(f'Priorität "{name}" wurde gelöscht.', 'success')
    return redirect(url_for('settings'))


# --- Einzelaufgaben ---
@app.route('/einzelaufgaben')
@login_required
def einzelaufgaben():
    search_query = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    prio_filter = request.args.get('prio', '')
    sort_column = request.args.get('sort', 'datum_bis')
    sort_dir = request.args.get('dir', 'asc')

    query = Einzelaufgabe.query.filter_by(oe_number=current_user.oe_number)

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(or_(Einzelaufgabe.aufgabe.ilike(search_term), Einzelaufgabe.themenfeld.ilike(search_term)))
    if status_filter:
        query = query.filter(Einzelaufgabe.status_id == status_filter)
    if prio_filter:
        query = query.filter(Einzelaufgabe.prioritaet_id == prio_filter)

    tasks = query.all()

    for task in tasks:
        total_assigned_hours = sum(zuordnung.stunden or 0 for zuordnung in task.mitarbeiter_zuordnung)
        unassigned_stunden = (task.aufwand_stunden or 0) - total_assigned_hours
        task.unassigned_stunden = unassigned_stunden
        task.unassigned_pt = unassigned_stunden / 8

    sort_reverse = (sort_dir == 'desc')
    sort_key_map = {
        'aufgabe': lambda t: t.aufgabe.lower(),
        'themenfeld': lambda t: (t.themenfeld or '').lower(),
        'status': lambda t: t.status.name.lower(),
        'prioritaet': lambda t: (t.prioritaet.name if t.prioritaet else '').lower(),
        'fertigstellungsgrad': lambda t: t.fertigstellungsgrad or 0,
        'datum_bis': lambda t: t.datum_bis if t.datum_bis else date.max,
        'aufwand_pt': lambda t: t.aufwand_pt or 0,
        'unassigned_pt': lambda t: t.unassigned_pt
    }

    sort_key = sort_key_map.get(sort_column, sort_key_map['datum_bis'])
    tasks.sort(key=sort_key, reverse=sort_reverse)
    
    stati = Status.query.order_by(Status.reihenfolge, Status.name).all()
    priorities = Prioritaet.query.order_by(Prioritaet.reihenfolge, Prioritaet.name).all()
    
    return render_template('einzelaufgaben.html', tasks=tasks, stati=stati, priorities=priorities)

@app.route('/einzelaufgaben/add', methods=['GET', 'POST'])
@login_required
def add_einzelaufgabe():
    if request.method == 'POST':
        try:
            new_task = Einzelaufgabe(
                themenfeld=request.form.get('themenfeld'),
                aufgabe=request.form.get('aufgabe'),
                datum_von=datetime.strptime(request.form['datum_von'], '%Y-%m-%d').date() if request.form.get('datum_von') else None,
                datum_bis=datetime.strptime(request.form['datum_bis'], '%Y-%m-%d').date() if request.form.get('datum_bis') else None,
                status_id=request.form.get('status_id'),
                prioritaet_id=request.form.get('prioritaet_id') if request.form.get('prioritaet_id') else None,
                fertigstellungsgrad=int(request.form.get('fertigstellungsgrad', 0)),
                aufwand_stunden=float(request.form['aufwand_stunden']) if request.form.get('aufwand_stunden') else None,
                aufwand_pt=float(request.form['aufwand_pt']) if request.form.get('aufwand_pt') else None,
                oe_number=current_user.oe_number
            )
            db.session.add(new_task)
            db.session.flush()

            employees_in_oe = Employee.query.filter_by(oe_number=current_user.oe_number).all()
            for emp in employees_in_oe:
                stunden = request.form.get(f'stunden_emp_{emp.id}')
                pt = request.form.get(f'pt_emp_{emp.id}')
                if (stunden and float(stunden) > 0) or (pt and float(pt) > 0):
                    zuordnung = EinzelaufgabeMitarbeiter(
                        einzelaufgabe_id=new_task.id,
                        employee_id=emp.id,
                        stunden=float(stunden) if stunden else None,
                        pt=float(pt) if pt else None
                    )
                    db.session.add(zuordnung)
            
            db.session.commit()
            log_action("Erstellen", f"Neue Einzelaufgabe '{new_task.aufgabe}' wurde angelegt.")
            flash('Neue Einzelaufgabe erfolgreich erstellt!', 'success')
            return redirect(url_for('einzelaufgaben'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Erstellen der Aufgabe: {e}', 'danger')
    
    employees = Employee.query.filter_by(oe_number=current_user.oe_number).order_by(Employee.name).all()
    stati = Status.query.order_by(Status.reihenfolge, Status.name).all()
    priorities = Prioritaet.query.order_by(Prioritaet.reihenfolge, Prioritaet.name).all()
    return render_template('add_einzelaufgabe.html', employees=employees, stati=stati, priorities=priorities)

@app.route('/einzelaufgaben/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_einzelaufgabe(task_id):
    task = Einzelaufgabe.query.get_or_404(task_id)
    if task.oe_number != current_user.oe_number and not current_user.is_admin:
        flash('Keine Berechtigung, diese Aufgabe zu bearbeiten.', 'danger')
        return redirect(url_for('einzelaufgaben'))

    if request.method == 'POST':
        try:
            task.themenfeld = request.form.get('themenfeld')
            task.aufgabe = request.form.get('aufgabe')
            task.datum_von = datetime.strptime(request.form['datum_von'], '%Y-%m-%d').date() if request.form.get('datum_von') else None
            task.datum_bis = datetime.strptime(request.form['datum_bis'], '%Y-%m-%d').date() if request.form.get('datum_bis') else None
            task.status_id = request.form.get('status_id')
            task.prioritaet_id = request.form.get('prioritaet_id') if request.form.get('prioritaet_id') else None
            task.fertigstellungsgrad = int(request.form.get('fertigstellungsgrad')) if request.form.get('fertigstellungsgrad') else 0
            task.aufwand_stunden = float(request.form['aufwand_stunden']) if request.form.get('aufwand_stunden') else None
            task.aufwand_pt = float(request.form['aufwand_pt']) if request.form.get('aufwand_pt') else None
            
            EinzelaufgabeMitarbeiter.query.filter_by(einzelaufgabe_id=task.id).delete()
            employees_in_oe = Employee.query.filter_by(oe_number=task.oe_number).all()
            for emp in employees_in_oe:
                stunden = request.form.get(f'stunden_emp_{emp.id}')
                pt = request.form.get(f'pt_emp_{emp.id}')
                if (stunden and float(stunden) > 0) or (pt and float(pt) > 0):
                    zuordnung = EinzelaufgabeMitarbeiter(
                        einzelaufgabe_id=task.id,
                        employee_id=emp.id,
                        stunden=float(stunden) if stunden else None,
                        pt=float(pt) if pt else None
                    )
                    db.session.add(zuordnung)

            db.session.commit()
            log_action("Bearbeiten", f"Einzelaufgabe '{task.aufgabe}' (ID: {task.id}) wurde aktualisiert.")
            flash('Aufgabe erfolgreich aktualisiert!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Aktualisieren der Aufgabe: {e}', 'danger')
        return redirect(url_for('einzelaufgaben'))

    task_oe_employees = Employee.query.filter_by(oe_number=task.oe_number).order_by(Employee.name).all()
    stati = Status.query.order_by(Status.reihenfolge, Status.name).all()
    priorities = Prioritaet.query.order_by(Prioritaet.reihenfolge, Prioritaet.name).all()
    existing_assignments = {assignment.employee_id: assignment for assignment in task.mitarbeiter_zuordnung}
    return render_template('edit_einzelaufgabe.html', task=task, employees=task_oe_employees, stati=stati, priorities=priorities, assignments=existing_assignments)

@app.route('/einzelaufgaben/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_einzelaufgabe(task_id):
    task = Einzelaufgabe.query.get_or_404(task_id)
    if task.oe_number != current_user.oe_number and not current_user.is_admin:
        flash('Keine Berechtigung zum Löschen.', 'danger')
        return redirect(url_for('einzelaufgaben'))
    
    aufgabe_name = task.aufgabe
    db.session.delete(task)
    db.session.commit()
    log_action("Löschen", f"Einzelaufgabe '{aufgabe_name}' (ID: {task_id}) wurde gelöscht.")
    flash('Einzelaufgabe erfolgreich gelöscht!', 'success')
    return redirect(url_for('einzelaufgaben'))

# --- Auslastungsanalyse ---
@app.route('/auslastungsanalyse')
@login_required
def workload_analysis():
    # 1. Standard-Zeitraum und Filter-Parameter abrufen
    today = date.today()
    default_start = (today - relativedelta(months=1)).replace(day=1)
    future_month_end = (today + relativedelta(months=3)).replace(day=1) - timedelta(days=1)
    default_end = future_month_end

    try:
        start_date_filter = datetime.strptime(request.args.get('start_date', default_start.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
        end_date_filter = datetime.strptime(request.args.get('end_date', default_end.strftime('%Y-%m-%d')), '%Y-%m-%d').date()
    except ValueError:
        flash("Ungültiges Datumsformat. Bitte YYYY-MM-DD verwenden.", "danger")
        start_date_filter = default_start
        end_date_filter = default_end
    
    search_term = request.args.get('search', '').lower()

    # 2. Mitarbeiter abrufen und filtern
    if current_user.is_admin:
        employees_query = Employee.query
        if search_term:
            employees_query = employees_query.filter(
                or_(
                    Employee.name.ilike(f'%{search_term}%'),
                    Employee.job_title.ilike(f'%{search_term}%'),
                    Employee.team.ilike(f'%{search_term}%'),
                    Employee.oe_number.ilike(f'%{search_term}%')
                )
            )
    else:
        employees_query = Employee.query.filter_by(oe_number=current_user.oe_number)
        if search_term:
            employees_query = employees_query.filter(
                or_(
                    Employee.name.ilike(f'%{search_term}%'),
                    Employee.job_title.ilike(f'%{search_term}%'),
                    Employee.team.ilike(f'%{search_term}%')
                )
            )
            
    employees = employees_query.order_by(Employee.oe_number, Employee.name).all()
    employee_ids = [emp.id for emp in employees]
    
    # 3. Kalenderwochen für den Zeitraum generieren
    calendar_weeks_data = []
    if start_date_filter <= end_date_filter:
        current_monday = start_date_filter - timedelta(days=start_date_filter.weekday())
        while current_monday <= end_date_filter:
            year, week, _ = current_monday.isocalendar()
            month_name = current_monday.strftime('%B')
            
            calendar_weeks_data.append({
                "week_str": f"KW {year}/{week:02d}",
                "monday_date_str": current_monday.strftime('%d.%m.'),
                "month_name": month_name,
                "start_of_week": current_monday
            })
            current_monday += timedelta(weeks=1)

    # 4. Aufgaben abrufen, die für die gefilterten Mitarbeiter relevant sind
    tasks_query = Einzelaufgabe.query.join(EinzelaufgabeMitarbeiter).filter(
        EinzelaufgabeMitarbeiter.employee_id.in_(employee_ids),
        Einzelaufgabe.datum_von.isnot(None),
        Einzelaufgabe.datum_bis.isnot(None),
        Einzelaufgabe.datum_von <= end_date_filter,
        Einzelaufgabe.datum_bis >= start_date_filter
    )
    tasks = tasks_query.all()

    # 5. Analyse-Datenstruktur initialisieren
    analysis_data = {emp.id: {week['week_str']: {'workload': 0.0, 'capacity': 0.0} for week in calendar_weeks_data} for emp in employees}
    
    # 6. Kapazität für jede Woche und jeden Mitarbeiter berechnen
    for emp in employees:
        for week_data in calendar_weeks_data:
            week_start_date = week_data["start_of_week"]
            latest_change = WorkingHoursChange.query.filter(
                WorkingHoursChange.employee_id == emp.id,
                WorkingHoursChange.change_date <= week_start_date
            ).order_by(WorkingHoursChange.change_date.desc()).first()
            analysis_data[emp.id][week_data['week_str']]['capacity'] = latest_change.new_hours if latest_change else 0.0

    # 7. Workload berechnen und verteilen
    for task in tasks:
        assignments = [a for a in task.mitarbeiter_zuordnung if a.employee_id in employee_ids]
        total_workdays_in_task = get_workdays(task.datum_von, task.datum_bis)
        if total_workdays_in_task == 0:
            continue

        for assignment in assignments:
            pt_per_workday = (assignment.pt or 0) / total_workdays_in_task
            
            current_date_in_loop = task.datum_von
            while current_date_in_loop <= task.datum_bis:
                if start_date_filter <= current_date_in_loop <= end_date_filter and current_date_in_loop.weekday() < 5:
                    year, week, _ = current_date_in_loop.isocalendar()
                    week_str = f"KW {year}/{week:02d}"
                    if week_str in analysis_data.get(assignment.employee_id, {}):
                        analysis_data[assignment.employee_id][week_str]['workload'] += pt_per_workday
                current_date_in_loop += timedelta(days=1)
    
    # 8. Summen und Daten für JSON vorbereiten
    employees_for_json = [{'id': emp.id, 'name': emp.name} for emp in employees]
    summary_data = {week['week_str']: {'workload': 0.0, 'capacity': 0.0} for week in calendar_weeks_data}
    for week_data in calendar_weeks_data:
        week_str = week_data['week_str']
        for emp in employees:
            summary_data[week_str]['workload'] += analysis_data[emp.id][week_str]['workload']
            summary_data[week_str]['capacity'] += analysis_data[emp.id][week_str]['capacity']

    settings_db = Settings.query.first()
    settings_for_json = {
        'red_threshold': settings_db.red_threshold if settings_db else 100.1,
        'green_min_threshold': settings_db.green_min_threshold if settings_db else 80.0
    }

    return render_template('workload_analysis.html', 
                           employees=employees, 
                           calendar_weeks_data=calendar_weeks_data, 
                           analysis_data=analysis_data,
                           summary_data=summary_data,
                           employees_for_json=employees_for_json,
                           start_date=start_date_filter.strftime('%Y-%m-%d'),
                           end_date=end_date_filter.strftime('%Y-%m-%d'),
                           search_term=search_term,
                           settings=settings_for_json)