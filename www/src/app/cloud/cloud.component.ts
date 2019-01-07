import { Component, OnInit } from '@angular/core';
import {WebsocketService} from "../websocket.service";

@Component({
  selector: 'app-cloud',
  templateUrl: './cloud.component.html',
  styleUrls: ['./cloud.component.sass']
})
export class CloudComponent implements OnInit {

  constructor(public WSService: WebsocketService) {

    WSService.on("*").subscribe(x => {
      console.log(x)
    });

    WSService.on("tree").subscribe(x => {
      console.log(x)
    });



  }

  ngOnInit() {
  }

}
