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
#   class cLog(object):
#
#       Represents info for logging inside container
#
################################################################################
class cLog(object):
    def __init__(self, rootfs):
        self.rootfs = rootfs

    def createLoggingConf(self, logNode, userName):
        entry =""

        if logNode != None:
            enable = logNode.attrib["enable"]
            if (enable == "true"):
                entry += "\n# LXC bindings for Logging\n"

		path = logNode.find("LogPath")
                entry += "lxc.mount.entry = /%s %s none rw,bind,nodev,noexec 0 0\n"%(path.text, path.text)
                self.rootfs.makeDir( "%s/%s"%(self.rootfs.getPathRootfsHost(), path.text))

		fd = open(self.rootfs.getRootfsPath() + "/etc/containerLog.properties", 'a')
		fd.write("\n# " + self.rootfs.getSandboxName())
		fd.write("\n" + self.rootfs.getSandboxName() + "_logs=\"")
		for log in logNode.iter('Log'):
			if (log != None and log.text != None):
				fd.write(" ")
				fd.write(log.text)
		if (logNode.iter('Log') != None):
			fd.write(" \"")
		fd.write("\n" + self.rootfs.getSandboxName() + "_user=" + userName.text + "\n")
		fd.close()

            else:
		entry = "\n# Logging disabled\n"

	return entry




