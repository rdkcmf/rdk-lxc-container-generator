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
import xml.etree.ElementTree as ET

from lib import cRootfs
from lib import cLauncher
from lib import cConfig
from lib import cSanityCheck


def parse_xml(input_xml, rootfsPath, soc, oe, shareRootfs, version, secure):

    tree = ET.parse(input_xml)
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

    sanityCheck = cSanityCheck(soc, oe, version, secure, name, rootfsPath)

    rootfs = cRootfs(name, rootfsPath, shareRootfs)
    if(not append):
        rootfs.createContainerTree()

    launcher = cLauncher(sanityCheck, rootfs)
    lxcParamsNode = launcher.matchVersion(container,"LxcParams")
    if (lxcParamsNode != None):
        launcher.createLauncher(lxcParamsNode)

    config = cConfig(sanityCheck, rootfs, secure, append)
    lxcConfigNode = container.find("LxcConfig")
    if (lxcConfigNode != None):
        config.createLxcConf(lxcConfigNode)

    if (rootfs.isRootfsShared):
        print ("[%s] Create /etc/passwd /etc/group entries for container\n"%(name))
        config.createPasswdAndGroupFiles(lxcParamsNode, lxcConfigNode)

    # now assign uid:gid to rootfs files
    userName = lxcConfigNode.find("UserNameRootFs");
    if (userName == None or userName.text == None):
        userName = lxcConfigNode.find("UserName");

    groupName = lxcConfigNode.find("GroupNameRootFs");
    if (groupName == None or groupName.text == None):
        groupName = lxcConfigNode.find("GroupName");
        # if no groupName provided, take userName as groupName
        if (groupName == None or groupName.text == None):
            groupName = userName

    if (userName != None and userName.text != None):
        uid=rootfs.userNameToUid(userName.text)
        gid=rootfs.groupNameToGid(groupName.text)

        rootfs.setUpContainersRights(uid, gid)
    else:
        rootfs.setUpContainersRights("0", "0")


def main():

    parser = OptionParser()

    parser.usage = """
genContainer.py [options]

Example:
genContainer.py -f lxc_conf_DIBBLER.xml -r ~/user/rdk/some_path_to_rootfs -R ro -s -S arm_16.4 -o 2.1 -v debug
    will generate secure DIBBLER container at given rootfs for debug version with architecture arm_16.4 and OE 2.1
"""

    parser.add_option("-f", "--file",   dest = "filename",
                                        action = "store", type = "string",
                                        help = "XML container configuration to parse and generate container from")

    parser.add_option("-r", "--rootfs", dest = "rootfs",
                                        action = "store", type = "string",
                                        help = "rootfs directory where container dir and its files will be generated")

    parser.add_option("-s",
                                        dest = "secure", action = "store_true",
                                        help = "Create unprivileged container")

    parser.add_option("-S", "--soc",    dest = "soc",
                                        action = "store", type = "string",
                                        help = "Platform Unique arch_version for example arm_16.3, arm_16.4 ")

    parser.add_option("-o", "--oe",     dest = "oe",
                                        action = "store", type = "string",
                                        help = "OE/Yocto Version [2.0 | 2.1 | 2.2]")

    parser.add_option("-e",
                                        dest = "shared_rootfs", action = "store_true",
                                        help = "Containers share rootfs with host")

    parser.add_option("-v", "--ver",    dest = "version",
                                        action = "store", type = "string",
                                        help = "debug, release or production")

    (options, args) = parser.parse_args()

    input_xml = options.filename

    rootfsPath = options.rootfs

    soc = options.soc

    oe = options.oe

    secure = False if options.secure == None else options.secure

    shared_rootfs = False if options.shared_rootfs == None else options.shared_rootfs

    version = options.version

    if not (rootfsPath):
        print parser.print_help()
        exit(1)

    if (input_xml) :
        parse_xml(input_xml, rootfsPath, soc, oe, shared_rootfs, version, secure);
    else:
        print parser.print_help()

if __name__ == "__main__":
        main()
