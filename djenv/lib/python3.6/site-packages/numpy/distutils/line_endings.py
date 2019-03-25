""" Functions for converting from DOS to UNIX line endings

"""
from __future__ import division, absolute_import, print_function

import sys, re, os

def dos2unix(file):
    "Replace CRLF with LF in argument files.  Print names of changed files."
    if os.path.isdir(file):
        print(file, "Directory!")
        return

    data = open(file, "rb").read()
    if '\0' in data:
        print(file, "Binary!")
        return

    newdata = re.sub("\r\n", "\n", data)
    if newdata != data:
        print('dos2unix:', file)
        f = open(file, "wb")
        f.write(newdata)
        f.close()
        return file
    else:
        print(file, 'ok')

def dos2unix_one_dir(modified_files, dir_name, file_names):
    for file in file_names:
        full_path = os.path.join(dir_name, file)
        file = dos2unix(full_path)
        if file is not None:
            modified_files.append(file)

def dos2unix_dir(dir_name):
    modified_files = []
    os.path.walk(dir_name, dos2unix_one_dir, modified_files)
    return modified_files
#----------------------------------

def unix2dos(file):
    "Replace LF with CRLF in argument files.  Print names of changed files."
    if os.path.isdir(file):
        print(file, "Directory!")
        return

    data = open(file, "rb").read()
    if '\0' in data:
        print(file, "Binary!")
        return
    newdata = re.sub("\r\n", "\n", data)
    newdata = re.sub("\n", "\r\n", newdata)
    if newdata != data:
        print('unix2dos:', file)
        f = open(file, "wb")
        f.write(newdata)
        f.close()
        return file
    else:
        print(file, 'ok')

def unix2dos_one_dir(modified_files, dir_name, file_names):
    for file in file_names:
        full_path = os.path.join(dir_name, file)
        unix2dos(full_path)
        if file is not None:
            modified_files.append(file)

def unix2dos_dir(dir_name):
    modified_files = []
    os.path.walk(dir_name, unix2dos_one_dir, modified_files)
    return modified_files

if __name__ == "__main__":
    dos2unix_dir(sys.argv[1])
