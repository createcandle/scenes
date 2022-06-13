"""

Example addon for Candle Controller / Webthings Gateway.

This addon has the following hierarchy:

Adapter
- Device (1x)
- - Property (4x)
- API handler


"""


import os
import sys
# This helps the addon find python libraries it comes with, which are stored in the "lib" folder. The "package.sh" file will download Python libraries that are mentioned in requirements.txt and place them there.
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib')) 

import json
import time
#import datetime
import requests  # noqa
#import threading
#import subprocess

# This loads the parts of the addon.
from gateway_addon import Database, Adapter, Device, Property, APIHandler, APIResponse
# Database - needed to read from the settings database. If your addon doesn't have any settings, then you don't need this.

# Adapter. Needed if you want to provide things' to the controller.
# Device. Needed if you want to provide things' to the controller.
# Property. Needed if you want to provide things' to the controller.

# APIHandler. Needed if you want to provide an API for a UI extension.
# APIResponse. Needed if you want to provide an API for a UI extension.

# This addon does not load part from other files, but if you had a big addon you might want to split it into separate parts. For example, you could have a file called "scenes_api_handler.py" at the same level as scenes.py, and import it like this:
#try:
#    from .internet_radio_api_handler import *
#    print("APIHandler imported")
#except Exception as ex:
#    print("Error, unable to load APIHandler: " + str(ex))


# Not sure what this is used for, but leave it in.
_TIMEOUT = 3

# Not sure what this is used for either, but leave it in.
_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.webthings', 'config'),
]

# Not sure what this is used for either, but leave it in.
if 'WEBTHINGS_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['WEBTHINGS_HOME'], 'config'))




# The adapter is the top level of this hierarchy

# Adapter  <- you are here
# - Device  
# - - Property  
# - Api handler

class ScenesAdapter(Adapter):
    """Adapter for addon """

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        
        #print("Starting adapter init")

        self.ready = False # set this to True once the init process is complete.
        self.addon_name = 'scenes'
        
        
        self.name = self.__class__.__name__ # TODO: is this needed?
        Adapter.__init__(self, self.addon_name, self.addon_name, verbose=verbose)

        # set up some variables
        self.DEBUG = False
        
        self.api_server = 'http://127.0.0.1:8080' # Where can the Gateway API be found? this will be replaced with https://127.0.0.1:4443 later on, if a test call to the api fails.
        

        self.run_last_scene_at_addon_startup = False
        


        # There is a very useful variable called "user_profile" that has useful values from the controller.
        #print("self.user_profile: " + str(self.user_profile))
        
        
        # This addon has a "hidden parent" itself, the manager_proxy.
        #print("self.adapter.manager_proxy: " + str(self.adapter.manager_proxy))
        
        
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


        self.DEBUG = True

        # 3. Now we check if all the values that should exist actually do

        if 'state' not in self.persistent_data:
            self.persistent_data['state'] = False

        if 'slider' not in self.persistent_data:
            self.persistent_data['slider'] = 0
            
        if 'dropdown' not in self.persistent_data:
            self.persistent_data['dropdown'] = 'Auto'

        if 'scenes' not in self.persistent_data:
            self.persistent_data['scenes'] = {}

        if 'current_scene' not in self.persistent_data:
            self.persistent_data['current_scene'] = "no name yet"

        if 'jwt' not in self.persistent_data:
            self.persistent_data['jwt'] = ""



        # Respond to gateway version
        try:
            if self.DEBUG:
                print("Gateway version: " + str(self.gateway_version))
        except:
            print("self.gateway_version did not exist")
            

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
            print("Could not create internet_radio_device: " + str(ex))


        
        # Just in case any new values were created in the persistent data store, let's save if to disk
        self.save_persistent_data()
        
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
                print(str(config)) # Print the entire config data
                
            if 'Set last selected scene when addon starts' in config:
                self.run_last_scene_at_addon_startup = bool(config['Set last selected scene when addon starts']) # sometime you may want the addon settings to override the persistent value
                if self.DEBUG:
                    print("Set last selected scene when addon starts preference was in config: " + str(self.run_last_scene_at_addon_startup))

            

        except Exception as ex:
            print("Error in add_from_config: " + str(ex))



    #
    #  CHANGING THE PROPERTIES
    #
        
        
    def set_scene(self,value):
        try:
            if self.DEBUG:
                print("in set_scene with value: " + str(value))
            if value in self.persistent_data['scenes']:
                
                # saves the new state in the persistent data file, so that the addon can restore the correct state if it restarts
                if self.persistent_data['current_scene'] != value:
                    self.persistent_data['current_scene'] = value
                    self.save_persistent_data() 
        
                # A cool feature: you can create popups in the interface this way:
                self.send_pairing_prompt("Scene: " + str(value))
        
                self.actually_set_scene(self.persistent_data['scenes'][value])
                
        
                try:
                    self.devices['scenes-thing'].properties['scenes'].update( value )
                except Exception as ex:
                    print("error setting dropdown value on thing: " + str(ex))
        
                
            else:
                print("Error, that scene does not exist")
        except Exception as ex:
            if self.DEBUG:
                print("error in set_scene: " + str(ex))

    def actually_set_scene(self,dictionary):
        if self.DEBUG:
            print("in actually_set_scene. Dictionary: " + str(dictionary))
        try:
            for thing_id in dictionary:
                #print("set_scene: thing_id: " + str(thing_id))
            
                for property_id in dictionary[thing_id]:
                    property_value = dictionary[thing_id][property_id]
            
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
        print("in start_pairing. Timeout: " + str(timeout))
        
        
    def cancel_pairing(self):
        """ Happens when the user cancels the pairing process."""
        # This happens when the user cancels the pairing process, or if it times out.
        print("in cancel_pairing")
        

    def unload(self):
        """ Happens when the user addon / system is shut down."""
        if self.DEBUG:
            print("Bye!")
            
        try:
            self.devices['scenes-thing'].properties['status'].update( "Bye")
        except Exception as ex:
            print("Error setting status on thing: " + str(ex))
        
        # Tell the controller to show the device as disconnected. This isn't really necessary, as the controller will do this automatically.
        self.devices['scenes-thing'].connected_notify(False)
        
        # A final chance to save the data.
        self.save_persistent_data()


    def remove_thing(self, device_id):
        """ Happens when the user deletes the thing."""
        #print("user deleted the thing")
        try:
            # We don't have to delete the thing in the addon, but we can.
            obj = self.get_device(device_id)
            self.handle_device_removed(obj) # Remove from device dictionary
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
                    json.dump( self.persistent_data, open( self.persistence_file_path, 'w+' ) )
                except Exception as ex:
                    print("Error saving to persistence file: " + str(ex))
                return True
            #self.previous_persistent_data = self.persistent_data.copy()

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
                print("jwt token is too short")
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
            
            
        except Exception as ex:
            print("Error preparing PUT: " + str(ex))

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(self.persistent_data['jwt']),
        }
        try:
            r = requests.put(
                self.api_server + api_path,
                json=json_dict,
                headers=headers,
                verify=False,
                timeout=5
            )
            if self.DEBUG:
                print("API PUT: " + str(r.status_code) + ", " + str(r.reason))
                print("PUT returned: " + str(r.text))

            if r.status_code != 200:
                if self.DEBUG:
                    print("Error communicating: " + str(r.status_code))
                return {"error": str(r.status_code)}
            else:
                if simplified:
                    return_value = {property_was:json.loads(r.text)} # json.loads('{"' + property_was + '":' + r.text + '}')
                else:
                    return_value = json.loads(r.text)
                
                return_value['succes'] = True
                return return_value

        except Exception as ex:
            print("Error doing http request/loading returned json: " + str(ex))
            return {"error": 500}



