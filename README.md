# Nova

A dumb agent with tools to help you every day (really me).

**install the ESP32 side at

Built on a ESP32 with a screen

Nova currently lets you fetch event from google calender, fetch google classroom assignment via calender ID, control your [Home Assistant](home-assistant.io), track a your PiHole Instance, and control your computer's volume.

- [ ] Timer Control
- [ ] Google calender
- [ ] Google Classroom
- [ ] Home assistant
- [ ] PiHole
- [ ] Computer volume
- [ ] Task Manager

Your passwords are stored in python Keyring. 

```bash
python3

import keyring
keyring.set_password("classroom-api", "your-email", "your-password")
keyring.set_password("calender-api", "your-email", "your-password")
```
