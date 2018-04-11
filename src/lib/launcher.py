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
    def __init__(self, sanityCheck, rootfs):
        self.sanityCheck = sanityCheck
        self.rootfs = rootfs
        self.luncherName  = ""
        self.execName = ""
        self.logFileOpt = ""
        self.logPriorityOpt = ""
        self.functionList = []
        self.uidAttach = ""
        self.gidAttach = ""
        self.containerName = ""

    def matchVersion(self, parentNode, nodeName):
        node = None
        for childNode in parentNode.iter(nodeName):
            if (childNode != None):
                if ('version' in childNode.attrib and childNode.attrib["version"] == self.sanityCheck.getVersion()):
                    node = childNode
                elif (not 'version' in childNode.attrib):
                    node = childNode
                else:
                    print("[INFO] Skipping entry Current Version does not match")
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
        if (output != None and output.attrib["enable"] == "true" and self.sanityCheck.validateAllTags(output) == True):
            self.logFileOpt = "-o " + output.find("LogFile").text
            self.logPriorityOpt = "-l " + output.find("LogPriority").text

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

    def generateSystemdNotify(self, node, command, isExec):
        shouldNotifySystemd = False
        processName = ""
        pidfile = ""
        systemdNotify = node.find("SystemdNotify")
        if (systemdNotify != None):
            if systemdNotify.attrib["create"] != None and systemdNotify.attrib["create"] == "yes":
                shouldNotifySystemd = True
                if systemdNotify.find("PidFile") != None:
                    pidfile = systemdNotify.find("PidFile").text
                if systemdNotify.find("ProcessName") != None:
                    processName = systemdNotify.find("ProcessName").text
                else:
                    processName = node.find("ExecName").text.split()[0]

        if (isExec):
            self.functionList.append(["start", command, pidfile, processName, shouldNotifySystemd])
        else:
            funcName = node.find("ParamName").text
            self.functionList.append([funcName, command, pidfile, processName, shouldNotifySystemd])

    def createScript(self):

        fd = open(self.rootfs.getLauncherFileHost(), 'w')
        fd.write("#!/bin/sh\n\n")
        fd.write("case "'$1'" in\n")

        for item in self.functionList:
            launcherCommand = item[0];
            commandline = item[1];
            pidfile = item[2];
            processName = item[3];
            shouldNotifySystemd = item[4]

            fd.write("\t" + launcherCommand + ")\n")
            if (pidfile != None and pidfile != "" ):
                fd.write("\t\t/bin/echo \"r " + pidfile + "\" | /bin/systemd-tmpfiles --remove /dev/stdin\n")
            fd.write("\t\t" + commandline + (" &" if shouldNotifySystemd else "") +"\n")

            if (shouldNotifySystemd):
                if (pidfile != None and pidfile != "" ):
                    fd.write("\t\tCOUNTER=300\n")
                    fd.write("\t\twhile [ $COUNTER -ne 0 ]\n")
                    fd.write("\t\tdo\n")
                    fd.write("\t\t\tif [ -e \"" + pidfile +  "\" ]; then\n")
                    fd.write("\t\t\t\tbreak\n")
                    fd.write("\t\t\tfi\n")
                    fd.write("\t\t\t/bin/usleep 100000\n")
                    fd.write("\t\t\tlet COUNTER-=1\n")
                    fd.write("\t\tdone\n")
                    fd.write("\t\tif [ $COUNTER -eq 0 ]; then\n")
                    fd.write("\t\t\texit 1\n")
                    fd.write("\t\tfi\n")
                fd.write("\t\tCHILD_PID=$(/usr/bin/lxccpid --ppid $! \"" + processName + "\" 2000)\n")
                fd.write("\t\tif [ -z $CHILD_PID ]; then\n")
                fd.write("\t\t\texit 1\n")
                fd.write("\t\telse\n")
                fd.write("\t\t\t/bin/systemd-notify --ready MAINPID=$CHILD_PID\n")
                fd.write("\t\t\t# Wait for systemd to assign the proper pid, before the main process exit.\n")
                fd.write("\t\t\t/bin/usleep 100000\n")
                fd.write("\t\tfi\n")
            fd.write("\t;;\n")
        fd.write("\t*)\n\t\texit 1\n")
        fd.write("esac\n")

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
                self.functionList.append(["stop","/usr/bin/lxc-stop -n " + self.containerName, "", "", False])

        self.createScript()
