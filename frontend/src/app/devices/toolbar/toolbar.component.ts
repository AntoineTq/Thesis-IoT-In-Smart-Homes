import { Component } from '@angular/core';
import {SystemService} from "../../system.service";
import {HttpClient} from "@angular/common/http";

@Component({
  selector: 'app-toolbar',
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.css'
})
export class ToolbarComponent {
  url:string = "";

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.url = new SystemService().getUrl();
  }

  clickIdle(){
    console.log("Clicked idle")
  }
  clickRoutine(){
    console.log("Clicked routine")
  }

  clickEvent(){
    console.log("Clicked event")
  }

}
