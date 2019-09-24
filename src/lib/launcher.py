################################################################################
# If not stated otherwise in this file or this component's Licenses.txt file the
# following copyright and licenses apply:
#
# Copyright 2017 Liberty Global B.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################
import os

################################################################################
#            class cRootfs(object):
#
#                    Represents directories for container environment
#
################################################################################
class cLauncher(object):
    class FunctionList(object):
        def __init__(self, launcherCommand, commandLine, pidFile, processName, shouldNotifySystemd, isProcessForking=False):
            self.launcherCommand = launcherCommand
            self.commandLine = commandLine
            self.pidFile = pidFile
            self.processName = processName
            self.shouldNotifySystemd = shouldNotifySystemd
            self.isProcessForking = isProcessForking

    def __init__(self, sanityCheck, rootfs, sleepUs):
        self.sanityCheck = sanityCheck
        self.rootfs = rootfs
        self.luncherName  = ""
        self.execName = ""
        self.logFileOpt = ""
        self.logPriorityOpt = ""
        # dict is unordered, use list for names so that start, stop and other launchers items are in the right order
        self.functionNames = []
        self.functions = dict()
        self.uidAttach = ""
        self.gidAttach = ""
        self.containerName = ""
        self.sleepUs = sleepUs

    def matchVersion(self, parentNode, nodeName):
        node = None
        for childNode in parentNode.iter(nodeName):
            node = childNode
        return node

    def getContainerName(self, lxcParams):
        containerName = lxcParams.find("ContainerName")
        if (containerName != None and containerName.text != None):
            self.containerName = containerName.text
        else:
            self.containerName = self.rootfs.getSandboxName()

    def getLauncherParams(self, lxcParams):
        self.luncherName = lxcParams.find("LauncherName").text
        self.execName = lxcParams.find("ExecName").text
        if (lxcParams.find("ExecParams") != None and lxcParams.find("ExecParams").text != None):
            self.execName += " " + lxcParams.find("ExecParams").text
        output = lxcParams.find("Output")
        if (output != None and output.attrib["enable"] == "true"):
            self.logFileOpt = "-o " + output.find("LogFile").text
            self.logPriorityOpt = "-l " + output.find("LogPriority").text

    def verifyContainerName(self, lxcParams):
        containerName = lxcParams.find("ContainerName")
        if (containerName != None and containerName.text != None):
            containerName = containerName.text
        else:
            containerName = self.rootfs.getSandboxName()

        if (self.containerName != containerName):
            raise AttributeError("ContainerName doesn't match. base: %s, append: %s"%(self.containerName, containerName))

    def verifyLauncherName(self, lxcParams):
        # LauncherName doesn't need to exist in append container. If it does exist, it needs to be the same
        launcherName = lxcParams.find("LauncherName")
        if (launcherName == None):
            return

        if (self.luncherName != launcherName.text):
            raise AttributeError("LauncherName doesn't match. base: %s, append: %s"%(self.luncherName, launcherName.text))

    def genAttachParams(self, attachEntry):
        pidfileAttach=""
        self.funcName = attachEntry.find("ParamName").text
        self.execAttach = attachEntry.find("ExecName").text
        paramAttach = attachEntry.find("ExecParams")
        if (paramAttach != None and paramAttach.text != None):
            self.execAttach += " " + paramAttach.text

        userName = attachEntry.find("UserName");
        groupName = attachEntry.find("GroupName");
        # if no groupName provided, take userName as groupName
        if(groupName == None or groupName.text == None):
            groupName = userName

        if (self.sanityCheck.isPrivileged() and userName != None and userName.text != None and groupName != None and groupName.text != None):
            self.uidAttach = "-u " + self.rootfs.userNameToUid(userName.text)
            self.gidAttach = "-g " + self.rootfs.groupNameToGid(groupName.text)
        else: # no uid and gid clean up class variables
            self.uidAttach =""
            self.gidAttach =""

    def appendFunctionList(self, functionName, function):
        self.functions[functionName] = function
        if (functionName not in self.functionNames):
            self.functionNames.append(functionName)
            self.functionNames.append("stop") # make sure "stop" is always last
            self.functionNames.remove("stop")

    def generateSystemdNotify(self, node, command, isExec):
        FORKING_TAG="forking"
        shouldNotifySystemd = False
        isProcessForking = False
        processName = ""
        pidfile = ""
        systemdNotify = node.find("SystemdNotify")
        if (systemdNotify != None):
            if systemdNotify.attrib.get(FORKING_TAG, '') == "yes":
                isProcessForking = True
            if systemdNotify.attrib["create"] != None and systemdNotify.attrib["create"] == "yes":
                shouldNotifySystemd = True
                if systemdNotify.find("PidFile") != None:
                    pidfile = systemdNotify.find("PidFile").text
                if systemdNotify.find("ProcessName") != None:
                    processName = systemdNotify.find("ProcessName").text
                else:
                    processName = node.find("ExecName").text.split()[0]

        launcherCommand = "start" if isExec else node.find("ParamName").text
        self.appendFunctionList(launcherCommand, self.FunctionList(launcherCommand, command, pidfile, processName, shouldNotifySystemd, isProcessForking))

    def createScript(self):

        fd = open(self.rootfs.getLauncherFileHost(), 'w')
        fd.write("#!/bin/sh\n\n")
        fd.write("case "'$1'" in\n")

        for name in self.functionNames:
            item = self.functions[name]

            fd.write("\t" + item.launcherCommand + ")\n")
            if (item.pidFile != None and item.pidFile != "" ):
                fd.write("\t\t/bin/echo \"r " + item.pidFile + "\" | /bin/systemd-tmpfiles --remove /dev/stdin\n")
            fd.write("\t\t" + item.commandLine + (" &" if item.shouldNotifySystemd else "") +"\n")

            if (item.shouldNotifySystemd):
                if (item.pidFile != None and item.pidFile != "" ):
                    fd.write("\t\tCOUNTER=300\n")
                    fd.write("\t\twhile [ $COUNTER -ne 0 ]\n")
                    fd.write("\t\tdo\n")
                    fd.write("\t\t\tif [ -e \"" + item.pidFile +  "\" ]; then\n")
                    fd.write("\t\t\t\tbreak\n")
                    fd.write("\t\t\tfi\n")
                    fd.write("\t\t\t/bin/usleep 100000\n")
                    fd.write("\t\t\tlet COUNTER-=1\n")
                    fd.write("\t\tdone\n")
                    fd.write("\t\tif [ $COUNTER -eq 0 ]; then\n")
                    fd.write("\t\t\texit 1\n")
                    fd.write("\t\tfi\n")
                if item.isProcessForking == True:
                    self.generateScriptToFindPidOfForkingProcess(fd, item.processName)
                else:    
                    fd.write("\t\tCHILD_PID=$(/usr/bin/lxccpid --ppid $! \"" + item.processName + "\" 3000)\n")
                fd.write("\t\tif [ -z $CHILD_PID ]; then\n")
                fd.write("\t\t\texit 1\n")
                fd.write("\t\telse\n")
                fd.write("\t\t\t/bin/systemd-notify --ready MAINPID=$CHILD_PID\n")
                fd.write("\t\t\t# Wait for systemd to assign the proper pid, before the main process exit.\n")
                fd.write("\t\t\t/bin/usleep " + str(self.sleepUs) + "\n")
                fd.write("\t\tfi\n")
            fd.write("\t;;\n")
        fd.write("\t*)\n\t\texit 1\n")
        fd.write("esac\n")

    def generateScriptToFindPidOfForkingProcess(self, fd, processName):
        fd.write("\n\t\t#Find lxc-execute of the container\n")
        fd.write("\t\tE_PID=$(/usr/bin/lxccpid --ppid 1 \"/usr/bin/lxc-execute -n "+ self.containerName +"\" 3000)\n")
        fd.write("\n\t\t#Find lxc-static of the container\n")
        fd.write("\t\tI_PID=$(/usr/bin/lxccpid --ppid $E_PID \"/init.lxc.static\" 3000)\n")
        fd.write("\n\t\t#Find the forking process to be started insidethe container\n")
        fd.write("\t\tCHILD_PID=$(/usr/bin/lxccpid --ppid $I_PID \""+ processName +"\" 3000)\n")

    def createLauncher(self, lxcParams):

        self.getLauncherParams(lxcParams)
        self.getContainerName(lxcParams)
        self.rootfs.setLauncherName(self.luncherName)

        command = "/usr/bin/lxc-execute -n %s  %s %s -f %s -- %s"%(self.containerName,
                                                                   self.logFileOpt,
                                                                   self.logPriorityOpt,
                                                                   self.rootfs.getConfFileTarget(),
                                                                   self.execName)

        self.generateSystemdNotify(lxcParams, command, True)

        self.createAttached(lxcParams)

    def createAttached(self, lxcParams):
        for attachEntry in lxcParams.iter('Attach'):

            self.genAttachParams(attachEntry)
            Attachcommand = "/usr/bin/lxc-attach -n %s -f %s %s %s -- %s"%(self.containerName,
                                                                           self.rootfs.getConfFileTarget(),
                                                                           self.uidAttach,
                                                                           self.gidAttach,
                                                                           self.execAttach)

            self.generateSystemdNotify(attachEntry, Attachcommand, False)


        stopFunction = lxcParams.find("StopFunction")
        if (stopFunction != None):
            if stopFunction.attrib["enable"] == "true":
                self.appendFunctionList("stop", self.FunctionList("stop","/usr/bin/lxc-stop -n " + self.containerName, "", "", False))

        self.createScript()

    def appendLauncher(self, lxcParams):
        self.verifyContainerName(lxcParams)
        self.verifyLauncherName(lxcParams)
        try:
            self.getLauncherParams(lxcParams)
            command = "/usr/bin/lxc-execute -n %s  %s %s -f %s -- %s"%(self.containerName,
                                                                       self.logFileOpt,
                                                                       self.logPriorityOpt,
                                                                       self.rootfs.getConfFileTarget(),
                                                                       self.execName)

            self.generateSystemdNotify(lxcParams, command, True)
        except:
            pass # appending xml doesn't need to contain the main launcher

        self.createAttached(lxcParams)
