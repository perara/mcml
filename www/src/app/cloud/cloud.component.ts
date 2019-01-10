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

    tree.forEach(service => {
      let service_type = service.service;
      let service_name  = service.remote_endpoint.host + ":" + service.remote_endpoint.port;
      let service_pid = service.remote_endpoint.pid;
      let service_depth = service.remote_endpoint.depth;

      nodes.push({
        id: service_name,
        label: service_type +
          "\n" + service_name +
          "\n" + service_pid +
          "\nIn: " + service.remote_endpoint.diagnosis.throughput_in +
          "\nOut: " + service.remote_endpoint.diagnosis.throughput_out,
          group: service_depth
      });

      let remotes = service.remote_endpoint.remotes;
      remotes.forEach(remote => {
        console.log(remote)
        let remote_name = remote.remote_endpoint.host + ":" + remote.remote_endpoint.port;
        edges.push({
          from: service_name, to: remote_name
        })
      })
    });

    /*
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


    }*/

    console.log(nodes);
    console.log(edges)

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
