# Third Eye

Third Eye is a full end 2 end Scene Monitoring System.

It can:
- analyse a scene 
- perform motion detection & object detection
- collect data and show useful statistics
- trigger security alerts when it's required

Ya, ya ... there are plenty of repos with similar projects out there, but it's fun to build you own one,
with the additional benefit of understanding what's going on under the hood, and full control.

Plus it's all modern, without much additional overhead and complexity.

All code is produced in Python, including configuration, HTML and CSS (with the help of Streamlit), so there is
not much context switching and brain farting as a result.

## Hardware

Let's talk hardware, shall we?

Here is the list of components needed to complete the project

- Raspberry PI (ideally RPi4) + case
- USB camera (or optionally Wi-Fi camera)
- Power supply or POE splitter
- Google Coral USB accelerator
- Micro-SD Card
- HDMI -> MicroHDMI adapter
- 5 Kilo of human brain (for potential camera or network troubleshooting)

## Installation (TODO)

- Raspbian
- Virtual env
- Supervisor
- Crontab

## Scripts in the repo (TODO)

## Overclocking RPi

It is possible to give RPi a little boost, but do it **at your risk**.

See this great [article](https://magpi.raspberrypi.org/articles/how-to-overclock-raspberry-pi-4) for more info on
that, and monitor your CPU temperature to avoid a nasty Cowabunga!

## License:

MIT

Copyright 2021 Alchemication

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.