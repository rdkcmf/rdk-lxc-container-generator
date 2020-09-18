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
import string
import sys
from optparse import OptionParser

from lib import cRootfs
from lib import cLauncher
from lib import cConfig
from lib import cSanityCheck

try:
    from lib.dobby import cConfigDobby
    from lib.dobby import cRootfsDobby
    from lib.dobby import cLauncherDobby
except ImportError:
    cConfigDobby = None
    cRootfsDobby = None
    cLauncherDobby = None

# per container structs to preserve container information when processing container "append" xml
# indexed by container name
containers_rootfs = dict()
containers_launchers = dict()
containers_UserNames = dict()
containers_GroupNames = dict()
containers_UserNameRootFs = dict()
containers_GroupNameRootFs = dict()

# Force python XML parser not faster C accelerators
# because we can't hook the C implementation
sys.modules['_elementtree'] = None
import xml.etree.ElementTree as ET

class LineNumberingParser(ET.XMLParser):
    def _start_list(self, *args, **kwargs):
        # Here we assume the default XML parser which is expat
        # and copy its element position attributes into output Elements
        element = super(self.__class__, self)._start_list(*args, **kwargs)
        element._start_line_number = self.parser.CurrentLineNumber
        return element

    def _end(self, *args, **kwargs):
        element = super(self.__class__, self)._end(*args, **kwargs)
        element._end_line_number = self.parser.CurrentLineNumber
        return element


def parse_xml(inputXml, rootfsPath, shareRootfs, secure, tags, enableMountCheck, sleepUs):

    tree = ET.parse(inputXml, parser=LineNumberingParser())
    container = tree.getroot()
    name = container.attrib["SandboxName"]
    append = False

    if ('APPEND' in container.attrib):
        append = True
        print("\n\n===================================================================")
        print("\tGENERATE %s CONTAINER APPEND FOR %s "%(name,container.attrib["APPEND"]))
        print("====================================================================")
    else:
        print("\n\n===================================================================")
        print("\tGENERATE %s CONTAINER"%(name))
        print("==================================================================")

    main_base = os.path.dirname(__file__)
    confPath=main_base + "/conf" + "/config.ini"

    sanityCheck = cSanityCheck(inputXml, secure, name, rootfsPath, confPath, tags, enableMountCheck)
    sanityCheck.filter_out_inactive_tags(container)

    orig_name = name
    containerType = container.get("Type")
    if containerType == "dobby":
        if cRootfsDobby is None or cLauncherDobby is None or cConfigDobby is None:
            raise Exception("dobby generator missing")
        name = "%s_%s" % (orig_name, containerType)
        rootfs_class = cRootfsDobby
        launcher_class = cLauncherDobby
        config_class = cConfigDobby
    else:
        rootfs_class = cRootfs
        launcher_class = cLauncher
        config_class = cConfig

    if name not in containers_rootfs:
        containers_rootfs[name] = rootfs_class(orig_name, rootfsPath, shareRootfs)
    rootfs = containers_rootfs[name]
    if(not append):
        rootfs.createContainerTree()

    if name not in containers_launchers:
        containers_launchers[name] = launcher_class(sanityCheck, rootfs, sleepUs)
    launcher = containers_launchers[name]
    lxcParamsNode = launcher.matchVersion(container,"LxcParams")
    if (lxcParamsNode != None):
        if(append):
            launcher.appendLauncher(lxcParamsNode)
        else:
            launcher.createLauncher(lxcParamsNode)

    if name not in containers_UserNames:
        containers_UserNames[name] = dict() # usernames are indexed by xml ParamName. For main launcher use "start"
    userNames = containers_UserNames[name]

    if name not in containers_GroupNames:
        containers_GroupNames[name] = dict()
    groupNames = containers_GroupNames[name]

    config = config_class(sanityCheck, rootfs, secure, append,
                     userNames.get("start"), groupNames.get("start")) # pass main launcher user and group from "base" XML
    lxcConfigNode = container.find("LxcConfig")
    if (lxcConfigNode != None):
        config.createLxcConf(lxcConfigNode)

    config.processUsersAndGroups(lxcParamsNode, lxcConfigNode, userNames, groupNames)

    if (lxcConfigNode != None):
        # now assign uid:gid to rootfs files
        userName = lxcConfigNode.find("UserNameRootFs");
        # if UserNameRootFs not provided fall back to the one given in base xml
        if (userName == None or userName.text == None):
            userName = containers_UserNameRootFs.get(name)
            # if this is a base xml or the value was not provided in base xml, try UserName
            if (userName == None or userName.text == None):
                userName = lxcConfigNode.find("UserName");

        groupName = lxcConfigNode.find("GroupNameRootFs");
        # if GroupNameRootFs not provided fall back to the one given in base xml
        if (groupName == None or groupName.text == None):
            groupName = containers_GroupNameRootFs.get(name)
            # if this is a base xml or the value was not provided in base xml, try GroupName
            if (groupName == None or groupName.text == None):
                groupName = lxcConfigNode.find("GroupName");
                # if no groupName provided, take userName as groupName
                if (groupName == None or groupName.text == None):
                    groupName = userName

        if (userName != None and userName.text != None):
            uid=rootfs.userNameToUid(userName.text)
            gid=rootfs.groupNameToGid(groupName.text)

            rootfs.setUpContainersRights(uid, gid)

            containers_UserNameRootFs[name] = userName
            containers_GroupNameRootFs[name] = groupName
        else:
            rootfs.setUpContainersRights("0", "0")


def main():

    parser = OptionParser()

    parser.usage = """
genContainer.py [options] [files]

Example:
genContainer.py -r ~/user/rdk/some_path_to_rootfs -R ro -s -u 5000000 lxc_conf_DIBBLER.xml
    will generate secure DIBBLER container at given rootfs for debug version with architecture arm_16.4 and OE 2.1
    Note: Several input files can be provided in one command line
          It is recommended to pass all .xml files related to one container in one run to handle
          dependencies correctly
"""

    parser.add_option("-r", "--rootfs", dest = "rootfs",
                                        action = "store", type = "string",
                                        help = "rootfs directory where container dir and its files will be generated")

    parser.add_option("-s","--secure",
                                        dest = "secure", action = "store_true",
                                        help = "Create unprivileged container")

    parser.add_option("-t", "--tags",
                                        dest = "tags", action = "store", type = "string",
                                        help = "tags")

    parser.add_option("-e", "--sharedRootfs",
                                        dest = "sharedRootfs", action = "store_true",
                                        help = "Containers share rootfs with host")

    parser.add_option("-S", "--sanity",
                                        dest = "enableMountCheck", action = "store_true",
                                        help = "Enable sanity check")

    parser.add_option("-u", "--usleep",
                                        dest = "sleepUs", action = "store", type = "int", default = 500000,
                                        help = "How many microseconds to sleep, after sending systemd-notify")

    (options, args) = parser.parse_args()

    rootfsPath = options.rootfs

    secure = False if options.secure == None else options.secure

    sharedRootfs = False if options.sharedRootfs == None else options.sharedRootfs

    enableMountCheck = False if options.enableMountCheck == None else options.enableMountCheck

    tags = options.tags

    sleepUs = options.sleepUs

    if not (rootfsPath) or len(args) == 0:
        print parser.print_help()
        exit(1)

    for inputXml in args:
        parse_xml(inputXml, rootfsPath, sharedRootfs, secure, tags, enableMountCheck, sleepUs);

    wasError = False
    for rootfs in containers_rootfs.values():
        if rootfs.checkLibraryDeps():
            wasError = True

    if wasError:
        sys.exit(1)

if __name__ == "__main__":
        main()
