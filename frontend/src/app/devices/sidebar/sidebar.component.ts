import { Component } from '@angular/core';
import {catchError, throwError} from "rxjs";
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {SystemService} from "../../system.service";

@Component({
  selector: 'app-sidebar',
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.css'
})
export class SidebarComponent {
  names:string[] = [];
  url:string = "";
  constructor(private http: HttpClient) {}

  ngOnInit(){
    this.url = new SystemService().getUrl();
    this.http.get<string[]>(`${this.url}/api/get_device_list`).pipe(
      catchError(this.handleError.bind(this))).subscribe(response => {
        this.names = response;
    });
  }
  private handleError(error: any) {
    console.error(error);
    return throwError(() => new Error('Server error'));

  }

}
