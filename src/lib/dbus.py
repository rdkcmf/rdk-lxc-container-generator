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
#   class cDbus(object):
#
#       Represents info for dbus container environment
#
################################################################################
class cDbus(object):
    def __init__(self, rootfs):
        self.rootfs = rootfs

    def getSocketPath(self):
        return "var/run/dbus/system_bus_socket"

    def getLibDbusPath(self):
        return "usr/lib/libdbus-1.so.3"

    def createDbusConf(self, dbusNode):
        entry =""

        if dbusNode != None:
            enable = dbusNode.attrib["enable"]
            entry += "\n# LXC bindings for D-Bus\n"
            if (enable == "true"):
                entry += "lxc.mount.entry = /%s %s none rw,bind,nosuid,nodev,noexec 0 0\n"%(self.getSocketPath(), self.getSocketPath())

                entry += "lxc.mount.entry = /%s %s none ro,bind,nosuid,nodev  0 0\n"%(self.getLibDbusPath(), self.getLibDbusPath())

                self.rootfs.makeFile( "%s/%s"%(self.rootfs.getPathRootfsHost(), self.getSocketPath()))
                self.rootfs.createMountPointForFile(self.getLibDbusPath())

            else:
                entry = "\n# D-Bus disabled\n"

        return entry
