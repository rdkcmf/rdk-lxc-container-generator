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

    def createStorageConf(self, configNode):

        entry = {}

        for storageNode in configNode.iter('Storage'):
            if storageNode is not None:
                entry["rdkPlugins"] = {
                    "storage": {
                        "required": False,
                        "data": {
                            "loopback": [],
                            "dynamic": [],
                            "mountOwner": []
                        }
                    }
                }

                # Process LoopBack mounts
                for loopback in storageNode.iter('Loopback'):
                    destination = loopback.attrib["destination"]
                    source = loopback.attrib["source"]

                    img_size = 0
                    # Default to 12MB
                    if "size" in loopback.attrib:
                        img_size = int(loopback.attrib["size"])
                    else:
                        img_size = 12582912

                    persistent = False
                    if "persistent" in loopback.attrib:
                        if loopback.attrib["persistent"].lower() == "true":
                            persistent = True

                    loopback_entry = {
                        "destination": destination,
                        "flags": 14,
                        "fstype": "ext4",
                        "source": source,
                        "imgsize": img_size,
                        "persistent": persistent
                    }

                    entry["rdkPlugins"]["storage"]["data"]["loopback"].append(loopback_entry)

                # Process dynamic mounts
                for dynamic in storageNode.iter('Dynamic'):
                    destination = dynamic.attrib["destination"]
                    source = dynamic.attrib["source"]
                    options = dynamic.attrib["options"]

                    dynamic_entry = {
                        "destination": destination,
                        "options": options.split(","),
                        "source": source
                    }

                    entry["rdkPlugins"]["storage"]["data"]["dynamic"].append(dynamic_entry)

                # Process mount owners
                for mountOwner in storageNode.iter('MountOwner'):
                    source = mountOwner.attrib["source"]
                    user = mountOwner.attrib["user"]
                    group = mountOwner.attrib["group"]

                    recursive = False
                    if "recursive" in mountOwner.attrib:
                        if mountOwner.attrib["recursive"].lower() == "true":
                            recursive = True

                    owner_entry = {
                        "source": source,
                        "user": user,
                        "group": group,
                        "recursive": recursive
                    }

                    entry["rdkPlugins"]["storage"]["data"]["mountOwner"].append(owner_entry)

        return entry

    def createThunderConfig(self, configNode):

        entry = {}

        thunderNode = configNode.find("Thunder")

        if thunderNode is not None:
            enable = thunderNode.attrib["enable"]

            if enable.lower() == "true":
                entry["rdkPlugins"] = {
                    "thunder": {
                        "required": True,
                        "dependsOn": ["networking"],
                        "data": {}
                    }
                }

            if "bearerUrl" in thunderNode.attrib:
                entry["rdkPlugins"]["thunder"]["data"]["bearerUrl"] = thunderNode.attrib["bearerUrl"]

            if "trusted" in thunderNode.attrib:
                if thunderNode.attrib["trusted"].lower() == "true":
                    entry["rdkPlugins"]["thunder"]["data"]["trusted"] = True

        return entry

    def createMinidumpConfig(self, configNode):

        entry = {}

        minidumpNode = configNode.find("Minidump")

        if minidumpNode is not None:
            enable = minidumpNode.attrib["enable"]
            path = minidumpNode.attrib["path"]

            if enable.lower() == "true":
                entry["rdkPlugins"] = {
                    "minidump": {
                        "required": False,
                        "data": {
                            "destinationPath": path
                        }
                    }
                }

        return entry

    def createOOMCrashConfig(self, configNode):

        entry = {}

        OOMCrashNode = configNode.find("OOMCrash")

        if OOMCrashNode is not None:
            enable = OOMCrashNode.attrib["enable"]
            path = OOMCrashNode.attrib["path"]

            if enable.lower() == "true":
                entry["rdkPlugins"] = {
                    "oomcrash": {
                        "required": False,
                        "data": {
                            "path": path
                        }
                    }
                }

        return entry

    def createMemCheckpointRestoreConfig(self, configNode):

        entry = {}

        memCheckpointRestoreNode = configNode.find('MemCheckpointRestore')
        if memCheckpointRestoreNode is not None:
            entry["rdkPlugins"] = {
                "memcheckpointrestore": {
                    "required": False,
                    "data": {
                        "mountpoints": []
                    }
                }
            }

            # Process mount points
            for mountPoint in memCheckpointRestoreNode.iter('MountPoint'):
                destination = mountPoint.attrib["destination"]
                source = mountPoint.attrib["source"]
                options = mountPoint.attrib["options"]

                mountPointEntry = {
                    "source" : source,
                    "destination": destination,
                    "type": "bind",
                    "options" : options.split(",")
                }

                entry["rdkPlugins"]["memcheckpointrestore"]["data"]["mountpoints"].append(mountPointEntry)

        return entry

    def createLocalTimeConfig(self, configNode):

        entry = {}

        LocalTimeNode = configNode.find("LocalTime")

        if LocalTimeNode is not None:
            enable = LocalTimeNode.attrib["enable"]

            if enable.lower() == "true":
                entry["rdkPlugins"] = {
                    "localtime": {
                        "required": False,
                        "data": {}
                    }
                }

                if "setTZ" in LocalTimeNode.attrib:
                    entry["rdkPlugins"]["localtime"]["data"]["setTZ"] = LocalTimeNode.attrib["setTZ"]

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

                multicast = networkNode.find("Multicast")
                if multicast is not None and "enable" in multicast.attrib:
                    entry["rdkPlugins"]["networking"]["data"]["multicastForwarding"] = []
                    for rule in multicast.iter("Rule"):
                        multicast_data = {
                            "ip": rule.attrib["ip"],
                            "port": int(rule.attrib["port"])
                        }
                        entry["rdkPlugins"]["networking"]["data"]["multicastForwarding"].append(multicast_data)


                port_forwarding = networkNode.find("PortForwarding")
                if port_forwarding is not None and "enable" in port_forwarding.attrib:
                    entry["rdkPlugins"]["networking"]["data"]["portForwarding"] = {}

                    if "localhostmasquerade" in port_forwarding.attrib:
                        entry["rdkPlugins"]["networking"]["data"]["portForwarding"]["localhostMasquerade"] = True

                    for rule in port_forwarding.iter("Rule"):
                        port_forward_rule = {
                            "port": int(rule.attrib["port"]),
                            "protocol": rule.attrib["protocol"]
                        }

                        if rule.attrib["direction"] == "ContainerToHost":
                            if entry["rdkPlugins"]["networking"]["data"]["portForwarding"].get("containerToHost") is None:
                                entry["rdkPlugins"]["networking"]["data"]["portForwarding"]["containerToHost"] = []

                            entry["rdkPlugins"]["networking"]["data"]["portForwarding"]["containerToHost"].append(port_forward_rule)
                        elif rule.attrib["direction"] == "HostToContainer":
                            if entry["rdkPlugins"]["networking"]["data"]["portForwarding"].get("hostToContainer") is None:
                                entry["rdkPlugins"]["networking"]["data"]["portForwarding"]["hostToContainer"] = []

                            entry["rdkPlugins"]["networking"]["data"]["portForwarding"]["hostToContainer"].append(port_forward_rule)
                        else:
                            raise Exception("INVALID PORT FORWARDING RULE")
        return entry

    def createSeccompConf(self, configNode):

        entry = {}
        seccompProfile = configNode.find("SeccompProfile")

        if self.sanityCheck.validateTextEntry(seccompProfile):
            names = []
            seccomp = {"defaultAction": "SCMP_ACT_ERRNO", "architectures": "SCMP_ARCH_ARM","syscalls":[{"names":names,"action":"SCMP_ACT_ALLOW"}]}

            file_base = os.path.dirname(__file__)
            seccompFile = file_base + "/" + seccompProfile.text
            if os.path.exists(seccompFile):
                with open(seccompFile, "r") as file:
                    for sysCall in file:
                        if sysCall is not None:
                            names.append(sysCall.rstrip("\n"))
                merge(entry, {"linux": {"seccomp": seccomp}})

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
                                        "source":  os.path.join("/", source),
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
                            "user": {
                                "uid": 0,
                                "gid": 0,
                                "additionalGids": []
                            },
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
                                    "size": 1
                                }
                            ]
                        }
                    })

            additionalGroupNode = configNode.find("AdditionalGroups")

            if self.sanityCheck.validateTextEntry(additionalGroupNode):
                for additionalGroupName in additionalGroupNode.iter("GroupName"):
                    if self.sanityCheck.validateTextEntry(additionalGroupName):
                        additionalGid = self.rootfs.groupNameToGid(additionalGroupName.text)
                        entry["linux"]["gidMappings"].append({
                            "hostID": int(additionalGid),
                            "containerID": int(additionalGid),
                            "size": 1
                        })
                        entry["process"]["user"]["additionalGids"].append(int(additionalGid))
            else:
                print("We do not need to add any additional gids")

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

    def generateResourcelimits(self, configNode):
        entry = {}
        entry["process"] = {}

        rLimitsNode = configNode.find("ResourceLimits")
        if self.sanityCheck.validateTextEntry(rLimitsNode):
            entry["process"]["rlimits"] = []
            for limit in rLimitsNode.iter("Limit"):
                limitType = limit.attrib["type"]
                limitSoft = limit.attrib["soft"]
                limitHard = limit.attrib["hard"]

                limitEntry = {
                    "type": limitType,
                    "hard": int(limitHard),
                    "soft": int(limitSoft)
                }

                entry["process"]["rlimits"].append(limitEntry)

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

        print("[%s] Create Dobby resource limits" % (self.sanityCheck.getName()))
        merge(data, self.generateResourcelimits(configNode))

        print("[%s] Create Dobby Network configuration" % (self.sanityCheck.getName()))
        merge(data, self.createNetworkConf(configNode))

        print("[%s] Create Dobby Storage configuration" % (self.sanityCheck.getName()))
        merge(data, self.createStorageConf(configNode))

        print("[%s] Create Dobby Seccomp configuration" % (self.sanityCheck.getName()))
        merge(data, self.createSeccompConf(configNode))

        print("[%s] Create Dobby Environment configuration" % (self.sanityCheck.getName()))
        merge(data, self.createEnvConf(configNode))

        print("[%s] Create Dobby Thunder configuration" % (self.sanityCheck.getName()))
        merge(data, self.createThunderConfig(configNode))

        print("[%s] Create Dobby Minidump configuration" % (self.sanityCheck.getName()))
        merge(data, self.createMinidumpConfig(configNode))

        print("[%s] Create Dobby OOMCrash configuration" % (self.sanityCheck.getName()))
        merge(data, self.createOOMCrashConfig(configNode))

        print("[%s] Create Dobby MemCheckpointRestore configuration" % (self.sanityCheck.getName()))
        merge(data, self.createMemCheckpointRestoreConfig(configNode))

        print("[%s] Create Dobby LocalTime configuration" % (self.sanityCheck.getName()))
        merge(data, self.createLocalTimeConfig(configNode))

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
                "cwd": "/"
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
