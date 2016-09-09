from fabric.api import sudo, task, cd

# CHANNEL TASKS
@task
def setup_redis():
    sudo("apt-get update && apt-get install -y redis-server")
    sudo("sed -i -e 's/127.0.0.1/0.0.0.0/g' /etc/redis/redis.conf")
    sudo("/etc/init.d/redis-server stop")
    sudo("/etc/init.d/redis-server start")


@task
def setup_channels():
    sudo("apt-get update && apt-get install -y git python-dev python-setuptools python-pip")
    sudo("pip install -U pip")
    sudo("pip install -U asgi_redis asgi_ipc git+https://github.com/django/daphne.git@#egg=daphne")
    sudo("rm -rf /srv/channels")
    sudo("git clone https://github.com/django/channels.git /srv/channels/")
    with cd("/srv/channels/"):
        sudo("python setup.py install")


@task
def run_daphne(redis_ip):
    with cd("/srv/channels/testproject/"):
        sudo("REDIS_URL=redis://%s:6379 daphne -b 0.0.0.0 -p 80 testproject.asgi:channel_layer" % redis_ip)


@task
def run_worker(redis_ip):
    with cd("/srv/channels/testproject/"):
        sudo("REDIS_URL=redis://%s:6379 python manage.py runworker" % redis_ip)


# Current loadtesting setup
@task
def setup_load_tester(src="https://github.com/django/channels.git"):
    sudo("apt-get update && apt-get install -y git nodejs && apt-get install npm")
    sudo("npm install -g loadtest")
    sudo("ln -s /usr/bin/nodejs /usr/bin/node")


# Run current loadtesting setup
# example usage: $ fab run_loadtest:http://127.0.0.1,rps=10 -i "id_rsa" -H ubuntu@example.com
@task
def run_loadtest(host, t=90):
    sudo("loadtest -c 10 -t {t} {h}".format(h=host, t=t))

# Run current loadtesting setup
# example usage: $ fab run_loadtest:http://127.0.0.1,rps=10 -i "id_rsa" -H ubuntu@example.com
@task
def run_loadtest_rps(host, t=90, rps=200):
    sudo("loadtest -c 10 --rps {rps} -t {t} {h}".format(h=host, t=t, rps=rps))


# Task that Andrew used for loadtesting earlier on
@task
def setup_tester():
    sudo("apt-get update && apt-get install -y apache2-utils python3-pip")
    sudo("pip3 -U pip autobahn twisted")
    sudo("rm -rf /srv/channels")
    sudo("git clone https://github.com/django/channels.git /srv/channels/")


@task
def shell():
    sudo("bash")
