import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import {SetupComponent} from "./setup/setup.component";


const routes: Routes = [
  { path: 'setup',
    component: SetupComponent
  },
  {
    path: "",
    loadChildren: () => import('./devices/devices.module').then(m => m.DevicesModule)
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
