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
from dbus import cDbus
from cgroup import cCgroup
from sanity_check import cSanityCheck

################################################################################
#   class cConfig(object):
#
#       Represents container configuration,
#       implements basic functionalities to generate lxc.conf.
#
################################################################################
class cConfig(object):
    def __init__(self, sanityCheck, rootfs, privileged, append, prevUserName, prevGroupName):
        self.sanityCheck = sanityCheck
        self.rootfs = rootfs
        self.privileged = privileged
        self.autodev = True
        self.isAppend = append
        self.prevUserName = prevUserName
        self.prevGroupName = prevGroupName

    def processUsersAndGroups(self, lxcParamsNode, lxcConfigNode, allUserNames, allGroupNames):
        # add username and groupname for main service
        if (lxcConfigNode != None):
            userName = lxcConfigNode.find("UserName");
            groupName = lxcConfigNode.find("GroupName");
            if (groupName == None or groupName.text == None):
                groupName = userName
            if (userName != None and userName.text != None):
                allUserNames["start"] = userName.text # main launcher doesn't have a ParamName attribute, so use "start"
            if (groupName != None and groupName.text != None):
                allGroupNames["start"] = groupName.text

            extraUserNames = lxcConfigNode.find("ExtraUsers")
            if extraUserNames != None:
                for userName in extraUserNames.iter("UserName"):
                    if (userName != None and userName.text != None):
                        allUserNames["additional-" + userName.text] = userName.text

            extraGroupNames = lxcConfigNode.find("ExtraGroups")
            if extraGroupNames != None:
                for groupName in extraGroupNames.iter("GroupName"):
                    if (groupName != None and groupName.text != None):
                        allGroupNames["additional-" + groupName.text] = groupName.text

        # add usernames and groupnames for secondary services if needed
        if (lxcParamsNode != None):
            for attachEntry in lxcParamsNode.iter('Attach'):
                paramName = attachEntry.find("ParamName").text
                userName = attachEntry.find("UserName");
                groupName = attachEntry.find("GroupName");
    
                # if no groupName provided, take userName as groupName
                if (groupName == None or groupName.text == None):
                    groupName = userName
    
                if (userName != None and userName.text != None):
                    allUserNames[paramName] = userName.text
                if (groupName != None and groupName.text != None):
                    allGroupNames[paramName] = groupName.text
    
        if (not self.sanityCheck.isPrivileged() ):
            allUserNames["hardcoded-root"] = "root" # assuming none of the launchers will ever have ParamName == "hardcoded-root"
            allGroupNames["hardcoded-root"] = "root"
            allUserNames["hardcoded-lxc"] = "lxc" # assuming none of the launchers will ever have ParamName == "hardcoded-lxc"
            allGroupNames["hardcoded-lxc"] = "lxc"

        if (not self.rootfs.isRootfsShared()):
            print ("[%s] Create /etc/passwd /etc/group entries for container"%(self.sanityCheck.getName()))
            self.rootfs.createUserGroupEntries(allUserNames, allGroupNames)

    def createEnvConf(self, lxcConfigNode):

        entry = ""
        envNode = lxcConfigNode.find("Environment")

        if (self.sanityCheck.validateTextEntry(envNode)):
            entry += "\n# Environment Variables Configuration\n"
            preload = list()

            for variable in envNode.iter('Variable'):
                if (variable != None and variable.text != None):
                    parts = variable.text.split("=")
                    var_name = parts[0].strip()
                    if (var_name == "LD_PRELOAD" and len(parts) > 1):
                        # avoid duplicates
                        for solib in parts[1].split(":"):
                            if solib not in preload:
                                preload.append(solib)
                    else:
                        entry += "lxc.environment = %s\n"%(variable.text)

            if preload:
                entry += "lxc.environment = LD_PRELOAD=%s\n"%(":".join(preload))
                for preload_lib in preload:
                    self.rootfs.addLibraryRequired(preload_lib, 'LD_PRELOAD')
        else:
                print("We do not need to create Environment variables")

        return entry

    def createNetworkConf(self, lxcConfigNode):

        entry  =""

        for networkNode in lxcConfigNode.iter('Network'):
            if networkNode != None:
                entry += "\n# LXC network interface configuration\n"
                type = networkNode.attrib["type"]

                if (type == "veth" or type == "macvlan"):
                    entry += "lxc.network.type = %s\n"%(type)

                    name   = networkNode.find("Name")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.name = %s\n"%(name.text)

                    flags  = networkNode.find("Flags")
                    if (self.sanityCheck.validateTextEntry(flags)):
                        entry += "lxc.network.flags = %s\n"%(flags.text)

                    link   = networkNode.find("Link")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.link = %s\n"%(link.text)

                    pair   = networkNode.find("Pair")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.veth.pair = %s\n"%(pair.text)

                    hwaddr = networkNode.find("HwAddr")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.hwaddr = %s\n"%(hwaddr.text)

                    ipv4   = networkNode.find("IPV4")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.ipv4 = %s\n"%(ipv4.text)

                    ipv4Gw = networkNode.find("IPV4gateway")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.ipv4.gateway = %s\n"%(ipv4Gw.text)

                    ipv6   = networkNode.find("IPV6")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.ipv6 = %s\n"%(ipv6.text)

                    ipv6Gw = networkNode.find("IPV6gateway")
                    if (self.sanityCheck.validateTextEntry(name)):
                        entry += "lxc.network.ipv6.gateway = %s\n"%(ipv6Gw.text)
                else :
                    entry += "lxc.network.type = %s\n"%(type)

        return entry

    def createMountPoint(self, type, path, source):

        if (type == "dir"):
            self.rootfs.makeDir( "%s/%s"%(self.rootfs.getPathRootfsHost(), path))
        elif (type == "file"):
            self.rootfs.createMountPointForFile(path, source)
        elif (type == "dev"):
            if(self.autodev):
                print("[%s] Skipping creating entry for devices cause - autodev enabled."%(self.sanityCheck.getName()))
            else:
                self.rootfs.makeFile( "%s/%s"%(self.rootfs.getPathRootfsHost(), path))
        else:
            raise Exception("No such type for mount point {%s}"%(type))

    def getAutodevSettings(self, lxcConfigNode):

        entry = "\n# When autodev =1 LXC mounts and populate a minimal /dev when container starts\n"
        autoDev = lxcConfigNode.find("AutoDev")

        if(self.rootfs.isRootfsShared()):
            print("[%s] Shared rootfs was set, overwriting autodev settings to false"%(self.sanityCheck.getName()))
            self.autodev = False
            entry += "lxc.autodev = 0\n"
        else:
            if (self.sanityCheck.validateTextEntry(autoDev)):
                entry += "lxc.autodev = %s\n"%(autoDev.text)
                if (autoDev.text == "0"):
                    self.autodev =False
                else:
                    self.autodev =True
            else:
                entry += "lxc.autodev = 1\n"
                self.autodev =True

        return entry


    def generateMountPoints(self, mountPointNode):

        entry = ""
        if (mountPointNode != None):
            entry += "\n# Mount Points Configuration\n"
            for mountPoint in mountPointNode.iter('Entry'):
                if(mountPoint != None):
                    source = mountPoint.find("Source")
                    destination = mountPoint.find("Destination")
                    options = mountPoint.find("Options").text
                    type = mountPoint.attrib["type"]
                    dump = 0
                    fsck = 0
                    fsType = "none"

                    if (self.sanityCheck.validateTextEntry(mountPoint.find("Dump"))):
                        dump = mountPoint.find("Dump").text

                    if (self.sanityCheck.validateTextEntry(mountPoint.find("Fsck"))):
                        fsck = mountPoint.find("Fsck").text

                    if (self.sanityCheck.validateTextEntry(mountPoint.find("FsType"))):
                        fsType = mountPoint.find("FsType").text

                    if (self.sanityCheck.validateTextEntry(source) and self.sanityCheck.validateTextEntry(destination)):

                        self.sanityCheck.validateMountBind(source.text, options)
                        self.sanityCheck.validateOptions(source.text, fsType, options)
                        if(source.text == destination.text):
                            if(not self.sanityCheck.checkNestedMountBinds(source.text)):
                                raise Exception("[%s] Nested mount bind found =  %s ", source.text)

                        entry += "lxc.mount.entry = %s %s %s %s %s %s\n"%(source.text,
                                                                        destination.text,
                                                                        fsType,
                                                                        options,
                                                                        dump,
                                                                        fsck)

                        self.createMountPoint(type, destination.text, source.text)
                        if (type == "dir"):
                            self.sanityCheck.addDir(source.text)
                            for unusedEntry in mountPoint.iter('Unused'):
                                if (self.sanityCheck.validateTextEntry(unusedEntry)):
                                    self.rootfs.unusedList.append(unusedEntry.text)
                            self.rootfs.checkElfDepsForDirectoryMountPoint(destination.text, source.text)

                    else:
                        raise Exception("INVALID DATA MOUNT POINT")

        return entry

    def moveContent(self, moveContentNode):

        if moveContentNode != None:
            for moveContent in moveContentNode.iter('Entry'):
                source = moveContent.find("Source")
                destination = moveContent.find("Destination")
                type = moveContent.attrib["type"]

                if (self.sanityCheck.validateTextEntry(source) and self.sanityCheck.validateTextEntry(destination)):
                    if type == "dir":
                        self.rootfs.moveDir("%s"%(self.rootfs.getRootfsPath() + source.text), "%s"%(self.rootfs.getPathRootfsHost() + destination.text))
                    elif type == "file":
                        self.rootfs.moveFile("%s"%(self.rootfs.getRootfsPath() + source.text), "%s"%(self.rootfs.getPathRootfsHost() + destination.text))
                    else:
                        print("[%s] No such type for mount content --> %s"%(type,self.sanityCheck.getName()))
        else:
            print("[%s] Move content entry not found, skipping"%(self.sanityCheck.getName()))

    def generateLibMountPoints(self, libBindingsNode):

        entry = ""
        if libBindingsNode != None:
            entry += "\n# Mount Binds Configuration For Libs\n"
            for libsScanDir in libBindingsNode.iter('LibsScanDir'):
                if self.sanityCheck.validateTextEntry(libsScanDir):
                    self.rootfs.addLibsScanDir(libsScanDir.text)
                else:
                   raise Exception("[!!! ERROR !!!] Invalid <LibsScanDir> tag: Must contain a dir")

            for libBinding in libBindingsNode.iter('Entry'):
                if (self.sanityCheck.validateTextEntry(libBinding)):
                    libList = self.rootfs.findLibByName(libBinding.text)
                    for source in libList:
                        if(self.sanityCheck.pathExist(source)):
                            entry += "lxc.mount.entry = /%s %s none ro,bind,nodev,nosuid 0 0\n"%(source,
                                                                                        source)
                            self.rootfs.createMountPointForFile(source)
                        else:
                            raise Exception("[!!! ERROR !!!] Rootfs does not contain (%s) - No such file or directory"%(source))
        return entry

    def generateHardlinks(self, libHardlinksNode):

        if libHardlinksNode is not None:
            for libHardlink in libHardlinksNode.iter('Entry'):
                if self.sanityCheck.validateTextEntry(libHardlink):
                    libList = self.rootfs.findLibByName(libHardlink.text)
                    for source in libList:
                        if self.sanityCheck.pathExist(source):
                            self.rootfs.createHardlinkForFile(source)
                        else:
                            raise Exception("[!!! ERROR !!!] Rootfs does not contain (%s) - No such file or directory"%(source))

    def createRootfsConf(self, rootfsNode):

        entry = ""

        if rootfsNode != None:
            rootfsCreate = rootfsNode.attrib["create"]
            if  rootfsCreate == "yes":
                if(not self.isAppend):
                    entry += "\n# Rootfs path settings\n"
                    entry +="lxc.rootfs = %s\n"%(self.rootfs.getPathRootfsTarget())
                entry += self.generateMountPoints(rootfsNode.find("MountPoints"))
                self.moveContent(rootfsNode.find("MoveContent"))
                entry += self.generateLibMountPoints(rootfsNode.find("LibsRoBindMounts"))
                self.generateHardlinks(rootfsNode.find("LibsHardlinks"))
            else:
                print("[%s] Mount namespace disabled"%(self.sanityCheck.getName()))

        return entry

    def genereteUserSettings(self, lxcConfigNode):

        entry = ""

        if(self.privileged):
            userName = lxcConfigNode.find("UserName");
            groupName = lxcConfigNode.find("GroupName");
            if (self.sanityCheck.validateTextEntry(userName) and self.sanityCheck.validateTextEntry(groupName)):
                if (self.prevUserName != userName.text or self.prevGroupName != groupName.text):
                    uid=self.rootfs.userNameToUid(userName.text)
                    gid=self.rootfs.groupNameToGid(groupName.text)
                    entry +="\n# USER/GROUP Container Configuration\n"
                    entry += "lxc.init_uid = %s\n"%(uid)
                    entry += "lxc.init_gid = %s\n"%(gid)

            print("[%s] Non-root container created"%(self.sanityCheck.getName()))
        else:
            print("[%s] Root container created"%(self.sanityCheck.getName()))

        return entry

    def generateCapsSettings(self, lxcConfigNode):

        entry = ""
        capDrop = lxcConfigNode.find("CapDrop");
        if (self.sanityCheck.validateTextEntry(capDrop)):
            capDropList = re.split(',| |\n|\t', capDrop.text)
            for capDropEntry in capDropList:
                entry += "lxc.cap.drop = %s\n"% capDropEntry

        capKeep = lxcConfigNode.find("CapKeep");
        if (self.sanityCheck.validateTextEntry(capKeep)):
            capKeepList = re.split(',| |\n|\t', capKeep.text)
            for capKeepEntry in capKeepList:
                entry += "lxc.cap.keep = %s\n"% capKeepEntry

        return entry

    def createLxcConf(self, lxcConfigNode):

        conf_fd = open(self.rootfs.getConfFileHost(), 'a')

        if(self.isAppend):
            conf_fd.write("\n\n# Platform specific settings \n")
        else:
            conf_fd.write("# Container hostname settings \n")
            conf_fd.write("lxc.utsname = %s\n"%self.rootfs.getSandboxName())

        print("[%s] Create LXC CGROUP configuration"%(self.sanityCheck.getName()))
        cgroup = cCgroup(self.sanityCheck)
        cgroupConfig = cgroup.createCGroupConf(lxcConfigNode.find("CGroupSettings"))
        conf_fd.write(cgroupConfig)

        capsConfig = self.generateCapsSettings(lxcConfigNode)
        conf_fd.write(capsConfig)

        userConfig = self.genereteUserSettings(lxcConfigNode)
        conf_fd.write(userConfig)

        print("[%s] Create LXC Network configuration"%(self.sanityCheck.getName()))
        networkConfig = self.createNetworkConf(lxcConfigNode);
        conf_fd.write(networkConfig);

        lxcInclude = lxcConfigNode.find("LxcInclude");
        if (self.sanityCheck.validateTextEntry(lxcInclude)):
            conf_fd.write("lxc.include = %s\n"% lxcInclude.text)

        print("[%s] Create LXC Environment configuration"%(self.sanityCheck.getName()))
        envInfo = self.createEnvConf(lxcConfigNode);
        conf_fd.write(envInfo);

        if( not self.isAppend):
            autodevInfo = self.getAutodevSettings(lxcConfigNode)
            conf_fd.write(autodevInfo);

        if (lxcConfigNode.find("Rootfs") == None or lxcConfigNode.find("Rootfs").attrib["create"] == "no"):
            self.rootfs.setShareRootfs(True)

        if(not self.rootfs.isRootfsShared()):
            print("[%s] Create LXC D-Bus configuration"%(self.sanityCheck.getName()))
            dbus = cDbus(self.rootfs)
            dbusConfig = dbus.createDbusConf(lxcConfigNode.find("Dbus"))
            conf_fd.write(dbusConfig);

            rootfsNode = lxcConfigNode.find("Rootfs");
            if (rootfsNode != None and rootfsNode.text != None):
                print("[%s] Create LXC Mount Points configuration"%(self.sanityCheck.getName()))
                rootfsInfo = self.createRootfsConf(rootfsNode);
                conf_fd.write(rootfsInfo);

            for autoMount in lxcConfigNode.iter("AutoMount"):
                if (self.sanityCheck.validateAutoMount(autoMount)):
                    conf_fd.write("\nlxc.mount.auto = %s\n"%(autoMount.text));

        else:
            conf_fd.write("\nlxc.autodev = 0\n")

        conf_fd.close()
