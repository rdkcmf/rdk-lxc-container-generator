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
import shlex
from json_utils import cJsonUtils
from config import cConfigDobby
from .. import cLauncher

merge = cJsonUtils.merge


################################################################################
#            class cLauncherDobby(cLauncher):
#
#                    Represents directories for container environment
#
################################################################################
class cLauncherDobby(cLauncher):
    def __init__(self, sanityCheck, rootfs, sleepUs):
        super(cLauncherDobby, self).__init__(sanityCheck, rootfs, sleepUs)

    def createLauncher(self, paramsNode):

        data = cJsonUtils.read(self.rootfs.getConfFileHost())

        if data is None:
            data = cConfigDobby.createDefault()

        if paramsNode is not None:
            merge(data, {
                "process": {
                    "terminal": False,  # default
                    "noNewPrivileges": True,  # default
                    "args": [
                        "/usr/libexec/DobbyInit",
                        paramsNode.find("ExecName").text
                    ],
                }
            })
            execParams = paramsNode.find("ExecParams")
            if self.sanityCheck.validateTextEntry(execParams):
                merge(data, {
                    "process": {
                        "args": shlex.split(execParams.text)
                    }
                })

        cJsonUtils.write(self.rootfs.getConfFileHost(), data)

    def appendLauncher(self, paramsNode):
        self.createLauncher(paramsNode)
