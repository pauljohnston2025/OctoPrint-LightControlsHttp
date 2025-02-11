# coding=utf-8
from __future__ import absolute_import

import copy
import octoprint.plugin
from octoprint.events import eventManager, Events
import sys, traceback
import flask
import requests

def clamp(n, _min, _max):
    return max(_min, min(n, _max))

class LightControlsHttpPlugin(  octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            octoprint.plugin.SimpleApiPlugin,
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.ShutdownPlugin ):

    defaultEntry = {'name': '',
                    'light_control_url': '',
                    'onOctoprintStartValue': '',
                    'onConnectValue': '',
                    'onDisconnectValue': '',
                    'onPrintStartValue': '',
                    'onPrintPausedValue': '',
                    'onPrintResumedValue': '',
                    'onPrintEndValue': '' }

    def __init__(self):
        self.Lights = {}

    def light_startup(self, light_control_url, settings):
        self._logger.debug("LightControlsHttp light_startup, light_control_url: {}, settings: {}".format(light_control_url, settings))
        # Remove to re-add if already present:
        if light_control_url in self.Lights:
            self.light_cleanup(light_control_url)

        try:
            self.Lights[light_control_url] = copy.deepcopy(settings)
            self.Lights[light_control_url]["value"] = 0
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            self._logger.error("exception in light_startup(): {}".format(exc_type))
            self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))

    def light_cleanup(self, light_control_url):
        self._logger.debug("LightControlsHttp light_cleanup, light_control_url: {}".format(light_control_url))

    def set_light_value(self, light_control_url, value):
        if light_control_url in self.Lights:
            iVal = int(value)
            # todo make the min/max configurable, its currently a % disaplay only, we will hard code 0-255 range here
            max_value = 255
            percentage_value = iVal
            raw_value = percentage_value / 100.0 * max_value
            raw_url = light_control_url.replace('{value}', str(int(raw_value)))
            self._logger.debug(f"set_light_value {raw_url}")
            # default to localhost, todo: allow specifying full remote url (or host prefix)
            requests.get("http://127.0.0.1:80" + raw_url)

            if iVal != self.get_light_value(light_control_url):
                self._plugin_manager.send_plugin_message(self._identifier, dict(light_control_url=light_control_url, value=iVal))
            self.Lights[light_control_url]["value"] = iVal

    def get_light_value(self, light_control_url):
        self._logger.debug("LightControlsHttp get_light_value light_control_url: {}".format(light_control_url))
        return self.Lights.get(light_control_url, {}).get("value", 0)

    def send_light_values(self):
        self._logger.debug("send_light_values")
        for light_control_url in self.Lights:
            self._plugin_manager.send_plugin_message(self._identifier, dict(light_control_url=light_control_url, value=self.get_light_value(light_control_url)))

    def LightName2light_control_url(self, name):
        light_control_urlArray = [light_control_url for light_control_url, light in self.Lights.items() if light['name'] == name]
        self._logger.debug("LightName2light_control_url() name: '{}', light_control_url: {}".format(name, light_control_urlArray))
        if not light_control_url:
            return None
        else:
            return light_control_urlArray[0]

    ##~~ SimpleApiPlugin mixin

    def get_api_commands(self):
        return dict(
            setLightValue=["light_control_url", "percentage"],
            getLightValues=[],
        )

    def on_api_command(self, command, data):
        if command == "setLightValue":
            try:
                light_control_url = data["light_control_url"]
                value = data["percentage"]
                self.set_light_value(light_control_url, value)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                self._logger.error("exception in setLightValue(): {}".format(exc_type))
                self._logger.error("TraceBack: {}".format(traceback.extract_tb(exc_tb)))
        elif command == "getLightValues":
            self.send_light_values()

    def on_api_get(self, request):
        self._logger.debug("on_api_get({}).Json: ".format(request, request.get_json()))
        if request == "getLightValues":
            response = dict()
            for light_control_url in self.Lights:
                response(light_control_url=self.get_light_value(light_control_url))
            return flask.jsonify(response)

    def is_api_adminonly(self):
        return True

    ##~~ EventHandlerPlugin mixin

    def on_event(self, event, payload):
        if event == Events.CONNECTED:
            # Client connected. Send current UI settings:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onConnectValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onConnectValue'])
        elif event == Events.DISCONNECTED:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onDisconnectValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onDisconnectValue'])
        elif event == Events.PRINT_STARTED:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onPrintStartValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onPrintStartValue'])
        elif event == Events.PRINT_PAUSED:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onPrintPausedValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onPrintPausedValue'])
        elif event == Events.PRINT_RESUMED:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onPrintResumedValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onPrintResumedValue'])
        elif event == Events.PRINT_DONE or event == Events.PRINT_CANCELLED or event == Events.PRINT_FAILED:
            for light_control_url in self.Lights:
                if self.Lights[light_control_url]['onPrintEndValue']:
                    self.set_light_value(light_control_url, self.Lights[light_control_url]['onPrintEndValue'])

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return dict (
            light_controls=[{
                'name': '',
                'light_control_url': None,
                'onOctoprintStartValue': '',
                'onConnectValue': '',
                'onDisconnectValue': '',
                'onPrintStartValue': '',
                'onPrintPausedValue': '',
                'onPrintResumedValue': '',
                'onPrintEndValue': ''
            }]
        )

    def checkLightControlEntryKeys(self, entry):
        return set(self.defaultEntry.keys()) == set(entry.keys())

    def updateLightControlEntry(self, entry):
        _entry = copy.deepcopy(self.defaultEntry)
        for key in entry:
            _entry[key]=entry[key]
        self._logger.info("Updated LightControlEntry from: {}, to {}".format(entry, _entry))
        return _entry

    def on_settings_initialized(self):
        LightControlsHttp_in = self._settings.get(["light_controls"])
        self._logger.debug("LightControlsHttp settings initialized: '{}'".format(LightControlsHttp_in))

        # Remove entries when their light_control_url is undefined to avoid errors later on.
        LightControlsHttp = [ctrl for ctrl in LightControlsHttp_in if (ctrl['light_control_url'] or -1) >= 0]

        # On initialization check for incomplete settings!
        modified=False
        for idx, ctrl in enumerate(LightControlsHttp):
            if not self.checkLightControlEntryKeys(ctrl):
                LightControlsHttp[idx] = self.updateLightControlEntry(ctrl)
                modified=True

            self.light_startup(LightControlsHttp[idx]["light_control_url"], LightControlsHttp[idx])

        if modified:
            self._settings.set(["light_controls"], LightControlsHttp)

        self._logger.debug("LightControlsHttp pruned settings after initialize: '{}'".format(LightControlsHttp))

    def on_settings_save(self, data):
        # Get old settings:

        # Get updated settings
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)

        # Cleanup old handles for lights that may be removed
        for light_control_url in list(self.Lights.keys()):
            self.light_cleanup(light_control_url)

        # Handle changes (if new != old)
        self._logger.debug("LightControlsHttp settings saved: '{}'".format(self._settings.get(["light_controls"])))
        for controls in self._settings.get(["light_controls"]):
            self.light_startup(controls["light_control_url"], controls)


    ##~~ StartupPlugin mixin

    def on_after_startup(self):
        for controls in self._settings.get(["light_controls"]):
            self.light_startup(controls["light_control_url"], controls)

        # Set all default Octoprint Startup values if available:
        for light_control_url in self.Lights:
            if self.Lights[light_control_url]['onOctoprintStartValue']:
                self.set_light_value(light_control_url, self.Lights[light_control_url]['onOctoprintStartValue'])


    ##~~ ShutdownPlugin mixin

    def on_shutdown(self):
        for light_control_url in list(self.Lights.keys()):
            self.light_cleanup(light_control_url)
        self._logger.debug("LightControlsHttp shutdown")


    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/LightControlsHttp.js"],
        }


    ##~~ TemplatePlugin mixin

    def get_template_configs(self):
        return [
            dict(type="settings", template="LightControlsHttp_settings.jinja2", custom_bindings=True),
            dict(type="generic", template="LightControlsHttp.jinja2", custom_bindings=True)
        ]


    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "LightControlsHttp": {
                "displayName": "LightControlsHttp Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "RoboMagus",
                "repo": "OctoPrint-LightControlsHttp",
                "current": self._plugin_version,

                "stable_branch": {
                    "name": "Stable",
                    "branch": "main",
                    "comittish": ["main"],
                },
                "prerelease_branches": [
                    {
                        "name": "Release Candidate",
                        "branch": "RC",
                        "comittish": ["RC", "main"],
                    },
                    {
                        "name": "Development",
                        "branch": "dev",
                        "comittish": ["dev", "RC", "main"],
                    }
                ],

                # update method: pip
                "pip": "https://github.com/RoboMagus/OctoPrint-LightControlsHttp/archive/{target_version}.zip",
            }
        }

    
    ##~~ Atcommand hook

    def atcommand_handler(self, _comm, _phase, command, parameters, tags=None, *args, **kwargs):
        if command != "LIGHTCONTROL":
            return

        [light, value, *_] = parameters.split() + ["", ""]
        self._logger.debug(f"@Command. Light: '{light}', Value: {value}")
        
        if light and value:
            light_control_url = self.LightName2light_control_url(light)
            self.set_light_value(light_control_url, clamp(int(value), 0, 100))
        else:
            self._logger.warning("@Command incomplete! Needs format '@LIGHTCONTROL [LightName] [LightValue]'")

        return None # No further actions required

        
    ##~~ Helper functions

    def ext_get_light_names(self):
        """
        Get light names
        :return: array of light names
        """
        val = [light['name'] for (light_control_url, light) in self.Lights.items()]
        self._logger.info("EXT. get_light_names(): {}".format(val))
        return val

    def ext_get_light_value(self, light_name=None):
        """
        Get light value from provided light name
        :param light_name: Name of the light
        :return: value from 0 to 100
        """
        light_control_url = self.LightName2light_control_url(light_name)
        val = self.get_light_value(light_control_url)
        self._logger.info("EXT. get_light_value(light_name: '{}'): {}".format(light_name, val))
        return val

    def ext_set_light_value(self, light_name=None, light_value=0):
        """
        Sets light value for provided light name
        :param light_name: Name of the light
        :param light_value: value for the light (0 to 100)
        :return: set value if successful, None otherwise.
        """
        self._logger.info(f"EXT. set_light_value(light_name: '{light_name}', light_value: {light_value})")
        if light_name and light_value != None:
            light_control_url = self.LightName2light_control_url(light_name)
            self.set_light_value(light_control_url, clamp(light_value, 0, 100))
            return self.get_light_value(light_control_url)

        return None


__plugin_name__ = "LightControlsHttp"
__plugin_pythoncompat__ = ">=3,<4" # only python 3

def __plugin_load__():
    plugin = LightControlsHttpPlugin()

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        get_light_names=plugin.ext_get_light_names,
        get_light_value=plugin.ext_get_light_value,
        set_light_value=plugin.ext_set_light_value
    )

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.atcommand.sending": __plugin_implementation__.atcommand_handler
    }
