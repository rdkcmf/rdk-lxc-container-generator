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
import sys
import ConfigParser
import os.path
from distutils.log import info

################################################################################
#    class cTag(object)
#        Represent the single tag, defined in config file
################################################################################
class cTag(object):
    def __init__(self, name):
        self.name = name
        self.allowsValues = []
        self.value = ""

    def getName(self):
        return self.name

    def getValue(self):
        return self.value

    def setAllowedValue(self, value):
        self.allowsValues.append(value)

    def isAllowed(self, value):
        for entry in self.allowsValues:
            if (value == entry):
                return True
        return False

    def inSet(self, tagvaluestring):
        def matched(value, tagvaluestring):
            for e in tagvaluestring.split(":"):
                if value == e:
                    return True
                if e.endswith("*") and value.startswith(e[:-1]):
                    return True
            return False
        if tagvaluestring.startswith("!"):
            return not matched(self.value, tagvaluestring[1:])
        return matched(self.value, tagvaluestring)

    def setValue(self, value):
        if(self.isAllowed(value)):
            self.value = value
        else:
            raise Exception("[!!! ERROR !!!] The given tag was not defined in config. Tag name = %s, given value = %s, Allowed values = %s "%(self.name, value, self.allowsValues))

################################################################################
#    class cRangeTag(object)
#        Represent the range tag, defined in config file
################################################################################
class cRangeTag(object):
    def __init__(self, name):
        self.name = name
        self.value = 0

    def getName(self):
        return self.name

    def getValue(self):
        return self.value

    def inRange(self, rrange):
        x = 0
        y = 0

        parts = rrange.split("..")
        m = len(parts)

        if m <= 0 or m > 2:
            raise Exception("[!!! ERROR !!!] Passed range is invalid: %s "%(rrange))

        try:
            if (parts[0] == ""):
                x = 0
            else:
                x = int(parts[0])
            y = x
        except ValueError as ex:
            raise Exception("[!!! ERROR !!!] Passed range is no numeric range: %s "%(rrange))

        if len(parts) == 2:
            try:
                if (parts[1] == ""):
                    y = sys.maxint
                else:
                    y = int(parts[1])
            except ValueError as ex:
                raise Exception("[!!! ERROR !!!] Passed range is no numeric range: %s "%(rrange))

        return (x <= self.value and self.value <= y)

    def isAllowed(self, value):
        try:
            int_value = int(value)
        except ValueError as ex:
            return False

        return int_value >= 0

    def setValue(self, value):
        if(self.isAllowed(value)):
            self.value = int(value)
        else:
            raise Exception("[!!! ERROR !!!] The given tag was not defined in config. Tag name = %s, given value = %s, Allowed values = numeric >= 0 "%(self.name, value))

