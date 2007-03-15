#! /bin/sh
#
# this file is *inserted* into the install section of the generated
# spec file
#

# this is, what dist.py normally does
python setup.py install --root=${RPM_BUILD_ROOT} --record="INSTALLED_FILES"

for i in `cat INSTALLED_FILES`; do
  if [ -f ${RPM_BUILD_ROOT}/$i ]; then
    echo $i >>FILES
  fi
  if [ -d ${RPM_BUILD_ROOT}/$i ]; then
    echo %dir $i >>DIRS
  fi
done

cat DIRS FILES >INSTALLED_FILES
