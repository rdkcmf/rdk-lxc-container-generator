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
################################################################################
#   class DeviceCgroup(object):
#
#       Represents info for container device cgroups
#
################################################################################
class cCgroup(object):
    def devNull(self):
        return "# /dev/null\nlxc.cgroup.devices.allow = c 1:3 rw\n"

    def devZero(self):
        return "# /dev/zero\nlxc.cgroup.devices.allow = c 1:5 rw\n"

    def devFull(self):
        return "# /dev/full\nlxc.cgroup.devices.allow = c 1:7 rw\n"

    def devRandom(self):
        return "# /dev/random\nlxc.cgroup.devices.allow = c 1:8 rw\n"

    def devURandom(self):
        return "# /dev/urandom\nlxc.cgroup.devices.allow = c 1:9 rw\n"

    def devTty(self):
        return "# /dev/tty\nlxc.cgroup.devices.allow = c 5:0 rw\n"

    def createLxcConfDevicesCGroup(self, CGroupNode):

        entry = ""
        deviceCgroup = CGroupNode.find("DeviceCgroup");
        if (deviceCgroup != None):
            for device in deviceCgroup:
                if (device != None and device.text != None):
                    if ("name" in device.attrib and device.attrib["name"] != None):
                        entry += "# %s\n"% device.attrib["name"]
                    if (device.tag == "DevicesDeny"):
                        entry += "lxc.cgroup.devices.deny = %s\n"% device.text
                    elif (device.tag == "DevicesAllow"):
                        entry += "lxc.cgroup.devices.allow = %s\n"% device.text
                elif (device.tag == "AllowDefaultDevices" and "enable" in device.attrib and device.attrib["enable"] == "yes"):
                    entry += "# default allowed devices\n"
                    entry += self.devNull()
                    entry += self.devZero()
                    entry += self.devFull()
                    entry += self.devRandom()
                    entry += self.devURandom()
                    entry += self.devTty()
        return entry

    def createCGroupConf(self, CGroupNode):

        entry = ""
        if CGroupNode != None:

            entry += "\n# CGroup Container Configuration\n"

        # MEMORY
            memoryLimit = CGroupNode.find("MemoryLimit");
            if (memoryLimit != None and memoryLimit.text != None):
                entry += "lxc.cgroup.memory.limit_in_bytes = %s\n"%memoryLimit.text

            SoftMemoryLimit = CGroupNode.find("SoftMemoryLimit");
            if (SoftMemoryLimit != None and SoftMemoryLimit.text != None):
                entry += "lxc.cgroup.memory.soft_limit_in_bytes = %s\n"%SoftMemoryLimit.text

            OOMControl = CGroupNode.find("OOMControl");
            if (OOMControl != None and OOMControl.text != None):
                entry += "lxc.cgroup.memory.oom_control = %s\n"%OOMControl.text

        # CPU
            CpuShares = CGroupNode.find("CpuShares");
            if (CpuShares != None and CpuShares.text != None):
                entry += "lxc.cgroup.cpu.shares = %s\n"%CpuShares.text

            CpuRtRuntimeUS = CGroupNode.find("CpuRtRuntimeUS");
            if (CpuRtRuntimeUS != None and CpuRtRuntimeUS.text != None):
                entry += "lxc.cgroup.cpu.rt_runtime_us = %s\n"%CpuRtRuntimeUS.text

            CpuRtRuntimePeriod = CGroupNode.find("CpuRtRuntimePeriod");
            if (CpuRtRuntimePeriod != None and CpuRtRuntimePeriod.text != None):
                entry += "lxc.cgroup.cpu.rt_period_us = %s\n"%CpuRtRuntimePeriod.text

        # CPUSET
            CpusetCpus = CGroupNode.find("CpusetCpus");
            if (CpusetCpus != None and CpusetCpus.text != None):
                entry += "lxc.cgroup.cpuset.cpus = %s\n"%CpusetCpus.text

            CpusetCpuExlusive = CGroupNode.find("CpusetCpuExlusive");
            if (CpusetCpuExlusive != None and CpusetCpuExlusive.text != None):
                entry += "lxc.cgroup.cpuset.cpu_exclusive = %s\n"%CpusetCpuExlusive.text

            CpusetMems = CGroupNode.find("CpusetMems");
            if (CpusetMems != None and CpusetMems.text != None):
                entry += "lxc.cgroup.cpuset.mems = %s\n"%CpusetMems.text

            CpusetMemExclusive = CGroupNode.find("CpusetMemExclusive");
            if (CpusetMemExclusive != None and CpusetMemExclusive.text != None):
                entry += "lxc.cgroup.cpuset.mem_exclusive = %s\n"%CpusetMemExclusive.text

            CpusetMemHardwall = CGroupNode.find("CpusetMemHardwall");
            if (CpusetMemHardwall != None and CpusetMemHardwall.text != None):
                entry += "lxc.cgroup.cpuset.mem_hardwall = %s\n"%CpusetMemHardwall.text

            CpusetMemoryMigrate = CGroupNode.find("CpusetMemoryMigrate");
            if (CpusetMemoryMigrate != None and CpusetMemoryMigrate.text != None):
                entry += "lxc.cgroup.cpuset.memory_migrate = %s\n"%CpusetMemoryMigrate.text

            CpusetMemoryPreasureEnabled = CGroupNode.find("CpusetMemoryPreasureEnabled");
            if (CpusetMemoryPreasureEnabled != None and CpusetMemoryPreasureEnabled.text != None):
                entry += "lxc.cgroup.cpuset.memory_pressure_enabled = %s\n"%CpusetMemoryPreasureEnabled.text

            CpusetMemoryPreasure = CGroupNode.find("CpusetMemoryPreasure");
            if (CpusetMemoryPreasure != None and CpusetMemoryPreasure.text != None):
                entry += "lxc.cgroup.cpuset.cpuset.memory_pressure = %s\n"%CpusetMemoryPreasure.text

            CpusetMemorySpreadPage = CGroupNode.find("CpusetMemorySpreadPage");
            if (CpusetMemorySpreadPage != None and CpusetMemorySpreadPage.text != None):
                entry += "lxc.cgroup.cpuset.cpuset.memory_spread_page = %s\n"%CpusetMemorySpreadPage.text

            CpusetMemorySpreadSlab = CGroupNode.find("CpusetMemorySpreadSlab");
            if (CpusetMemorySpreadSlab != None and CpusetMemorySpreadSlab.text != None):
                entry += "lxc.cgroup.cpuset.cpuset.memory_spread_slab = %s\n"%CpusetMemorySpreadSlab.text

            CpusetSchedLoadBalance = CGroupNode.find("CpusetSchedLoadBalance");
            if (CpusetSchedLoadBalance != None and CpusetSchedLoadBalance.text != None):
                entry += "lxc.cgroup.cpuset.cpuset.sched_load_balance = %s\n"%CpusetSchedLoadBalance.text

            CpusetSchedDomainLevel = CGroupNode.find("CpusetSchedDomainLevel");
            if (CpusetSchedDomainLevel != None and CpusetSchedDomainLevel.text != None):
                entry += "lxc.cgroup.cpuset.cpuset.sched_relax_domain_level = %s\n"%CpusetSchedDomainLevel.text

            entry += "\n# CGroup Device Configuration\n"
            entry += self.createLxcConfDevicesCGroup(CGroupNode)

        return entry
