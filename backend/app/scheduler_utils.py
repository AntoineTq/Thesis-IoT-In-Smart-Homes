import os
import subprocess
from datetime import datetime

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

from .app_utils import filter_traffic, predict_routine_event, train_event_model, power_consumption_profile, train_idle_model
from .database import NetworkInterface, Events, Devices

scheduler = BackgroundScheduler()


def capture(duration, interface, db, app):
    print(f"enter {datetime.now()} for {duration}")
    folder = "raw_daily_captures"

    if not os.path.exists("pcap_files/" + folder):
        os.makedirs("pcap_files/" + folder)

    # create a file
    date = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
    file = f"pcap_files/{folder}/traffic_{date}.pcap"

    # start capture with tcpdump
    try:
        with app.app_context():
            devices = db.session.query(Devices).all()
            dev_ips = [device.ip_address for device in devices if device.idle_done]
            hosts = " or ".join([f"host {ip}" for ip in dev_ips])
        print(f"hosts to capture routine are {hosts}")
        subprocess.run(["timeout", "--preserve-status", duration, "tcpdump", "-i", interface, hosts, "-w", file], check=True)

    except Exception as e:
        raise ValueError("capture routine failed")


def add_events_to_db(db, app):
    path = os.path.join(os.getcwd(), "event_inference/data/routines-filtered-std")
    if not os.path.isdir(path):
        print("tried to add_events_to_db but path doesn't exist yet")
        return

    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        csv = pd.read_csv(file_path)
        with app.app_context():
            for i in range(len(csv['start_time'])):
                date = datetime.fromtimestamp(csv['start_time'][i])
                device = csv['device'][i]
                if db.session.query(Events).filter_by(device_name=device, timestamp=date).first() is not None:
                    continue
                event = Events(device_name=device, timestamp=date)
                db.session.add(event)
            db.session.commit()


def retrieve_predictions(db, app):
    path = os.path.join(os.getcwd(), "event_inference/logs/log_unknown_routines-filtered-std")
    print(f"path: {path}")
    if not os.path.isdir(path):
        return
    with app.app_context():
        for file in os.listdir(path): # loop through all devices
            file_path = os.path.join(path, file)
            device_name = file.replace(".txt", "").replace("test-","")
            print(f"device: {device_name}")
            with open(file_path, 'r') as f:
                lines = f.readlines()
                for line in lines: # loop through all events
                    line_split = line.strip().split(" :")
                    date = datetime.strptime(line_split[0], "%m/%d/%Y, %H:%M:%S.%f")
                    event_prediction = line_split[1]
                    query = db.session.query(Events).filter(Events.device_name==device_name, Events.timestamp==date).first()
                    if query is None:
                        raise ValueError(f"Event at date {date} for device {device_name} was not added in the database")
                    if not query.is_classified and query.event_name == "unclassified":
                        query.event_name = event_prediction
                        db.session.commit()




def routine_prediction(db, app):
    train_event_model()
    filter_traffic("daily", db, app)
    predict_routine_event()
    add_events_to_db(db, app)
    retrieve_predictions(db, app)

def idle_build(db, app):
    filter_traffic("idle", db, app)
    train_idle_model()

def start_idle_scheduler(db, app):
    try:
        scheduler.add_job(idle_build, 'date', run_date=datetime.now(),id="idle", args=[db, app])
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

def start_capture_scheduler(interface, db, app):
    try:
        scheduler.add_job(capture, 'interval', hours=4, seconds=5, args=['4h', interface, db, app],id="capture", next_run_time=datetime.now())
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


def start_routine_prediction_scheduler(db, app):
    try:
        scheduler.add_job(routine_prediction, 'cron', hour='8,16', args=[db, app],id="routine", next_run_time=datetime.now()+pd.Timedelta(minutes=5))
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


def start_event_training_scheduler():
    try:
        scheduler.add_job(train_event_model, 'cron', hour=12, minute=45,id="event", next_run_time=datetime.now())
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


def get_scheduler_status():
    return scheduler.running


def get_job_status(job):
    job_status = scheduler.get_job(job)
    if job_status is not None:
        return job_status.next_run_time is not None
    return False


def consumption_profile_scheduler(db, app):
    with app.app_context():
        devices = db.session.query(Devices.device_name).all()
        for device in devices:
            power_consumption_profile(device.device_name, app, db)


def start_consumption_profile_scheduler(db,app):
    try:
        scheduler.add_job(consumption_profile_scheduler, 'cron', hour=12, args=[db, app],id="consumption")
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

# ckeck if scheduler can be started (this means the app crashed/restarted AND that the setup is done
def start_scheduler(db, app):
    with app.app_context():
        network_interface = db.session.query(NetworkInterface).first()
        if network_interface is None:
            print('cannot start scheduler')
            return
        if network_interface.can_capture:
            start_capture_scheduler(network_interface.interface_name, db, app)
            start_routine_prediction_scheduler(db, app)
            start_consumption_profile_scheduler(db, app)
            scheduler.start()
        else:
            print('app can not capture routine traffic')  # TODO remove



