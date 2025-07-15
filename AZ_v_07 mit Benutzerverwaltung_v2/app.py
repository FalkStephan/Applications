# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from models import db, Employee, WorkingHoursChange, Holiday, DepartmentTask, EmployeeTask, Settings
from datetime import datetime
import csv 
from io import TextIOWrapper 
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key' # Ersetzen Sie dies durch einen sicheren Schlüssel

db.init_app(app)

# Datenbanktabellen erstellen und Standardeinstellungen initialisieren
# Dies wird EINMAL beim Start der Anwendung ausgeführt.
with app.app_context(): # <-- NEU: Hier wird der Anwendungs-Kontext erzwungen
    migrate = Migrate(app, db)
    db.create_all()
    # Sicherstellen, dass ein Einstellungsdatensatz existiert
    if not Settings.query.first():
        default_settings = Settings()
        db.session.add(default_settings)
        db.session.commit()
        
# Datenbank initialisieren
# @app.before_request
# def create_tables():
# db.create_all()


# --- Hauptrouten ---

@app.route('/')
def index():
    return render_template('index.html')

### **1. Mitarbeiterverwaltung**

### **Mitarbeiterliste und Hinzufügen**

### **Route:**

@app.route('/employees')
def employees():
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)


@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if request.method == 'POST':
        name = request.form['name']
        job_title = request.form['job_title']
        team = request.form.get('team') # NEU: Team-Feld abrufen
        new_employee = Employee(name=name, job_title=job_title, team=team) # NEU: Team übergeben
        db.session.add(new_employee)
        db.session.commit()
        flash('Mitarbeiter erfolgreich hinzugefügt!', 'success')
        return redirect(url_for('employees'))
    return render_template('add_employee.html')

