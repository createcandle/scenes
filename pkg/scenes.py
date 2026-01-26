import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')) 

import json
import time
import requests  # noqa
import threading
from gateway_addon import Database, Adapter, Device, Property, APIHandler, APIResponse

_TIMEOUT = 3

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))




class ScenesAdapter(Adapter):
    """Adapter for addon """

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        
        self.ready = False # set this to True once the init process is complete.
        self.addon_name = 'scenes'
        
        
        self.name = self.__class__.__name__ # TODO: is this needed?
        Adapter.__init__(self, self.addon_name, self.addon_name, verbose=verbose)

        self.running = True

        # set up some variables
        self.DEBUG = False
        
        self.api_server = 'http://127.0.0.1:8080' # Where can the Gateway API be found? this will be replaced with https://127.0.0.1:4443 later on, if a test call to the api fails.
        

        self.run_last_scene_at_addon_startup = False
    
        
        # Create some path strings. These point to locations on the drive.
        self.addon_path = os.path.join(self.user_profile['addonsDir'], self.addon_name) # addonsDir points to the directory that holds all the addons (/home/pi/.webthings/addons).
        self.data_path = os.path.join(self.user_profile['dataDir'], self.addon_name)
        self.persistence_file_path = os.path.join(self.data_path, 'persistence.json') # dataDir points to the directory where the addons are allowed to store their data (/home/pi/.webthings/data)
        
        # Create the data directory if it doesn't exist yet
        if not os.path.isdir(self.data_path):
            print("making missing data directory")
            os.mkdir(self.data_path)
        			
			
        self.persistent_data = {}
            
        # 1. Get persistent data
        try:
            with open(self.persistence_file_path) as f:
                self.persistent_data = json.load(f)
                if self.DEBUG:
                    print('self.persistent_data was loaded from file: ' + str(self.persistent_data))
                    
        except:
            if self.DEBUG:
                print("Could not load persistent data (if you just installed the add-on then this is normal)")

        # 2. now that we have the persistent data (except on the first run), we allow the basic settings to override some of the values, if they are set.

        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config: " + str(ex))


        #self.DEBUG = True

        # 3. Now we check if all the values that should exist actually do

        self.should_save_persistent_data = False
        
        if 'state' not in self.persistent_data:
            self.persistent_data['state'] = False
            self.should_save_persistent_data = True

        if 'slider' not in self.persistent_data:
            self.persistent_data['slider'] = 0
            self.should_save_persistent_data = True
            
        if 'dropdown' not in self.persistent_data:
            self.persistent_data['dropdown'] = 'Auto'
            self.should_save_persistent_data = True

        if 'scenes' not in self.persistent_data:
            self.persistent_data['scenes'] = {}
            self.should_save_persistent_data = True

        if 'current_scene' not in self.persistent_data:
            self.persistent_data['current_scene'] = "no name yet"
            self.should_save_persistent_data = True

        if 'timers' not in self.persistent_data:
            self.persistent_data['timers'] = {}
            self.should_save_persistent_data = True

        if 'jwt' not in self.persistent_data:
            self.persistent_data['jwt'] = ""
            self.should_save_persistent_data = True


        # migrate old data to newer data scheme for timers
        scene_names = list(self.persistent_data['scenes'].keys())
        if len(scene_names) > 0:
            for scene_name in scene_names:
                #print("checking if scene needs update: " + str(scene_name))
                if not 'name' in self.persistent_data['scenes'][scene_name]:
                    #print("updating scene to new scheme: " + str(scene_name))
                    self.persistent_data['scenes'][scene_name] = {'name':scene_name,'things':self.persistent_data['scenes'][scene_name]}
                    self.should_save_persistent_data = True

        
        
        try:
            if self.DEBUG:
                print("Gateway version: " + str(self.gateway_version))
            
            # prune old timers from persistent data
            timer_scene_ids = list(self.persistent_data['timers'].keys())
        
            for timer_scene_id in timer_scene_ids:
                if self.persistent_data['timers'][timer_scene_id]['time'] < time.time():
                    if self.DEBUG:
                        print("scenes init: pruning old scene timer: " + str(self.persistent_data['timers'][timer_scene_id]))
                    del self.persistent_data['timers'][timer_scene_id]
            
        except Exception as ex:
            print("scenes init: caught error pruning old timers: " + str(ex))
            

        # Start the API handler. This will allow the user interface to connect
        try:
            if self.DEBUG:
                print("starting api handler")
            self.api_handler = ScenesAPIHandler(self, verbose=True)
            if self.DEBUG:
                print("Adapter: API handler initiated")
        except Exception as e:
            if self.DEBUG:
                print("Error, failed to start API handler: " + str(e))


        # Create the thing
        try:
            # Create the device object
            scenes_device = ScenesDevice(self)
            
            # Tell the controller about the new device that was created. This will add the new device to self.devices too
            self.handle_device_added(scenes_device)
            
            if self.DEBUG:
                print("scenes_device created")
                
            # You can set the device to connected or disconnected. If it's in disconnected state the thing will visually be a bit more transparent.
            self.devices['scenes-thing'].connected = True
            self.devices['scenes-thing'].connected_notify(True)

        except Exception as ex:
            if self.DEBUG:
                print("Could not create scenes-thing: " + str(ex))
        
        if self.DEBUG:
            print("Starting the internal clock")
        try:
            t = threading.Thread(target=self.clock)
            t.daemon = True
            t.start()
        except:
            print("Error starting the clock thread")
        
        # The addon is now ready
        self.ready = True 

        if self.run_last_scene_at_addon_startup:
            self.set_scene(self.persistent_data['current_scene'])



    def add_from_config(self):
        """ This retrieves the addon settings from the controller """
        try:
            database = Database(self.addon_name)
            if not database.open():
                print("Error. Could not open settings database")
                return

            config = database.load_config()
            database.close()

        except:
            print("Error. Failed to open settings database. Closing proxy.")
            self.close_proxy() # this will purposefully "crash" the addon. It will then we restarted in two seconds, in the hope that the database is no longer locked by then
            return
            
        try:
            if not config:
                print("Warning, no config.")
                return
            

            # Let's start by setting the user's preference about debugging, so we can use that preference to output extra debugging information
            if 'Debugging' in config:
                self.DEBUG = bool(config['Debugging'])
                if self.DEBUG:
                    print("Debugging enabled")

            if self.DEBUG:
                print("config: " + str(config)) # Print the entire config data
                
            if 'Set last selected scene when addon starts' in config:
                self.run_last_scene_at_addon_startup = bool(config['Set last selected scene when addon starts']) # sometime you may want the addon settings to override the persistent value
                if self.DEBUG:
                    print("Set last selected scene when addon starts preference was in config: " + str(self.run_last_scene_at_addon_startup))

            

        except Exception as ex:
            print("Error in add_from_config: " + str(ex))



    #
    #  CLOCK
    #

    def clock(self):
        """ Runs every second """
        
        while self.running:
            
            time.sleep(1)
            
            try:
                timer_scene_ids = list(self.persistent_data['timers'].keys())
                
                for timer_scene_id in timer_scene_ids:
                    #if self.DEBUG:
                    #    print("checking timer_scene_id: " + str(timer_scene_id))
                        
                    if not 'start_time' in self.persistent_data['timers'][timer_scene_id]:
                         del self.persistent_data['timers'][timer_scene_id]
                         
                    if self.persistent_data['timers'][timer_scene_id]['start_time'] < time.time() - 5:
                        if self.DEBUG:
                            print("scenes clock: deleting a timer that should have been acted on over 5 seconds ago: " + str(self.persistent_data['timers'][timer_scene_id]))
                        del self.persistent_data['timers'][timer_scene_id]
                         
                    elif self.persistent_data['timers'][timer_scene_id]['start_time'] < time.time():
                        if self.DEBUG:
                            print("scenes clock: found a timer that should be run now: " + str(self.persistent_data['timers'][timer_scene_id]))
                        
                        del self.persistent_data['timers'][timer_scene_id]
                        self.set_scene(timer_scene_id)
            
            except Exception as ex:
                if self.DEBUG:
                    print("clock: caught error looping over timers: " + str(ex))
            
            if self.should_save_persistent_data:
                if self.DEBUG:
                    print("clock: saving to persistent data")
                self.should_save_persistent_data = False
                self.save_persistent_data()
            
        if self.DEBUG:
            print("scenes clock: beyond while loop (clock stopped)")




    #
    #  CHANGING THE PROPERTIES
    #
        
    def set_scene(self,scene_id):
        try:
            if self.DEBUG:
                print("in set_scene with scene_id: " + str(scene_id))
            if scene_id in self.persistent_data['scenes']:
                
                # saves the new state in the persistent data file, so that the addon can restore the correct state if it restarts
                if self.persistent_data['current_scene'] != scene_id:
                    self.persistent_data['current_scene'] = scene_id
                    self.should_save_persistent_data = True
        
                # A cool feature: you can create popups in the interface this way:
                self.send_pairing_prompt("Scene: " + str(self.persistent_data['scenes'][scene_id]['name']))
        
                self.actually_set_scene(self.persistent_data['scenes'][scene_id]['things'])
                
                try:
                    self.devices['scenes-thing'].properties['scenes'].update( self.persistent_data['scenes'][scene_id]['name'] )
                except Exception as ex:
                    if self.DEBUG:
                        print("error setting dropdown value on thing: " + str(ex))
                
                if 'timer' in self.persistent_data['scenes'][scene_id] and self.persistent_data['scenes'][scene_id]['timer'] != None and 'next_scene_id' in self.persistent_data['scenes'][scene_id]['timer']:
                    now_time = time.time()
                    scene_duration = int(self.persistent_data['scenes'][scene_id]['timer']['seconds'])
                    start_time = now_time + scene_duration
                    next_scene_id = self.persistent_data['scenes'][scene_id]['timer']['next_scene_id']
                    
                    self.persistent_data['timers'][next_scene_id] = {'scene_id':next_scene_id, 'name': self.persistent_data['scenes'][scene_id]['name'], 'parent_scene_id':scene_id ,'start_time':start_time, 'creation_time':now_time}
                    self.should_save_persistent_data = True
                    
            else:
                print("Error, that scene does not exist")
        except Exception as ex:
            if self.DEBUG:
                print("error in set_scene: " + str(ex))


    def actually_set_scene(self,things_dictionary):
        if self.DEBUG:
            print("in actually_set_scene. things_dictionary: " + str(things_dictionary))
        try:
            for thing_id in things_dictionary:
                #print("set_scene: thing_id: " + str(thing_id))
            
                for property_id in things_dictionary[thing_id]:
                    property_value = things_dictionary[thing_id][property_id]
            
                    api_path = '/things/' + str(thing_id) + '/properties/' + str(property_id)
                    
                    if self.DEBUG:
                        print("\nthing_id to set: " + str(thing_id))
                        print("property_id to set: " + str(property_id))
                        print("property_value to set: " + str(property_value))
                
                    if property_value == 'true':
                        property_value = True
                    elif property_value == 'false':
                        property_value = False
                    elif property_value == 'null' or property_value == '':
                        property_value = None
                    elif property_value.isnumeric():
                        property_value = get_int_or_float(property_value)
                    
                    json_dict = {property_id:property_value}
                
                    if self.DEBUG:
                        print("json_dict: " + str(json_dict) + " will be sent to API endpoint: " + str(api_path))
            
                    try:
                        api_result = self.api_put(api_path, json_dict)
                    except Exception as ex:
                        print("error doing api_put: " + str(ex))
                        
        except Exception as ex:
            if self.DEBUG:
                print("error in actually_set_scene: " + str(ex))
        
        




    #
    # The methods below are called by the controller
    #

    def start_pairing(self, timeout):
        """
        Start the pairing process. This starts when the user presses the + button on the things page.
        
        timeout -- Timeout in seconds at which to quit pairing
        """
        #print("in start_pairing. Timeout: " + str(timeout))
        
        
    def cancel_pairing(self):
        """ Happens when the user cancels the pairing process."""
        # This happens when the user cancels the pairing process, or if it times out.
        #print("in cancel_pairing")
        

    def unload(self):
        """ Happens when the user addon / system is shut down."""
        if self.DEBUG:
            print("in unload. Bye!")
        
        self.running = False
        
        self.devices['scenes-thing'].connected_notify(False)
        



    def remove_thing(self, device_id):
        """ Happens when the user deletes the thing."""
        try:
            obj = self.get_device(device_id)
            self.handle_device_removed(obj)
            if self.DEBUG:
                print("User removed thing")
        except:
            print("Could not remove thing from devices")




    #
    # This saves the persistent_data dictionary to a file
    #
    
    def save_persistent_data(self):
        if self.DEBUG:
            print("Saving to persistence data store")

        try:
            if not os.path.isfile(self.persistence_file_path):
                open(self.persistence_file_path, 'a').close()
                if self.DEBUG:
                    print("Created an empty persistence file")
            else:
                if self.DEBUG:
                    print("Persistence file existed. Will try to save to it.")

            with open(self.persistence_file_path) as f:
                if self.DEBUG:
                    print("saving: " + str(self.persistent_data))
                try:
                    with open( self.persistence_file_path, 'w' ) as f:
                        json.dump( self.persistent_data, f, indent=4)
                except Exception as ex:
                    print("Error saving to persistence file: " + str(ex))
                return True

        except Exception as ex:
            if self.DEBUG:
                print("Error: could not store data in persistent store: " + str(ex) )
        
        return False



    def api_put(self, api_path, json_dict):
        """Sends data to the Candle Controller / WebThings Gateway API."""
        
        try:
            
            if self.DEBUG:
                print("PUT > api_path = " + str(api_path))
                print("PUT > json dict = " + str(json_dict))
                print("PUT > self.api_server = " + str(self.api_server))
                print("self.gateway_version: " + str(self.gateway_version))
        
            if len(self.persistent_data['jwt']) < 10:
                if self.DEBUG:
                    print("Error: jwt token is too short")
                return
        
            simplified = False
            property_was = None
            if self.gateway_version != "1.0.0":
        
                if 'things/' in api_path and '/properties/' in api_path:
                    if self.DEBUG:
                        print("PUT: properties was in api path: " + str(api_path))
                    for bla in json_dict:
                        property_was = bla
                        simpler_value = json_dict[bla]
                        json_dict = simpler_value
                    #simpler_value = [elem[0] for elem in json_dict.values()]
                    if self.DEBUG:
                        print("simpler 1.1.0 value to put: " + str(simpler_value))
                    simplified = True
                    #likely_property_name = api_path.rsplit('/', 1)[-1]
                    #to_return = {}
            
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': 'Bearer {}'.format(self.persistent_data['jwt']),
            }
            
            
            try:
                if self.DEBUG:
                    print("sending this json_dict: " + str(json_dict))
                    
                r = requests.put(
                    self.api_server + api_path,
                    json=json_dict,
                    headers=headers,
                    verify=False,
                    timeout=2
                )
                if self.DEBUG:
                    print("API PUT: " + str(r.status_code) + ", " + str(r.reason))
                    print("PUT returned r.text: " + str(r.text))

                if r.status_code == 204:
                    if simplified:
                        return_value = {property_was:json_dict} #simpler_value # json.loads('{"' + property_was + '":' + r.text + '}')
                    else:
                        return_value = json_dict
                
                    return_value['succes'] = True
                    return return_value
                    
                elif r.status_code == 200:
                    if simplified:
                        return_value = {property_was:json.loads(r.text)} # json.loads('{"' + property_was + '":' + r.text + '}')
                    else:
                        return_value = json.loads(r.text)
                
                    return_value['succes'] = True
                    return return_value
                    
                else:
                    if self.DEBUG:
                        print("Error communicating: " + str(r.status_code))
                    return {"error": str(r.status_code)}

            except Exception as ex:
                print("Error doing http request/loading returned json: " + str(ex))
                return {"error": 500}
            
            
        except Exception as ex:
            print("Error preparing PUT: " + str(ex))

        



