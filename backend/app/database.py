from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
db = SQLAlchemy()
db.DateTime()

# Create table in database for all devices
class Devices(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(50), nullable=False, unique=True)
    ip_address = db.Column(db.String(15), nullable=False, unique=True)
    mac_address = db.Column(db.String(17), nullable=False, unique=True)
    idle_done = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"device {self.id}: {self.device_name} - ip {self.ip_address}"


# table to store network interface
class NetworkInterface(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interface_name = db.Column(db.String(50), nullable=False)
    can_capture = db.Column(db.Boolean, nullable=False, default=False)
    router_ip = db.Column(db.String(15), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.now())

    def __repr__(self):
        return f"interface is {self.interface_name}"


class Events(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(50), nullable=False)
    is_classified = db.Column(db.Boolean, nullable=False, default=False) # true if user has classified the event
    event_name = db.Column(db.String(50), nullable=False, default="unclassified")
    timestamp = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"event {self.event_name} for device {self.device_name} at {self.timestamp}"


class Consumption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(50), nullable=False)
    active_power = db.Column(db.Float, nullable=False)
    idle_power = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"device {self.device_name} has ON:{self.active_power} and OFF: {self.idle_power}"