import { Component } from '@angular/core';
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {catchError, throwError} from "rxjs";
import {SystemService} from "../system.service";

export interface Device {
  hostname: string;
  mac: string;
  ip: string;
  vendor: string;
  interface: string;
  device_name: string;
}

@Component({
  selector: 'app-setup',
  templateUrl: './setup.component.html',
  styleUrl: './setup.component.css'
})

export class SetupComponent {
  name:any;
  response:any;
  captureIdleDone:boolean = false;
  devices: Device[] = [];
  dev_names: string[] = [];
  queryingDevices:boolean = false;
  devicesFound:boolean = false;
  interfaceSelected:boolean = false;
  devicesRegistered:boolean = false;
  deviceRegistrationComplete:boolean = false;
  captureComplete:boolean = false;
  error:boolean = false;
  interface:string = "";
  buttonClicked:boolean = false;
  constructor(private http: HttpClient) {}
  url:string = "";

  ngOnInit() {
    this.url = new SystemService().getUrl();

    /*this.http.get(`${this.url}/api/setup_status`).subscribe(response => {
      this.response = response;
      if (this.response['status'] == "capture_needed"){
        this.deviceRegistrationComplete = true;
      }
      if (this.response['status'] == "completed"){
        this.deviceRegistrationComplete = true;
        this.captureComplete = true;
      }
      this.response = "";

    });*/
   /* let deviceRegistration = localStorage.getItem('deviceRegistrationComplete');
    if (deviceRegistration == 'true'){
      this.deviceRegistrationComplete = true;
    }
    let idleCapture = localStorage.getItem('idleCaptureComplete');
    if (idleCapture == 'true'){
      this.captureComplete = true;
    }*/
  }

  startSetup(){
    this.queryingDevices = true;
    this.http.get(`${this.url}/api/start_setup`).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
      this.devicesFound = true;
      this.response = response;
      if (this.response['interface'] != "none"){
        this.interface = this.response['interface'];
        this.interfaceSelected = true;
      }
      if (this.response['list'].length == 0){
        console.log("No new devices found")
        this.deviceRegistrationComplete = true;
        this.devicesRegistered = true;
        this.getDevicesToCapture();
      }
      this.devices = this.response['list'];
      this.response = "";
    });
  }

  submitInterface(){
    this.http.post<Device[]>(`${this.url}/api/submit_interface`, this.interface).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
      this.interfaceSelected = true;
      this.devices = response
    });
  }

  submitDeviceNames(){
    this.http.post(`${this.url}/api/submit_device_names`, this.devices).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
      this.response = response;
      if (this.response == 'success') {
        //localStorage.setItem('deviceRegistrationComplete', "true");
        this.deviceRegistrationComplete = true;
        this.devicesRegistered = true;
      }
      this.getDevicesToCapture();
    });
  }

  getDevicesToCapture(){
    this.http.get<string[]>(`${this.url}/api/get_devices_to_capture`).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
      console.log(response);
      this.response = response;
      this.dev_names = this.response;
      if (this.dev_names.length == 0){
        this.captureComplete = true;
      }
      console.log(this.dev_names);
    });
  }

  clickIdle(){
    this.buttonClicked = true;
    this.http.get(`${this.url}/api/capture_idle`).subscribe(response => {
      this.response = response;
      if (this.response['status'] == 'capture idle success'){
        //localStorage.setItem('idleCaptureComplete', "true");
        this.captureIdleDone = true;
        this.captureComplete = true;
      }else {
        this.response['status'] = "Error, try again"
      }
    });
  }


  private handleError(error: any) {
    console.error(error);
    this.error = true;
    return throwError(() => new Error('Server error'));

  }


}
