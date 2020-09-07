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
from .. import cRootfs


################################################################################
#   class cRootfsDobby(cRootfs):
#
#       Represents directories on rootfs,
#       implements basic functionalities to manipulate with rootfs.
#
################################################################################
class cRootfsDobby(cRootfs):
    def __init__(self, name, rootfsPath, shareRootfs):
        super(cRootfsDobby, self).__init__(name, rootfsPath, shareRootfs)

    def getPathRootfsTarget(self):
        return "/container/%s/rootfs_dobby" % self.name

    def getPathRootfsHost(self):
        return "%s/container/%s/rootfs_dobby" % (self.rootfsPath, self.name)

    def getConfFileHost(self):
        return "%s/container/%s/config.json" % (self.rootfsPath, self.name)

    def getPathPasswdFileTarget(self):
        return "%s/container/%s/rootfs_dobby/etc/passwd" % (self.rootfsPath, self.name)

    def getPathGroupFileTarget(self):
        return "%s/container/%s/rootfs_dobby/etc/group" % (self.rootfsPath, self.name)

################################################################################
#
#   createContainerTree():
#
#   Generate container directory:
#         /container/name
#                     |__rootfs_dobby
#
################################################################################
    def createContainerTree(self):
        self.makeDir(self.getPathRootfsHost())

    def setUpContainersRights(self, uid, gid):
        linux_cmd = "chmod o-rwx,a-w %s -R " % self.getPathContainerHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}" % error)

        linux_cmd = "chmod 550 %s" % self.getPathContainerParentDirHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}" % error)

        linux_cmd = "chmod 440 %s -R " % self.getConfFileHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}" % error)

################################################################################
#
#   createUsersEntries(userNames, groupNames):
#
#   Parse /etc/passwd and /etc/group on host rootfs and generate /etc/passwd
#   and /etc/group in container rootfs with minimum of information.
#   (Only container users amd groups).
#
################################################################################
    def createUserGroupEntries(self, userNames, groupNames):
        if not userNames and not groupNames:
            print("Skipping passwd and group generation")
            return

        self.makeFile(self.getPathPasswdFileTarget())
        fd = open(self.getPathPasswdFileTarget(), 'w')
        with open(self.getPathPasswdFileHost(), "r") as file:
            for line in file:
                for userName in userNames.values():
                    if line.startswith(userName + ":"):
                        p = line.split(":")
                        fd.write("%s:%s:0:0:%s" % (p[0], p[1], ":".join(p[4:])))
                        break
        file.close()
        fd.close()

        self.makeFile(self.getPathGroupFileTarget())
        fd = open(self.getPathGroupFileTarget(), 'w')
        with open(self.getPathGroupFileHost(), "r") as file:
            for line in file:
                for groupName in groupNames.values():
                    if line.startswith(groupName + ":"):
                        p = line.split(":")
                        fd.write("%s:%s:0:%s" % (p[0], p[1], ":".join(p[3:])))
                        break
        file.close()
        fd.close()
