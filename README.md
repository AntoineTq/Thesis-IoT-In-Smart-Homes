Thesis "Analyzing energy consumption of smart home devices through network monitoring"
at UCLouvain by Antoine Tacq


## Requirements for the application
**tcpdump**, **wireshark** and **timeout** (that is part of the GNU coreutils) are required to run the app. 
You can install them with :
```
sudo apt install wireshark
sudo apt install tcpdump
sudo apt install coreutils
sudo apt install tshark
```

to use tcpdump without sudo we need to give the user the privileges with :
```
sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/tcpdump
```
Note : the path to tcpdump may vary depending on the system.
sources : 
https://github.com/hortinstein/node-dash-button/issues/15 
and
https://askubuntu.com/questions/1432914/executing-tcpdump-without-sudo-on-ubuntu-20-04


There is also a **requirements.txt** file that contains all the python libraries for this project.
The command to install them is:
```
pip install -r requirements.txt
```

### Run the application
To run the application you have to go to the backend folder and run the app.py file. 
Note that the frontend is built from the angular frontend and placed in the backend/static 
and backend/templates folders but if you want to change the way you want to use it just follow the next sections.
```
cd backend
python app.py
```
The application will then be accessible through the default 
http://127.0.0.1:5000 address



### frontend

You can also decide to start the frontend separately if you want to.
for this you will need node.js.
```
sudo apt install nodejs
cd frontend
npm install
```

You can then start the frontend with the following command (Note: by default it runs on http://localhost:4200):
```
ng serve
```

### Note
if you change the host address used for the backend and frontend,
you have to make sure to change the corresponding elements in the code:

- In **frontend/src/app/system.service.ts** you have to change the code `private url = 'http://127.0.0.1:5000';` 
  to correspond the address of the backend.
- In **backend/app.py** line 14. You have to change `accepted_address = "http://localhost:4200"` to the address of the frontend.





