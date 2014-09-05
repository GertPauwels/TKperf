'''
Created on 07.08.2012

@author: gschoenb
'''
__version__ = '1.3'

import logging
import subprocess
from lxml import etree
import json
import datetime
import os
import time

import perfTest.SsdTest as ssd
import perfTest.DeviceTests as tests
import perfTest.HddTest as hdd
from reports.XmlReport import XmlReport
from reports.RstReport import RstReport
import plots.genPlots as pgp
from perfTest.Devices import SSD
from perfTest.Options import Options

class PerfTest(object):
    '''
    A performance test, consists of multiple Device Tests
    '''
    
    def __init__(self,testname,device):
        '''
        A performance test has several reports and plots.
        @param testname Name of the performance test
        @param device A Device object, the device to run tests on
        '''
        ## The output file for the fio job test results.
        self.__testname = testname
        
        ## The device object to run test on.
        self.__device = device
        
        ## Xml file to write test results to
        self.__xmlReport = XmlReport(self.__testname)
        
        ## Rst file to generate pdf of
        self.__rstReport = RstReport(self.__testname)
        
        ## Dictionary of tests to carry out
        self.__tests = {}
        
        ## Date the test has been carried out
        self.__testDate = None
        
        ## Per default use the version from main module
        self.__IOPerfVersion = __version__

        ## Information about the used operating system
        self.__OSInfo = {}
        self.collOSInfos()

        ## Hold the command line used to call the test
        self.__cmdLineArgs = None

    def getTestname(self): return self.__testname
    def getDevice(self): return self.__device
    def getTestDate(self): return self.__testDate
    def getIOPerfVersion(self): return self.__IOPerfVersion
    def getCmdLineArgs(self): return self.__cmdLineArgs
    def getOSInfo(self): return self.__OSInfo
    def getTests(self): return self.__tests
    def getXmlReport(self): return self.__xmlReport
    def getRstReport(self): return self.__rstReport

    def collOSInfos(self):
        '''
        Collects some information about the current OS in use
        @return True if all infos are present, False on error
        '''
        out = subprocess.Popen(['uname','-r'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout,stderr) = out.communicate()
        if stderr != '':
            logging.error("uname -r encountered an error: " + stderr)
            return False
        else:
            self.__OSInfo['kernel'] = stdout
        #Check if we are on red hat based distributions
        if os.path.isfile('/etc/redhat-release'):
            out = subprocess.Popen(['cat','/etc/redhat-release'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        else:
            out = subprocess.Popen(['lsb_release','-d'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        (stdout,stderr) = out.communicate()
        if stderr != '':
            logging.error("getting OS information encountered an error: " + stderr)
            return False
        else:
            self.__OSInfo['lsb'] = stdout
        return True

    def readCmdLineArgs(self,argv):
        '''
        Reads the command line argument list argv and sets it as
        __cmdLineArgs
        @param argv The command line argument list
        '''
        self.__cmdLineArgs = ''
        for arg in argv:
            self.__cmdLineArgs += (arg + ' ')
        self.__cmdLineArgs = self.__cmdLineArgs.rstrip()

    def setOSInfo(self,key,value):
        '''
        Sets the current OS information.
        @param key A key to be used in the OS info dict.
        @param value The value being assigned to the key.
        '''
        if value != None:
            self.__OSInfo[key] = value

    def setTestDate(self,dateStr):
        '''
        Sets the date the test has been carried out.
        @param dateStr The date string.
        '''
        self.__testDate = dateStr

    def setIOPerfVersion(self,verStr):
        '''
        Sets the current io perf version.
        @param verStr The version string.
        '''
        self.__IOPerfVersion = verStr

    def setCmdLineArgs(self,cmdLineStr):
        '''
        Sets the command line arg string.
        @param cmdLineStr The command line string
        '''
        self.__cmdLineArgs = cmdLineStr

    def addTest(self,key,test):
        '''
        Add a test to the test dictionary.
        @param key The key for the test in the dictionary.
        @param test The test object to be added.
        '''
        self.__tests[key] = test
    
    def resetTests(self):
        '''
        Clear the dictionary containing the tests.
        '''
        self.__tests.clear()

    def initialize(self):
        '''
        Initialize the given tests, this sets the device and Fio
        init params for all tests.
        '''
        sorted(self.__tests.items())
        for k,v in self.__tests.items():
            logging.info("# Initialiazing test "+k)
            v.initialize()

    def runTests(self):
        '''
        Call the run method of every test in the test dictionary. The run method
        of a test is its core function where the performance test is carried out.
        '''
        #sort per key to ensure tests have the same order
        sorted(self.__tests.items())
        for k,v in self.__tests.items():
            print "Starting test: " + k
            #before each test sleep, to ensure device operations of previous
            #tests are finished
            logging.info("# Sleeping for 15 seconds...")
            time.sleep(15)
            v.run()

    def genPlots(self):
        sorted(self.__tests.items())
        for k,v in self.__tests.items():
            logging.info("# Generating plots for "+k+" test")
            v.genPlots()

    def toXml(self):
        '''
        First the device information is written to the xml file.
        Calls for every test in the test dictionary the toXMl method
        and writes the results to the xml file.
        '''
        tests = self.getTests()
        e = self.getXmlReport().getXml()
        # Add the current date to the xml
        if self.__testDate != None:
            dev = etree.SubElement(e,'testdate')
            dev.text = json.dumps(self.__testDate)
        # Add the device information to the xml file
        self.getDevice().toXml(e)
        # Add OS information
        if self.__OSInfo != None:
            if 'kernel' in self.__OSInfo:
                dev = etree.SubElement(e,'kernel')
                dev.text = json.dumps(self.__OSInfo['kernel'])
            if 'lsb' in self.__OSInfo:
                dev = etree.SubElement(e,'lsb')
                dev.text = json.dumps(self.__OSInfo['lsb'])
        # Add the current test suite version to the xml file
        dev = etree.SubElement(e,'ioperfversion')
        dev.text = json.dumps(self.__IOPerfVersion)
        # Add the command line to xml
        if self.__cmdLineArgs != None:
            dev = etree.SubElement(e,'cmdline')
            dev.text = json.dumps(self.__cmdLineArgs)
        # Add Fio version to xml, only take it from one test
        self.__tests.itervalues().next().getFioJob().appendXml(e)
        # Add the options to xml, only take it from one test
        self.__tests.itervalues().next().getOptions().appendXml(e)
        # Call the xml function for every test in the dictionary
        sorted(self.__tests.items())
        for k,v in tests.iteritems():
            e.append(v.toXml(k))
        self.getXmlReport().xmlToFile(self.getTestname())

    def fromXml(self):
        '''
        Reads out the xml file name 'testname.xml' and initializes the test
        specified with xml. The valid tags are "iops,lat,tp,writesat" for ssd,
        "iops, tp" for ssd. But there isn't always every test run, so xml can
        miss a test.
        '''
        self.getXmlReport().fileToXml(self.getTestname())
        self.resetTests()
        root = self.getXmlReport().getXml()

        if(root.findtext('testdate')):
            self.setTestDate(json.loads(root.findtext('testdate')))
        else:
            self.setTestDate('n.a.')
        # Read the operating system information
        if(root.findtext('kernel')):
            self.setOSInfo('kernel',json.loads(root.findtext('kernel')))
        else:
            self.setOSInfo('kernel','n.a.')
        if(root.findtext('lsb')):
            self.setOSInfo('lsb',json.loads(root.findtext('lsb')))
        else:
            self.setOSInfo('lsb','n.a.')
        # Read version and command line
        if(root.findtext('ioperfversion')):
            self.setIOPerfVersion(json.loads(root.findtext('ioperfversion')))
        if(root.findtext('cmdline')):
            self.setCmdLineArgs(json.loads(root.findtext('cmdline')))
        else:
            self.setCmdLineArgs('n.a.')
        # Read the Fio Version
        if(root.findtext('fioversion')):
            fioVersion = json.loads(root.findtext('fioversion'))
        else:
            fioVersion = 'n.a.'
        # Read used options
        options = Options(None,None)
        options.fromXml(root)
        # Initialize device and performance tests
        if isinstance(self, SsdPerfTest):
            device = SSD('ssd',None,self.getTestname()) 
            device.fromXml(root)
            for tag in SsdPerfTest.testKeys:
                #check which test tags are in the xml file
                for elem in root.iterfind(tag):
                    test = None
                    if elem.tag == SsdPerfTest.iopsKey:
                        test = tests.SsdIopsTest(self.getTestname(),device,options)
                    if elem.tag == SsdPerfTest.latKey:
                        test = tests.SsdLatencyTest(self.getTestname(),device,options)
                    if elem.tag == SsdPerfTest.tpKey:
                        test = tests.SsdTPTest(self.getTestname(),device,options)
                    if elem.tag == SsdPerfTest.wrKey:
                        test = tests.SsdWriteSatTest(self.getTestname(),device,options)
                    #we found a tag in the xml file, now we can read the data from xml
                    if test != None:
                        test.fromXml(elem)
                        test.getFioJob().setFioVersion(fioVersion)
                        self.addTest(tag, test)
            #TODO Add HDD test here

class SsdPerfTest(PerfTest):
    '''
    A performance test for ssds consists of all ssd tests
    '''
    ## Keys valid for tests
    iopsKey = 'iops'
    latKey = 'lat'
    tpKey = 'tp'
    wrKey = 'writesat'
    ## Keys for the tests carried out
    testKeys = [iopsKey,latKey,tpKey,wrKey]

    def __init__(self,testname,device,options=None):
        PerfTest.__init__(self, testname, device)
        #Add current date to test
        now = datetime.datetime.now()
        self.setTestDate(now.strftime("%Y-%m-%d"))
        #Add every test to the performance test
        for testType in SsdPerfTest.testKeys:
            if testType == SsdPerfTest.iopsKey:
                test = tests.SsdIopsTest(testname,device,options)
            if testType == SsdPerfTest.latKey:
                test = tests.SsdLatencyTest(testname,device,options)
            if testType == SsdPerfTest.tpKey:
                test = tests.SsdTPTest(testname,device,options)
            if testType == SsdPerfTest.wrKey:
                test = tests.SsdWriteSatTest(testname,device,options)
            #Add the test to the key/value structure
            self.addTest(testType, test)

    def run(self):
        self.runTests()
        self.toXml()
        self.genPlots()
        self.toRst()

    def toRst(self):
        tests = self.getTests()
        rst = self.getRstReport()
        
        rst.addFooter()
        rst.addTitle()
        rst.addDevInfo(self.getDevInfo(),self.getFeatureMatrix())
        rst.addCmdLine(self.getCmdLineArgs())
        
        #add the fio version, nj, iod and general info of one test to the report
        for keys in tests.iterkeys():
            rst.addSetupInfo(self.getIOPerfVersion(),tests[keys].getFioJob().getFioVersion(),
                             self.getTestDate())
            rst.addFioJobInfo(tests[keys].getNj(), tests[keys].getIod())
            rst.addOSInfo(self.getOSInfo())
            rst.addGeneralInfo('ssd')
            break
        
        if SsdPerfTest.iopsKey in tests:
            rst.addChapter("IOPS")
            rst.addTestInfo('ssd','iops',tests['iops'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['iops'].getFigures()):
                rst.addFigure(fig,'ssd','iops',i)
            rst.addSection("Measurement Window Summary Table")
            rst.addTable(tests['iops'].getTables()[0],ssd.IopsTest.bsLabels,'iops')
        if SsdPerfTest.tpKey in tests:
            rst.addChapter("Throughput")
            rst.addTestInfo('ssd','tp',tests['tp'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['tp'].getFigures()):
                rst.addFigure(fig,'ssd','tp',i)
            rst.addSection("Measurement Window Summary Table")    
            rst.addTable(tests['tp'].getTables()[0],ssd.TPTest.bsLabels,'tp')
        if SsdPerfTest.latKey in tests:
            rst.addChapter("Latency")
            rst.addTestInfo('ssd','lat',tests['lat'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['lat'].getFigures()):
                #index 2 and 3 are 2D measurement plots that are not required
                #but we need them to generate the measurement overview table
                if i == 2 or i == 3: continue
                rst.addFigure(fig,'ssd','lat',i)
            rst.addSection("Measurement Window Summary Table")    
            rst.addTable(tests['lat'].getTables()[0],ssd.LatencyTest.bsLabels,'avg-lat')#avg lat 
            rst.addTable(tests['lat'].getTables()[1],ssd.LatencyTest.bsLabels,'max-lat')#max lat
        if SsdPerfTest.wrKey in tests:
            rst.addChapter("Write Saturation")
            rst.addTestInfo('ssd','writesat',tests['writesat'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['writesat'].getFigures()):
                rst.addFigure(fig,'ssd','writesat',i)

        rst.toRstFile()

class HddPerfTest(PerfTest):
    '''
    A performance test for hdds consists of all hdd tests.
    '''
    
    ## Keys valid for test dictionary and xml file
    testKeys = ['iops','tp']
    ## Keys valid for tests
    iopsKey = 'iops'
    tpKey = 'tp'
    
    def __init__(self,testname,devicename, nj, iod):
        PerfTest.__init__(self, testname, devicename)
        
        ## Number of jobs for fio.
        self.__nj = nj
        
        ## Number of iodepth for fio.
        self.__iod = iod
        
        #Add current date
        now = datetime.datetime.now()
        self.setTestDate(now.strftime("%Y-%m-%d"))
        
                #Add every test to the performance test
        for testType in HddPerfTest.testKeys:
            if testType == HddPerfTest.iopsKey:
                test = hdd.IopsTest(testname,devicename,nj,iod)
            if testType == HddPerfTest.tpKey:
                test = hdd.TPTest(testname,devicename,nj,iod)
            #add the test to the key/value structure
            self.addTest(testType, test)
        
    def run(self):
        self.runTests()
        self.toXml()
        self.getPlots()
        self.toRst()
    
    def fromXml(self):
        '''
        Reads out the xml file name 'testname.xml' and initializes the test
        specified with xml. The valid tags are "iops,tp", but
        there don't must be every tag in the file.
        Afterwards the plotting and rst methods for the specified tests are
        called.
        '''
        self.getXmlReport().fileToXml(self.getTestname())
        self.resetTests()
        root = self.getXmlReport().getXml()

        if(root.findtext('testdate')):
            self.setTestDate(json.loads(root.findtext('testdate')))

        #first read the device information from xml
        self.setDevInfo(json.loads(root.findtext('devinfo')))
        
        #read the feature matrix from the xml file
        if(root.findtext('featmatrix')):
            self.setFeatureMatrix(json.loads(root.findtext('featmatrix')))
            
        #read the operating system information
        if(root.findtext('kernel')):
            self.setOSInfo('kernel',json.loads(root.findtext('kernel')))
        if(root.findtext('lsb')):
            self.setOSInfo('lsb',json.loads(root.findtext('lsb')))
        
        #first read the device information from xml
        if(root.findtext('ioperfversion')):
            self.setIOPerfVersion(json.loads(root.findtext('ioperfversion')))
            
        if(root.findtext('cmdline')):
            self.setCmdLineArgs(json.loads(root.findtext('cmdline')))
        else:
            self.setCmdLineArgs('n.a.')  

        for tag in HddPerfTest.testKeys:
            for elem in root.iterfind(tag):
                test = None
                if elem.tag == HddPerfTest.iopsKey:
                    test = hdd.IopsTest(self.getTestname(),self.getDevName(),self.__nj,self.__iod)
                if elem.tag == HddPerfTest.tpKey:
                    test = hdd.TPTest(self.getTestname(),self.getDevName(),self.__nj,self.__iod)
                if test != None:
                    test.fromXml(elem)
                    self.addTest(tag, test)

    def toRst(self):
        tests = self.getTests()
        rst = self.getRstReport()
        rst.addFooter()
        rst.addTitle()
        rst.addDevInfo(self.getDevInfo(),self.getFeatureMatrix())
        rst.addCmdLine(self.getCmdLineArgs())
        
        #Setup and OS infos are the same for all tests, just take one
        for keys in tests.iterkeys():
            rst.addSetupInfo(self.getIOPerfVersion(),tests[keys].getFioJob().getFioVersion(),
                             self.getTestDate())
            rst.addFioJobInfo(tests[keys].getNj(), tests[keys].getIod())
            rst.addOSInfo(self.getOSInfo())
            rst.addGeneralInfo('hdd')
            break
        
        if HddPerfTest.iopsKey in tests:
            rst.addChapter("IOPS")
            rst.addTestInfo('hdd','iops',tests['iops'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['iops'].getFigures()):
                rst.addFigure(fig,'hdd','iops',i)
        
        if HddPerfTest.tpKey in tests:
            rst.addChapter("Throughput")
            rst.addTestInfo('hdd','tp',tests['tp'])
            rst.addSection("Measurement Plots")
            for i,fig in enumerate(tests['tp'].getFigures()):
                rst.addFigure(fig,'hdd','tp',i)
        
        rst.toRstFile()
        
    def getPlots(self):
        tests = self.getTests()
        if HddPerfTest.iopsKey in tests:
            pgp.IOPSplot(tests['iops'])
        if HddPerfTest.tpKey in tests:
            pgp.TPplot(tests['tp'])
            pgp.TPBoxPlot(tests['tp'])
            

        