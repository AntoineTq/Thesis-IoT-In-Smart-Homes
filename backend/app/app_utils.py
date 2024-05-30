import os
import subprocess
from datetime import datetime, timedelta
import pandas as pd
from .database import Devices, Events, NetworkInterface, Consumption
import numpy as np
import mac_vendor_lookup
import time
import socket
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ZeroconfServiceTypes


class MyListener(ServiceListener):
    services = []
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        self.services.append(info)

def get_zeroconf_services():
    list = []
    ips = []
    types = ZeroconfServiceTypes.find()
    zeroconf = Zeroconf()
    listener = MyListener()
    for t in types:
        browser = ServiceBrowser(zeroconf, t, listener)
    try:
        time.sleep(20)
        for i in listener.services:
            device = i.name.split('.')[0]
            ip = socket.inet_ntoa(i.addresses[0])

            if ip not in ips:
                list.append({"name": device, "ip": ip})
                ips.append(ip)

    finally:
        zeroconf.close()

    print(f"Zeroconf services found the following {len(list)} devices:")
    for i in list:
        print(i)
    return list


def scan_network():
    print("Scanning network for devices")
    zeroconf_devices = get_zeroconf_services()
    arp = os.popen("arp -a").read().strip().split("\n")
    arp_valid = [i for i in arp if 'incomplete' not in i]

    device_list = []
    for entry in arp_valid:
        device = entry.split(' ')
        device_hostname = device[0]
        if device_hostname == '?':
            device_hostname = "unknown"
        if not "192.168" in device[1]:
            continue
        interface = device[device.index('on') + 1]
        ip = device[1].strip("()")
        for dev in zeroconf_devices:
            if dev['ip'] == ip:
                device_hostname = dev['name']

        mac = device[3]
        mac = mac.split(":")
        for i in range(len(mac)):
            if len(mac[i]) == 1:
                mac[i] = "0" + mac[i]
        mac = ":".join(mac)
        device[3] = mac
        vendor = "unknown"
        try:
            vendor = mac_vendor_lookup.MacLookup().lookup(device[3])
        except Exception as e:
            print(e)

        device_dict = {"hostname": device_hostname, "ip": ip, "mac": device[3],
                       "interface": interface, "vendor": vendor}
        device_list.append(device_dict)

    return device_list


def filter_traffic(type, db, app):
    with app.app_context():
        router_ip = db.session.query(NetworkInterface).first().router_ip

    pcap_path = os.path.abspath("pcap_files")
    event_path = os.path.abspath("event_inference")

    # Initialize variables corresponding to the capture (and change them if type is routine)
    input_folder = os.path.join(pcap_path, "raw_idle_captures")
    output_folder = "idle"
    sub_folder = "unctr"
    event_input_path = f"{event_path}/inputs/idle_inputs.txt"
    event_dns_path = f"{event_path}/inputs/idle_dns.txt"

    if type == 'daily':
        input_folder = os.path.join(pcap_path, "raw_daily_captures")
        output_folder = "routine"
        sub_folder = "trace"
        event_input_path = f"{event_path}/inputs/routine-dataset.txt"
        event_dns_path = f"{event_path}/inputs/routine_dns.txt"

    if type != 'idle' and type != 'daily':
        raise ValueError(f"Invalid type: {type}")
    # create a folder to store the filtered files (in: pcap_files/idle or pcap_files/routine)
    if not os.path.exists(pcap_path + "/" + output_folder):
        os.makedirs(pcap_path + "/" + output_folder)
    list_of_files_to_delete = []

    for file in os.listdir(input_folder):
        print(f"Filtering file: {file}")
        if not file.endswith(".pcap"):
            print(f"File {file} is not a pcap file, skipping")
            continue

        # check if date is more than 6 hours ago to avoid filtering recent files
        file_date = file[-24:-5]
        print(f"File date: {file_date}")
        file_datetime = datetime.strptime(file_date, "%d_%m_%Y_%H_%M_%S")
        if file_datetime > datetime.now() - timedelta(hours=4):
            print(f"File {file} is too recent (less than 4 hours) {file_datetime} vs {datetime.now()}, skipping the filtering")
            continue


        file_abs_path = os.path.join(input_folder, file)
        # TODO maybe check if file date is in last 7 days to avoid running every old files

        # filter the pcap file with tcpdump to get all the 192.168.x.x ip addresses
        ips = os.popen(
            f"tcpdump -n -r {file_abs_path} |awk '{{print $3}}'| cut -d . -f 1-4 | grep '192.168' | sort -u").read()

        ips = ips.strip().split("\n")
        if len(ips) == 0:
            raise ValueError(f"No ip addresses found in the pcap file: {file}")

        device_map_path = os.path.abspath(pcap_path) + "/../device_mapping.txt"

        # Loop through all ip addresses and create a filtered pcap file for each of them
        for ip in ips:
            if ip == router_ip:
                continue

            # check if device exists in the known devices
            device = None
            with app.app_context():
                device = db.session.query(Devices).filter_by(ip_address=str(ip)).first()
            if device is None:
                print(f"Device not found in device_mapping file for ip: {ip}")
                continue
            device_name = device.device_name

            # Create the folder to store the filtered pcap file
            file_folder = f"{pcap_path}/{output_folder}/{device_name}/{sub_folder}"
            if not os.path.exists(file_folder):
                os.makedirs(file_folder)

            file_date = file[-24:-5]  # get the date from the input file name
            output_pcap = f"{file_folder}/filtered_{file_date}.pcap"
            try :
                subprocess.run(["tcpdump", "-n", "-r", file_abs_path, "host", ip, "-w", output_pcap], check=True)
            except Exception as e:
                print(f"Filtering failed for file {file}: {e}")
                continue

            # After the filter, the event inference requires to write the path of the new pcap file
            # In a input text file, so write the path to this file
            with open(event_input_path, "a") as event_input:
                if output_pcap not in open(event_input_path).read():
                    event_input.write(os.path.abspath(output_pcap))
                    event_input.write("\n")

            # filter the DNS and TLS traffic. That is required by the event inference code to match hostnames
            file_folder_dns = f"{pcap_path}/{output_folder}_dns/{device_name}"
            if not os.path.exists(file_folder_dns):
                os.makedirs(file_folder_dns)

            output_pcap_dns = f"{file_folder_dns}/filtered_{file_date}_dns.pcap"
            subprocess.run(["tcpdump", "-r", file_abs_path, "-n", "((tcp dst port 443 and (tcp[((tcp[12] & 0xf0) >> 2)] = 0x16)) or (udp port 53)) and host " + ip, "-w", output_pcap_dns], check=True)

            # this tcpdump filter found on https://stackoverflow.com/a/39644735
            with open(event_dns_path, "a") as event_dns:
                if output_pcap_dns not in open(event_dns_path).read():
                    event_dns.write(os.path.abspath(output_pcap_dns))
                    event_dns.write("\n")

            # Event inference also requires dns for events.
            # As there is a high possibility to not have it in the captured traffic for those events,
            # A shortcut is to add the dns traffic from idle capture directly
            if type == 'idle':
                with open(f"{event_path}/inputs/activity_dns.txt", "a") as activity_dns:
                    if output_pcap_dns not in open(f"{event_path}/inputs/activity_dns.txt").read():
                        activity_dns.write(os.path.abspath(output_pcap_dns))
                        activity_dns.write("\n")

        # check if date is more than 24 hours ago to avoid deleting too recent files
        if file_datetime > datetime.now() - timedelta(hours=24):
            print(f"cannot delete file {file} because it is too recent (less than 24 hours) {file_datetime} vs {datetime.now()}")
            continue
        else:
            print(f"Raw file to delete: {file_abs_path}")
            list_of_files_to_delete.append(file_abs_path)


    for file in list_of_files_to_delete:
        if os.path.exists(file):
            print(f"Deleting file: {file}")
            os.remove(file)
        else :
            print(f"File {file} should exist but wasn't found")



