'''
Created on 09.07.2012

@author: gschoenb
'''
from __future__ import division
import matplotlib.pyplot as plt
import numpy as np

import perfTest as pT

def stdyStVerPlt(toPlot,mode):
    '''
    Generate a steady state verification plot.
    The plot includes:
    -Measured IOPS of rounds in which steady state was reached
    -Average IOPS in steady state rounds
    -Slope of best fit line of measured IOPS
    -Top and Bottom limits: +-10% percent of average
    The figure is saved as SsdTest.Testname-stdyStVerPlt.png.
    @param toPlot A SsdTest object.
    @param mode A string representing the test mode (iops|throughput)
    '''
    x = np.array(toPlot.getStdyRnds())
    #calculate average and its top and bottom limit
    av = []
    avT = []
    avB = []
    av.append(toPlot.getStdyAvg())
    avTop = toPlot.getStdyAvg() * 1.10
    avBot = toPlot.getStdyAvg() * 0.9
    avT.append(avTop)
    avB.append(avBot)
    av = av * len(x)
    avT = avT * len(x)
    avB = avB * len(x)
    
    plt.clf()#clear
    plt.plot(x,toPlot.getStdyValues(),'o', label=mode, markersize=10)
    plt.plot(x, toPlot.getStdySlope()[0]*x + toPlot.getStdySlope()[1], 'r', label='Slope')
    plt.plot(x, av, '-', color='black',label='Average')
    plt.plot(x, avT, '--', color='black',label='Top')
    plt.plot(x, avB, '--', color='black',label='Bottom')
    
    #set the y axes to start at 3/4 of mininum
    plt.ylim(min(toPlot.getStdyValues())*0.75,max(toPlot.getStdyValues())*1.25)
    plt.xticks(x)
    plt.title("Steady State Verification Plot")
    plt.xlabel("Round")
    if mode == "bw":
        plt.ylabel(mode + " KB/s")
    else:
        plt.ylabel(mode)
    plt.legend()
    plt.savefig(toPlot.getTestname()+'-'+mode+'-stdyStVerPlt.png',dpi=300)
    
def stdyStConvPlt(toPlot):
    '''
    Generate a steady state convergence plot.
    The plot consists of:
    -Measured IOPS of pure random write
    -All lines are the different block sizes
    -IOPS of all the rounds are plotted
    The figure is saved as SsdTest.Testname-stdyStConvPlt.png.
    @param toPlot A SsdTest object.
    '''
    rnds = toPlot.getRnds()
    matrices = toPlot.getRndMatrices()
    bsLens = len(matrices[0][-1])#fetch the number of bs of the first matrix
    
    #initialize matrix for plotting
    lines = []
    for i in range(bsLens):
        lines.append([])

    for rndMat in matrices:
        row = rndMat[-1]#last row is random write
        for i in range(len(row)):
            lines[i].append(row[i])#switch from row to column wise ordering of values
    
    plt.clf()#clear
    #fetch number of rounds, we want to include all rounds
    #as stdy state was reached at rnds, it must be included
    x = range(rnds + 1)
    for i in range(len(lines)):
        plt.plot(x,lines[i],'o-',label='bs='+pT.SsdTest.SsdTest.bsLabels[i])
    
    plt.xticks(x)
    plt.title("Steady State Convergence Plot")
    plt.xlabel("Round")
    plt.ylabel("IOPS")
    plt.legend()
    plt.savefig(toPlot.getTestname()+'-stdyStConvPlt.png',dpi=300)
    
def mes2DPlt(toPlot):
    '''
    Generate a measurement 2D plot.
    The plot includes:
    -Lines of the workloads
    -Each line consists of the average of IOPS per round
    for each block size.
    Therefore the x axes are the block sizes, the plotted lines
    are the different workloads (from 100% read to 100% write). The
    y axes is the average of IOPS over all rounds for each block size
    and workload.
    The figure is saved as SsdTest.Testname-mes2DPlt.png.
    @param toPlot A SsdTest object.
    '''
    mixWLds = []
    #each row will be a workload percentage
    for i in range(len(pT.SsdTest.SsdTest.mixWlds)):
        mixWLds.append([])
        #in each row will be the different block sizes
        for bs in range(len(pT.SsdTest.SsdTest.bsLabels)):
            mixWLds[i].append(0)
    matrices = toPlot.getRndMatrices()    
    for rndMat in matrices:
        #each row is a percentage of a workload
        for i,row in enumerate(rndMat):
            #in each row are the different block sizes
            for bs in range(len(row)):
                #calculate average
                if mixWLds[i][bs] != 0:
                    mixWLds[i][bs] += row[bs]
                    mixWLds[i][bs] = (mixWLds[i][bs]) / 2
                else:
                    mixWLds[i][bs] = row[bs]
    plt.clf()#clear plot
    x = [8,4,0.5]#FIXME Add correct block sizes here
    for i in range(len(mixWLds)):
        #the labels are r/w percentage of mixed workload
        plt.plot(x,mixWLds[i],'o-',
                  label=str(pT.SsdTest.SsdTest.mixWlds[i])+'/'+str(100-pT.SsdTest.SsdTest.mixWlds[i]))
     
    #TODO Scale axes log   
         
    plt.xticks(x)
    plt.title("IOPS test")
    plt.xlabel("Block Size (KB)")
    plt.ylabel("IOPS")
    plt.legend()
    plt.savefig(toPlot.getTestname()+'-mes2DPlt.png',dpi=300)
    
def writeSatIOPSPlt(toPlot):
    #fetch number of rounds, we want to include all rounds
    #as stdy state was reached at rnds, it must be included
    rnds = toPlot.getWriteSatRnds()
    x = range(rnds + 1)
    
    iops_l = toPlot.getWriteSatMatrix()[0]#first elem in matrix are iops

    plt.clf()#clear plot        
    plt.plot(x,iops_l,'-',label='Avg IOPS')
    plt.ylim(min(iops_l)*0.75,max(iops_l)*1.25)
    plt.xticks(x)
    plt.title("Write Saturation Test")
    plt.xlabel("Round #")
    plt.ylabel("IOPS")
    plt.legend()
    plt.savefig(toPlot.getTestname()+'-writeSatIOPSPlt.png',dpi=300)
    
def writeSatLatPlt(toPlot):
    rnds = toPlot.getWriteSatRnds()
    x = range(rnds + 1)
    
    lats_l = toPlot.getWriteSatMatrix()[1]#second elem in matrix are latencies
    
    #get the average latencies from the lat list (last elem)
    av_lats = []
    for i in lats_l:
        av_lats.append((i[2]) / 1000)
    
    plt.clf()#clear plot
    plt.plot(x,av_lats,'-',label='Avg latency')
    #set the y axes to start at 3/4 of mininum
    plt.ylim(min(av_lats)*0.75,max(av_lats)*1.25)
    plt.xticks(x)
    plt.title("Write Saturation Test")
    plt.xlabel("Round #")
    plt.ylabel("Latency ms")
    plt.legend()
    plt.savefig(toPlot.getTestname()+'-writeSatLatPlt.png',dpi=300)
    
    
    
    
    
    
    
    
    
    