#
# DEVICE
#

# This addon is very basic, in that it only creates a single thing.
# The device can be seen as a "child" of the adapter


class ScenesDevice(Device):
    """Internet Radio device type."""

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

    # Creates these options "on the fly", as radio stations get added and removed.
    def update_scene_property(self, call_handle_device_added=True):
        #print("in update_stations_property")
        # Create list of scene names for the scenes thing.
        scene_names = list(self.adapter.persistent_data['scenes'].keys())
        
        print("scene_names: " + str(scene_names))
        if len(scene_names) > 0:
            self.adapter.scene_names = scene_names
            #print("remaking property? List: " + str(radio_stations_names))
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
            print("no scenes exist yet")
    


#
# PROPERTY
#

class ScenesProperty(Property):

    def __init__(self, device, name, description, value):
        
        Property.__init__(self, device, name, description)
        
        self.device = device # a way to easily access the parent device, of which this property is a child.
        
        # TODO: set the ID properly?
        self.id = name
        self.name = name # TODO: is name still used?
        self.title = name # TODO: the title isn't really being set?
        self.description = description # a dictionary that holds the details about the property type
        self.value = value # the value of the property
        
        # Notifies the controller that this property has a (initial) value
        self.set_cached_value(value)
        self.device.notify_property_changed(self)
        
        print("property: initiated: " + str(self.title) + ", with value: " + str(value))


    def set_value(self, value):
                
        try:
            if self.id == 'scenes':
                self.device.adapter.set_scene(str(value))
                
        
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
        print("INSIDE API HANDLER INIT")
        
        self.adapter = adapter
        self.DEBUG = self.adapter.DEBUG

        print("self.DEBUG in api handler: " + str(self.DEBUG))
        # Intiate extension addon API handler
        try:
            
            APIHandler.__init__(self, self.adapter.addon_name) # gives the api handler the same id as the adapter
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
                    if action == 'init':
                        if self.DEBUG:
                            print("API: in init")
                        
                        try:
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
                                      'scenes': self.adapter.persistent_data['scenes'],
                                      'debug': self.adapter.DEBUG
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
                            scene_name = str(request.body['scene_name'])
                            scene_settings = request.body['scene_settings']
                            
                            if self.DEBUG:
                                print("incoming scene_name: " + str(scene_name))
                                print("incoming scene_settings: " + str(scene_settings))
                            
                            self.adapter.persistent_data['scenes'][scene_name] = scene_settings
                            #print("self.adapter.persistent_data['scenes']: " + str(self.adapter.persistent_data['scenes']))
                            
                            self.adapter.save_persistent_data()
                            
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
                        
                            self.adapter.actually_set_scene(scene_settings)
                        
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
                    
                    
                    
                    # DELETE
                    # In this example we call out to a separate delete method instead of handling the action directly
                    elif action == 'delete':
                        if self.DEBUG:
                            print("API: in delete")
                        
                        state = False
                        
                        try:
                            scene_name = str(request.body['scene_name'])
                            del self.adapter.persistent_data['scenes'][scene_name]
                            self.adapter.save_persistent_data()
                            
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
                            scene_name = str(request.body['scene_name'])
                            if self.DEBUG:
                                print("API: request to play: " + str(scene_name))
                            self.adapter.set_scene(scene_name)
                            state = True
                            
                        except Exception as ex:
                            if self.DEBUG:
                                print("Error playing: " + str(ex))
                        
                        return APIResponse(
                          status=200,
                          content_type='application/json',
                          content=json.dumps({'state' : state}),
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
    