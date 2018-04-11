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
#   class cRootfs(object):
#
#       Represents directories on rootfs,
#       implements basic functionalities to manipultae with rootfs.
#
################################################################################
class cRootfs(object):
    def __init__(self, name, rootfsPath, shareRootfs ):
        self.name = name
        self.rootfsPath = rootfsPath
        self.shareRootfs = shareRootfs
        self.launcherName = " "

    def isRootfsShared(self):
        return self.shareRootfs

    def setShareRootfs(self,shareRootfs):
        self.shareRootfs = shareRootfs

    def setLauncherName(self, launcherName):
        self.launcherName=launcherName

    def getRootfsPath(self):
        return self.rootfsPath

    def getSandboxName(self):
        return self.name

    def getPathContainerParentDirHost(self):
        return "%s/container"%self.rootfsPath

    def getPathContainerHost(self):
        return "%s/container/%s"%(self.rootfsPath, self.name)

    def getPathRootfsTarget(self):
        return "/container/%s/rootfs"%self.name

    def getPathRootfsHost(self):
        return "%s/container/%s/rootfs"%(self.rootfsPath, self.name)

    def getPathConfFileHost(self):
        return "%s/container/%s/conf"%(self.rootfsPath, self.name)

    def getConfFileHost(self):
        return "%s/container/%s/conf/lxc.conf"%(self.rootfsPath, self.name)

    def getConfFileTarget(self):
        return "/container/%s/conf/lxc.conf"%self.name

    def getPathLauncherFileHost(self):
        return "%s/container/%s/launcher"%(self.rootfsPath, self.name)

    def getLauncherFileHost(self):
        return "%s/container/%s/launcher/%s.sh"%(self.rootfsPath, self.name, self.launcherName)

    def getPathPasswdFileHost(self):
        return "%s/etc/passwd"%(self.rootfsPath)

    def getPathPasswdFileTarget(self):
        return "%s/container/%s/rootfs/etc/passwd"%(self.rootfsPath, self.name)

    def getPathGroupFileHost(self):
        return "%s/etc/group"%(self.rootfsPath)

    def getPathGroupFileTarget(self):
        return "%s/container/%s/rootfs/etc/group"%(self.rootfsPath, self.name)

    def makeDir(self, dirName):
        if (os.path.exists(dirName)):
            raise Exception("The directory already exist -- nested mount bind found {%s}"%(dirName))
        else:
            error = os.makedirs(dirName)
            if error:
                raise Exception("program returned error code {%s}"%(error))

    def makeFile(self, filename):
        if not os.path.exists(os.path.dirname(filename)):
            error = os.makedirs(os.path.dirname(filename))
            if error:
                raise Exception("program returned error code {%s}"%(error))

        error = os.system("touch %s"%(filename))
        if error:
            raise Exception("program returned error code {%s}"%(error))

################################################################################
#
#   createContainerTree():
#
#   Generate container directory:
#         /container/name
#                     |__launcher
#                     |__conf
#                     |__rootfs
#                        |__dev
#                        |__init.lxc.static
#
################################################################################
    def createContainerTree(self):
        self.makeDir(self.getPathLauncherFileHost())
        self.makeDir(self.getPathConfFileHost())
        self.makeDir(self.getPathRootfsHost())
        self.makeDir(self.getPathRootfsHost()+"/dev")
        self.makeFile("%s/init.lxc.static" % (self.getPathRootfsHost()));

    def moveFile(self, source, destination):
        if not os.path.exists(os.path.dirname(destination)):
            error = os.makedirs(os.path.dirname(destination))
            if error:
                raise Exception("program returned error code {%s}"%(error))

        error = os.system("mv %s %s"%(source, destination))
        if error:
            raise Exception("program returned error code {%s}"%(error))

    def moveDir(self, source, destination):
        if not os.path.exists(destination):
            error = os.makedirs(destination)
            if error:
                raise Exception("program returned error code {%s}"%(error))

        error = os.system("mv %s %s"%(source, destination))
        if error:
            raise Exception("program returned error code {%s}"%(error))

    def setUpContainersRights(self, uid, gid):

        if (uid != "0" and gid != "0"):
            linux_cmd = "chown %s:%s -R %s"%(uid,gid,self.getPathRootfsHost())
            error = os.system(linux_cmd)
            if error:
                raise Exception("program returned error code {%s}"%(error))

        # remove all "other" user file rights and all write rights for this container
        linux_cmd = "chmod o-rwx,a-w %s -R "%self.getPathContainerHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}"%(error))

        # set proper rights for container parent dir, non-recursive
        linux_cmd = "chmod 550 %s"%self.getPathContainerParentDirHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}"%(error))

        # set proper rights for container launcher
        if (self.launcherName != None and self.launcherName != " "):
            linux_cmd = "chmod 550 %s -R "%self.getLauncherFileHost()
            error = os.system(linux_cmd)
            if error:
                raise Exception("program returned error code {%s}"%(error))

        # set the proper rights for lxc.conf
        linux_cmd = "chmod 440 %s -R "%self.getConfFileHost()
        error = os.system(linux_cmd)
        if error:
            raise Exception("program returned error code {%s}"%(error))

