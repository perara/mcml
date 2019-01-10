import {Component, ElementRef, OnInit, ViewChild} from '@angular/core';
import {WebsocketService} from "../websocket.service";
import {Network, DataSet} from 'vis';

@Component({
  selector: 'app-cloud',
  templateUrl: './cloud.component.html',
  styleUrls: ['./cloud.component.sass']
})
export class CloudComponent implements OnInit {
  @ViewChild('visElement') visElement: ElementRef;
  private network: Network;
  private edges: DataSet<Object> = new DataSet();
  private nodes: DataSet<Object> = new DataSet();
  networkOptions = {
    layout: {
      hierarchical: {
        direction: "UD",
        sortMethod: "directed",
        nodeSpacing: 425,
        blockShifting: false,
        edgeMinimization: false,
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

    return {
      nodes: nodes,
      edges: edges
    }
  }

  constructor(public WSService: WebsocketService) {

  }

  ngOnInit() {
    this.network = new Network(this.visElement.nativeElement, {
      nodes: this.nodes,
      edges: this.edges
    },this.networkOptions);


    this.WSService.on("*").subscribe(x => {
      console.log(x)
    });

    this.WSService.on("tree").subscribe(x => {
      let tree = x.services;

      let data = this.treeToNetwork(tree);

      this.nodes.clear();
      this.nodes.clear();

      this.nodes.add(data.nodes);
      this.edges.add(data.edges)
      this.network.stabilize()

    });



  }

}
