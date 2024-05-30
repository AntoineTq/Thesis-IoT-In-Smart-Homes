import { Component } from '@angular/core';
import {ActivatedRoute} from "@angular/router";
import {HttpClient} from "@angular/common/http";
import {SystemService} from "../../system.service";
import {catchError, throwError} from "rxjs";
import {Chart} from "chart.js/auto";
import 'chartjs-adapter-moment';
interface Device{
  name:string;
  mac:string;
  ip:string;
  events:boolean;
}

interface Event{
  timestamp:string;
  device_name:string;
  event_name:string;
  prediction:string;
}

interface GraphData{
  labels:string[];
  timestamp:string[];
  event_names:string[];
  energy:string[];
}

@Component({
  selector: 'app-device',
  templateUrl: './device.component.html',
  styleUrl: './device.component.css'
})
export class DeviceComponent {


  chart:any;
  urlDevice:string = "";
  device = {} as Device;
  events : Event[] = [];
  graphData: GraphData = {} as GraphData;
  url:string = "";
  response:any;
  eventsRegistered:boolean = false;
  FilterDate: string="";


  constructor(
    private route: ActivatedRoute,
    private http: HttpClient,
  ) { }


  ngOnInit() {
    this.eventsRegistered = false;
    this.url = new SystemService().getUrl();
    this.route.params.pipe(
      catchError(this.handleError.bind(this))
    ).subscribe(params => {
      this.urlDevice = params['device'];
      this.http.get<Device>(`${this.url}/api/getDevice?name=${this.urlDevice}`).subscribe(deviceResponse => {
        this.device = deviceResponse;
        if(this.device.events){
          this.http.get<Event[]>(`${this.url}/api/getEvents?device=${this.urlDevice}`).subscribe(eventResponse => {
            this.events = eventResponse;
          });
        }
      });
      this.createChart();

    });

  }

  createChart(){
    if (this.chart) {
      this.chart.destroy();
    }
    this.http.get<GraphData>(`${this.url}/api/getGraphData?device=${this.urlDevice}`).pipe(
      catchError(this.handleError.bind(this))
    ).subscribe(response => {
      this.graphData = response;

      const labels = this.graphData.labels;
      // chart created with the example from https://www.chartjs.org/docs/latest/samples/scales/stacked.html
      this.chart = new Chart("MyChart", {
        type: 'line', //this denotes tha type of chart
        data: {// values on X-Axis
          labels: this.graphData.timestamp,
          datasets: [
            {
              label: 'energy consumption (w)',
              data: this.graphData.energy,
              borderColor:'rgb(255, 99, 132)',
              backgroundColor: 'rgb(255, 99, 132)',
              stepped: true,
            },
            {
              label: 'device state',
              data: this.graphData.event_names,
              borderColor: 'rgb(54, 162, 235)',
              backgroundColor: 'rgb(54, 162, 235)',
              stepped: true,
              yAxisID: 'y2',
            }
          ]
        },

        options: {
          responsive: true,
          scales: {
            x: {
              type: 'time',
              time: {
                unit: 'day',
              },
              title: {
                display: true,
                text: 'Time'
              }
            },
            y: {
              type: 'linear',
              position: 'left',
              stack: 'demo',
              stackWeight: 2,
              border: {
                color: 'rgb(255, 99, 132)'
              },
              title:{
                display: true,
                text: 'Energy consumption (watts)'
              }
            },
            y2: {
              type: 'category',
              labels: ['on', 'off'],
              offset: true,
              position: 'left',
              stack: 'demo',
              stackWeight: 1,
              border: {
                color: 'rgb(54, 162, 235)'
              },
              title:{
                display: true,
                text: 'Device state'
              }
            }
          }
        }
      });
    });
  }



  /*
  * Function used to filter the graph. It filters it based on the day selected by the user and
  * basically just updates the arrays by selecting the events that are in the selected day
   */
  filterData(){

    const startDate = new Date(this.FilterDate);
    const endDate = new Date(this.FilterDate);
    endDate.setDate(endDate.getDate() + 1);
    const startFilterDate = startDate.toISOString().substring(0, 10);
    const endFilterDate = endDate.toISOString().substring(0, 10);

    const filteredDates: string[] = [];
    for (const date of this.graphData.timestamp) {
        if (date >= startFilterDate && date <= endFilterDate){
            filteredDates.push(date);
        }
    }

    const indexStart = this.graphData.timestamp.indexOf(filteredDates[0]);
    const indexEnd = this.graphData.timestamp.indexOf(filteredDates[filteredDates.length-1]);

    const filteredEvents = this.graphData.event_names.slice(indexStart, indexEnd+1);
    const filteredEnergy = this.graphData.energy.slice(indexStart, indexEnd+1);


    // These 2 group of lines are used to add elements at the beginning and end of the arrays corresponding to the first and last event of the day
    // For this the first element will be the opposite of the first real event end the last is just a copy of the real last event
    filteredDates.splice(0, 0, this.FilterDate);
    filteredEvents.splice(0, 0,(() => this.graphData.event_names[indexStart] === 'on' ? 'off' : 'on')());
    const energy1 = this.graphData.energy[indexStart];
    const energy2 = this.graphData.energy[indexStart+1];
    filteredEnergy.splice(0, 0, (() => this.graphData.energy[indexStart] === energy1 ? energy2 : energy1)());

    filteredDates.splice(filteredDates.length, 0, endFilterDate);
    filteredEvents.splice(filteredDates.length, 0, this.graphData.event_names[indexEnd]);
    filteredEnergy.splice(filteredDates.length, 0, this.graphData.energy[indexEnd]);


    this.chart.data.labels = filteredDates;
    this.chart.data.datasets[0].data = filteredEnergy;
    this.chart.data.datasets[1].data = filteredEvents;
    this.chart.update();

  }

  /*
  * Reset the graph to its original state by updating the data to the original data from the http get request
   */
  resetGraph(){
    this.FilterDate = "";
    this.chart.data.labels = this.graphData.timestamp;
    this.chart.data.datasets[0].data = this.graphData.energy;
    this.chart.data.datasets[1].data = this.graphData.event_names;
    this.chart.update();
  }

  submitEventNames(){
    this.http.post(`${this.url}/api/submit_event_names`, this.events).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
      this.response = response;
      if (this.response == 'success') {
        this.eventsRegistered = true;
      }
      this.createChart();
    });
  }

  private handleError(error: any) {
    console.error(error);
    return throwError(() => new Error('Server error'));

  }

}
