# midea2mqtt
This is a (simple) bridge between midea appliances and mqtt. It is inspirede by bridges like [zigbee2mqtt](https://github.com/Koenkk/zigbee2mqtt). I really like using mqtt as a message backbone to integrate different IOT architectures. The communication to the midea appliances is realized via [midea-beautiful-air](https://github.com/nbogojevic/midea-beautiful-air). You'll need to extract your local access credentials (token/key) as described there. 
This is a very first version and not well tested. In my home enverionment evereythings works fine, using a single appliance. You are very welcome to test and enhance. Using different appliances and exposing the right/useful state-information depends heavyly on having access to these appliances. My tests are done using a [Midea Cube 20](https://www.midea.com/de/klimatisieren-heizen/luftaufbereiter/luftentfeuchter-cube-20).

# MQTT
Each appliance will publish its state using the configured topic. To change settings add "/set" to the topic and publish the desired changes as json.

# Configuration
Edit mide2mqtt.yml and add your appliance(s) and credentials to access your mqtt broker.

# Docker
Build docker container: ./docker_build.sh
Run container: docker-compose up

# Notice
Midea, Inventor, Comfee', Pro Breeze, and other names are trademarks of their respective owners.
