# Third Eye

Third Eye is an end 2 end Scene Monitoring System, designed to run fully on a resource constraint device.

The key benefits of such an approach are:
- enhanced security
- data privacy
- portability
- low cost, and low power consumption

Third Eye can:
- analyse a scene 
- perform motion detection & object detection
- collect data and show useful statistics
- trigger security alerts when it's required
- **Coming Soon:** talk to system via sms or email (disarm, arm, enable video stream)

It can be also hacked, fully configured and adapted to any environment.

Ya, ya ... there are plenty of repos with similar projects out there, but it's fun to build you own one,
with the additional benefit of understanding what's going on under the hood, and full control.

Plus it's all modern, without much additional overhead and complexity.

100% of source code is written in Python, including configuration, HTML and CSS (with the help of Streamlit),
so there is not much context switching and brain farting.

## Hardware

Let's talk hardware, shall we?

Even though, it would be quite trivial to adapt this app to any OS and hardware, it has been developed, tailored and
tested on resource constraint devices, like Raspberry PI.

Here is a list of components needed to complete the project in its ideal setup. 

- Raspberry PI (ideally RPi4) + case (connected via Ethernet or Wi-Fi)
- USB camera (or optionally Wi-Fi camera)
- Power supply or POE splitter
- Google Coral USB accelerator
- Micro-SD Card
- HDMI -> MicroHDMI adapter
- 5 Kilo of human brain (for potential camera or network troubleshooting) ;-D

## Installation

- Raspbian
- Virtual env
- Clone repo
- Supervisor
- Crontab

TODO: Add more details here...

## Project file structure

Whole application source is in the `src` folder.

2 main modules:
- backend.py - this is the heart of the app where image processing, and alert triggering is happening
- frontend.py - this is the front end, where we can see the live feed and data visualisations

Other supporting modules:
- config.py - app configuration
- database.py - database connection (currently SQLite seems to be sufficient)
- detections.py - provide trending datasets about historical detections (and some detections related functions)
- models.py - SQL Alchemy models and DB creation
- object_tracker.py - object tracking
- security.py - check if alerts need to be triggered based on defined criteria and configuration, and send SMS and email alerts

Standalone scripts:
- rand_data_generator.py - generate some synthetic data in dev, which will populate plots
- rec_video.py - record video clip from the video stream 
- rpi_stats.py - record Raspberry PI temperature and voltage stats (useful when overclocking) 
- device_finder.py - find devices currently connected to the local network

ML models:
- models/ contains labels and ssd_mobilenet model for object detection inference

Other:
- images folder
- database folder
- logs folder

The 3 folders listed above should be created somewhere outside the source code, so if source code gets wiped, they will
stay in place. The first 2 folders can be configured via the config file.

The `logs` folder is configured in CronJobs and Supervisor (see the Installation section).

## Overclocking RPi

It is possible to give RPi a little boost, but do it **at your risk**.

See this great [article](https://magpi.raspberrypi.org/articles/how-to-overclock-raspberry-pi-4) for more info on
that, and monitor your CPU temperature to avoid a nasty Cowabunga!

## Contributions/Feedback

Any feedback is totally welcome. I did this project 100% during my spare time, so there are certainly many aspects,
which can be improved.

Please send a mail to [app.thirdeye@gmail.com](mailto:app.thirdeye@gmail.com) or create a PR.

## Acknowledgements

This project would not be possible if not many lessons and courses available at [PyImageSearch](https://www.pyimagesearch.com/).

## License

MIT

Copyright 2021 Alchemication

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.