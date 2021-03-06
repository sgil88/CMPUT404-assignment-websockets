#!/usr/bin/env python
# coding: utf-8
# Copyright (c) 2013-2014 Abram Hindle, Bronte Lee, Stephanie Gil
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import flask
from flask import Flask, request, redirect, url_for
from flask_sockets import Sockets
import gevent
from gevent import queue
import time
import json
import os

app = Flask(__name__)
sockets = Sockets(app)
app.debug = True

class World:
    def __init__(self):
        self.clear()
        # we've got listeners now!
        self.listeners = list()
        
    def add_set_listener(self, listener):
        self.listeners.append( listener )

    def rm_set_listener(self, listener):
        self.listeners.remove( listener )

    def update(self, entity, key, value):
        entry = self.space.get(entity,dict())
        entry[key] = value
        self.space[entity] = entry
        self.update_listeners( entity )

    def set(self, entity, data):
        self.space[entity] = data
        self.update_listeners( entity )

    def update_listeners(self, entity):
        '''update the set listeners'''
        for listener in self.listeners:
            listener(entity, self.get(entity))

    def clear(self):
        self.space = dict()

    def get(self, entity):
        return self.space.get(entity,dict())
    
    def world(self):
        return self.space

myWorld = World()        

def set_listener( entity, data ):
    ''' do something with the update ! '''
    set_listener.entities.put({entity:data})

# how to create static variables in python found at:
# http://stackoverflow.com/questions/279561/what-is-the-python-equivalent-of-static-variables-inside-a-function
listener = set_listener
listener.entities = queue.Queue()
myWorld.add_set_listener( listener)

@app.route('/')
def hello():
    '''Return something coherent here.. perhaps redirect to /static/index.html '''
    return redirect(url_for('static', filename='index.html'))

# modified the code from: https://github.com/abramhindle/WebSocketsExamples
def read_ws(ws):
    '''A greenlet function that reads from the websocket and updates the world'''
    # XXX: TODO IMPLEMENT ME
    try:
        while True:
            entity = ws.receive()
            print "WS RECV:%s" % entity
            if entity is not None :
                packet = json.loads(entity)
                new_entity = packet.keys()[0]
                if new_entity == "world":
                    ws.send(json.dumps({"world":myWorld.world()}))
                else:
                    myWorld.set(new_entity, packet[new_entity])
            else:
                socket_list.remove(ws)
                break
    except:
        '''Done'''

socket_list = list()

# modified the code from: https://github.com/abramhindle/WebSocketsExamples
@sockets.route('/subscribe')
def subscribe_socket(ws):
    '''Fufill the websocket URL of /subscribe, every update notify the
       websocket and read updates from the websocket '''
    # XXX: TODO IMPLEMENT ME
    socket_list.append(ws)
    g = gevent.spawn(read_ws, ws)
    try:
        while True:
            entity = listener.entities.get()
            print "Sending..." + str(entity)
            for sock in socket_list:
                sock.send(json.dumps(entity))
    except Exception as e:
        print "WS Error %s" % e
    finally:
        socket_list.remove(ws)
        gevent.kill(g)

def flask_post_json():
    '''Ah the joys of frameworks! They do so much work for you
       that they get in the way of sane operation!'''
    if (request.json != None):
        return request.json
    elif (request.data != None and request.data != ''):
        return json.loads(request.data)
    else:
        return json.loads(request.form.keys()[0])

@app.route("/entity/<entity>", methods=['POST','PUT'])
def update(entity):
    '''update the entities via this interface'''
    new_entity = flask_post_json()

    # Update The World: Add the new entity's keys (such as x & y coords)
    for key in new_entity.keys():
        myWorld.update(entity, key, new_entity[key]);

    # Convert to new entity to JSON and return it
    return json.dumps( myWorld.get(entity) )

@app.route("/world", methods=['POST','GET'])    
def world():
    global myWorld
    '''you should probably return the world here'''
    return json.dumps( myWorld.world())

@app.route("/entity/<entity>")    
def get_entity(entity):
    global myWorld
    '''This is the GET version of the entity interface, return a representation of the entity'''
    return json.dumps( myWorld.get(entity) )


@app.route("/clear", methods=['POST','GET'])
def clear():
    global myWorld
    '''Clear the world out!'''
    myWorld.clear()
    return json.dumps( myWorld.world() )


if __name__ == "__main__":
    ''' This doesn't work well anymore:
        pip install gunicorn
        and run
        gunicorn -k flask_sockets.worker sockets:app
    '''
    app.run()
