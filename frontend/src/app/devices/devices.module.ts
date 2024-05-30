import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DevicesRoutingModule } from './devices-routing.module';
import { DeviceComponent } from './device/device.component';
import { DeviceManagerComponent } from './device-manager/device-manager.component';
import {SidebarComponent} from "./sidebar/sidebar.component";
import {FormsModule} from "@angular/forms";
import {HomeComponent} from "./home/home.component";
import { ToolbarComponent } from './toolbar/toolbar.component';


@NgModule({
  declarations: [
    DeviceComponent,
    DeviceManagerComponent,
    SidebarComponent,
    HomeComponent,
    ToolbarComponent
  ],
    imports: [
        CommonModule,
        DevicesRoutingModule,
        FormsModule
    ]
})
export class DevicesModule { }
