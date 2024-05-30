import os
from pathlib import Path
import re

# Useful paths
script_path = Path(os.path.abspath(__file__))  # This script's path
script_dir = script_path.parents[0]            # This script's directory
parent_dir = script_path.parents[1]            # This script's parent directory

device_names = []
dirc = os.path.join(script_dir, "freq_period", "idle")
#dirc2 = os.path.join(script_dir, "freq_period", "2021_1h")

out_dir = os.path.join(script_dir, "freq_period", "fingerprints")
non_dir = os.path.join(script_dir, "freq_period", "nonperiod")
All_total = 0
All_nonperoid = 0
All_period = 0
for file in os.listdir(dirc):  #  /freq_new/
        if file.endswith('.txt'):
            device_name = file.replace('.txt', '')
            device_names.append(device_name)
            
            print(device_name)

            f = open(os.path.join(dirc, file)) # './freq_new/'+
            #f2 = open(os.path.join(dirc2, file))

            out_file_path = os.path.join(out_dir, file)
            out_file = open(out_file_path, 'w+')
            #non_file_path = os.path.join(non_dir, file)
            #non_file = open(non_file_path, 'w+')

            non_nums = 0
            is_nums = 0
            total_number = 0

            output_dic = {}
            for line in f:
                if line=='\n':
                    continue

                total_number += int(re.findall(r'# \d+', line)[0].split()[-1])
                if line.startswith('No'): #   
                    continue
                    # if (line.split()[3] != 'DNS' and line.split()[3] != 'DHCP' and line.split()[3] != 'NTP' and line.split()[3] != 'MDNS'  and line.split()[3] != 'SSDP'):
                    #     # print([int(s) for s in line.split() if s.isdigit()])
                    #     # print(re.findall(r'# \d+', line))
                    #     non_nums += int(re.findall(r'# \d+', line)[0].split()[-1])
                    # else:
                    #     is_nums += int(re.findall(r'# \d+', line)[0].split()[-1])
                elif line!='\n': 
                    # print(re.findall(r'# \d+', line))
                    is_nums += int(re.findall(r'# \d+', line)[0].split()[-1])

                    protocol = line.split()[0]
                    domain_name = line.split()[1]
                    # print(re.findall(r'best: \d+', line)[0].split())
                    tmp_period =  int(re.findall(r'best: \d+', line)[0].split()[1])# int(line.split()[-1])

                    # print(protocol, domain_name, tmp_period)
                    output_dic[(protocol, domain_name)] = [tmp_period]
                    # out_file.write('%s %s %d \n' %(protocol, domain_name, tmp_period))


            """
            for line in f2:
                if line=='\n':
                    continue

                if line.startswith('No'): #   or line.startswith('Unsure')
                    protocol = line.split()[3]
                    domain_name = line.split()[4]
                    if (protocol,domain_name) in output_dic:
                        continue
                    else:
                        if (line.split()[3] != 'DNS' and line.split()[3] != 'DHCP' and line.split()[3] != 'NTP' and line.split()[3] != 'MDNS'  and line.split()[3] != 'SSDP'):

                            non_nums += int(re.findall(r'# \d+', line)[0].split()[-1])
                            non_file.write('%s' % line)
                        else:
                            is_nums += int(re.findall(r'# \d+', line)[0].split()[-1])

                elif line!='\n': 
                    
                    protocol = line.split()[0]
                    domain_name = line.split()[1]
                    tmp_period = int(line.split()[-1])*7200
                    if (protocol,domain_name) in output_dic:
                        if tmp_period == output_dic[(protocol, domain_name)][0]:
                            continue
                        else:
                            output_dic[(protocol, domain_name)].append( tmp_period )
                    else:
                        output_dic[(protocol, domain_name)] = [tmp_period]
                        is_nums += int(re.findall(r'# \d+', line)[0].split()[-1])
            """

            
            for key in output_dic.keys():
                if len(output_dic[key]) == 1:
                    tmp_period = output_dic[key][0]
                    out_file.write(f"{key[0]} {key[1]} {tmp_period} \n")
                else:
                    out_file.write(f"{key[0]} {key[1]} {output_dic[key][0]} {output_dic[key][1]}")
                
            print('non-period: ', non_nums)
            print('period: ', is_nums)
            print('total: ', total_number)
            print('')
            All_total += total_number
            All_period += is_nums
            All_nonperoid += non_nums

            out_file.close()
            #non_file.close()

print('All non-period: ', All_nonperoid)
print('All period: ', All_period)
print('All total: ', All_total)
