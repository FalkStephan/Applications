# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    oe_number = db.Column(db.String(50), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    username = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(500), nullable=False)

    user = db.relationship('User', backref='logs')

    def __repr__(self):
        return f'<Log {self.timestamp} - {self.username} - {self.action}>'
    
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    weekly_working_hours = db.Column(db.Float, default=0.0)
    team = db.Column(db.String(100), nullable=True)
    oe_number = db.Column(db.String(50), nullable=False)

    # Beziehungen
    working_hours_changes = db.relationship('WorkingHoursChange', backref='employee', lazy=True, cascade="all, delete-orphan")
    assigned_tasks = db.relationship('EmployeeTask', backref='employee', lazy=True, cascade="all, delete-orphan")
    einzelaufgaben_zuordnung = db.relationship('EinzelaufgabeMitarbeiter', back_populates='employee', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Employee {self.name}>'

class WorkingHoursChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    old_hours = db.Column(db.Float, nullable=True)
    new_hours = db.Column(db.Float, nullable=False)
    change_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f'<WorkingHoursChange {self.employee_id} on {self.change_date} from {self.old_hours} to {self.new_hours}>'

class Holiday(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Holiday {self.holiday_date}>'

class DepartmentTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    oe_number = db.Column(db.String(50), nullable=False)

    assigned_tasks = db.relationship('EmployeeTask', backref='task', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<DepartmentTask {self.name}>'

class EmployeeTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('department_task.id'), nullable=False)
    assignment_date = db.Column(db.Date, default=datetime.utcnow)
    assignment_type = db.Column(db.String(50), nullable=False)
    percentage = db.Column(db.Float, nullable=True)

    __table_args__ = (db.UniqueConstraint('employee_id', 'task_id', name='_employee_task_uc'),)

    def __repr__(self):
        return f'<EmployeeTask Employee:{self.employee_id} Task:{self.task_id} Type:{self.assignment_type} Percentage:{self.percentage}>'

class Status(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    reihenfolge = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Status {self.name}>'

class Prioritaet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    reihenfolge = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Prioritaet {self.name}>'

class Einzelaufgabe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    themenfeld = db.Column(db.String(200), nullable=True)
    aufgabe = db.Column(db.Text, nullable=False)
    datum_von = db.Column(db.Date, nullable=True)
    datum_bis = db.Column(db.Date, nullable=True)
    fertigstellungsgrad = db.Column(db.Integer, nullable=True)
    aufwand_stunden = db.Column(db.Float, nullable=True)
    aufwand_pt = db.Column(db.Float, nullable=True)
    oe_number = db.Column(db.String(50), nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('status.id'), nullable=False)
    prioritaet_id = db.Column(db.Integer, db.ForeignKey('prioritaet.id'), nullable=True)

    status = db.relationship('Status', backref='einzelaufgaben')
    prioritaet = db.relationship('Prioritaet', backref='einzelaufgaben')
    mitarbeiter_zuordnung = db.relationship('EinzelaufgabeMitarbeiter', back_populates='einzelaufgabe', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Einzelaufgabe {self.aufgabe}>'

class EinzelaufgabeMitarbeiter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stunden = db.Column(db.Float, nullable=True)
    pt = db.Column(db.Float, nullable=True)
    einzelaufgabe_id = db.Column(db.Integer, db.ForeignKey('einzelaufgabe.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    
    employee = db.relationship('Employee', back_populates='einzelaufgaben_zuordnung')
    einzelaufgabe = db.relationship('Einzelaufgabe', back_populates='mitarbeiter_zuordnung')
    
    __table_args__ = (db.UniqueConstraint('einzelaufgabe_id', 'employee_id', name='_einzelaufgabe_mitarbeiter_uc'),)
    def __repr__(self):
        return f'<EinzelaufgabeMitarbeiter Aufgabe:{self.einzelaufgabe_id} Mitarbeiter:{self.employee_id}>'

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    red_threshold = db.Column(db.Float, default=100.1)
    green_min_threshold = db.Column(db.Float, default=80.0)
    yellow_max_threshold = db.Column(db.Float, default=79.9)

    def __repr__(self):
        return f'<Settings Red:>{self.red_threshold} GreenMin:{self.green_min_threshold} YellowMax:{self.yellow_max_threshold}>'