# -*- coding: utf-8 -*-
import argparse
import random
import os
import json

import cherrypy

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage

class LocationWebSocketHandler(WebSocket):
    def __init__(self, *args, **kwargs):
        super(LocationWebSocketHandler, self).__init__(*args, **kwargs)

    def send_current_location(self, currentLat, currentLon):
        location_data = {
            "type" : "current_location",
            "lat" : float(currentLat),
            "lon" : float(currentLon)
        }
        json_data = json.dumps(location_data)
        self.send(json_data)

    def send_error_message(self, message):
        message_data = {
            "type" : "error_message",
            "message" : message
        }
        json_data = json.dumps(message_data)
        self.send(json_data)

    def received_message(self, m):
        pass
        #cherrypy.engine.publish('websocket-broadcast', m)

    def closed(self, code, reason="A client left the room without a proper explanation."):
        pass
        #cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

class Root(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.scheme = "ws"
        self.currentLocationLat = None;
        self.currentLocationLon = None;
        self.current_location_listeners = []

    @cherrypy.expose
    def setLocation(self, lat, lon):
        self.currentLocationLat = lat
        self.currentLocationLon = lon
        for l in self.current_location_listeners:
            try:
                l.send_current_location(lat, lon)
            except AttributeError:
                self.current_location_listeners.remove(l)
        return "Virkar? %s, %s"%(lat, lon)

    @cherrypy.expose
    def index(self):
        return """<html>
    <head>
    <style type="text/css">
      html, body, #map-canvas { height: 100%%; margin: 0; padding: 0;}
    </style>
    <script type="text/javascript"
      src="https://maps.googleapis.com/maps/api/js?key=AIzaSyDn11yH1h4kJfnN4BQU_Ok0g3lbT9si_Tg">
    </script>
      <script type='application/javascript' src='https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js'></script>
      <script type='application/javascript'>

        var mapInitialized = false;
        var map = null;
        var myLocationMarker = null;
        var infoWindow = null;

        $(document).ready(function() {

          websocket = '%(scheme)s://%(host)s:%(port)s/ws';
          if (window.WebSocket) {
            ws = new WebSocket(websocket);
          }
          else if (window.MozWebSocket) {
            ws = MozWebSocket(websocket);
          }
          else {
            console.log('WebSocket Not Supported');
            return;
          }

          ws.onmessage = function (evt) {
             jsonObject = JSON.parse(evt.data)

            if (jsonObject.type == "error_message")
            {
                infoWindow = new google.maps.InfoWindow({
                    content: jsonObject.message
                });
                infoWindow.open(map, routeEndpointMarker);
                return;
            }

             if (jsonObject.type == "current_location" &&!mapInitialized)
             {
                 var mapOptions = {
                    center: { lat: jsonObject.lat, lng: jsonObject.lon},
                    zoom: 15
                };
            map = new google.maps.Map(document.getElementById('map-canvas'),
            mapOptions);
            marker = new google.maps.Marker({
                position: { lat: jsonObject.lat, lng: jsonObject.lon},
                icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                map: map
            });

            
            mapInitialized = true;
             }

            if (jsonObject.type == "current_location")
            {
                marker.setPosition(new google.maps.LatLng(jsonObject.lat, jsonObject.lon));
            }
          };


          ws.onopen = function() {
          };

        });
      </script>
    </head>
    <body>

    <div id="map-canvas">Bíð eftir staðsetningu...</div>

    </body>
    </html>
    """ % {'host': self.host, 'port': self.port, 'scheme': self.scheme}

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))
        self.current_location_listeners.append(cherrypy.request.ws_handler)

if __name__ == '__main__':
    import logging
    from ws4py import configure_logger
    configure_logger(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Location CherryPy Server')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('-p', '--port', default=9000, type=int)
    args = parser.parse_args()

    cherrypy.config.update({'server.socket_host': args.host,
                            'server.socket_port': args.port,
                            'tools.staticdir.root': os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))})

    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    cherrypy.quickstart(Root(args.host, args.port), '', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': LocationWebSocketHandler
            },
        '/js': {
              'tools.staticdir.on': True,
              'tools.staticdir.dir': 'js'
            }
        }
    )
