import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import {ProjectComponent} from "./project/project.component";
import {NotfoundComponent} from "./notfound/notfound.component";
import {CloudComponent} from "./cloud/cloud.component";

const routes: Routes = [
  { path: '', redirectTo: '/cloud', pathMatch: 'full' },
  { path: 'project', component: ProjectComponent },
  { path: 'cloud', component: CloudComponent },
  { path: '**', component: NotfoundComponent }

];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
