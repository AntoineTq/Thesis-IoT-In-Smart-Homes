import sys
import os
from pathlib import Path
import numpy as np
import Constants as c
import pickle

# Useful paths
script_path = Path(os.path.abspath(__file__))  # This script's path
script_dir = script_path.parents[0]            # This script's directory
event_inference_dir = script_path.parents[1]   # This script's parent directory
print(f"event inference dir = {event_inference_dir}")

def print_usage(is_error):
    PATH = sys.argv[0]
    USAGE = """
    Usage: python3 {prog_name} inputs/input_dns_file.txt

    This file extracts ip-host tuple from dns and tls messages. 

    Example: python3 {prog_name} inputs/2021/idle_dns.txt

    For more information, see model_details.md.""".format(prog_name=PATH)
    
    print(USAGE, file=sys.stderr) if is_error else print(USAGE)
    exit(is_error)

def hostname_extract(infiles, dev_name):
    ip_host = {} # dictionary of destination IP to hostname

    for in_pcap in infiles:
        # file contains hosts and ips in format [hostname]\t[ip,ip2,ip3...]
        hosts = str(os.popen("tshark -r %s -Y \"dns&&dns.a\" -T fields -e dns.qry.name -e dns.a -e frame.time_epoch"
                            % in_pcap).read()).splitlines()
        tls_hosts = str(os.popen("tshark -r %s -Y \"tls.handshake.extensions_server_name\" -T fields -e tls.handshake.extensions_server_name -e ip.dst -e frame.time_epoch"
                            % in_pcap).read()).splitlines()
        # make dictionary of ip to host from DNS requests
        
        for line in hosts: # load ip_host
            line = line.split("\t") # host_name, ips, time_epoch
            if line[0].startswith('192.168.'):
                continue
            ips = line[1].split(",")
            for ip in ips:
                # if ip in ip_host and ip_host[ip] != line[0]:
                    # print(ip, ip_host[ip], line[0], line[-1]) # check if some ips would be dynamically used by multiple domains. 
                if ip in ip_host:
                    ip_host[ip].append((line[0],line[-1]))
                else:
                    ip_host[ip] = [(line[0],line[-1])]
    
        for line in tls_hosts:
            line = line.split("\t")
            if line[0].startswith('192.168.'):
                continue
            ips = line[1].split(",")
            for ip in ips:
                if ip in ip_host:
                    ip_host[ip].append((line[0],line[-1]))
                else:
                    ip_host[ip] = [(line[0],line[-1])]
    print(dev_name) # , ip_host

    return ip_host

def main():
    print(os.getcwd())
    [ print_usage(0) for arg in sys.argv if arg in ("-h", "--help") ]

    print("Running %s..." % sys.argv[0])

    in_txt = sys.argv[1]

    errors = False
    if not in_txt.endswith(".txt"):
        errors = True
        print(c.WRONG_EXT % ("Input text file", "text (.txt)", in_txt), file=sys.stderr)
    elif not os.path.isfile(in_txt):
        errors = True
        print(c.INVAL % ("Input text file", in_txt, "file"), file=sys.stderr)
    elif not os.access(in_txt, os.R_OK):
        errors = True
        print(c.NO_PERM % ("input text file", in_txt, "read"), file=sys.stderr)

    if errors:
        print_usage(1)

    print("Input file located in: %s\n" % (in_txt))


    dns_files = {}

    with open(in_txt, "r") as f:
        for pcap in f:
            pcap = pcap.strip()
            if not pcap.endswith(".pcap"):
                print(c.WRONG_EXT % ("Input pcaps", "pcap (.pcap)", pcap))
            elif not os.path.isfile(pcap):
                print(c.INVAL % ("Input pcap", pcap, "file"))
            elif not os.access(pcap, os.R_OK):
                print(c.NO_PERM % ("input pcap", pcap, "read"))
            else:


                dir_name = os.path.dirname(pcap)
                #dev_name = os.path.basename(pcap)
                dev_name = os.path.basename(dir_name)

                print(f"dir_name = {dir_name}")
                print(f"dev_name = {dev_name}")
                # if dev_name != 'ring-doorbell':
                #     continue

                ## only accept merged file, not origial pcap file
                # if os.path.basename(pcap).startswith('2021'):
                #     continue
                
                if dev_name in dns_files:
                    dns_files[dev_name].append(pcap)
                else:
                    dns_files[dev_name] = [pcap]
    ip_hosts_all = {}
    for dev in dns_files.keys():
        print(f"\ndev {dev}")
        ip_hosts_all[dev] = hostname_extract(dns_files[dev],dev)

    
    # output dir
    out_dir = os.path.join(event_inference_dir, "ip_host")
    os.makedirs(out_dir, exist_ok=True)
    
    if in_txt.endswith('routine_dns.txt'):
        model_file = os.path.join(out_dir, "routines.model")
    elif in_txt.endswith('activity_dns.txt'):
        model_file = os.path.join(out_dir, "activity.model")
    elif in_txt.endswith('idle_dns.txt'):
        model_file = os.path.join(out_dir, "ip_host_idle.model")
    elif in_txt.endswith('uncontrolled_dns.txt'):
        model_file = os.path.join(out_dir, "uncontrolled_21-22.model")
    else:
        print('Please manually specify output model file')
        exit(1)
    
    pickle.dump(ip_hosts_all, open(model_file, 'wb'))
    # ip_hosts_all = pickle.load(open(model_file, 'rb'))


if __name__ == "__main__":
    main()

