"""
Copyright (c) 2008, Opencraft <www.open-craft.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

#!/usr/bin/python

import sys
import subprocess
import signal
import migrationwizard.ocsettings as ocsettings

if (len(sys.argv) < 2 ):
	print 'Invalid number of arguments'
	sys.exit(1)


username = sys.argv[1]

pid = subprocess.Popen(["python" , ocsettings.project_path+"/transferuser.py" , username]).pid
signal.signal(signal.SIGCHLD, signal.SIG_IGN)
sys.exit(0)
