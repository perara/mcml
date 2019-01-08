import {Component, ElementRef, OnInit, ViewChild} from '@angular/core';
import {WebsocketService} from "../websocket.service";
import {Network, Data} from 'vis';

@Component({
  selector: 'app-cloud',
  templateUrl: './cloud.component.html',
  styleUrls: ['./cloud.component.sass']
})
export class CloudComponent implements OnInit {
  @ViewChild('visElement') visElement: ElementRef;
  private network: Network;
  networkOptions = {
    layout: {
      hierarchical: {
        direction: "UD",
        sortMethod: "directed"
      }
    },
    interaction: {
      dragNodes :true
    },
    physics: {
      enabled: true
    },
    configure: {
      filter: function (option, path) {
        if (path.indexOf('hierarchical') !== -1) {
          return false;
        }
        return false;
      },
      showButton:false
    }
  };

  treeToNetwork(tree){
    let nodes = [];
    let edges = [];
    for(let service_type in tree){
      let services = tree[service_type]

      for(let service_name in services){
        let service = services[service_name];

        nodes.push({
          id: service_name,
          label: service_type + "\n" + service_name + "\n" + service.pid,
          group: service.depth
        });

        for(let edge_name in service.remotes){
          edges.push({
            from: service_name, to: edge_name
          })
        }

      }


    }

    return {
      nodes: nodes,
      edges: edges
    }
  }

  constructor(public WSService: WebsocketService) {



    WSService.on("*").subscribe(x => {
      console.log(x)
    });

    WSService.on("tree").subscribe(x => {
      let tree = x.services;


      this.network = new Network(this.visElement.nativeElement, this.treeToNetwork(tree), this.networkOptions);

      console.log(this.network)
    });



  }

  ngOnInit() {

  }

}
