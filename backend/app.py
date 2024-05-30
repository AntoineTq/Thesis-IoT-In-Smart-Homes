import os
from datetime import datetime, timedelta

import netifaces
from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import subprocess
from app.database import db, Devices, NetworkInterface, Events, Consumption
from app.app_utils import filter_traffic, train_idle_model, prepare_events_for_graph, scan_network, power_consumption_profile
import app.scheduler_utils as scheduler_utils

app = Flask(__name__)

accepted_address = "http://localhost:4200"
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:4200", accepted_address]}})

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///energyMonitoring.db'

db.init_app(app)
with app.app_context():
    db.create_all()

possible_devices = []


def add_event_to_prediction_model(event,event_date):
    device_name = event['device_name']
    path = f"pcap_files/routine/{device_name}/trace/"
    output_folder = f"pcap_files/events/{device_name}/{event['event_name']}"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        split = file.split('_')
        start_date = datetime(int(split[3]), int(split[2]), int(split[1]), int(split[4]), int(split[5]), int(split[6][:-5]))
        end_date = start_date + timedelta(hours=4)
        if start_date <= event_date <= end_date:
            end_event_time = event_date + timedelta(seconds=1)
            os.popen(f"editcap -A '{event_date}' -B '{end_event_time}' '{os.path.abspath(file_path)}' '{output_folder}/{event_date}.pcap'")
            with open("event_inference/inputs/test.txt", "a") as file:
                file.write(f"{os.path.abspath(f'{output_folder}/{event_date}.pcap')}\n")
            with open("event_inference/inputs/train.txt", "a") as file:
                file.write(f"{os.path.abspath(f'{output_folder}/{event_date}.pcap')}\n")


@app.route('/api/start_setup', methods=['GET'])
def start_setup():
    global possible_devices
    try:
        with app.app_context():
            possible_devices = scan_network()
            if len(possible_devices) == 0:
                raise ValueError("No devices found on this interface")
            interface = db.session.query(NetworkInterface).first()
            if interface is not None:
                devices = db.session.query(Devices).all()
                if len(devices) > 0:
                    to_remove = []
                    for device in possible_devices:
                        for known_device in devices:
                            if device['ip'] == known_device.ip_address:
                                to_remove.append(device['ip'])
                    possible_devices = [dev for dev in possible_devices if dev['ip'] not in to_remove]
                possible_devices = [dev for dev in possible_devices if dev['interface'] == interface.interface_name]
                print(f"to remove: {to_remove}")
                return jsonify({"list": possible_devices, "interface": interface.interface_name}), 200
            else:
                return jsonify({"list": possible_devices, "interface": "none"}), 200


    except Exception as e:
        print(f"error in start_setup: {str(e)}")
        return jsonify({'Error': str(e)}), 500

@app.route('/api/setup_status', methods=['GET'])
def setup_status():
    with app.app_context():
        status = db.session.query(NetworkInterface.can_capture).first()
        if status is None:
            return jsonify({"status": "device_needed"}), 200
        elif not status[0]:
            return jsonify({"status": "capture_needed"}), 200
        elif status[0]:
            return jsonify({"status": "completed"}), 200



@app.route('/api/submit_interface', methods=['POST'])
def submit_interface():
    global possible_devices
    try:
        data = request.get_data(as_text=True)

        with app.app_context():
            if len(db.session.query(NetworkInterface).all()) == 0:
                router_ip = netifaces.ifaddresses(data)[netifaces.AF_INET][0]['addr']
                db.session.add(NetworkInterface(interface_name=data, router_ip=router_ip, start_time=datetime.now()))
                db.session.commit()

        possible_devices = [dev for dev in possible_devices if dev['interface'] == data]
        if len(possible_devices) == 0:
            raise ValueError("No devices found on this interface")
        return jsonify(possible_devices), 200
    except Exception as e:
        print(f"error in submit_interface: {str(e)}")
        return jsonify({'Error': str(e)}), 500


@app.route('/api/submit_device_names', methods=['POST'])
def submit_device_names():
    try:
        data = request.get_json()
        accepted_list = []
        with app.app_context():
            for device in data:
                if 'device_name' in device:
                    accepted_list.append(device)
                    device['device_name'] = device['device_name'].replace(" ", "_")
                    new_device = Devices(device_name=device['device_name'], ip_address=device['ip'],
                                         mac_address=device['mac'])
                    db.session.add(new_device)
                    new_profile = Consumption(device_name=device['device_name'], active_power=0, idle_power=0)
                    db.session.add(new_profile)
            db.session.commit()
        with open("devices.txt", "a") as file:
            for device in accepted_list:
                file.write(f"{device['mac']} {device['device_name']}\n")
        return jsonify("success"), 200
    except Exception as e:
        print(f"error in submit_device_names: {str(e)}")
        return jsonify({'Error': str(e)}), 500


@app.route('/api/get_devices_to_capture', methods=['GET'])
def get_devices_to_capture():
    with app.app_context():
        devices = db.session.query(Devices).all()
        dev_list = [device.device_name for device in devices if not device.idle_done]
        return jsonify(dev_list), 200