def train_idle_model():
    try:
        subprocess.run(["sudo", "./event_inference/scripts/process_idle_traffic.sh"], check=True)
    except Exception as e:
        print(f"Training idle model failed : {e}")


def train_event_model():
    try:
        subprocess.run(["sudo", "./event_inference/scripts/process_events.sh"], check=True)
    except Exception as e:
        print(f"Training event model failed: {e}")


def predict_routine_event():
    try:
        subprocess.run(["sudo", "./event_inference/scripts/process_routine_traffic.sh"], check=True)
    except Exception as e:
        print(f"Predict routine event failed: {e}")


def power_consumption_profile(device, app, db):
    with app.app_context():
        events = db.session.query(Events).filter(Events.device_name == device).all()
        powers = []
        for event in events:
            power = extract_power_consumption(event)
            if power != -1 and abs(power) > 0.4:
                powers.append(abs(power))
        if len(powers) == 0:
            return
        device_power = np.median(powers)
        print(f"device {device} has new active power: {device_power}")
        query = db.session.query(Consumption).filter(Consumption.device_name == device).first()
        if query is not None:
            query.active_power = device_power
            db.session.commit()


def extract_power_consumption(event):
    try:
        consumption_data = pd.read_csv('instance/total_consumption.csv')
    except Exception as e:
        print("no total consumption file yet")
        return 0
    timestamps_before = [t for t in consumption_data['date'] if t < event.timestamp.timestamp()]
    timestamps_after = [t for t in consumption_data['date'] if t > event.timestamp.timestamp()]

    closest_time_before = min(timestamps_before, key=lambda x: abs(x - event.timestamp.timestamp()))
    closest_time_after = min(timestamps_after, key=lambda x: abs(x - event.timestamp.timestamp()))

    before_to_date = datetime.fromtimestamp(closest_time_before)
    after_to_date = datetime.fromtimestamp(closest_time_after)

    if after_to_date > event.timestamp + timedelta(seconds=60):
        return 0

    power_before = consumption_data.loc[consumption_data['date'] == closest_time_before].values[0][1]
    power_after = consumption_data.loc[consumption_data['date'] == closest_time_after].values[0][1]

    return float(power_after) - float(power_before)


def prepare_events_for_graph(db, app, device):
    events = {
        "labels": [],
        "timestamp": [],
        "event_names": [],
        "energy": []
    }

    with app.app_context():
        query = db.session.query(Events).filter_by(device_name=device).all()
        for event in query:
            if event.event_name == "unclassified" or event.event_name == "skip":
                continue
            if event.event_name not in events["labels"]:
                events["labels"].append(event.event_name)

            events["timestamp"].append(event.timestamp.isoformat())
            events["event_names"].append(event.event_name)

            if event.event_name.lower() == "on":
                energy = db.session.query(Consumption).filter(Consumption.device_name == device).first()
                if energy is not None:
                    events["energy"].append(energy.active_power)
                else:
                    events["energy"].append(0)
            else:
                events["energy"].append(0)
    return events
