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
from .. import cDbus
from json_utils import cJsonUtils

merge = cJsonUtils.merge


################################################################################
#   class cDbusDobby(cDbus):
#
#       Represents info for dbus container environment
#
################################################################################
class cDbusDobby(cDbus):
    def __init__(self, rootfs):
        super(cDbusDobby, self).__init__(rootfs)

    def createDbusConf(self, dbusNode):
        entry = {}

        if dbusNode is not None:
            enable = dbusNode.attrib["enable"]
            if enable == "true":
                entry["rdkPlugins"] = {
                    "ipc": {
                        "required": False,
                        "data": {
                            # TODO hardcoded
                            "session": "ai-public",
                            "system": "system"
                        }
                    }
                }

        return entry
