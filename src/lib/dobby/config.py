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
import re
from .. import cConfig
from cgroup import cCgroupDobby
from dbus import cDbusDobby
from json_utils import cJsonUtils

merge = cJsonUtils.merge


################################################################################
#   class cConfigDobby(cConfig):
#
#       Represents container configuration,
#       implements basic functionalities to generate config.json.
#
################################################################################
class cConfigDobby(cConfig):
    def __init__(self, sanityCheck, rootfs, privileged, append, prevUserName, prevGroupName):
        super(cConfigDobby, self).__init__(sanityCheck, rootfs, privileged, append, prevUserName, prevGroupName)
        self.autodev = False

    def createEnvConf(self, configNode):

        entry = {}
        envNode = configNode.find("Environment")

        if self.sanityCheck.validateTextEntry(envNode):
            preload = list()

            for variable in envNode.iter('Variable'):
                if self.sanityCheck.validateTextEntry(variable):
                    parts = variable.text.split("=")
                    var_name = parts[0].strip()
                    if var_name == "LD_PRELOAD" and len(parts) > 1:
                        for solib in parts[1].split(":"):
                            if solib not in preload:
                                preload.append(solib)
                    merge(entry, {
                        "process": {
                            "env": [variable.text]
                        }
                    })

            for preload_lib in preload:
                self.rootfs.addLibraryRequired(preload_lib, 'LD_PRELOAD')
        else:
            print("We do not need to create Environment variables")

        return entry

    def createNetworkConf(self, configNode):

        entry = {}

        for networkNode in configNode.iter('Network'):
            if networkNode is not None:
                type = networkNode.attrib["type"]

                entry["rdkPlugins"] = {
                    "networking": {
                        "required": False,
                        "data": {
                            "type": type
                        }
                    }
                }

                ipv6 = networkNode.find("IPv6")
                if ipv6 is not None and "enable" in ipv6.attrib:
                    entry["rdkPlugins"]["networking"]["data"]["ipv6"] = ipv6.attrib["enable"] == "true"

                ipv4 = networkNode.find("IPv4")
                if ipv4 is not None and "enable" in ipv4.attrib:
                    entry["rdkPlugins"]["networking"]["data"]["ipv4"] = ipv4.attrib["enable"] == "true"

                dnsmasq = networkNode.find("DNSMasq")
                if dnsmasq is not None and "enable" in dnsmasq.attrib:
                    entry["rdkPlugins"]["networking"]["data"]["dnsmasq"] = dnsmasq.attrib["enable"] == "true"

        return entry

    def generateMountPoints(self, mountPointNode):

        entry = {}
        if mountPointNode is not None:
            for mountPoint in mountPointNode.iter('Entry'):
                if mountPoint is not None:
                    source = mountPoint.find("Source")
                    destination = mountPoint.find("Destination")
                    options = mountPoint.find("Options").text
                    type = mountPoint.attrib["type"]
                    fsType = "none"

                    if self.sanityCheck.validateTextEntry(mountPoint.find("FsType")):
                        fsType = mountPoint.find("FsType").text
                    elif options.find("rbind") != -1 or options.find("bind") != -1:
                        fsType = "bind"

                    if self.sanityCheck.validateTextEntry(source) and self.sanityCheck.validateTextEntry(destination):

                        self.sanityCheck.validateMountBind(source.text, options)
                        self.sanityCheck.validateOptions(source.text, fsType, options)
                        if source.text == destination.text:
                            if not self.sanityCheck.checkNestedMountBinds(source.text):
                                raise Exception("[%s] Nested mount bind found =  %s ", source.text)

                        merge(entry, {
                            "mounts": [
                                {
                                    "destination": os.path.join("/", destination.text),
                                    "options": options.split(","),
                                    "source": source.text,
                                    "type": fsType
                                }
                            ]
                        })

                        self.createMountPoint(type, destination.text, source.text)
                        if type == "dir":
                            self.sanityCheck.addDir(source.text)
                            for unusedEntry in mountPoint.iter('Unused'):
                                if self.sanityCheck.validateTextEntry(unusedEntry):
                                    self.rootfs.unusedList.append(unusedEntry.text)
                            self.rootfs.checkElfDepsForDirectoryMountPoint(destination.text, source.text)

                    else:
                        raise Exception("INVALID DATA MOUNT POINT")

        return entry

    def generateLibMountPoints(self, libBindingsNode):

        entry = {}
        if libBindingsNode is not None:
            for libsScanDir in libBindingsNode.iter('LibsScanDir'):
                if self.sanityCheck.validateTextEntry(libsScanDir):
                    self.rootfs.addLibsScanDir(libsScanDir.text)
                else:
                    raise Exception("[!!! ERROR !!!] Invalid <LibsScanDir> tag: Must contain a dir")

            for libBinding in libBindingsNode.iter('Entry'):
                if self.sanityCheck.validateTextEntry(libBinding):
                    libList = self.rootfs.findLibByName(libBinding.text)
                    for source in libList:
                        if self.sanityCheck.pathExist(source):
                            merge(entry, {
                                "mounts": [
                                    {
                                        "destination": os.path.join("/", source),
                                        "options": ["ro", "bind", "nodev", "nosuid"],
                                        "source": source,
                                        "type": "bind"
                                    }
                                ]
                            })

                            self.rootfs.createMountPointForFile(source)
                        else:
                            raise Exception(
                                "[!!! ERROR !!!] Rootfs does not contain (%s) - No such file or directory" % source)
        return entry

    def createRootfsConf(self, rootfsNode):

        entry = {}

        if rootfsNode is not None:
            rootfsCreate = rootfsNode.attrib["create"]
            if rootfsCreate == "yes":
                entry["root"] = {
                    "path": os.path.basename(self.rootfs.getPathRootfsTarget()),
                    "readonly": True
                }
                entry["rootfsPropagation"] = "rprivate"
                merge(entry, self.generateMountPoints(rootfsNode.find("MountPoints")))
                self.moveContent(rootfsNode.find("MoveContent"))
                merge(entry, self.generateLibMountPoints(rootfsNode.find("LibsRoBindMounts")))
                self.generateHardlinks(rootfsNode.find("LibsHardlinks"))
            else:
                print("[%s] Mount namespace disabled" % (self.sanityCheck.getName()))

        return entry

    def genereteUserSettings(self, configNode):

        entry = {}

        if self.privileged:
            userName = configNode.find("UserName")
            groupName = configNode.find("GroupName")
            if self.sanityCheck.validateTextEntry(userName) and self.sanityCheck.validateTextEntry(groupName):
                if self.prevUserName != userName.text or self.prevGroupName != groupName.text:
                    uid = self.rootfs.userNameToUid(userName.text)
                    gid = self.rootfs.groupNameToGid(groupName.text)
                    merge(entry, {
                        "process": {
                            "user": {"uid": 0, "gid": 0},
                        },
                        "linux": {
                            "uidMappings": [
                                {
                                    "hostID": int(uid),
                                    "containerID": 0,
                                    "size": 1
                                }
                            ],
                            "gidMappings": [
                                {
                                    "hostID": int(gid),
                                    "containerID": 0,
                                    "size": 10
                                }
                            ]
                        }
                    })

        return entry

    def generateCapsSettings(self, configNode):

        entry = {}
        capKeep = configNode.find("CapKeep")
        if self.sanityCheck.validateTextEntry(capKeep):
            capKeepList = re.split(',| |\n|\t', capKeep.text)
            capList = ['CAP_' + element.upper() for element in capKeepList]
            merge(entry, {
                "process": {
                    "capabilities": {
                        "bounding": capList,
                        "effective": capList,
                        "inheritable": capList,
                        "permitted": capList,
                        "ambient": capList
                    }
                }
            })

        return entry

    def createLxcConf(self, configNode):

        data = cJsonUtils.read(self.rootfs.getConfFileHost())

        if data is None:
            data = self.createDefault()

        data["hostname"] = self.rootfs.getSandboxName()

        print("[%s] Create Dobby CGROUP configuration" % (self.sanityCheck.getName()))
        cgroup = cCgroupDobby(self.sanityCheck)
        merge(data, cgroup.createCGroupConf(configNode.find("CGroupSettings")))

        merge(data, self.generateCapsSettings(configNode))
        merge(data, self.genereteUserSettings(configNode))
        merge(data, self.createConsoleConf(configNode))

        print("[%s] Create Dobby Network configuration" % (self.sanityCheck.getName()))
        merge(data, self.createNetworkConf(configNode))

        print("[%s] Create Dobby Environment configuration" % (self.sanityCheck.getName()))
        merge(data, self.createEnvConf(configNode))

        if configNode.find("Rootfs") is None or configNode.find("Rootfs").attrib["create"] == "no":
            self.rootfs.setShareRootfs(True)

        if not self.rootfs.isRootfsShared():
            print("[%s] Create Dobby D-Bus configuration" % (self.sanityCheck.getName()))
            dbus = cDbusDobby(self.rootfs)
            merge(data, dbus.createDbusConf(configNode.find("Dbus")))

            rootfsNode = configNode.find("Rootfs")
            if rootfsNode is not None:
                print("[%s] Create Dobby Mount Points configuration"%(self.sanityCheck.getName()))
                merge(data, self.createRootfsConf(rootfsNode))

        cJsonUtils.write(self.rootfs.getConfFileHost(), data)

    def createConsoleConf(self, configNode):

        entry = {}
        loggingNode = configNode.find("Logging")
        if loggingNode is not None:
            type = loggingNode.attrib["type"]
            if type == "file":
                logPath = loggingNode.find("LogPath")
                log = loggingNode.find("Log")
                if self.sanityCheck.validateTextEntry(logPath) and self.sanityCheck.validateTextEntry(log):
                    entry["rdkPlugins"] = {
                        "logging": {
                            "required": True,
                            "data": {
                                "fileOptions": {
                                    "limit": 1048576,
                                    "path": os.path.join("/", logPath.text, log.text),
                                },
                                "sink": "file"
                            }
                        },
                    }
                else:
                    raise Exception("[!!! ERROR !!!] Unknown console path value")
            else:
                Priority = loggingNode.find("Priority")
                if self.sanityCheck.validateTextEntry(Priority):
                    entry["rdkPlugins"] = {
                        "logging": {
                            "required": True,
                            "data": {
                                "journaldOptions": {
                                    "priority": Priority.text,
                                },
                                "sink": "journald"
                            }
                        },
                    }

        return entry

    @staticmethod
    def createDefault():

        return {
            "ociVersion": "1.0.2-dobby",
            "platform": {
                "os": "linux",
                # TODO hardcoded
                "arch": "arm"
            },
            "linux": {
                "resources": {
                    "devices": [{
                        "allow": False,
                        "access": "rwm"
                    }]
                },
                "namespaces": [
                    {"type": "pid"},
                    {"type": "ipc"},
                    {"type": "uts"},
                    {"type": "user"},
                    {"type": "mount"}
                ],
                "maskedPaths": [
                    "/proc/kcore",
                    "/proc/latency_stats",
                    "/proc/timer_stats",
                    "/proc/sched_debug"
                ],
                "readonlyPaths": [
                    "/proc/asound",
                    "/proc/bus",
                    "/proc/fs",
                    "/proc/irq",
                    "/proc/sys",
                    "/proc/sysrq-trigger"
                ]
            },
            "process": {
                # TODO hardcoded
                "cwd": "/",
                "rlimits": [
                    {
                        "type": "RLIMIT_NOFILE",
                        "hard": 1024,
                        "soft": 1024
                    },
                    {
                        "type": "RLIMIT_NPROC",
                        "hard": 300,
                        "soft": 300
                    },
                    {
                        "type": "RLIMIT_RTPRIO",
                        "hard": 6,
                        "soft": 6
                    }
                ],
            },
            "rdkPlugins": {
                "gpu": {
                    "required": False,
                    "data": {
                        "memory": 67108864
                    }
                }
            }
        }
