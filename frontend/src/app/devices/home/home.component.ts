import { Component } from '@angular/core';
import {SystemService} from "../../system.service";
import {HttpClient} from "@angular/common/http";

@Component({
  selector: 'app-home',
  templateUrl: './home.component.html',
  styleUrl: './home.component.css'
})
export class HomeComponent {
  url:string = "";
  capture_status = "";
  constructor(private http: HttpClient) {
  }
  ngOnInit() {
    this.url = new SystemService().getUrl();
    this.http.get(`${this.url}/api/jobStatus?job=capture`).subscribe(response => {
      if (response == true) {
        this.capture_status = "routine capture is running"
      }
      else{
        this.capture_status = "routine capture is not running"
      }
    });
  }

}
