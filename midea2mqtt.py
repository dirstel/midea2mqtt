import logging
import json
import yaml
import time
import paho.mqtt.client as mqtt
from midea_beautiful import appliance_state

__VERSION__ = "Midea2MQTT v0.2.2"
_CONFIG_FILE = "/etc/opt/midea2mqtt/midea2mqtt.yml"

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

class midea2mqtt():

    def __init__(self):
        self.online = False
        self.refreshDelay = 60

        _LOGGER.info(__VERSION__)
        with open(_CONFIG_FILE) as file:
            try:
                data = yaml.safe_load(file)
                valid = True

            except yaml.YAMLError as exception:
                _LOGGER.info(f"unable to parse yaml from {configFile}")
                _LOGGER.info(exception)
                valid = False

        # valid = self._parseConfigGeneral(data["general"]) if valid else False
        valid = self._parseConfigMqtt(data["mqtt"]) if valid else False
        valid = self._parseConfigAppliances(data["devices"]) if valid else False
        valid = self._connectMqtt() if valid else False
        valid = self._connectAppliances() if valid else False

        _LOGGER.info(f"init complete: poll and publish every {self.refreshDelay} seconds")
        self.mqtt_client.loop_start()
        while True:
            time.sleep(self.refreshDelay)
            try:
                for topic, appliance in self.appliances.items():
                    _LOGGER.debug(f"accessing {topic} {type(appliance)}")
                    self.mqtt_client.publish(topic, appliance.refresh())
            except Exception as e:
                _LOGGER.error(e)

        self.mqtt_client.loop_stop()
        _LOGGER.info(f"main loop stopped")

    def _parseConfigGeneral(self, config):
        valid = False

        self.generalPollrate = config["pollrate"] if "pollrate" in config else 60
        self.generalLoglevel = config["loglevel"] if "loglevel" in config else ""

        return valid

    def _parseConfigMqtt(self, config):
        valid = False

        self.mqttBroker = config["broker"] if "broker" in config else ""
        if (type(self.mqttBroker) is str) and not (self.mqttBroker == ""):
            self.mqttPort = config["port"] if "port" in config else 1883
            self.mqttUsername = config["username"] if "username" in config else ""
            self.mqttPassword = config["password"] if "password" in config else ""
            self.mqttClientid = config["clientid"] if "clientid" in config else "midea2mqtt"
            self.mqttBasetopic = config["basetopic"] if "basetopic" in config else "midea"
            valid = True

        return valid

    def _parseConfigAppliances(self, config):
        applianceCount = 0

        self.appliances = dict()
        for config_entry in config:
            config_entry["topic"] = f"{self.mqttBasetopic}/{config_entry["topic"]}"
            newAppliance = midea_appliance(
                config_entry["topic"], config_entry["address"],
                config_entry["token"], config_entry["key"]
            )
            if newAppliance.valid:
                applianceCount += 1
                self.appliances[config_entry["topic"]] = newAppliance

        return(applianceCount > 0)

    def _connectAppliances(self):
        applianceOnlineCount = 0

        # loop through entries in self.appliances and connect per each entry
        for topic, appliance in self.appliances.items():
            if appliance.connect():
                applianceOnlineCount += 1
                self.mqtt_client.publish(topic, appliance.refresh())

        return(applianceOnlineCount > 0)

    def _connectMqtt(self):
        self.mqtt_client = mqtt.Client(
            client_id = self.mqttClientid, userdata = None, 
            callback_api_version = mqtt.CallbackAPIVersion.VERSION2
        )

        # callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        # TODO ? self.mqtt_client.on_disconnect = self._on_disconnect ?

        # enable TLS for secure connection
        # mqtt_client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)

        # set username and password if given
        # mqtt_client.username_pw_set(self.configMqtt["username"]}, self.configMqtt["password"]})

        self.online = self.mqtt_client.connect(self.mqttBroker, self.mqttPort) == 0
        return self.online

    def _on_message(self, client, userdata, msg):
        _LOGGER.debug(f"{msg.topic}: {msg.payload}")
        topic = msg.topic[:-4] # remove trailing 4 chars (/set) from topic
        if not topic in self.appliances:
            _LOGGER.warning(f"no midea appliance named {topic}")
        else:
            appliance = self.appliances[topic]
            if appliance.parseSetMsg(msg.payload):
                self.mqtt_client.publish(topic, appliance.refresh())

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            _LOGGER.error(f"Failed to connect to '{self.mqttBroker}' for reason '{reason_code}'.")
        else:
            _LOGGER.info(f"(re)connected to '{self.mqttBroker}':{self.mqttPort}")
            # (re)new subscriptions
            self._subscribeToTopic((self.mqttBasetopic, "set"))
            for topic in self.appliances:
                self._subscribeToTopic((topic, "set"))

    def _subscribeToTopic(self, topic):
        topic = "/".join(topic) if type(topic) is tuple else topic
        valid = (self.mqtt_client.subscribe(topic)[0] == 0)
        if valid:
            _LOGGER.info(f"succesfully subscribed to: {topic}")
        else:
            _LOGGER.warning(f"unable to subscribe to: {topic}")

        return(valid)



class midea_appliance():

    def __init__(self, topic, address, token, key):
        self.valid = False

        # TODO check parameter to decide weather its valid or not
        self.topic = topic
        self.address = address
        self.token = token
        self.key = key

        self.valid = True
        self._appliance = None # appliance will be Instantiated later

    def connect(self):
        if self.valid:
            self._appliance = appliance_state(
                address = self.address, token = self.token, key = self.key,
            )
            self._attribs = ["running", "fan_speed", "target_humidity", "ion_mode", "mode", 
                "current_humidity", "current_temperature", "tank_level", "tank_full",
                "model", "type", "name"]
            _LOGGER.info(f"connected device {self.topic}")
 
    def refresh(self):
        self._appliance.refresh()

        # prepare state as json (=> publish via mqtt)
        data = {}
        for attribute in self._attribs:
            data[attribute] = getattr(self._appliance.state, attribute)
        payload = json.dumps(data)
        _LOGGER.debug(self._appliance)

        return payload

    def parseSetMsg(self, payload):
        if self.valid and self._appliance.online:
            try:
                data = json.loads(payload)
                for key, value in data.items():
                    setattr(self._appliance.state, key, value)
                if self._appliance.state.needs_refresh:
                    self._appliance.apply()

            except yaml.YAMLError as exception:
                _LOGGER.error(f"parseSetMsg(): unable to parse yaml from {payload}")
                _LOGGER.debug(exception)

        return True

# Start app
mideaMqtt = midea2mqtt()
