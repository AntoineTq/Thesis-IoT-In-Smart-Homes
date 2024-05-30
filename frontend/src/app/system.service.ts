import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class SystemService {

  private url = 'http://127.0.0.1:5000'
  constructor() { }

  getUrl(){
    return this.url;
  }
}