################################################################################
#
#   findLibByName(libName):
#
#       Find libs version based on their name. Function finds the lib,
#       then checks if it matches the pattern
#
################################################################################
    def findLibByName(self, libName):

        lib = []

        for root, dirs, files in os.walk(self.rootfsPath + "/lib"):
            if (root == self.rootfsPath +"/lib"):
                for file in sorted(files):
                    if file.startswith(libName):
                        if (libName + "." in file or libName + "-" in file):
                            lib.append(os.path.join("lib", file))

        for root, dirs, files in os.walk(self.rootfsPath + "/usr/lib"):
            if (root == self.rootfsPath +"/usr/lib"):
                for file in sorted(files):
                    if file.startswith(libName):
                        if (libName + "." in file or libName + "-" in file):
                            lib.append(os.path.join("usr/lib", file))

        if not lib:
            raise Exception("[!!! FIND  !!!] Rootfs does not contain (%s) - No such file or directory"%(libName))

        return lib

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

        self.makeFile(self.getPathPasswdFileTarget())
        fd = open(self.getPathPasswdFileTarget(), 'a')
        with open(self.getPathPasswdFileHost(), "r") as file:
            for lines in file:
                for userName in userNames:
                    if lines.startswith(userName + ":"):
                        fd.write(lines)
                        break
        file.close()
        fd.close()

        self.makeFile(self.getPathGroupFileTarget())
        fd = open(self.getPathGroupFileTarget(), 'a')
        with open(self.getPathGroupFileHost(), "r") as file:
            for lines in file:
                parts = lines.split(":")
                if (len(parts) > 3):
                    # include main groups of users
                    isMainGroup = False
                    for groupName in groupNames:
                        if (parts[0] == groupName):
                            isMainGroup = True
                            break
                    # include any groups they are member of
                    members = parts[3].strip().split(",")
                    builtMembersString = ""
                    for member in members:
                        for userName in userNames:
                            if (member == userName):
                                builtMembersString += "," + userName
                                break
                    if (isMainGroup or builtMembersString):
                        fd.write("%s:%s:%s:%s\n"%(parts[0], parts[1], parts[2], builtMembersString[1:]))
        file.close()
        fd.close()

################################################################################
#   userNameToUid(cCurrPath,userName):
#       Convert user name to UID
################################################################################
    def userNameToUid(self, userName):
        uid=""

        with open(self.getPathPasswdFileHost(), "r") as file:
            for lines in file:
                if lines.startswith(userName + ":"):
                    uid=lines.split(":")[2]
            file.close()

        if (uid == None or uid==""):
            raise Exception("No such user! [Name = %s]"%(userName))

        return uid

################################################################################
#   groupNameToGid(cCurrPath,groupName):
#       Convert group name to GID
################################################################################
    def groupNameToGid(self, groupName):
        gid=""

        with open(self.getPathGroupFileHost(), "r") as file:
            for lines in file:
                if lines.startswith(groupName + ":"):
                    gid=lines.split(":")[2]
            file.close()

        if (gid == None or gid==""):
            raise Exception("No such group! [Name = %s]"%(groupName))

        return gid

