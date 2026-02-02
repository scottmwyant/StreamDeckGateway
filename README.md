# Streamdeck

This project captures events from a Streamdeck Mk.2 and relays events to an MQTT broker.

## Submodules

This project pulls source for dependencies rather than installing the dependencies with a package manager.

`git submodule add https://github.com/apmorton/pyhidapi`

`git submodules add https://github.com/eclipse-paho/paho.mqtt.python`

## Install as a service

1. Create a Unit file for the *streamdeck* service.
2. Reload systemd to pick up the new file.
3. Enable the service (will run at next boot)
4. Start the service (run immidiately)
5. View logs in system journal

```
sudo nano /etc/systemd/system/streamdeck.service
sudo systemctl daemon-reload
sudo systemctl enable streamdeck
sudo systemctl start streamdeck
journalctl -u streamdeck -f
```

/etc/systemd/system/streamdeck.service 
```
[Unit]
Description=Stream Deck Gateway
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/streamdeck/src/main.py
WorkingDirectory=/home/pi/streamdeck
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target

```
