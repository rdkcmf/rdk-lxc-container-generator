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
#   class cSanityCheck(object)
################################################################################

class cSanityCheck(object):
    def __init__(self,soc, oe, version, privileged, name, rootfsPath):
        self.name = name
        self.soc = soc
        self.oe = oe
        self.version = version
        self.privileged = privileged
        self.rootfsPath = rootfsPath
        self.dirList = []
        self.nonFlashDirs = [
        "/var",                     # tmpfs directory
        "/run",                     # tmpfs directory
        "/tmp",                     # tmpfs directory
        "/mnt",                     # directory contains storages mount points
        "/opt",                     # tmpfs directory
        "/media",                   # directory contains storages mount points
        "/dev",                     # direcotry contains devices mknodes
        "proc",                     # proc filesystem
        "/proc",                    # proc filesystem
        "sysfs",                    # sys filesystem
        "/sys",                     # sys filesystem
        "tmpfs"                     # tmpfs filesystenm (skipping local tmpfs mounted in container)
     ]

        self.execDirs = [
        "/usr/bin",
        "/usr/sbin",
        "/sbin",
        "/bin",
        "/usr/lib",
        "/lib",
        "/etc"
    ]

    def isPrivileged(self):
        return self.privileged

    def getPlatformSettings(self):
        return "soc = %s, oe = %s, version = %s "%(self.soc, self.oe, self.version)

    def getVersion(self):
        return self.version

    def getName(self):
        return self.name

    def validateVersion(self, node):
        if (node != None):
            if ('version' in node.attrib and node.attrib["version"] == self.version):
                return True
            elif (not 'version' in node.attrib):
                return True
            else:
                return False
        else:
            raise Exception("[ERROR] Invalid entry")

    def validateTextEntry(self, entry):
        if (entry != None and entry.text != None):
            return True
        else:
            return False

    def pathExist(self, path):
        # check if path or symlink exist
        if (not os.path.exists(self.rootfsPath + "/" + path) and not os.path.islink(self.rootfsPath + "/" + path)) :
            return False
        return True

    def isOnFlash(self, dir):
        for entry in self.nonFlashDirs:
            if (dir.startswith(entry)):
                return False
        return True

    def isExecDir(self, dir):
        for entry in self.execDirs:
            if (dir.startswith(entry)):
                return True
        return False

    def validateOptions(self, mountBind, fsType, options):
        if (self.version == "production" ): # in debug and release we do not have to follow NASC requirements
# Check if tmpfs is mounted with defined size option           
            if (fsType == "tmpfs"):
                if (options.find("size") == -1):
                    raise Exception("[!!! ERROR !!!] The tmpfs type requires sieze option define. Current settings: mountBind = %s options = %s "%(mountBind, options))

# FLASH and not EXEC
            if(self.isOnFlash(mountBind) and not self.isExecDir(mountBind)):
                if options.find("ro") != -1 and  options.find("nosuid") != -1 and  options.find("nodev") != -1 and options.find("noexec") != -1:
                    return True
                else:
                    raise Exception("[!!! ERROR !!!] Invalid mount bind options. Recomended nodev nosuid noexec ro  Current settings: mountBind = %s options = %s "%(mountBind, options))
# NOT on FLASH and not dev ?
            elif (not self.isOnFlash(mountBind) and not mountBind.startswith("/dev")):
                if options.find("nosuid") != -1 and  options.find("nodev") != -1 and options.find("noexec") != -1:
                    return True
                else:
                    raise Exception("[!!! ERROR !!!] Invalid mount bind options nosuid nodev noexec . Current settings: mountBind = %s options = %s "%(mountBind, options))

    def validateMountBind(self, mountBind):
        #check if it is not in tmpfs directory
        if (self.isOnFlash(mountBind)and not self.pathExist(mountBind)):
            raise Exception("[!!! ERROR !!!] Rootfs does not contain (%s) - No such file or directory"%(mountBind))

    def addDir(self, dir):
        self.dirList.append(dir)

    def checkNestedMountBinds(self, mountBind):
        for item in self.dirList:
            #  print "item =%s mount =%s"%(item, mountBind)
            if (mountBind.startswith(item+"/")):
                return False

        return True

################################################################################
#
#   validateSocOE(node):
#       Validate if node matches the SOC and OE tag
#
################################################################################
    def validateSocOE(self, node):
        if (node != None):
            if ('SOC_VER' in node.attrib and node.attrib["SOC_VER"] == self.soc and 'OE_VER' in node.attrib and node.attrib["OE_VER"] == self.oe):
                return True
            elif ('SOC_VER' in node.attrib and node.attrib["SOC_VER"] == self.soc and not 'OE_VER' in node.attrib):
                return True
            elif ('OE_VER' in node.attrib and node.attrib["OE_VER"] == self.oe and not 'SOC_VER' in node.attrib):
                return True
            elif (not 'SOC_VER' in node.attrib and not 'OE' in node.attrib):
                return True
            else:
                return False
        else:
            raise Exception("[ERROR] Invalid entry")

################################################################################
#
#   createRootfsConf(rootfs, rootfsNode):
#
#       parse the mount points configuration inside the xml
#       return the configuration
#
################################################################################

    def validateAllTags(self, node):
        if (self.validateSocOE(node) == True and self.validateVersion(node) == True):
            return True
        else:
            return False
