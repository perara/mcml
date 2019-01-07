import { Injectable } from '@angular/core';
import { webSocket } from 'rxjs/webSocket'

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private ws;

  constructor() {
    this.ws = webSocket('ws://' + window.location.host + "/ws");

  }

  on(channel) {
    return this.ws.multiplex(
      () => new Object({
        type: "subscribe",
        payload: {
          channel: channel
        }
      }),
      () => new Object({
        type: "unsubscribe",
        payload: {
          channel: channel
        }
      }),
      message => message.channels.includes(channel) || channel === '*'
      );
  }
}

