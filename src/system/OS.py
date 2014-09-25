'''
Created on Sep 24, 2014

@author: gschoenb
'''

from abc import ABCMeta, abstractmethod
import subprocess
import logging
from string import split
import re
from os import lstat
from stat import S_ISBLK

class RAIDtec(object):
    '''
    Representing a RAID technology, used from the OS.
    '''
    __metaclass__ = ABCMeta

    def __init__(self, path):
        ## Path of the RAID utils
        self.__util = None
        ## Path of the raid device
        self.__path = path
        ## List of current RAID virtual drives
        self.__vds = None
        ## List of block Devices in OS
        self.__blockdevs = None

    def getUtil(self): return self.__util
    def getDevPath(self): return self.__path
    def getVDs(self): return self.__vds
    def getBlockDevs(self): return self.__blockdevs

    def setUtil(self, u):
        self.__util = u
    def setVDs(self, v):
        self.__vds = v

    def checkBlockDevs(self):
        '''
        Checks the current available block devices.
        Sets blockdevs of OS.
        '''
        out = subprocess.Popen(['lsblk', '-l', '-n', '-e', '7', '-e', '1', '-o', 'NAME'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = out.communicate()
        if stderr != '':
            logging.error("lsblk encountered an error: " + stderr)
            raise RuntimeError, "lsblk command error"
        else:
            self.__blockdevs = stdout.splitlines()

    @abstractmethod
    def initialize(self):
        ''' Initialize the specific RAID technology. '''
    @abstractmethod
    def checkRaidPath(self):
        ''' Checks if the virtual drive exists. '''
    @abstractmethod
    def checkVDs(self):
        ''' Check which virtual drives are configured. '''
    @abstractmethod
    def createVD(self, level, devices):
        ''' Create a virtual drive. '''
    @abstractmethod
    def deleteVD(self, vd, devices):
        ''' Delete a virtual drive. '''
    @abstractmethod
    def isReady(self, vd, devices):
        ''' Check if a virtual drive is ready. '''

class Mdadm(RAIDtec):
    '''
    Represents a linux software RAID technology.
    '''

    def initialize(self):
        '''
        Checks for mdadm and sets the util path.
        '''
        mdadm = subprocess.Popen(['which', 'mdadm'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout = mdadm.communicate()[0]
        if mdadm.returncode != 0:
            logging.error("# Error: command 'which mdadm' returned an error code.")
            raise RuntimeError, "which mdadm command error"
        else:
            self.setUtil(stdout.rstrip("\n"))

    def checkRaidPath(self):
        try:
            mode = lstat(self.getDevPath()).st_mode
        except OSError:
            return False
        else:
            return S_ISBLK(mode)

    def createVD(self, level, devices):
        args = [self.getUtil(), "--create", self.getDevPath(), "--quiet", "--metadata=default", str("--level=" + str(level)), str("--raid-devices=" + str(len(devices)))]
        for dev in devices:
            args.append(dev)
        logging.info("# Creating raid device "+self.getDevPath())
        logging.info("# Command line: "+subprocess.list2cmdline(args))
        ##Execute the commandline
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stderr = process.communicate()[1]
        if stderr != '':
            logging.error("mdadm encountered an error: " + stderr)
            raise RuntimeError, "mdadm command error"

class Storcli(RAIDtec):
    '''
    Represents a storcli based RAID technology.
    '''

    def initialize(self):
        '''
        Checks for the storcli executable and sets the path of storcli.
        '''
        storcli = subprocess.Popen(['which', 'storcli'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout = storcli.communicate()[0]
        if storcli.returncode != 0:
            storcli = subprocess.Popen(['which', 'storcli64'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            stdout = storcli.communicate()[0]
        if storcli.returncode != 0:
            logging.error("# Error: command 'which storcli' returned an error code.")
            raise RuntimeError, "which storcli command error"
        else:
            self.setUtil(stdout.rstrip("\n"))

    def checkVDs(self):
        '''
        Checks which virtual drives are configured.
        Sets VDs as a list of virtual drives.
        '''
        process1 = subprocess.Popen([self.getUtil(), '/call', '/vall', 'show'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process2 = subprocess.Popen(['awk', 'BEGIN{RS=ORS=\"\\n\\n\";FS=OFS=\"\\n\\n\"}/TYPE /'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=process1.stdout)
        process3 = subprocess.Popen(['awk', '/^[0-9]/{print $1}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=process2.stdout)
        process1.stdout.close()
        process2.stdout.close()
        (stdout, stderr) = process3.communicate()
        if process3.returncode != 0:
            logging.error("storcli encountered an error: " + stderr)
            raise RuntimeError, "storcli command error"
        else:
            self.setVDs(stdout.splitlines())

    def createVD(self, level, devices):
        '''
        Creates a virtual drive from a given raid level and a list of
        enclosure:drive IDs.
        @param level The desired raid level
        @param devices The list of raid devices as strings, e.g. ['e252:1','e252:2']
        ''' 
        encid = split(devices[0], ":")[0]
        args = [self.getUtil(), '/c0', 'add', 'vd', str('type=r' + str(level))]
        devicearg = "drives=" + encid + ":"
        for dev in devices:
            devicearg += split(dev, ":")[1] + ","
        args.append(devicearg.rstrip(","))
        logging.info("# Creating raid device with storcli")
        logging.info("# Command line: "+subprocess.list2cmdline(args))
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout,stderr) = process.communicate()
        if process.returncode != 0:
            logging.error("storcli encountered an error: " + stderr)
            raise RuntimeError, "storcli command error"
        else:
            logging.info(stdout)

    def deleteVD(self, vd, devices=None):
        '''
        Deletes a virtual drive.
        @param vd The ID of the virtual drive, e.g. 0/0.
        '''
        match = re.search('^[0-9]\/([0-9]+)',vd)
        vdNum = match.group(1)
        storcli = subprocess.Popen([self.getUtil(),'/c0/v'+vdNum, 'del', 'force'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stderr = storcli.communicate()[1]
        if storcli.returncode != 0:
            logging.error("storcli encountered an error: " + stderr)
            raise RuntimeError, "storcli command error"
        else:
            logging.info("# Deleting raid device VD "+vdNum)

    def isReady(self, vd, devices):
        '''
        Checks if a virtual device is ready, i.e. if no rebuild on any PDs is running
        and if not initializarion process is going on.
        @param vd ID of the VD, e.g. 0/0.
        @param devices Array of enclosusre:PD IDs, e.g. ['e252:1','e252:2']
        @return True if VD is ready, False if not
        '''
        ready = None
        storcli = subprocess.Popen([self.getUtil(),'/c0/eall/sall', 'show', 'rebuild'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = storcli.communicate()
        if storcli.returncode != 0:
            logging.error("storcli encountered an error: " + stderr)
            raise RuntimeError, "storcli command error"
        else:
            for line in stdout.splitlines():
                match = re.search('^\/c0\/e([0-9]+\/s[0-9]+).*$',line)
                if match != None:
                    for d in devices:
                        d = d.replace(':','/s')
                        if d == match.group(1):
                            logging.info(line)
                            status = re.search('Not in progress',line)
                            if status != None:
                                ready = True
                            else:
                                ready = False
        match = re.search('^[0-9]\/([0-9]+)',vd)
        vdNum = match.group(1)
        storcli = subprocess.Popen([self.getUtil(),'/call', '/v'+vdNum, 'show', 'init'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout, stderr) = storcli.communicate()
        if storcli.returncode != 0:
            logging.error("storcli encountered an error: " + stderr)
            raise RuntimeError, "storcli command error"
        else:
            for line in stdout.splitlines():
                match = re.search(vdNum+' INIT',line)
                if match != None:
                    logging.info(line)
                    status = re.search('Not in progress',line)
                    if status != None:
                        ready = True
                    else:
                        ready = False
        return ready