################################################################################
#   class cSanityCheck(object)
################################################################################
class cSanityCheck(object):
    def __init__(self, filename, privileged, name, rootfsPath, confPath, givenTags, enableMountCheck):
        self.name = name
        self.filename = filename
        self.privileged = privileged
        self.rootfsPath = rootfsPath
        self.confPath = confPath
        self.enableMountCheck = enableMountCheck
        self.dirList = []
        self.tags = []
        self.rangeTags = []
        self.writableDirs = []
        self.executableDirs = []
        self.paresConfig()
        self.parseTags(givenTags)

    def paresConfig(self):
        config = ConfigParser.RawConfigParser()
        config.optionxform = str
        config.read(self.confPath)
        self.executableDirs = config.get("EXECUTABLE","paths").split('\n')
        self.writableDirs = config.get("WRITABLE","paths").split('\n')

        for options in config.options("TAGS"):
            entries = config.get("TAGS",options).split('\n')
            tag = cTag(options)
            for entry in entries:
                items = entry.split(",")
                for item in items:
                    tag.setAllowedValue(item.strip())
            self.tags.append(tag)

        for options in config.options("RANGE"):
            rangeTag = cRangeTag(options)
            self.rangeTags.append(rangeTag)

    def parseTags(self, tagsString):
        entries = tagsString.split(",")
        for entry in entries:
            tag = entry.split("=")
            for iter in self.tags:
                if(iter.getName() == tag[0]):
                    iter.setValue(tag[1])
            for iter in self.rangeTags:
                if(iter.getName() == tag[0]):
                    iter.setValue(tag[1])

    def isPrivileged(self):
        return self.privileged

    def getPlatformSettings(self):
        info = " "
        for entry in self.tags:
            info += "%s = %s "%(entry.getName(), entry.getValue())
        return info

    def getName(self):
        return self.name

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

    def isWritable(self, dir):
        for entry in self.writableDirs:
            if (dir.startswith(entry)):
                return False
        return True

    def isExecutable(self, dir):
        for entry in self.executableDirs:
            if (dir.startswith(entry)):
                return True
        return False

    def validateOptions(self, mountBind, fsType, options):
        if(self.enableMountCheck):
            if (fsType == "tmpfs"):
                if (options.find("size") == -1):
                    raise Exception("[!!! ERROR !!!] The tmpfs type requires sieze option define. Current settings: mountBind = %s options = %s "%(mountBind, options))
            if(self.isWritable(mountBind) and not self.isExecutable(mountBind)):
                if options.find("ro") != -1 and  options.find("nosuid") != -1 and  options.find("nodev") != -1 and options.find("noexec") != -1:
                    return True
                else:
                    raise Exception("[!!! ERROR !!!] Invalid mount bind options. Recomended nodev nosuid noexec ro  Current settings: mountBind = %s options = %s "%(mountBind, options))
            elif (not self.isExecutable(mountBind) and not mountBind.startswith("/dev")):
                if options.find("nosuid") != -1 and  options.find("nodev") != -1 and options.find("noexec") != -1:
                    return True
                else:
                    raise Exception("[!!! ERROR !!!] Invalid mount bind options nosuid nodev noexec . Current settings: mountBind = %s options = %s "%(mountBind, options))

    def validateMountBind(self, mountBind, options):
        if (self.isWritable(mountBind) and (options.find("optional") == -1) and not self.pathExist(mountBind)):
            raise Exception("[!!! ERROR !!!] Rootfs does not contain (%s) - No such file or directory"%(mountBind))

    def addDir(self, dir):
        self.dirList.append(dir)

    def checkNestedMountBinds(self, mountBind):
        for item in self.dirList:
            if (mountBind.startswith(item+"/")):
                return False
        return True

    def validateTags(self,node):
        if (node != None):
            for entry in self.tags:
                if(entry.getName() in node.attrib and not entry.inSet(node.attrib[entry.getName()])):
                    return False
            for entry in self.rangeTags:
                if(entry.getName() in node.attrib and not entry.inRange(node.attrib[entry.getName()])):
                    return False
        return True

    def validateAutoMount(self, entry):
        valid_automount_options = ["cgroup:ro", "cgroup:mixed", "sys:ro", "sys:mixed", "sys", "proc:mixed", "proc"]
        if not self.validateTextEntry(entry):
            return False
        if entry.text not in valid_automount_options:
            raise Exception("[!!! ERROR !!!] Invalid AutoMount option value (%s) in %s"%(entry.text, self.name))
        return True

    def report_skipping_entry(self, node, path):
        # Implement notification for different types of elements
        def c_default(node):
            v = "<"+node.tag
            for (an,av) in node.attrib.items():
                v += " %s=\"%s\""%(an,av)
            return v + ">"

        # special handling
        def c_env_var(node):
            return "for variable = "+node.text
        def c_env_mpoint(node):
            e=node.find("Source")
            if e == None:
                e = "????"
            else:
                e = e.text
            return "for mount point %s"%e
        def c_env_libs(node):
            return "for variable = "+node.text
        handlers = {
            "CONTAINER.LxcConfig.Environment.Variable" : c_env_var,
            "CONTAINER.LxcConfig.Rootfs.MountPoints.Entry" : c_env_mpoint,
            "CONTAINER.LxcConfig.Rootfs.LibsRoBindMounts.Entry" : c_env_libs
        }
        if path.replace(".Group.",".") in handlers:
            entryName = handlers[path.replace(".Group.",".")](node)
        else:
            entryName = c_default(node)
        messageFooter = ""
        if "_start_line_number" in dir(node):
            if node._start_line_number == node._end_line_number:
                messageFooter += "\t (%s:%d)"%(os.path.basename(self.filename), node._start_line_number)
            else:
                messageFooter += "\t (%s:%d-%d)"%(os.path.basename(self.filename), node._start_line_number, node._end_line_number)
        print("[%s] Skipping entry %s \t Current Settings: %s %s"%(self.getName(), entryName, self.getPlatformSettings(), messageFooter))

    # Apply conditional rules on xml tree
    def filter_out_inactive_tags(self,node,path=None):
        if path == None:
            path = node.tag
        index = 0
        for child in node[:]:
            cpath = path+"."+child.tag
            if not self.validateTags(child):
                # child filtered out
                self.report_skipping_entry(child, cpath)
                node.remove(child)
                continue
            self.filter_out_inactive_tags(child, cpath)
            if child.tag != "Group":
                index = index+1
                continue
            # Special handling for <Group> element
            # Extract all sub-elements instead
            # <Group ATTRS> can be used to control set of parameters
            for sub in child[:]:
                child.remove(sub)
                node.insert(index, sub)
                index = index+1
            node.remove(child)
