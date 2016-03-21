from fabric.api import sudo, task, cd


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
    sudo("pip install -U asgi_redis git+https://github.com/andrewgodwin/daphne.git@#egg=daphne")
    sudo("rm -rf /srv/channels")
    sudo("git clone https://github.com/andrewgodwin/channels.git /srv/channels/")
    with cd("/srv/channels/"):
        sudo("python setup.py install")


@task
def setup_tester():
    sudo("apt-get update && apt-get install -y apache2-utils python3-pip")
    sudo("pip3 -U pip autobahn twisted")
    sudo("rm -rf /srv/channels")
    sudo("git clone https://github.com/andrewgodwin/channels.git /srv/channels/")


@task
def run_daphne(redis_ip):
    with cd("/srv/channels/testproject/"):
        sudo("REDIS_URL=redis://%s:6379 daphne -b 0.0.0.0 -p 80 testproject.asgi:channel_layer" % redis_ip)


@task
def run_worker(redis_ip):
    with cd("/srv/channels/testproject/"):
        sudo("REDIS_URL=redis://%s:6379 python manage.py runworker" % redis_ip)


@task
def shell():
    sudo("bash")
