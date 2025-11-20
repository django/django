#!/bin/bash

# Backport helper for Django stable branches.

set -xue

if [ -z $1 ]; then
    echo "Full hash of commit to backport is required."
    exit
fi

BRANCH_NAME=`git branch | sed -n '/\* stable\//s///p'`
echo $BRANCH_NAME

# Ensure clean working directory
git reset --hard

REV=$1

TMPFILE=tmplog.tmp

# Cherry-pick the commit
git cherry-pick ${REV}

# Create new log message by modifying the old one
git log --pretty=format:"[${BRANCH_NAME}] %s%n%n%b%nBackport of ${REV} from main." HEAD^..HEAD \
    | grep -v '^BP$' > ${TMPFILE}

# Commit new log message
git commit --amend -F ${TMPFILE}

# Clean up temporary files
rm -f ${TMPFILE}

git show
