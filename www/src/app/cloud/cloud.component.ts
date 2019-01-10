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

  public selectedNode: Object;
  public depthStat: Object = {};
  public depthMax: Object = {};
  public Object = Object;

  private network: Network;
  private edges: DataSet<Object> = new DataSet();
  private nodes: DataSet<Object> = new DataSet();
  networkOptions = {
    nodes: {
      borderWidth: 1,
      borderWidthSelected: 2,
      size: 100,
      font : {
        size : 20,
        color : '#000000'
      },

    },

    layout: {
      hierarchical: {
        direction: "UD",
        sortMethod: "directed",
        levelSeparation: 200,
      }
    },
    interaction: {
      dragNodes :true
    },
    physics: {
      enabled: true,

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
      let service_id  = service.remote_endpoint.id;
      let service_name  = service.remote_endpoint.host + ":" + service.remote_endpoint.port;
      let service_pid = service.remote_endpoint.pid;
      let service_depth = service.remote_endpoint.depth;

      /*  +
          "\n" + service_name +
          "\n" + service_pid +
          "\nIn: " + service.remote_endpoint.diagnosis.throughput_in +
          "\nOut: " + service.remote_endpoint.diagnosis.throughput_out,*/
      nodes.push({
        id: service_id,
        label: service_type + "\n" + service_name,
        group: service_depth,
        metadata: service
      });

      let remotes = service.remote_endpoint.remotes;
      remotes.forEach(remote => {
        let remote_id = remote.remote_endpoint.id;
        let remote_name = remote.remote_endpoint.host + ":" + remote.remote_endpoint.port;
        edges.push({
          from: service_id, to: remote_id
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

  getNode(nodeID){
    return this.nodes["_data"][nodeID];
  }

  selectNode(nodeID){
    this.nodeClick({
      nodes: [nodeID]
    });



    this.network.selectNodes([nodeID])
  }

  nodeClick(properties){
    let ids = properties.nodes;

    let nodeID = ids[0];

    this.selectedNode = this.nodes["_data"][nodeID];

  }

  ngOnInit() {
    this.network = new Network(this.visElement.nativeElement, {
      nodes: this.nodes,
      edges: this.edges
    },this.networkOptions);

    /* When node is clicked. */
    this.network.on( 'click', this.nodeClick.bind(this));

    /*this.WSService.on("*").subscribe(x => {
      //console.log(x)
    });*/

    this.WSService.on("tree").subscribe(x => {
      let tree = x.services;

      let data = this.treeToNetwork(tree);

      let changed = false;


      data.nodes.forEach(updated_node => {

        if(updated_node.id in this.nodes["_data"]){
          this.nodes["_data"][updated_node.id]["metadata"] = updated_node.metadata;

        }else{
          this.nodes.add(updated_node);
          changed = true;
        }

        // Create depth level if not exists
        if(!(updated_node.metadata.remote_endpoint.depth in this.depthStat)){
          this.depthStat[updated_node.metadata.remote_endpoint.depth] = {}
        }

        // Update inbound and outbound for node
        this.depthStat[updated_node.metadata.remote_endpoint.depth][updated_node.id] = {
          inbound: updated_node.metadata.remote_endpoint.diagnosis.throughput_in,
          outbound: updated_node.metadata.remote_endpoint.diagnosis.throughput_out
        };

        if(!(updated_node.metadata.remote_endpoint.depth in this.depthMax)){
          this.depthMax[updated_node.metadata.remote_endpoint.depth] = {
            inbound: 0,
            outbound: 0,
          }
        }

        this.depthMax[updated_node.metadata.remote_endpoint.depth] = {
          inbound: Math.max(
            this.depthStat[updated_node.metadata.remote_endpoint.depth][updated_node.id].inbound,
            this.depthMax[updated_node.metadata.remote_endpoint.depth].inbound
          ),
          outbound: Math.max(
            this.depthStat[updated_node.metadata.remote_endpoint.depth][updated_node.id].outbound,
            this.depthMax[updated_node.metadata.remote_endpoint.depth].outbound
          ),
        }

      });

      data.edges.forEach(updated_edge => {
          this.edges.update(updated_edge)
      });

      if(changed) {
        this.network.stabilize();
        this.network.redraw();
      }




    });



  }

}
