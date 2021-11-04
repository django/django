## Source Code ##
git clone https://github.com/ActiveState/django.git
git checkout stable/1.11.x
git checkout rickp/CVE-2021-33203
## Setup ##
yay -S python2
sudo python2.7 -m ensurepip
python2.7 -m pip install --user -r requirements/py2.txt
python2 -m pip install --user -e ..
## Run The Tests ##
python2 ./runtests.py --parallel 1 (edited) 