#
# DEVICE
#

class ScenesDevice(Device):
    """Scenes device type."""

    def __init__(self, adapter):
        """
        Initialize the object.
        adapter -- the Adapter managing this device
        """

        Device.__init__(self, adapter, 'scenes')

        self._id = 'scenes-thing' # TODO: probably only need the first of these
        self.id = 'scenes-thing'
        self.adapter = adapter
        self.DEBUG = adapter.DEBUG

        self.name = 'Scene' # TODO: is this still used? hasn't this been replaced by title?
        self.title = 'Scene'
        self.description = 'Select which scene you want to enable'
        
        try:
            
            # Create the property with the list of scenes
            self.update_scene_property(False)

        except Exception as ex:
            if self.DEBUG:
                print("error adding properties to thing: " + str(ex))

        if self.DEBUG:
            print("thing has been created.")

    # Creates these options "on the fly"
    def update_scene_property(self, call_handle_device_added=True):
        
        scene_names = []
        scene_ids = list(self.adapter.persistent_data['scenes'].keys())
        
        for scene_id in scene_ids:
            scene_names.append(self.adapter.persistent_data['scenes'][scene_id]['name'])
        
        if self.DEBUG:
            print("update_scene_property: scene_names: " + str(scene_names))
        if len(scene_names) > 0:
            self.adapter.scene_names = scene_names
            self.properties["scenes"] = ScenesProperty(
                            self,
                            "scenes",
                            {
                                'title': "Current scene",
                                'type': 'string',
                                'enum': scene_names,
                            },
                            self.adapter.persistent_data['current_scene'])

            self.adapter.handle_device_added(self)
            self.notify_property_changed(self.properties["scenes"])
        else:
            if self.DEBUG:
                print("update_scene_property: no scenes exist yet")
    


