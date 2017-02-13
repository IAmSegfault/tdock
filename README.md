# tdock
A Python script for docking your Thinkpad running Bumblebee.

Installation instructions for release 0.0.1 "It compiles, ship it!"
-------------------------------------------------------------------------------
1. Copy the included example config file either to /etc/tdock/tdock.conf or to ~/.config/tdock/tdock.conf
2. You will need to get the product id for your specific model dock by running `lsusb` on the terminal.
3. Put the value you found under the "PRODUCTID" field in decimal format.
4. Run `xrandr` on on your terminal and make note of the currently selected mode. If your external monitor is a different resolution than your laptop monitor, also make note of a matching output mode under your laptop output.
5. Place the output modes you found under the "UNDOCKED_MODE" and "DOCKED_MODE" fields in the "LAPTOP" object.
6. Run `intel-virtual-output && xrandr` while the laptop is hooked into the dock to get the correct virtual output and display modes for the external monitor.
7. Put the virtual output and mode under "OUTPUT" and "DOCKED_MODE" fields in the "MONITOR" object; also make sure to run `killall intel-virtual-output` to terminate the process you ran earlier.
8. Copy the tdock.py file to /usr/bin or some other directory where you store binary files, such as /opt
9. Set tdock.py to auto start on login using your desktop manager.
10. Have fun using a bigger-er monitor with your laptop!
