import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import {DeviceManagerComponent} from "./device-manager/device-manager.component";
import {DeviceComponent} from "./device/device.component";
import {HomeComponent} from "./home/home.component";

const routes: Routes = [
  {
    path: '',
    component: DeviceManagerComponent,
    children: [
      {
        path: ':device',
        component: DeviceComponent
      },
      {
        path: '',
        component: HomeComponent
      }
    ]
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class DevicesRoutingModule { }
