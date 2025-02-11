/*
 * View model for OctoPrint-LightControlsHttp
 *
 * Author: RoboMagus
 * License: AGPLv3
 */
$(function() {
    function LightControlsHttpViewModel(parameters) {
        var self = this;

        var PLUGIN_ID = "LightControlsHttp"

        self.settings = parameters[0];
        self.control = parameters[1];

        self.light_controls = ko.observableArray(); // Raw settings
        self.lights = ko.observableArray(); // light states

        ko.subscribable.fn.withUpdater = function (handler, target, identifier) {
            var self = this;

            var _oldValue;
            this.subscribe(function (oldValue) {
                _oldValue = oldValue;
            }, null, 'beforeChange');

            this.subscribe(function (newValue) {
                handler.call(target, _oldValue, newValue, identifier);
            });
            this.extend({ rateLimit: 50 });
        
            return this;
        };

        var sliderUpdate = function (oldvalue, newvalue, identifier) {
            if( oldvalue != newvalue) {
                // communicate update to backend
                $.ajax({
                    url: API_BASEURL + "plugin/"+PLUGIN_ID,
                    type: "POST",
                    dataType: "json",
                    data: JSON.stringify({
                        command: "setLightValue",
                        light_control_url: identifier,
                        percentage: newvalue
                    }),
                    contentType: "application/json; charset=UTF-8"
                }).done(function(data){

                }).always(function(){

                });
            }
        }

        self.requestDistributeLightValues = function() {
            // console.log("Requesting light levels!");
            $.ajax({
                url: API_BASEURL + "plugin/"+PLUGIN_ID,
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "getLightValues",
                }),
                contentType: "application/json; charset=UTF-8"
            }).done(function(data){

            }).always(function(){

            });
        }

        self.updateLightsStructure = function() {
            self.lights([]);
            ko.utils.arrayForEach(self.settings.settings.plugins.LightControlsHttp.light_controls(), function (item, index) {
                self.lights.push({ 
                    name: item.name, 
                    light_control_url: item.light_control_url,
                    light_val: ko.observable(0).withUpdater(sliderUpdate, self, item.light_control_url()),
                    light_toggle : function() {
                        this.light_val((this.light_val() == 0) ? 100 : 0);
                    }
                 });
            });
            // Request values whenever the light structure is updated!
            self.requestDistributeLightValues();
        };

        self.onBeforeBinding = function() {
            // self.updateLightsStructure();
        };

        self.onAfterBinding = function() {
            // I want this to be placed after MultiWebcam :)
            var lightsControl = $('#LightControlsHttp');
            var containerGeneral = $('#control-jog-general');

            lightsControl.insertAfter(containerGeneral);
            lightsControl.css('display', '');

            self.updateLightsStructure();
        };

        self.onSettingsBeforeSave = function() {
            // ko.utils.arrayForEach(self.settings.settings.plugins.LightControlsHttp.light_controls(), function (item, index) {
            // });
        };

        self.onEventSettingsUpdated = function(payload) {
			self.settings.requestData();
            self.light_controls(self.settings.settings.plugins.LightControlsHttp.light_controls());
            self.updateLightsStructure();
        };

        self.addLightControl = function() {
            self.settings.settings.plugins.LightControlsHttp.light_controls.push({
                name: ko.observable('Light '+self.light_controls().length), 
                light_control_url: ko.observable(''),
                onOctoprintStartValue: ko.observable(''),
                onConnectValue: ko.observable(''),
                onDisconnectValue: ko.observable(''),
                onPrintStartValue: ko.observable(''),
                onPrintPausedValue: ko.observable(''),
                onPrintResumedValue: ko.observable(''),
                onPrintEndValue: ko.observable('') });
            self.light_controls(self.settings.settings.plugins.LightControlsHttp.light_controls());
        };

        self.removeLightControl = function(profile) {
            self.settings.settings.plugins.LightControlsHttp.light_controls.remove(profile);
            self.light_controls(self.settings.settings.plugins.LightControlsHttp.light_controls());
        };

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin == PLUGIN_ID) {
                if (data.light_control_url != undefined && data.value != undefined) {        
                    ko.utils.arrayForEach(self.lights(), function(item) {
                        if(item.light_control_url() == data.light_control_url) {
                            item.light_val(data.value);
                        }
                    });
                }
            }
        }
    }


    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: LightControlsHttpViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ "settingsViewModel", "controlViewModel" ],
        // Elements to bind to, e.g. #settings_plugin_LightControlsHttp, #tab_plugin_LightControlsHttp, ...
        elements: [ "#settings_plugin_LightControlsHttp_form", "#LightControlsHttp" ]
    });
});
