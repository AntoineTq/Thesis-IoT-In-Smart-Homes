import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import {HttpClientModule} from "@angular/common/http";
import { SetupComponent } from './setup/setup.component';
import { HeaderComponent } from './header/header.component';
import {FormsModule} from "@angular/forms";
import {SystemService} from "./system.service";

@NgModule({
  declarations: [
    AppComponent,
    SetupComponent,
    HeaderComponent,
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    HttpClientModule,
    FormsModule
  ],
  providers: [SystemService],
  bootstrap: [AppComponent]
})
export class AppModule { }
