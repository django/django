#! /bin/sh
#
# This file becomes the install section of the generated spec file.
#

# This is what dist.py normally does.
%{__python} setup.py install --root=${RPM_BUILD_ROOT} --record="INSTALLED_FILES"

# Sort the filelist so that directories appear before files. This avoids
# duplicate filename problems on some systems.
touch DIRS
for i in `cat INSTALLED_FILES`; do
  if [ -f ${RPM_BUILD_ROOT}/$i ]; then
    echo $i >>FILES
  fi
  if [ -d ${RPM_BUILD_ROOT}/$i ]; then
    echo %dir $i >>DIRS
  fi
done

# Make sure we match foo.pyo and foo.pyc along with foo.py (but only once each)
sed -e "/\.py[co]$/d" -e "s/\.py$/.py*/" DIRS FILES >INSTALLED_FILES

mkdir -p ${RPM_BUILD_ROOT}/%{_mandir}/man1/
cp docs/man/* ${RPM_BUILD_ROOT}/%{_mandir}/man1/
cat << EOF >> INSTALLED_FILES
%doc %{_mandir}/man1/*"
EOF