@app.route('/employees/edit/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if request.method == 'POST':
        employee.name = request.form['name']
        employee.job_title = request.form['job_title']
        employee.team = request.form.get('team') # NEU: Team-Feld aktualisieren
        db.session.commit()
        flash('Mitarbeiter erfolgreich aktualisiert!', 'success')
        return redirect(url_for('employees'))
    return render_template('edit_employee.html', employee=employee)

@app.route('/employees/delete/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    db.session.delete(employee)
    db.session.commit()
    flash('Mitarbeiter erfolgreich gelöscht!', 'success')
    return redirect(url_for('employees'))


@app.route('/holidays')
def holidays():
    # Feiertage aufsteigend nach Datum sortieren (Standard-Sortierung vom Server)
    holidays = Holiday.query.order_by(Holiday.holiday_date.asc()).all()
    return render_template('holidays.html', holidays=holidays)

@app.route('/holidays/add', methods=['GET', 'POST'])
def add_holiday():
    if request.method == 'POST':
        holiday_date_str = request.form['holiday_date']
        description = request.form['description']
        try:
            holiday_date = datetime.strptime(holiday_date_str, '%Y-%m-%d').date()
            new_holiday = Holiday(holiday_date=holiday_date, description=description)
            db.session.add(new_holiday)
            db.session.commit()
            flash('Feiertag erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('holidays'))
        except ValueError:
            flash('Ungültiges Datumsformat. Bitte YYYY-MM-DD verwenden.', 'danger')
        except Exception as e:
            flash(f'Fehler beim Hinzufügen des Feiertags: {e}', 'danger')
    return render_template('add_holiday.html')

@app.route('/holidays/delete/<int:holiday_id>', methods=['POST'])
def delete_holiday(holiday_id):
    holiday = Holiday.query.get_or_404(holiday_id)
    db.session.delete(holiday)
    db.session.commit()
    flash('Feiertag erfolgreich gelöscht!', 'success')
    return redirect(url_for('holidays'))

@app.route('/holidays/import', methods=['GET', 'POST'])
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

# Diese Route wird die Liste der Arbeitszeitänderungen anzeigen.
# Sie ist bereits in Ihrem Code vorhanden.
@app.route('/working_hours_changes')
def working_hours_changes():
    # Sortiert die Änderungen nach Datum absteigend, um die neuesten zuerst anzuzeigen
    changes = WorkingHoursChange.query.order_by(WorkingHoursChange.change_date.desc()).all()
    employees = Employee.query.all() # Wird für die Dropdown-Liste im Formular benötigt
    today = datetime.now().strftime('%Y-%m-%d') # Heutiges Datum für das Hinzufügen-Formular
    return render_template('working_hours_changes.html', changes=changes, employees=employees, today=today)

# Diese Route verarbeitet das Hinzufügen neuer Arbeitszeitänderungen.
# Sie ist bereits in Ihrem Code vorhanden.
@app.route('/add_working_hours_change', methods=['POST'])
def add_working_hours_change():
    employee_id = request.form['employee_id']
    new_hours_str = request.form['new_hours']
    change_date_str = request.form['change_date']
    reason = request.form['reason']

    try:
        new_hours = float(new_hours_str)
        change_date = datetime.strptime(change_date_str, '%Y-%m-%d').date()

        employee = Employee.query.get(employee_id)
        if not employee:
            flash(f'Mitarbeiter mit ID {employee_id} nicht gefunden.', 'danger')
            return redirect(url_for('working_hours_changes'))

        # Die alte Arbeitszeit ist die aktuelle Wochenarbeitszeit des Mitarbeiters VOR dieser Änderung.
        # Dies setzt voraus, dass employee.weekly_working_hours immer aktuell ist.
        old_hours = employee.weekly_working_hours if employee.weekly_working_hours is not None else 0.0

        # Aktualisiere die weekly_working_hours des Mitarbeiters in der Employee-Tabelle auf die neuen Stunden
        employee.weekly_working_hours = new_hours
        db.session.add(employee) # Füge den geänderten Mitarbeiter zur Session hinzu

        # Füge den Eintrag der Arbeitszeitänderung hinzu
        new_change = WorkingHoursChange(
            employee_id=employee_id,
            old_hours=old_hours,
            new_hours=new_hours,
            change_date=change_date,
            reason=reason
        )
        db.session.add(new_change)
        db.session.commit()
        flash('Arbeitszeitänderung erfolgreich hinzugefügt und Mitarbeiter aktualisiert!', 'success')
    except ValueError:
        flash('Ungültige Eingabe für Arbeitszeit oder Datum. Stellen Sie sicher, dass das Datum im Format JJJJ-MM-TT ist.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Ein unerwarteter Fehler ist aufgetreten: {e}', 'danger')
    return redirect(url_for('working_hours_changes'))


# NEUE ROUTE: Arbeitszeitänderung bearbeiten
@app.route('/edit_working_hours_change/<int:change_id>', methods=['GET', 'POST'])
def edit_working_hours_change(change_id):
    # Holt den zu bearbeitenden Arbeitszeitänderungs-Eintrag
    change = WorkingHoursChange.query.get_or_404(change_id)
    # Holt alle Mitarbeiter für die Dropdown-Liste im Bearbeitungsformular
    employees = Employee.query.all()

    if request.method == 'POST':
        # Speichere die ursprüngliche Mitarbeiter-ID und die "neuen Stunden" des Eintrags
        # (die als "alte Stunden" für den Mitarbeiter vor dieser Änderung gelten würden),
        # für den Fall, dass der Mitarbeiter oder die Stunden geändert werden.
        old_employee_id = change.employee_id
        original_new_hours_of_this_entry = change.new_hours

        # Aktualisiere die Felder des WorkingHoursChange-Eintrags mit den Formulardaten
        change.employee_id = request.form['employee_id']
        change.new_hours = float(request.form['new_hours'])
        change.change_date = datetime.strptime(request.form['change_date'], '%Y-%m-%d').date()
        change.reason = request.form['reason']

        try:
            db.session.commit() # Speichere die Änderungen am WorkingHoursChange-Eintrag

            # --- Logik zur Aktualisierung der weekly_working_hours des Mitarbeiters ---
            # Diese Logik ist entscheidend, um die "aktuelle" Wochenarbeitszeit des Mitarbeiters
            # in der Employee-Tabelle korrekt zu halten, nachdem eine Änderung bearbeitet wurde.

            # 1. Betrachte den Mitarbeiter, der ursprünglich mit diesem Eintrag verknüpft war (falls er sich geändert hat)
            if old_employee_id != change.employee_id:
                # Wenn der Mitarbeiter geändert wurde, müssen wir den alten Mitarbeiter aktualisieren.
                # Finde die neueste Arbeitszeitänderung für den alten Mitarbeiter, die NICHT der aktuell bearbeitete Eintrag ist.
                last_change_for_old_employee = WorkingHoursChange.query.filter_by(employee_id=old_employee_id)\
                                                .filter(WorkingHoursChange.id != change.id)\
                                                .order_by(WorkingHoursChange.change_date.desc()).first()
                
                old_employee = Employee.query.get(old_employee_id)
                if old_employee:
                    if last_change_for_old_employee:
                        # Setze die Wochenarbeitszeit des alten Mitarbeiters auf die Stunden der letzten verbleibenden Änderung
                        old_employee.weekly_working_hours = last_change_for_old_employee.new_hours
                    else:
                        # Wenn keine anderen Änderungen für den alten Mitarbeiter vorhanden sind, setze auf 0.0 (oder einen Standardwert)
                        old_employee.weekly_working_hours = 0.0
                    db.session.add(old_employee) # Füge den aktualisierten alten Mitarbeiter zur Session hinzu

            # 2. Betrachte den Mitarbeiter, der JETZT mit diesem Eintrag verknüpft ist
            # Finde die neueste Arbeitszeitänderung für den (potenziell neuen) Mitarbeiter.
            # Dies ist wichtig, da die "aktuelle" Arbeitszeit des Mitarbeiters immer die der neuesten Änderung sein sollte.
            latest_change_for_current_employee = WorkingHoursChange.query.filter_by(employee_id=change.employee_id)\
                                                    .order_by(WorkingHoursChange.change_date.desc()).first()
            
            current_employee = Employee.query.get(change.employee_id)
            if current_employee:
                if latest_change_for_current_employee:
                    # Setze die Wochenarbeitszeit des aktuellen Mitarbeiters auf die Stunden der neuesten Änderung
                    current_employee.weekly_working_hours = latest_change_for_current_employee.new_hours
                else:
                    # Dies sollte normalerweise nicht passieren, wenn ein Eintrag existiert, aber als Fallback
                    current_employee.weekly_working_hours = 0.0
                db.session.add(current_employee) # Füge den aktualisierten aktuellen Mitarbeiter zur Session hinzu
            
            db.session.commit() # Speichere die Änderungen an den Employee-Objekten
            flash('Arbeitszeitänderung erfolgreich aktualisiert!', 'success')
            return redirect(url_for('working_hours_changes'))
        except ValueError:
            db.session.rollback() # Rollback bei Validierungsfehlern
            flash('Ungültige Eingabe für Arbeitszeit oder Datum. Stellen Sie sicher, dass das Datum im Format JJJJ-MM-TT ist.', 'danger')
            return redirect(url_for('edit_working_hours_change', change_id=change.id))
        except Exception as e:
            db.session.rollback() # Rollback bei anderen Fehlern
            flash(f'Ein unerwarteter Fehler ist aufgetreten: {e}', 'danger')
            return redirect(url_for('edit_working_hours_change', change_id=change.id))

    # Für GET-Anfragen: Rendere das Bearbeitungsformular
    return render_template('edit_working_hours_change.html', change=change, employees=employees)

# NEUE ROUTE: Arbeitszeitänderung löschen
@app.route('/delete_working_hours_change/<int:change_id>', methods=['POST'])
def delete_working_hours_change(change_id):
    # Holt den zu löschenden Arbeitszeitänderungs-Eintrag
    change = WorkingHoursChange.query.get_or_404(change_id)
    employee_id = change.employee_id # Speichere die Mitarbeiter-ID, bevor der Eintrag gelöscht wird

    try:
        db.session.delete(change) # Lösche den Eintrag aus der Datenbank
        db.session.commit() # Bestätige die Löschung

        # --- Logik zur Aktualisierung der weekly_working_hours des Mitarbeiters nach dem Löschen ---
        # Nach dem Löschen müssen wir die "aktuelle" Wochenarbeitszeit des betroffenen Mitarbeiters neu berechnen.
        # Finde die neueste Arbeitszeitänderung für den Mitarbeiter, die nach dem Löschen dieses Eintrags noch vorhanden ist.
        latest_change = WorkingHoursChange.query.filter_by(employee_id=employee_id)\
                                        .order_by(WorkingHoursChange.change_date.desc()).first()
        
        employee = Employee.query.get(employee_id)
        if employee:
            if latest_change:
                # Setze die Wochenarbeitszeit des Mitarbeiters auf die Stunden der neuesten verbleibenden Änderung
                employee.weekly_working_hours = latest_change.new_hours
            else:
                # Wenn keine weiteren Änderungen für diesen Mitarbeiter vorhanden sind,
                # setze die Wochenarbeitszeit auf 0.0 (oder einen geeigneten Standardwert).
                employee.weekly_working_hours = 0.0
            db.session.add(employee) # Füge den aktualisierten Mitarbeiter zur Session hinzu
            db.session.commit() # Speichere die Änderung am Employee-Objekt

        flash('Arbeitszeitänderung erfolgreich gelöscht!', 'success')
    except Exception as e:
        db.session.rollback() # Rollback bei Fehlern
        flash(f'Ein Fehler ist aufgetreten: {e}', 'danger')
    return redirect(url_for('working_hours_changes'))

@app.route('/department_tasks')
def department_tasks():
    tasks = DepartmentTask.query.all()
    return render_template('department_tasks.html', tasks=tasks)


@app.route('/department_tasks/add', methods=['GET', 'POST'])
def add_department_task():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        new_task = DepartmentTask(name=name, description=description)
        try:
            db.session.add(new_task)
            db.session.commit()
            flash('Aufgabe erfolgreich hinzugefügt!', 'success')
            return redirect(url_for('department_tasks'))
        except Exception as e:
            flash(f'Fehler beim Hinzufügen der Aufgabe: {e}', 'danger')
    return render_template('add_department_task.html')

@app.route('/department_tasks/edit/<int:task_id>', methods=['GET', 'POST'])
def edit_department_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    if request.method == 'POST':
        task.name = request.form['name']
        task.description = request.form['description']
        db.session.commit()
        flash('Aufgabe erfolgreich aktualisiert!', 'success')
        return redirect(url_for('department_tasks'))
    return render_template('edit_department_task.html', task=task)

@app.route('/department_tasks/delete/<int:task_id>', methods=['POST'])
def delete_department_task(task_id):
    task = DepartmentTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    flash('Aufgabe erfolgreich gelöscht!', 'success')
    return redirect(url_for('department_tasks'))

@app.route('/assign_tasks', methods=['GET', 'POST'])
def assign_tasks():
    employees = Employee.query.all()
    tasks = DepartmentTask.query.all()

    assignment_types = {
        'v': 'Haupt-Verantwortlich',
        'v1': 'Vertretung 1',
        'v2': 'Vertretung 2',
        'o': 'Mitwirkung'
    }
    
    assigned_tasks_data = {}
    total_percentages_per_employee = {}

    for employee in employees:
        assigned_tasks_data[employee.id] = {}
        current_employee_total_percentage = 0.0
        for et in employee.assigned_tasks:
            assigned_tasks_data[employee.id][et.task_id] = {
                'type': et.assignment_type,
                'percentage': et.percentage
            }
            if et.percentage is not None:
                current_employee_total_percentage += et.percentage
        total_percentages_per_employee[employee.id] = current_employee_total_percentage

    # Lade die aktuellen Einstellungen
    current_settings = Settings.query.first() 
    if not current_settings: # Falls aus irgendeinem Grund keine Einstellungen gefunden wurden, nutze Defaults
        current_settings = Settings()

    if request.method == 'POST':
        new_assignments = []
        for employee in employees:
            for task in tasks:
                assignment_type = request.form.get(f'assignment_type_{employee.id}_{task.id}')
                percentage_str = request.form.get(f'percentage_{employee.id}_{task.id}')

                if assignment_type:
                    percentage = None
                    if percentage_str:
                        try:
                            percentage = float(percentage_str)
                            if percentage < 0 or percentage > 100:
                                flash(f'Ungültiger Prozentsatz für {employee.name} - {task.name}. Muss zwischen 0 und 100 liegen.', 'danger')
                                continue
                        except ValueError:
                            flash(f'Ungültiges Format für Prozentsatz bei {employee.name} - {task.name}. Bitte Zahl eingeben.', 'danger')
                            continue

                    new_assignments.append({
                        'employee_id': employee.id,
                        'task_id': task.id,
                        'assignment_type': assignment_type,
                        'percentage': percentage
                    })

        db.session.query(EmployeeTask).delete()
        
        for assignment in new_assignments:
            new_assignment_obj = EmployeeTask(
                employee_id=assignment['employee_id'],
                task_id=assignment['task_id'],
                assignment_type=assignment['assignment_type'],
                percentage=assignment['percentage']
            )
            db.session.add(new_assignment_obj)
        
        db.session.commit()
        flash('Aufgaben und Prozentsätze erfolgreich zugeordnet!', 'success')
        return redirect(url_for('assign_tasks'))
    
    return render_template('assign_tasks.html', 
                           employees=employees, 
                           tasks=tasks, 
                           assigned_tasks_data=assigned_tasks_data,
                           assignment_types=assignment_types,
                           total_percentages_per_employee=total_percentages_per_employee,
                           settings=current_settings) # NEU: Einstellungen übergeben

# NEUE ROUTE für Einstellungen
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    current_settings = Settings.query.first()
    if not current_settings:
        current_settings = Settings() # Fallback, falls kein Eintrag existiert

    if request.method == 'POST':
        try:
            red = float(request.form['red_threshold'])
            green_min = float(request.form['green_min_threshold'])
            yellow_max = float(request.form['yellow_max_threshold'])

            # Grundlegende Validierung
            if not (0 <= green_min <= 100) or not (0 <= yellow_max <= 100) or not (0 <= red <= 1000): # Red kann auch über 100 sein
                flash('Alle Grenzwerte müssen Zahlen zwischen 0 und 100 (oder größer für Rot) sein!', 'danger')
                return redirect(url_for('settings'))
            
            if green_min > red:
                flash('Grün (min) darf nicht größer als Rot (über) sein.', 'danger')
                return redirect(url_for('settings'))

            if yellow_max >= green_min: # Gelb_Max ist der obere Wert für Gelb, muss unter Grün_Min liegen
                 flash('Gelb (max) muss kleiner als Grün (min) sein.', 'danger')
                 return redirect(url_for('settings'))

            current_settings.red_threshold = red
            current_settings.green_min_threshold = green_min
            current_settings.yellow_max_threshold = yellow_max
            
            db.session.commit()
            flash('Einstellungen erfolgreich gespeichert!', 'success')
            return redirect(url_for('settings'))
        except ValueError:
            flash('Ungültige Eingabe. Bitte geben Sie gültige Zahlen ein.', 'danger')
        except Exception as e:
            flash(f'Ein Fehler ist aufgetreten: {e}', 'danger')

    return render_template('settings.html', settings=current_settings)

