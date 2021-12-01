# ----------------------------------------------------------------------
# Author:   yury.matveev@desy.de
# ----------------------------------------------------------------------

import os, subprocess

aliases_path = os.path.expanduser('~/.bash_aliases')

my_alias = "alias camera='" + os.getcwd() + "/start_camera.sh'\n"

if os.path.exists(aliases_path):
    print('bash_aliases existing, modifying')
    with open(aliases_path, 'r') as f:
        current_file = f.readlines()

need_to_add_alias = True
for ind, line in enumerate(current_file):
    if 'camera' in line:
        need_to_add_alias = False
        current_file[ind] = my_alias
        break

if need_to_add_alias:
    current_file.append(my_alias)

with open(aliases_path, 'w') as f:
    f.writelines(current_file)

print('bash_aliases edited')