#
# PROPERTY
#

class ScenesProperty(Property):

    def __init__(self, device, name, description, value):
        
        Property.__init__(self, device, name, description)
        
        self.device = device
        
        self.id = name
        self.name = name
        self.title = name
        self.description = description
        self.value = value
        
        # Notifies the controller that this property has a (initial) value
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        
        if self.device.adapter.DEBUG:
            print("property: initiated: " + str(self.title) + ", with value: " + str(value))


    def set_value(self, value):
        try:
            if self.device.adapter.DEBUG:
                print("property: set_value: " + str(value))
                
            if self.id == 'scenes':
                scene_ids = self.device.adapter.persistent_data['scenes'].keys()
                for scene_id in scene_ids:
                    if self.device.adapter.persistent_data['scenes'][scene_id]['name'] == str(value):
                        if self.device.adapter.DEBUG:
                            print("property: found scene_id for scene name: " + str(value) + " -> " + str(scene_id))
                        self.device.adapter.set_scene(str(scene_id))
                
        except Exception as ex:
            print("property: set_value error: " + str(ex))


    def update(self, value):
        if value != self.value:
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)






#
#  API HANDLER
#


class ScenesAPIHandler(APIHandler):
    """API handler."""

    def __init__(self, adapter, verbose=False):
        """Initialize the object."""
        
        self.adapter = adapter
        self.DEBUG = self.adapter.DEBUG

        try:
            
            APIHandler.__init__(self, self.adapter.addon_name)
            self.manager_proxy.add_api_handler(self) # tell the controller that the api handler now exists
            
        except Exception as e:
            print("Error: failed to init API handler: " + str(e))
        
        
    #
    #  HANDLE REQUEST
    #

    def handle_request(self, request):
        """
        Handle a new API request for this handler.

        request -- APIRequest object
        """
        #print("incoming API request. Method: " + str(request.method))
        #print("self.adapter.DEBUG: " + str(self.adapter.DEBUG))
        #print("self.DEBUG in api handler: " + str(self.DEBUG))
        
        try:
        
            if request.method != 'POST':
                return APIResponse(status=404) # we only accept POST requests
            
            if request.path == '/ajax':

                try:
                    
                    action = str(request.body['action']) 
                    #print("action: " + str(action))
                    
                    if self.DEBUG:
                        print("API handler is being called. Action: " + str(action))
                        print("request.body: " + str(request.body))
                    
                    
                    # INIT (AND SAVE TOKEN AGAIN)
                    # POLL
                    if action == 'init':
                        if self.DEBUG:
                            print("API: in init/poll")
                        
                        try:
                            if 'jwt' in request.body.keys():
                                if len(str(request.body['jwt'])) > 20:
                                    self.adapter.persistent_data['jwt'] = str(request.body['jwt'])
                                else:
                                    if self.DEBUG:
                                        print("API: init: token not long enough")
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error: Api: init: could not save token: " + str(ex))
                        
                        return APIResponse(
                                status=200,
                                content_type='application/json',
                                content=json.dumps({
                                      'token_length': len(self.adapter.persistent_data['jwt']),
                                      'scenes': self.adapter.persistent_data['scenes'],
                                      'timers': self.adapter.persistent_data['timers'],
                                      'debug': self.adapter.DEBUG
                                      }),
                        )
                        
                        
                    elif action == 'get_timers':
                        if self.DEBUG:
                            print("API: in get_timers")
                            
                        return APIResponse(
                                status=200,
                                content_type='application/json',
                                content=json.dumps({
                                      'timers': self.adapter.persistent_data['timers']
                                      }),
                        )
                    
                    
                        
                    # SAVE TOKEN
                    elif action == 'save_token':
                        if self.adapter.DEBUG:
                            print("API: in save_token")
                        state = False
                        
                        try:
                            if len(str(request.body['jwt'])) > 20:
                                self.adapter.persistent_data['jwt'] = str(request.body['jwt'])
                                self.adapter.save_persistent_data()
                                state = True
                            else:
                                if self.adapter.DEBUG:
                                    print("API: token not long enough")
                        except Exception as ex:
                            if self.adapter.DEBUG:
                                print("Error saving token: " + str(ex))
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state}),
                        )
                    
                    
                    
                    # SAVE SCENE
                    # The add API call append a new item to the list directly
                    elif action == 'save_scene':
                        if self.DEBUG:
                            print("API: in save_scene")
                        state = False
                        
                        try:
                            scene_id = str(request.body['scene_id'])
                            scene_settings = request.body['scene_settings']
                            
                            if self.DEBUG:
                                print("incoming scene_id: " + str(scene_id))
                                print("incoming scene_settings: " + str(scene_settings))
                            
                            self.adapter.persistent_data['scenes'][scene_id] = scene_settings #{'name':scene_name,'things':scene_settings,'timer':scene_timer}
                            #print("self.adapter.persistent_data['scenes']: " + str(self.adapter.persistent_data['scenes']))
                            
                            self.adapter.should_save_persistent_data = True
                            
                            self.adapter.devices['scenes-thing'].update_scene_property()
                            
                            state = True
                            
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error saving scene: " + str(ex))
                        
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state,
                                              'scenes': self.adapter.persistent_data['scenes'],
                                              'timers': self.adapter.persistent_data['timers'],
                                              }),
                        )
                    
                    
                    
                    # TEST SCENE
                    elif action == 'test_scene':
                        if self.DEBUG:
                            print("API: in test_scene")
                        state = False
                    
                        try:
                            scene_settings = request.body['scene_settings']
                            
                            if self.DEBUG:
                                print("incoming scene_settings: " + str(scene_settings))
                            if 'things' in scene_settings:
                        
                                self.adapter.actually_set_scene(scene_settings['things'])
                        
                                state = True
                        
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error testing: " + str(ex))
                    
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state,
                                              'scenes': self.adapter.persistent_data['scenes'],
                                              }),
                        )
                    
                    
                    
                    
                    
                    # DELETE TIMER
                    
                    elif action == 'delete_timer':
                        if self.DEBUG:
                            print("API: in delete_timer")
                        
                        state = False
                        
                        try:
                            scene_id = str(request.body['scene_id'])
                            if scene_id in self.adapter.persistent_data['timers']:
                                del self.adapter.persistent_data['timers'][scene_id]
                                self.adapter.should_save_persistent_data = True
                                state = True
                            
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error deleting: " + str(ex))
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state}),
                        )
                    
                    
                    
                    # DELETE SCENE
                    
                    elif action == 'delete':
                        if self.DEBUG:
                            print("API: in delete")
                        
                        state = False
                        
                        try:
                            scene_id = str(request.body['scene_id'])
                            if scene_id in self.adapter.persistent_data['scenes']:
                                del self.adapter.persistent_data['scenes'][scene_id]
                                self.adapter.should_save_persistent_data = True
                            
                                self.adapter.devices['scenes-thing'].update_scene_property()
                            
                                state = True
                            
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error deleting: " + str(ex))
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state}),
                        )
                        
                    
                    # PLAY
                    elif action == 'play':
                        if self.DEBUG:
                            print("API: in play")
                        
                        state = False
                        
                        try:
                            scene_id = str(request.body['scene_id'])
                            if self.DEBUG:
                                print("API: request to play: " + str(scene_id))
                            self.adapter.set_scene(scene_id)
                            state = True
                            
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error playing: " + str(ex))
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state':state, 'timers':self.adapter.persistent_data['timers']}),
                        )
                        
                    
                    else:
                        print("Error, that action is not possible")
                        return APIResponse(
                            status=404
                        )
                        
                        
                except Exception as ex:
                    if self.DEBUG:
                        print("Ajax error: " + str(ex))
                    return APIResponse(
                        status=500,
                        content_type='application/json',
                        content=json.dumps({"error":"Error in API handler"}),
                    )
                    
            else:
                if self.DEBUG:
                    print("invalid path: " + str(request.path))
                return APIResponse(status=404)
                
        except Exception as e:
            if self.DEBUG:
                print("Failed to handle UX extension API request: " + str(e))
            return APIResponse(
                status=500,
                content_type='application/json',
                content=json.dumps({"error":"General API error"}),
            )





#
#  SMALL HELPER FUNCTIONS
#

def get_int_or_float(v):
    number_as_float = float(v)
    number_as_int = int(number_as_float)
    #print("number_as_float=" + str(number_as_float))
    #print("number_as_int=" + str(number_as_int))
    
    if round(number_as_float) != number_as_float:
        #print("vvvv float")
        return float( int( number_as_float * 100) / 100) 
    else:
        #print("vvvv int")
        return number_as_int
    