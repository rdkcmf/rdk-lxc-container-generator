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
import re
from ..cgroup import cCgroup
from json_utils import cJsonUtils

merge = cJsonUtils.merge


################################################################################
#   class cCgroupDobby(cCgroup):
#
#       Represents info for container device cgroups
#
################################################################################
class cCgroupDobby(cCgroup):
    def __init__(self, sanityCheck):
        super(cCgroupDobby, self).__init__(sanityCheck)

    def createLxcConfDevicesCGroup(self, CGroupNode):

        entry = {}
        deviceCgroup = CGroupNode.find("DeviceCgroup")
        if deviceCgroup is not None:
            for device in deviceCgroup:
                if self.sanityCheck.validateTextEntry(device):
                    if "name" in device.attrib and device.attrib["name"] is not None:
                        path = device.attrib["name"]
                        m = re.match('(.) (.+):(.+) (.+)', device.text)
                        type = m.group(1)
                        major = int(m.group(2))
                        minor = int(m.group(3))
                        access = m.group(4)
                        dev = {"path": path, "type": type, "major": major, "minor": minor}
                        merge(entry, {"linux": {"devices": [dev]}})
                        allow = device.tag != "DevicesDeny"
                        dev = {"allow": allow, "type": type, "major": major, "minor": minor, "access": access}
                        merge(entry, {"linux": {"resources": {"devices": [dev]}}})
                    else:
                        raise Exception("Device name is required")

                elif device.tag == "AllowDefaultDevices" and "enable" in device.attrib and device.attrib["enable"] == "yes":
                    defaultDevices = [
                        self.devNull(),
                        self.devZero(),
                        self.devFull(),
                        self.devRandom(),
                        self.devURandom(),
                        self.devTty()
                    ]
                    for d in defaultDevices:
                        m = re.match('# (.+)\nlxc.cgroup.devices.allow = (.) (.+):(.+) (.+)\n', d)
                        path = m.group(1)
                        type = m.group(2)
                        major = int(m.group(3))
                        minor = int(m.group(4))
                        access = m.group(5)
                        dev = {"path": path, "type": type, "major": major, "minor": minor}
                        merge(entry, {"linux": {"devices": [dev]}})
                        dev = {"allow": True, "type": type, "major": major, "minor": minor, "access": access}
                        merge(entry, {"linux": {"resources": {"devices": [dev]}}})

        return entry

    def createCGroupConf(self, CGroupNode):

        entry = {}
        if CGroupNode is not None:

            # MEMORY
            memoryLimit = CGroupNode.find("MemoryLimit")
            if self.sanityCheck.validateTextEntry(memoryLimit):
                merge(entry, {"linux": {"resources": {"memory": {"limit": int(memoryLimit.text)}}}})
            memoryMemSwapLimit = CGroupNode.find("MemoryMemSwapLimit")
            if self.sanityCheck.validateTextEntry(memoryMemSwapLimit):
                merge(entry, {"linux": {"resources": {"memory": {"swap": int(memoryMemSwapLimit.text)}}}})
            SoftMemoryLimit = CGroupNode.find("SoftMemoryLimit")
            if self.sanityCheck.validateTextEntry(SoftMemoryLimit):
                merge(entry, {"linux": {"resources": {"memory": {"reservation": int(SoftMemoryLimit.text)}}}})
            OOMControl = CGroupNode.find("OOMControl")
            if self.sanityCheck.validateTextEntry(OOMControl):
                merge(entry, {"linux": {"resources": {"memory": {"disableOOMKiller": bool(OOMControl.text)}}}})

            # CPU
            CpuShares = CGroupNode.find("CpuShares")
            if self.sanityCheck.validateTextEntry(CpuShares):
                merge(entry, {"linux": {"resources": {"cpu": {"shares": int(CpuShares.text)}}}})
            CpuRtRuntimeUS = CGroupNode.find("CpuRtRuntimeUS")
            if self.sanityCheck.validateTextEntry(CpuRtRuntimeUS):
                merge(entry, {"linux": {"resources": {"cpu": {"realtimeRuntime": int(CpuRtRuntimeUS.text)}}}})
            CpuRtRuntimePeriod = CGroupNode.find("CpuRtRuntimePeriod")
            if self.sanityCheck.validateTextEntry(CpuRtRuntimePeriod):
                merge(entry, {"linux": {"resources": {"cpu": {"realtimePeriod": int(CpuRtRuntimePeriod.text)}}}})

            # CPUSET
            CpusetCpus = CGroupNode.find("CpusetCpus")
            if self.sanityCheck.validateTextEntry(CpusetCpus):
                merge(entry, {"linux": {"resources": {"cpu": {"cpus": CpusetCpus.text}}}})
            CpusetMems = CGroupNode.find("CpusetMems")
            if self.sanityCheck.validateTextEntry(CpusetMems):
                merge(entry, {"linux": {"resources": {"cpu": {"mems": CpusetMems.text}}}})

            merge(entry, self.createLxcConfDevicesCGroup(CGroupNode))

        return entry
