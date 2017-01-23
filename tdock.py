#!/usr/bin/python
import sys
import json
import subprocess
import time
import signal
import daemon
import syslog
import usb.core
import pyudev as udev
from os import getpid, getuid , kill
from os.path import expanduser


class ThinkDaemon(object):
    def __init__(self):
        self.dev = None
        self.hwobserver = None
        self.vdriver = None
        self.dock_state = False
        self.dock_vendor = None
        self.dock_product = None
        self.eoutput = []
        self.emode = []
        self.eposition = []
        self.monitor = {}
        self.output_state = {}
        self.loutput = None
        self.ldock_mode = None
        self.lundock_mode = None
        self.lstate = False
        self.off_ondock = False
        self.laptop = None
        self.laptop_state = True

    def eventhandler(self, action, device):
        dev_conn = None
        dev_conn = usb.core.find(idVendor=self.dock_vendor, idProduct=self.dock_product)

        # Note: Only use an explicit equality check here.
        if action == "add" and self.dock_state == False:
            if dev_conn is not None:
                self.dev = dev_conn
                self.dock_state = True
                self.connect()

        # Note: Here also.
        elif action == "remove" and self.dock_state == True:
            self.dev = None
            self.dock_state = False
            self.disconnect()

    def cleanup(self, signum=None, frame=None):
        syslog.syslog('uid[%s]: Signal handler called with signal %s' % (getuid(), signum))
        if self.hwobserver is not None:
            self.hwobserver.send_stop()
        if self.vdriver is not None:
            subprocess.Popen(["killall", "intel-virtual-output"]).wait(10)
        time.sleep(60.0 / 1000.0)
        sys.exit(0)

    def connect(self):
        subprocess.Popen(["xrandr", "--output", self.loutput, "--mode", self.ldock_mode])
        self.vdriver = subprocess.Popen(["intel-virtual-output"])
        self.vdriver.wait(timeout=15)
        for entry in self.eoutput:
            index = self.eoutput.index(entry)
            # TODO: Replace these subrocess calls with Xlib. Scraping output from xrandr like this is somewhat absurd.
            # TODO: Also replace  the subprocess calls in the initdaemon function.
            xrandr = subprocess.Popen(["xrandr", "-q"], stdout=subprocess.PIPE)
            display = subprocess.Popen(["grep", "-i", self.emode[index]], stdin=xrandr.stdout, stdout=subprocess.PIPE)
            state = subprocess.Popen(["grep", "-o", "*"], stdin=display.stdout, stdout=subprocess.PIPE)
            status = state.stdout.read().decode().rstrip()
            if status == "*":
                self.output_state[entry] = True
            else:
                self.output_state[entry] = False
            state.kill()
            display.kill()
            xrandr.kill()

        for entry, state in self.output_state.items():
            if state is False:
                index = self.eoutput.index(entry)
                position = self.eposition[index].lower()
                mode = self.emode[index]
                if position == "mirror":
                    screen = subprocess.Popen(["xrandr", "--output", entry, "--mode", mode])
                    screen.wait(timeout=15)
                    self.output_state[entry] = True
                    # TODO: Add handlers for right-of and left-of options.

    def disconnect(self):
        for output in self.eoutput:
            subprocess.Popen(["xrandr", "--output", output, "--off"]).wait(15)

        # TODO: It looks like intel-virtual output forks itself. We call killall here to kill the process by name.
        # We should however find a way to get the pid of the child so we can kill it directly.
        # self.vdriver.terminate()
        subprocess.Popen(["killall", "intel-virtual-output"])
        self.vdriver = None
        subprocess.Popen(["xrandr", "--output", self.loutput, "--mode", self.lundock_mode]).wait(15)


def initdaemon(tdock, config):
    tdock.dock_vendor = config["DOCK"]["VENDORID"]
    tdock.dock_product = config["DOCK"]["PRODUCTID"]
    tdock.laptop = config["LAPTOP"]
    tdock.loutput = config["LAPTOP"]["OUTPUT"]
    tdock.ldock_mode = config["LAPTOP"]["DOCKED_MODE"]
    tdock.lundock_mode = config["LAPTOP"]["UNDOCKED_MODE"]
    tdock.eoutput = config["MONITOR"]["OUTPUT"]
    tdock.emode = config["MONITOR"]["DOCKED_MODE"]
    tdock.eposition = config["MONITOR"]["DISPLAY_POSITION"]
    tdock.monitor = config["MONITOR"]

    tdock.dev = usb.core.find(idVendor=tdock.dock_vendor, idProduct=tdock.dock_product)
    if tdock.dev is not None:
        tdock.dock_state = True
        if tdock.dock_state is True:
            if tdock.laptop["BUMBLEBEE"] is True:
                tdock.connect()
            if tdock.off_ondock is True:
                subprocess.Popen(["xrandr", "--output", tdock.loutput, "--off"])
                tdock.laptop_state = False
        else:
            subprocess.Popen(["xrandr", "--output", tdock.loutput, "--mode", tdock.lundock_mode])


def rundaemon():
    tdockd = ThinkDaemon()
    proc_context = daemon.DaemonContext()
    cleanup = tdockd.cleanup
    sigs = {signal.SIGTERM: cleanup, signal.SIGQUIT: cleanup, signal.SIGINT: cleanup, signal.SIGHUP: cleanup}
    proc_context.signal_map = sigs
    syslog.syslog("tdockd started with PID %s as user %s" % (getpid(), getuid()))

    config_path = "/etc/tdock/"
    config_upath = expanduser("~") + "/.config/tdock/"
    config_file = config_path + "tdock.conf"
    uconfig_file = config_upath + "tdock.conf"

    try:
        with open(uconfig_file) as conf:
            config = json.load(conf)
        if config is not None:
            initdaemon(tdockd, config)

    except FileNotFoundError as e:
        try:
            syslog.syslog("tdockd: uid[%s] does not have a user config file." % getuid())
            with open(config_file) as conf:
                config = json.load(conf)
            if config is not None:
                initdaemon(tdockd, config)
        except FileNotFoundError as e:
            syslog.syslog("tdockd: Can't read config file; exiting with return code 1")
            sys.exit(1)

    context = udev.Context()
    monitor = udev.Monitor.from_netlink(context)
    monitor.filter_by('usb')
    tdockd.hwobserver = udev.MonitorObserver(monitor, tdockd.eventhandler)
    tdockd.hwobserver.start()

    while True:
        time.sleep(6)

if __name__ == "__main__":
    rundaemon()
