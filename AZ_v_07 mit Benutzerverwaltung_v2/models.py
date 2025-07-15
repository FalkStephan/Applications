# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    weekly_working_hours = db.Column(db.Float, default=0.0) 
    team = db.Column(db.String(100), nullable=True) 

    # Beziehungen
    working_hours_changes = db.relationship('WorkingHoursChange', backref='employee', lazy=True)
    assigned_tasks = db.relationship('EmployeeTask', backref='employee', lazy=True)

    def __repr__(self):
        return f'<Employee {self.name}>'

class WorkingHoursChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    old_hours = db.Column(db.Float, nullable=True) # NEU HINZUGEFÜGT: Alte Stunden
    new_hours = db.Column(db.Float, nullable=False)
    change_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(500), nullable=True) # Grund der Änderung

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

    # Beziehung
    assigned_tasks = db.relationship('EmployeeTask', backref='task', lazy=True)

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

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    red_threshold = db.Column(db.Float, default=100.0)
    green_min_threshold = db.Column(db.Float, default=80.0)
    yellow_max_threshold = db.Column(db.Float, default=79.9)

    def __repr__(self):
        return f'<Settings Red:>{self.red_threshold} GreenMin:{self.green_min_threshold} YellowMax:{self.yellow_max_threshold}>'