@app.route('/api/capture_idle', methods=['GET'])
def capture_idle():
    folder = "raw_idle_captures"

    if not os.path.exists("pcap_files/" + folder):
        os.makedirs("pcap_files/" + folder)

    # create a file
    date = datetime.now().strftime('%d_%m_%Y_%H_%M_%S')
    file = f"pcap_files/{folder}/traffic_{date}.pcap"
    interface = ""
    dev_list = []
    dev_ips = []
    hosts = ""
    with app.app_context():
        interface = db.session.query(NetworkInterface).first().interface_name
        devices = db.session.query(Devices).all()
        dev_list = [device.device_name for device in devices if not device.idle_done]
        dev_ips = [device.ip_address for device in devices if not device.idle_done]
        hosts = " or ".join([f"host {ip}" for ip in dev_ips])
    print(f"hosts to capture idle are {hosts}")
    # start capture with tcpdump
    try:
        subprocess.run(["timeout", "--preserve-status", "6h", "tcpdump", "-i", interface, hosts, "-w", file], check=True)
        filter_traffic("idle", db, app)
        with app.app_context():
            db.session.query(NetworkInterface).first().can_capture = True
            for device in dev_list:
                db.session.query(Devices).filter(Devices.device_name == device).first().idle_done = True
            db.session.commit()
        train_idle_model()
        scheduler_utils.start_scheduler(db, app)
        return jsonify({"status": "capture idle success"}), 200
    except Exception as e:
        print(f"error in capture_idle: {str(e)}")
        return jsonify({"status": "capture idle failed"}), 200


@app.route('/api/get_device_list', methods=['GET'])
def get_device_list():
    with app.app_context():
        devices = db.session.query(Devices.device_name).all()
        names = [device.device_name for device in devices]
        return jsonify(names), 200


@app.route('/api/getDevice', methods=['GET'])
def get_device():
    device_name = request.args.get('name')
    try:
        with app.app_context():
            device = db.session.query(Devices).filter(Devices.device_name == device_name).first()
            start_time = db.session.query(NetworkInterface.start_time).first()
            start_time = datetime.fromisoformat(str(start_time[0]))

            events_needed = True
            if datetime.now() > start_time + timedelta(days=30):
                events_needed = False
            return jsonify({"name": device.device_name, "mac": device.mac_address, "ip": device.ip_address, "events":events_needed}), 200
    except Exception as e:
        print(str(e))
        return jsonify({'Error': str(e)}), 500


@app.route('/api/getEvents', methods=['GET'])
def get_events():
    device_name = request.args.get('device')
    try:
        with app.app_context():
            events_query = db.session.query(Events).filter(Events.device_name == device_name,
                                                           Events.is_classified == False).all()
            print(events_query)
            # use isoformat() to avoid conversion errors when exchanging data from back to front and vice versa
            events_list = [{"device_name": event.device_name, "timestamp": event.timestamp.isoformat(), "prediction": event.event_name} for event in events_query]
            return jsonify(events_list), 200
    except Exception as e:
        print(str(e))
        return jsonify({'Error': str(e)}), 500


@app.route('/api/submit_event_names', methods=['POST'])
def submit_event_names():
    try:
        data = request.get_json()
        with (app.app_context()):
            for event in data:
                # As isoformat() was used to send the information, convert again to datetime to query the db
                date = datetime.fromisoformat(event['timestamp'])
                if 'event_name' not in event or event['event_name'] == "":
                    query = db.session.query(Events).filter(Events.device_name == event['device_name'],
                                                    Events.timestamp == date).first()
                    query.event_name = "skip"
                    query.is_classified = True
                    db.session.commit()
                else:
                    query =  db.session.query(Events).filter(Events.device_name == event['device_name'],
                                                    Events.timestamp == date).first()
                    query.event_name = event['event_name']
                    query.is_classified = True
                    add_event_to_prediction_model(event, date)
                    db.session.commit()
        return jsonify("success"), 200
    except Exception as e:
        print(f"error in submit_event_names: {str(e)}")
        return jsonify({'Error': str(e)}), 500


# Not used at the moment
@app.route('/api/jobStatus', methods=['GET'])
def scheduler_status():
    job = request.args.get('job')
    print(job)
    return jsonify(scheduler_utils.get_job_status(job)), 200


@app.route('/api/getGraphData', methods=['GET'])
def get_graph_data():
    device_name = request.args.get('device')
    try:
        data = prepare_events_for_graph(db, app, device_name)
        return jsonify(data), 200
    except Exception as e:
        print(f"error in get_graph_data: {str(e)}")
        return jsonify({'Error': str(e)}), 500



@app.route('/')
@app.route('/static/')
@app.route('/static/setup')
def main():
    return render_template('index.html')

if __name__ == '__main__':
    with app.app_context():
        interface = db.session.query(NetworkInterface).first()
        if interface is not None:
            print("interface is set : starting scheduler tasks")
            scheduler_utils.start_idle_scheduler(db, app)
            scheduler_utils.start_scheduler(db, app)
        else:
            print("interface is none so skipping scheduler tasks for now")

    # start the app
    app.run()
