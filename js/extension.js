(function() {
	class Scenes extends window.Extension {
	    constructor() {
	      	super('scenes');
      		
            this.debug = false; // if enabled, show more output in the console
            
            this.all_things = [];
            this.scenes = {};
			this.timers = {};
			
			this.getting_timers = false;
            
			//this.busy_editing_a_scene = false;
            
			//console.log("Adding scenes addon to main menu");
			this.addMenuEntry('Scenes');
            
            
            // Send the token to the backout. Timeout gives the backend some time to get started.
            setTimeout(() => {
                const jwt = localStorage.getItem('jwt');

                window.API.postJson(
                  `/extensions/${this.id}/api/ajax`,
        			{'action':'save_token','jwt':jwt}

                ).then((body) => {

                }).catch((e) => {
          			console.log("Error saving token: ", e);
                });
            }, 5000);
            
            
            
            
            
            // Load the html
            this.content = ''; // The html from the view will be loaded into this variable
			fetch(`/extensions/${this.id}/views/content.html`)
	        .then((res) => res.text())
	        .then((text) => {
	         	this.content = text;
                
                // This is needed because the user might already be on the addon page and click on the menu item again. This helps to reload it.
	  		 	if( document.location.href.endsWith("extensions/scenes") ){
	  		  		this.show();
	  		  	}
	        })
	        .catch((e) => console.error('Failed to fetch content:', e));
            
            
            // This is not needed, but might be interesting to see. It will show you the API that the controller has available. For example, you can get a list of all the things this way.
            //console.log("window API: ", window.API);
            
	    }






		//
        //  SHOW
        //
        // This is called then the user clicks on the addon in the main menu, or when the page loads and is already on this addon's location.
	    show() {
			//console.log("scenes show called");
			//console.log("this.content:");
			//console.log(this.content);
            
            
			const main_view = document.getElementById('extension-scenes-view');
			
			if(this.content == ''){
                //console.log("content has not loaded yet");
				return;
			}
			else{
				main_view.innerHTML = this.content;
			}
			
            
            
            
            
            
            
            // SAVE button press
            document.getElementById('extension-scenes-edit-save-button').addEventListener('click', (event) => {
            	//console.log("scenes: edit save button clicked. Event: ", event);
                this.save_scene();
            });
            
            
            // TEST button press
            document.getElementById('extension-scenes-edit-test-button').addEventListener('click', (event) => {
            	//console.log("scenes: edit test button clicked. Event: ", event);
                this.save_scene(true);
            });
            
			// Show timers tutorial
            document.getElementById('extension-scenes-edit-thing-timers-learn-more-button').addEventListener('click', (event) => {
            	document.getElementById('extension-scenes-edit-thing-timers-learn-more-button').style.display = 'none';
				document.getElementById('extension-scenes-edit-thing-timers-tutorial').classList.remove('extension-scenes-hidden');
            });
            
            
            
            // Easter egg when clicking on the title
			document.getElementById('extension-scenes-title').addEventListener('click', (event) => {
				//alert("You found an easter egg!");
                this.edit_scene();
			});
            
            
            
            
            // Button to show the second page
            document.getElementById('extension-scenes-show-second-page-button').addEventListener('click', (event) => {
                //console.log("scenes: clicked on + button");
                document.getElementById('extension-scenes-content-container').classList.add('extension-scenes-showing-second-page');
                
                // iPhones need this fix to make the back button lay on top of the main menu button
                document.getElementById('extension-scenes-view').style.zIndex = '3';
				document.getElementById('extension-scenes-edit-id').value = '';
				
                this.edit_scene();
                
			});
            
            // Back button, shows main page
            document.getElementById('extension-scenes-back-button-container').addEventListener('click', (event) => {
                //console.log("scenes: clicked on back button");
                document.getElementById('extension-scenes-content-container').classList.remove('extension-scenes-showing-second-page');
                //this.busy_editing_a_scene = false;
				
                // Undo the iphone fix, so that the main menu button is clickable again
                document.getElementById('extension-scenes-view').style.zIndex = 'auto';
                
            	document.getElementById('extension-scenes-edit-thing-timers-learn-more-button').style.display = 'initial';
				document.getElementById('extension-scenes-edit-thing-timers-tutorial').classList.add('extension-scenes-hidden');
				
                this.get_init_data(); // repopulate the main page
                
			});
            
            
            // Scroll the content container to the top
            document.getElementById('extension-scenes-view').scrollTop = 0;
            
            // Finally, request the first data from the addon's API
            this.get_init_data();
			let timers_counter = 0;
			let content_el = this.view.querySelector('#extension-scenes-content-container');
			if(content_el){
				content_el.scenes_interval = setInterval(() => {
					
					if(!content_el.classList.contains('extension-scenes-showing-second-page')){
						this.generate_timers_list();
					}
					
					timers_counter++;
					if(timers_counter > 10){
						timers_counter = 0;
						this.get_timers();
					}
					
					if(timers_counter == 5 && this.getting_timers == false){
						this.get_timers();
					}
					
					if( !document.location.href.endsWith("extensions/scenes") ){
						console.log("user navigated away from scenes addon. Stopping scenes interval");
						clearInterval(content_el.scenes_interval);
						document.getElementById('extension-scenes-view').innerHTML = '';
					}
					
				},1000);
			}
            
		}
		
	
		hide() {
			//console.log("scenes hide called");
		}
        
    
    
    
        //
        //  INIT
        //
        // This gets the first data from the addon API
        
        get_init_data(){
            
			try{
                
                const jwt = localStorage.getItem('jwt');
                
		  		// Init
		        window.API.postJson(
		          `/extensions/${this.id}/api/ajax`,
                    {'action':'init','jwt':jwt}

		        ).then((body) => {
                    //console.log("init response: ", body);
                    
                    // We have now received initial data from the addon, so we can hide the loading spinner by adding the 'hidden' class to it.
                    document.getElementById('extension-scenes-loading').classList.add('extension-scenes-hidden');
                    
                    // If debug is available in the init data, set the debug value and output the init data to the console
                    if(typeof body.debug != 'undefined'){
                        this.debug = body.debug;
                        if(body.debug == true){
                            console.log("scenes: debugging enabled. Init API result: ", body);
                            
                            // If debugging is enabled, please show a big warning that this is the case. 
                            // Debugging can be a privacy risk, since lots of data will be stored in the internal logs. Showing this warning helps avoid abuse.
                            // Here we just manipulate the element style directly, instead of using the 'hidden' class.
                            if(document.getElementById('extension-scenes-debug-warning') != null){
                                document.getElementById('extension-scenes-debug-warning').style.display = 'block';
                            }
                        }
                    }
                    // Generate the list of scenes
                    if(typeof body.scenes != 'undefined'){
                        this.scenes = body['scenes'];
                        this.regenerate_items(body['scenes']);
                    }
                    else{
                        if(this.debug){
                            console.log("scenes debug: no scenes saved yet");
                        }
                    }
                    if(typeof body.timers != 'undefined'){
                        this.timers = body['timers'];
                        this.generate_timers_list();
                    }
				
		        }).catch((err) => {
		  			console.error("Scenes: error getting init data: ", err);
		        });	

			}
			catch(err){
				console.error("Scenes: caught error in API call to init: ", err);
			}
        }
    

        
        get_timers(){
			this.getting_timers = true;
	        window.API.postJson(
	          `/extensions/${this.id}/api/ajax`,
                {'action':'get_timers'}
	        ).then((body) => {
                if(typeof body.timers != 'undefined'){
                    this.timers = body['timers'];
					this.getting_timers = false;
                }
	        }).catch((err) => {
	  			console.error("Scenes: caught error getting timers data via API: ", err);
				this.getting_timers = false;
	        });	
        }
        
    
	
		//
		//  REGENERATE ITEMS LIST ON MAIN PAGE
		//
	
		regenerate_items(items){
            // This funcion takes a list of items and generates HTML from that, and places it in the list container on the main page
			
            document.getElementById('extension-scenes-view').scrollTop = 0;
            
            try {
				
		        if(this.debug){
                    console.log("scenes: debugging: regenerating. items: ", items);
		        }
                
                let list_el = document.getElementById('extension-scenes-main-items-list'); // list element
                if(list_el == null){
                    console.error("Scenes: Error, the main list container did not exist yet");
                    return;
                }
                
                let scene_names = [];
				let reverse_lookup = {};
				for (const [scene_id, details] of Object.entries(items)) {
					if(typeof details['name'] == 'string' && details['name'].length){
						reverse_lookup[ details['name'] ] = scene_id;
						scene_names.push(details['name']);
					}
				}
				
				if(this.debug){
					//console.log("scenes debug: regenerate_item: reverse_lookup: ", reverse_lookup);
				}
                
                // If the items list does not contain actual items, then stop
                if(scene_names.length == 0){
                    let explanation_html = '<div id="extension-scenes-start-page-explanation" class="extension-scenes-flex">';
					explanation_html += '<img src="/extensions/scenes/images/man_reading_on_couch.svg" alt="Man reading a book on a couch">';
					explanation_html += '<div>';
					explanation_html += '<p>Scenes allow you to change the values of many things at once.</p><p>For example, you could create scenes for:</p>';
					explanation_html += '<ul>';
					explanation_html += '<li><span>Watching Movies</span>Such a scene could turn down the lights and close the curtains in the livingroom, disable any other distractions, and turn on the TV.</li>';
					explanation_html += '<li><span>Dinner party</span>Turn on some mood lights, throw in some colour, and turn on a relaxing radio station.</li>';
					explanation_html += '<li><span>Going to bed</span>The scene could close curtains, turn off music, lock the doors, limit heating to bedrooms, and limit noisy devices such as air filters.</li>';
					explanation_html += '<li><span>Away from home</span>The scene could turn off all the lights and heating, and turn on security systems.</li>';
					explanation_html += '</ul>';
					
                    explanation_html += '</div>';
					explanation_html += '</div>';
					explanation_html += '<p></p><p style="text-align:center">Click on the <img src="/images/add.svg" width="16" height="16" alt="plus icon"> button in the bottom-right corner to create a new scene.</p>';
					
					
					
					list_el.innerHTML = explanation_html;
					return
                }
                else{
                    list_el.innerHTML = "";
                }
                
                // The original item which we'll clone  for each item that is needed in the list.  This makes it easier to design each item.
				const original = document.getElementById('extension-scenes-original-item');
			    //console.log("original: ", original);
                
				
                scene_names.sort();
                
                //console.log("alphabetically sorted scene_names: ", scene_names);
                
				// Loop over all items in the list to create HTML for each item. 
                // This is done by cloning an existing hidden HTML element, updating some of its values, and then appending it to the list element
				for( var index in scene_names ){
					
                    const item_name = scene_names[index];
                    //console.log("item_name: ", item_name);
					var clone = original.cloneNode(true); // Clone the original item
					clone.removeAttribute('id'); // Remove the ID from the clone
                    
                    // Place the name in the clone
                    clone.querySelector(".extension-scenes-item-name").innerText = item_name; // The original and its clones use classnames to avoid having the same ID twice
                    //clone.getElementsByClassName("extension-scenes-item-value")[0].innerText = items[item].value; // another way to do the exact same thing - select the element by its class name
                     
                    clone.querySelector(".extension-scenes-item-setter").setAttribute('data-name', item_name);
                    // Create a short description of what the scene does
                    
					clone.querySelector(".extension-scenes-item-setter").setAttribute('data-scene_id', reverse_lookup[item_name]);
					
					
					
                    var summary = "";
                    
                    //console.log("scene in regen length: ", Object.keys(items[item]).length);
                    
					let item_description = '';
					const scene_things_count = Object.keys(items[ reverse_lookup[ item_name ] ]['things']).length;
					item_description += scene_things_count;
					if(scene_things_count == 1){
						item_description += ' thing'
					}
					else{
						item_description += ' things'
					}
					
					if(typeof items[ reverse_lookup[ item_name ] ]['timer'] != 'undefined' && typeof items[ reverse_lookup[ item_name ] ]['timer']['next_scene_id'] == 'string'){
						const next_scene_id = items[ reverse_lookup[ item_name ] ]['timer']['next_scene_id'];
						if(typeof items[ next_scene_id ]['name'] == 'string' && items[ next_scene_id ]['name'].length){
							const next_scene_name = items[ next_scene_id ]['name'];
							item_description += ', starts ' + next_scene_name;
						}
						
					}
                    
						
                    clone.querySelector(".extension-scenes-item-description").innerText = item_description;
                    
                    
                    
                    // You could add a specific CSS class to an element depending, for example depending on some value
                    //clone.classList.add('extension-scenes-item-highlighted');   
                    
                    
                    // ADD EDIT BUTTON
                    const edit_button = clone.querySelector('.extension-scenes-item-setter');
                    edit_button.addEventListener('click', (event) => {
                        //console.log("edit button click. event: ", event);
						if(this.debug){
                        	console.log("scenes debug: clicked on button to edit scene: ", event.target.closest(".extension-scenes-item-setter").dataset);
						}
                        document.getElementById('extension-scenes-content-container').classList.add('extension-scenes-showing-second-page');
                        document.getElementById('extension-scenes-view').style.zIndex = '3';
                        this.edit_scene(event.target.closest(".extension-scenes-item-setter").dataset.scene_id);
                        // event.target.closest(".extension-scenes-item")
                    });
                    
                    
                    // ADD PLAY BUTTON
                    const play_button = clone.querySelectorAll('.extension-scenes-item-play-button')[0];
					
					play_button.setAttribute('data-name', item_name);
                    play_button.setAttribute('data-scene_id', reverse_lookup[ item_name ]);
					
					play_button.addEventListener('click', (event) => {
                        //console.log("play button click. event: ", event);
                        
						// Inform backend
						window.API.postJson(
							`/extensions/${this.id}/api/ajax`,
							{'action':'play','scene_id': event.target.dataset.scene_id}
						).then((body) => { 
							if(this.debug){
                                console.log("scenes debug: play scene response: ", body);
                            }
							if(typeof body.timers != 'undefined'){
								this.timers = body.timers;
								this.generate_timers_list();
							}
                            if(body.state == true){
                                if(this.debug){
									console.log('scenes debug: the scene was started');
								}
                                const item_el = play_button.closest(".extension-scenes-item");
								if(item_el){
									item_el.classList.add('extension-scenes-last-selected');
								}
                                else{
                                	if(this.debug){
										console.error("scenes debug:could not find closest parent item");
									}
                                }
                            }

						}).catch((err) => {
							console.error("scenes: caught api error in play handler: ", err);
						});
                    
                    });
                    
                    
					// ADD DELETE BUTTON
					const delete_button = clone.querySelectorAll('.extension-scenes-item-delete-button')[0];
                    delete_button.setAttribute('data-name', item_name);
					delete_button.setAttribute('data-scene_id', reverse_lookup[ item_name ]);
                    
					delete_button.addEventListener('click', (event) => {
                        //console.log("delete button click. event: ", event);
                        if(confirm("Are you sure you want to delete this scene?")){
    						
							//console.log("event.target.dataset.scene_id: ", event.target.dataset.scene_id);
							
    						// Inform backend
    						window.API.postJson(
    							`/extensions/${this.id}/api/ajax`,
    							{'action':'delete','scene_id': event.target.dataset.scene_id}
    						).then((body) => { 
    							if(this.debug){
                                    console.log("scenes debug: delete item response: ", body);
                                }
                                if(body.state == true){
                                    //console.log('the item was deleted on the backend');
                                    
                                    event.target.closest(".extension-scenes-item").style.display = 'none'; // find the parent item
                                    // Remove the item form the list, or regenerate the entire list instead
                                    // parent4.removeChild(parent3);
                                }

    						}).catch((err) => {
    							console.error("scenes: caught error calling delete scene API: ", err);
    						});
                        }
				  	});

                    // Add the clone to the list container
					list_el.append(clone);
                    
                    
                    
				} // end of for loop
                
            
            
			}
			catch (err) {
				console.log("Scenes: general error in regenerate_items: ", err);
			}
		}
	
	
	
		//
		//  GENERATE ACTIVE TIMERS LIST
		//
	
		generate_timers_list(){
			/*
			if(this.debug){
				if(Object.keys(this.timers).length){
					console.log("scenes debug: in generate_timers_list. this.timers: ", this.timers);
				}
			}
			*/
			const timers_container_el = this.view.querySelector('#extension-scenes-timers-list');
			if(timers_container_el == null){
				console.error("scenes: missing timers_container_el");
				return
			}
			
			timers_container_el.innerHTML = '';
			
			for (const [scene_id, details] of Object.entries(this.timers)) {
				
				let timer_item_el = document.createElement('div');
				timer_item_el.classList.add('extension-scenes-timers-list-item');
				
				if(typeof details['name'] == 'string' && details['name'].length == 0){
					console.error("scenes: timer item had empty name.  scene_id,details: ", scene_id, details);
					continue
				}
				
				// Add the timer's name to the item
				let timer_info_container_el = document.createElement('div');
				timer_info_container_el.classList.add('extension-scenes-timers-list-item-info');
				
				let timer_name_el = document.createElement('span');
				timer_name_el.classList.add('extension-scenes-timers-list-item-info-name');
				timer_name_el.textContent = this.scenes[ scene_id ]['name']; //details['name'];
				timer_name_el.addEventListener('click', () => {
					this.edit_scene(details['scene_id']);
				});
				timer_info_container_el.appendChild(timer_name_el);
				
				//console.log("parent_scene_id: ", details['parent_scene_id'], this.scenes[ details['parent_scene_id'] ]['name']);
				//console.log("scene_id: ", scene_id, this.scenes[ scene_id ]['name']);
				
				if(typeof this.scenes[ details['parent_scene_id'] ] != 'undefined' && typeof this.scenes[ details['parent_scene_id'] ]['name'] == 'string' && this.scenes[ details['parent_scene_id'] ]['name'].length){
					let timer_parent_name_el = document.createElement('span');
					timer_parent_name_el.classList.add('extension-scenes-timers-list-item-info-parent-name');
					timer_parent_name_el.textContent = "Created by: " + this.scenes[ details['parent_scene_id'] ]['name'];
					timer_parent_name_el.addEventListener('click', () => {
						this.edit_scene(details['parent_scene_id']);
					});
					timer_info_container_el.appendChild(timer_parent_name_el);
				}
				
				timer_item_el.appendChild(timer_info_container_el);
				
				
				// Add time-to-go details to timer item
				if(typeof details['start_time'] == 'number'){
					
					let seconds_to_go = details['start_time'] - (Date.now() / 1000);
					if(this.debug){
						//console.log("scenes debug: timer: seconds_to_go: ", seconds_to_go);
					}
					
					if(seconds_to_go < 0){
						if(this.debug){
							console.warn("scenes debug: seconds_to_go was negative - this timer is expired: ", seconds_to_go);
						}
						continue
					}
					
					let timer_time_to_go_el = document.createElement('span');
					timer_time_to_go_el.classList.add('extension-scenes-timers-list-item-time-to-go');
					if(seconds_to_go < 60 * 2){
						timer_time_to_go_el.textContent = "Starting in " + Math.floor(seconds_to_go) + " seconds";
					}
					else if(seconds_to_go < (3600 * 2)){
						timer_time_to_go_el.textContent = "Starting in " + Math.floor(seconds_to_go / 60) + " minutes";
					}
					else if(seconds_to_go < (38400 * 2)){
						timer_time_to_go_el.textContent = "Starting in " + Math.floor(seconds_to_go / 3600) + " hours";
					}
					else{
						timer_time_to_go_el.textContent = "Starting in " + Math.floor(seconds_to_go / 38400) + " days";
					}
					
					timer_item_el.appendChild(timer_time_to_go_el);
				}
				
				
				// Add button to delete active timer
				let timer_delete_button_container_el = document.createElement('div');
				timer_delete_button_container_el.classList.add('extension-scenes-timers-list-delete-button-container');
				
				let timer_delete_button_el = document.createElement('span');
				timer_delete_button_el.classList.add('extension-scenes-item-delete-button');
				timer_delete_button_el.addEventListener('click', () => {
					delete this.timers[scene_id];
					timer_item_el.style.display = 'none';
					
					// Inform backend
					window.API.postJson(
						`/extensions/${this.id}/api/ajax`,
						{'action':'delete_timer','scene_id': scene_id}
					).then((body) => { 
						if(this.debug){
                            console.log("scenes debug: delete timer response: ", body);
                        }
                        if(body.state == true){
							this.generate_timers_list();
                        }
					}).catch((err) => {
						console.error("scenes: caught error in delete_timer API request: ", err);
					});
					
				});
				
				
				timer_delete_button_container_el.appendChild(timer_delete_button_el);
				timer_item_el.appendChild(timer_delete_button_container_el);
				
				// add new timer item to list
				timers_container_el.appendChild(timer_item_el);
				
			}
			
		}
	
	
	
	
	
	
    
    
    
    
        edit_scene(scene_id){
			if(this.debug){
				console.log("scenes debug: in edit_scene. scene_id: ", scene_id);
			}
			
            document.getElementById('extension-scenes-view').scrollTop = 0;
            
			const scene_id_input_el = this.view.querySelector('#extension-scenes-edit-id');
			if(scene_id_input_el == null){
				console.error("scenes: edit_scene: could not find scene_id input element");
				return
			}
			if(typeof scene_id == 'string'){
				scene_id_input_el.value = scene_id;
			}
			
			const scene_name_input_el = this.view.querySelector('#extension-scenes-edit-name');
			
            var scene_settings = {};
			
			scene_name_input_el.value = '';
			
            if(typeof this.scenes[scene_id] != 'undefined'){
				if(typeof this.scenes[scene_id]['name'] == 'string'){
					document.getElementById('extension-scenes-edit-name').value = this.scenes[scene_id]['name'];
				}
            }
            
            document.getElementById('extension-scenes-edit-thing-settings').innerHTML = "";
            
    		// Pre populating the original item that will be clones to create new ones
    	    API.getThings().then((things) => {
			
    			this.all_things = things;
    			if(this.debug){
                    console.log("scenes debug: all things: ", things);
                }
			    
    			// pre-populate the hidden 'new' item with all the thing names
    			var thing_ids = [];
    			var thing_titles = [];
			
    			for (let key in things){

                    if( things[key].hasOwnProperty('properties') ){ // things without properties should be skipped (edge case)
                        
        				var thing_title = 'unknown';
        				if( things[key].hasOwnProperty('title') ){
        					thing_title = things[key]['title'];
        				}
        				else if( things[key].hasOwnProperty('label') ){ // very old addons sometimes used label instead of title
        					thing_title = things[key]['label'];
        				}
				
        				var thing_id = things[key]['href'].substr(things[key]['href'].lastIndexOf('/') + 1);
                        //console.log("thing_id: ", thing_id);
                        
                        if(thing_id == 'scenes-thing'){
                            //console.log("FOUND IT scenes-thing");
                            continue;
                        }
                        
                        if (thing_id.startsWith('highlights-') ){
    						//console.log(thing_id + " starts with highlight-, so skipping.");
    						continue;
                        }
                        
                        //console.log("thing_title and ID: ", thing_title, thing_id);

                        var thing_container = document.createElement('div');
                        thing_container.classList.add('extension-scenes-edit-item')
                        thing_container.dataset.thing_id = thing_id;
                    
                        var thing_checkbox = document.createElement('input');
                        thing_checkbox.type = "checkbox";
                        thing_checkbox.name = 'extension-scenes-' + thing_id;
                        thing_checkbox.id = 'extension-scenes-' + thing_id;
                        thing_checkbox.classList.add('extension-scenes-edit-item-thing-checkbox');
                    
                        // Set the checkbox of the thing to checked if it was already in the scene
                        if (typeof this.scenes[scene_id] != 'undefined' && typeof this.scenes[scene_id]['things'] != 'undefined'){
                            if (typeof this.scenes[scene_id]['things'][thing_id] != 'undefined'){
                                //console.log("checking thing checkbox");
                                thing_checkbox.checked = true;
                            }
                        }
                    
                        var thing_label = document.createElement('label');
                        thing_label.htmlFor = 'extension-scenes-' + thing_id;
                        //label.appendChild(checkbox);
                        thing_label.appendChild(document.createTextNode(thing_title));
                
                        
                        // ADD PROPERTIES CONTAINER TO THE THING CONTAINER
                    
                        var properties_container = document.createElement('div');
                        properties_container.classList.add('extension-scenes-edit-item-properties');
                        
                        var found_write_property = false;
                        let properties = things[key]['properties'];
                		for (let prop in properties){
                			//console.log(properties[prop]);
                			var property_title = 'unknown';
                			if( properties[prop].hasOwnProperty('title') ){
                				property_title = properties[prop]['title'];
                			}
                			else if( properties[prop].hasOwnProperty('label') ){
                				property_title = properties[prop]['label'];
                			}
			
                			var property_id = properties[prop]['forms'][0]['href'].substr(properties[prop]['forms'][0]['href'].lastIndexOf('/') + 1);
                            //console.log("property_id: ", property_id);
                            
                            var read_only = false;
                            if( typeof properties[prop]['readOnly'] != 'undefined'){
                                if(properties[prop]['readOnly'] == true){
                                    read_only = true;
                                }
                            }
                            
                            if(read_only == false){
                                
                                // Create container for property
                                var property_container = document.createElement('div');
                                property_container.classList.add('extension-scenes-edit-item-property');
                                property_container.dataset.property_id = property_id
                                
                                // Property is part of scene checkbox
                                var property_checkbox = document.createElement('input');
                                property_checkbox.type = "checkbox";
                                property_checkbox.name = 'extension-scenes-' + thing_id + '---' + property_id;
                                property_checkbox.id = 'extension-scenes-' + thing_id + '---' + property_id;
                                property_checkbox.classList.add('extension-scenes-edit-item-property-checkbox');
                                
                                // Set the checkbox of the property to checked if it was already enabled in the scene
                                if (typeof this.scenes[scene_id] != 'undefined' && typeof this.scenes[scene_id]['things'] != 'undefined'){
                                    if (typeof this.scenes[scene_id]['things'][thing_id] != 'undefined'){
                                        if (typeof this.scenes[scene_id]['things'][thing_id][property_id] != 'undefined'){
                                            //console.log("checking property checkbox");
                                            property_checkbox.checked = true;
                                        }
                                    }
                                }
                                
                                // Create label for property
                                var property_label_el = document.createElement('label');
                                property_label_el.htmlFor = 'extension-scenes-' + thing_id + '---' + property_id;
                                property_label_el.appendChild(document.createTextNode(property_title));
                                
                                
                                // Create input element for the property value
                                var input_el = document.createElement('input');
                                input_el.name = 'extension-scenes-' + thing_id + '-----' + property_id;
                                input_el.id = 'extension-scenes-' + thing_id + '-----' + property_id;
                                input_el.classList.add('extension-scenes-edit-item-property-value');
                                
                    			
                                // Number property
                    			if( properties[prop]['type'] == 'integer' || properties[prop]['type'] == 'float' || properties[prop]['type'] == 'number'){
                                    // If a property is a number
    			                    //console.log("number property spotted");
                                    input_el.type = "number";
                    			}
                                
                                // Boolean property
                                else if( properties[prop]['type'] == 'boolean'){
                                    //console.log("boolean property spotted");
                                    input_el = document.createElement('select');
                                    input_el.name = 'extension-scenes-' + thing_id + '-----' + property_id;
                                    input_el.id = 'extension-scenes-' + thing_id + '-----' + property_id;
                                    input_el.classList.add('extension-scenes-edit-item-property-value');
                                    
                                    var unknown_option = document.createElement("option");
                                    unknown_option.value = 'unknown';
                                    unknown_option.text = 'unknown';
                                    input_el.appendChild(unknown_option);
                                    
                                    var true_option = document.createElement("option");
                                    true_option.value = 'true';
                                    true_option.text = 'true';
                                    input_el.appendChild(true_option);
                                    
                                    var false_option = document.createElement("option");
                                    false_option.value = 'false';
                                    false_option.text = 'false';
                                    input_el.appendChild(false_option);
                                    
                                }
                                
                                // Color property
                                else if( properties[prop]['type'] == 'color'){
                                    //console.log("color property spotted");
                                    input_el.type = "color";
                                }
                                
                                // String property
                                else if( properties[prop]['type'] == 'string'){
                                    //console.log("string property spotted");
                                    input_el.type = "text";
                                    
                                    if(property_id == "color"){
                                        input_el.type = "color";
                                    }
                                    
                                    if (typeof properties[prop]['enum'] != 'undefined'){
                                        //console.log('enum spotted');
                                        
                                        input_el = document.createElement('select');
                                        input_el.name = 'extension-scenes-' + thing_id + '-----' + property_id;
                                        input_el.id = 'extension-scenes-' + thing_id + '-----' + property_id;
                                        input_el.classList.add('extension-scenes-edit-item-property-value');
                                        
                                        for (var i = 0; i < properties[prop]['enum'].length; i++) {
                                            var option = document.createElement("option");
                                            option.value = properties[prop]['enum'][i];
                                            option.text = properties[prop]['enum'][i];
                                            input_el.appendChild(option);
                                        }
                                        
                                    }
                                }
                                
                                // unsupported property
                                else{
                                    if(this.debug){
                                        console.log("Scenes: Warning, unsupported property type. Skipping");
                                    }
                                    continue;
                                }
                                
                                found_write_property = true;
                                
                                if (typeof this.scenes[scene_id] != 'undefined'){
                                    if (typeof this.scenes[scene_id]['things'][thing_id] != 'undefined'){
                                        if (typeof this.scenes[scene_id]['things'][thing_id][property_id] != 'undefined'){
                                            if (this.scenes[scene_id]['things'][thing_id][property_id] != 'undefined'){
                                                //console.log("adding input value: ", this.scenes[scene_name][thing_id][property_id]);
                                                input_el.value = this.scenes[scene_id]['things'][thing_id][property_id];
                                            }
                                        }
                                    }
                                }
                                
                                // Automatically check the checkbox if the property is changed
                                input_el.addEventListener('change', (event) => {
        	                        //console.log("Value changed. Event: ", event);
                                    //console.log("event.currentTarget.parentNode: ", event.currentTarget.parentNode);
                                    const parent_el = event.currentTarget.closest('.extension-scenes-edit-item-property');
                                    //console.log("parent_el: ", parent_el);
                                    const checkbox_sibling = parent_el.getElementsByClassName('extension-scenes-edit-item-property-checkbox')[0];
                                    //console.log("checkbox_sibling: ", checkbox_sibling);
                                    checkbox_sibling.checked = true;
                                });
                                
                                // Add property element to the property container
                                property_container.appendChild(property_checkbox);
                                property_container.appendChild(property_label_el);
                                property_container.appendChild(input_el);
                                
                                // Add the property container to the thing container
                                properties_container.appendChild(property_container);
                            }
                			
                		}
                    
                    
                        // Add thing container to the edit overview
                        if(found_write_property){
                            thing_container.appendChild(thing_checkbox);
                            thing_container.appendChild(thing_label);
                            thing_container.appendChild(properties_container);
                            
                            // Append edit view to the dom
                            document.getElementById('extension-scenes-edit-thing-settings').appendChild(thing_container);
                        }
                        else{
                            if(this.debug){
                                console.log('scenes:debug: thing has no writeable properties: ', thing_id);
                            }
                        }
                        
                    }
    			}
    	    });
			
			
			
			//
			//  GENERATE TIMER UI
			//
			
			let timer_settings_container_el = this.view.querySelector('#extension-scenes-edit-thing-timer-settings');
			if(timer_settings_container_el == null){
				console.error("scenes: timer_settings_container_el is missing");
				return
			}
			
			timer_settings_container_el.innerHTML = '';
			
			
			// add " After " span
			let timer_settings_text1_el = document.createElement('span');
			timer_settings_text1_el.textContent = 'After ';
			timer_settings_container_el.appendChild(timer_settings_text1_el);
			
			// Geneate time number input
			let timer_settings_counter_input_el = document.createElement('input');
			timer_settings_counter_input_el.setAttribute('type','number');
			timer_settings_counter_input_el.setAttribute('id','extension-scenes-edit-thing-timer-count');
			
			// Generate time units select dropdown
			let timer_settings_time_unit_select_el = document.createElement('select');
			timer_settings_time_unit_select_el.setAttribute('id','extension-scenes-edit-thing-timer-unit');
			
			const time_units = {'seconds':1,'minutes':60,'hours':3600,'days':38400};
			
			for (const [time_unit_name, time_unit_multiplier] of Object.entries(time_units)) {
				let select_option_el = document.createElement('option');
				select_option_el.textContent = time_unit_name;
				select_option_el.setAttribute('value',time_unit_multiplier);
				timer_settings_time_unit_select_el.appendChild(select_option_el);
			}
			
			// Restore time unit value
            if(typeof this.scenes[scene_id] != 'undefined' && typeof this.scenes[scene_id]['timer'] != 'undefined' && typeof this.scenes[scene_id]['timer']['time_unit'] == 'number' && Object.values(time_units).indexOf(this.scenes[scene_id]['timer']['time_unit']) != -1){
				timer_settings_time_unit_select_el.value = this.scenes[scene_id]['timer']['time_unit'];
				if(typeof this.scenes[scene_id]['timer']['seconds'] == 'number'){
					timer_settings_counter_input_el.value = Math.round(this.scenes[scene_id]['timer']['seconds'] / this.scenes[scene_id]['timer']['time_unit']);
				}
            }
			else{
				if(typeof this.scenes[scene_id] != 'undefined' && typeof this.scenes[scene_id]['timer'] != 'undefined' && typeof this.scenes[scene_id]['timer']['seconds'] == 'number'){
					timer_settings_counter_input_el.value = this.scenes[scene_id]['timer']['seconds'];
				}
				else{
					timer_settings_time_unit_select_el.value = 1;
				}
			}
			
			// Wrap the input and select in a div to make sure they are always shown next to each other
			const time_inputs_wrapper_el = document.createElement('div');
			time_inputs_wrapper_el.classList.add('extension-scenes-inline-block');
			
			time_inputs_wrapper_el.appendChild(timer_settings_counter_input_el);
			time_inputs_wrapper_el.appendChild(timer_settings_time_unit_select_el);
			timer_settings_container_el.appendChild(time_inputs_wrapper_el);
			
			
			// add " start " span
			let timer_settings_text2_el = document.createElement('span');
			timer_settings_text2_el.textContent = ' start ';
			timer_settings_container_el.appendChild(timer_settings_text2_el);
			
			
			// generate scene names select dropdown
			let timer_settings_scene_select_el = document.createElement('select');
			timer_settings_scene_select_el.setAttribute('id','extension-scenes-edit-thing-timer-next-scene');
			let scene_names = ['-'];
			let reverse_lookup = {};
			
			for (const [select_scene_id, details] of Object.entries(this.scenes)) {
				if(this.debug){
					console.log(`Scenes debug: scene_id and details: ${select_scene_id}: ${details}`);
				}
				if(typeof details['name'] == 'string' && details['name'] != '-'){
					scene_names.push(details['name']);
					reverse_lookup[details['name']] = select_scene_id;
				}
			}
			
			if(this.debug){
				console.log("scenes debug: timer: reverse_lookup: ", reverse_lookup);
			}
			
			for(let sn = 0; sn < scene_names.length; sn++){
				let select_option_el = document.createElement('option');
				select_option_el.textContent = scene_names[sn];
				if(scene_names[sn] == '-'){
					select_option_el.setAttribute('value', '');
				}else{
					select_option_el.setAttribute('value', reverse_lookup[ scene_names[sn] ]);
				}
				
				timer_settings_scene_select_el.appendChild(select_option_el);
			}
			
			// Restore scene select value
            if(typeof this.scenes[scene_id] != 'undefined' && typeof this.scenes[scene_id]['timer'] != 'undefined' && typeof this.scenes[scene_id]['timer']['next_scene_id'] == 'string' && this.scenes[scene_id]['timer']['next_scene_id'] != '' && Object.keys(this.scenes).indexOf(this.scenes[scene_id]['timer']['next_scene_id']) != -1){
				timer_settings_scene_select_el.value = this.scenes[scene_id]['timer']['next_scene_id'];
            }
			else{
				timer_settings_scene_select_el.value  = '';
			}
			
			timer_settings_container_el.appendChild(timer_settings_scene_select_el);
			
			
			// add " scene" span
			/*
			let timer_settings_text3_el = document.createElement('span');
			timer_settings_text3_el.textContent = ' scene';
			timer_settings_container_el.appendChild(timer_settings_text3_el);
			*/
            
        } // end of edit_scene
    
	
	
        save_scene(test){
            
            if(typeof test == 'undefined'){
                test = false;
            }
            
			const scene_id_input_el = document.getElementById('extension-scenes-edit-id');
			let scene_id = scene_id_input_el.value;
            if(scene_id == ''){
            	scene_id = crypto.randomUUID();
            }
			
			const scene_name = document.getElementById('extension-scenes-edit-name').value;
            if(scene_name == ""){
                alert("Please provide a name");
                return;
            }
            
            var scene_settings = {}
            
            document.querySelectorAll('#extension-scenes-edit-thing-settings .extension-scenes-edit-item').forEach(function(thing_item) {
                //console.log('thing_item: ', thing_item);
                let thing_checkbox = thing_item.getElementsByClassName("extension-scenes-edit-item-thing-checkbox")[0]; //item.querySelector['.extension-scenes-edit-item-thing-checkbox'];
                //console.log('thing_checkbox: ', thing_checkbox);
                if(thing_checkbox != null){
                    if( thing_checkbox.checked ){
                        //console.log("'\n\nCHECKED");
                        const thing_id = thing_item.dataset.thing_id;
                        //console.log("scanning thing: " + thing_id);
                        
                        const property_elements = thing_item.querySelectorAll('.extension-scenes-edit-item-property');
                        for (var i = 0; i < property_elements.length; i++) {
                            const property_item = property_elements[i];
                            const property_id = property_item.dataset.property_id;
                            //console.log("scanning property: ", property_id, property_item);
                            
                            let property_checkbox = property_item.getElementsByClassName('extension-scenes-edit-item-property-checkbox')[0];
                            if( property_checkbox.checked ){
                                //console.log("'\n\nPROPERTY CHECKED. thing_id: ", thing_id);
                                
                                if(typeof scene_settings[thing_id] == 'undefined'){
                                    scene_settings[thing_id] = {};
                                }
                                
                                let property_value_item = property_item.getElementsByClassName('extension-scenes-edit-item-property-value')[0];
                                
                                //console.log('- value: ', property_value_item.value);
                                
                                var prop_value = property_value_item.value;
                                if(prop_value == "" || prop_value == "unknown"){
                                    prop_value = null;
                                }
                                
                                scene_settings[thing_id][property_id] = prop_value;
                                
                            }
                            
                        }
                    
                    }
                }
                else{
                    console.error("scenes: error, could not find thing checkbox inside edit item"); 
                }
                
            });
            
            if ( Object.keys(scene_settings).length == 0){
                alert("Please create some settings for your things");
                return;
            }
            else{
                if(this.debug){
                    console.log("\n\nscenes debug: scene things settings: ", scene_settings);
                }
            }
            
            
            var action = 'save_scene';
            if(test){
                action = 'test_scene';
            }
			
			let complete_scene_settings = {'name':scene_name, 'things':scene_settings}
			
			const timer_next_scene_el = this.view.querySelector('#extension-scenes-edit-thing-timer-next-scene');
			if(timer_next_scene_el && typeof timer_next_scene_el.value == 'string' && timer_next_scene_el.value != ''){
				const timer_count_el = this.view.querySelector('#extension-scenes-edit-thing-timer-count');
				const time_unit_el = this.view.querySelector('#extension-scenes-edit-thing-timer-unit');
			
				if(timer_count_el && time_unit_el){
					let timer_count = parseInt(timer_count_el.value);
					let timer_multiplier = parseInt(time_unit_el.value);
					if(timer_count > 0){
						complete_scene_settings['timer'] = {'next_scene_id':timer_next_scene_el.value, 'seconds':(timer_count * timer_multiplier), 'time_unit':timer_multiplier}
					}
					
				}
				else{
					console.error("missing timer input elements.  timer_count_el,time_unit_el: ", timer_count_el,time_unit_el);
				}
				
			}
			
            if(this.debug){
                console.log("\n\nscenes debug: complete_scene_settings: ", complete_scene_settings);
            }
			
            
            
            // If we end up here, then a name and number were present in the input fields. We can now ask the backend to save the new item.
			window.API.postJson(
				`/extensions/${this.id}/api/ajax`,
				{'action':action, 'scene_id':scene_id, 'scene_settings':complete_scene_settings}
                
			).then((body) => {
                if(this.debug){
                    console.log("scenes debug: save scene response: ", body);
                }
                if(body.state == true){
                    //console.log("saving scene went ok");
                    if(action == 'save_scene'){
                        document.getElementById('extension-scenes-content-container').classList.remove('extension-scenes-showing-second-page');
						scene_id_input_el.value = '';
                        document.getElementById('extension-scenes-view').style.zIndex = 'auto';
                        this.scenes = body['scenes'];
                        this.regenerate_items(body['scenes']);
                    }
                }
                else{
                    //console.log("saving new item failed!");
                    alert("Sorry, saving the scene failed.");
                }
                
			}).catch((e) => {
				console.error("scenes: connnection error after save item button press: ", e);
                alert("failed to save scene: connection error");
			});
            
        }
    
    }

	new Scenes();
	
})();


