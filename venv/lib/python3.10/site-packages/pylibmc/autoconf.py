"Autoconfiguration"

import pylibmc

class UnsupportedAutoconfMethod(Exception):
    pass

class NoAutoconfFound(Exception):
    pass

def _elasticache_config_get(address, key):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    host, port = address.split(':')
    port = int(port)
    sock.connect((host, port))
    sock.send((f'config get {key}\r\n').encode('ascii'))
    state = 'wait-nl-header'
    nbytes = 0
    buff = b''
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError('failed reading cluster config')
        buff += chunk
        if state.startswith('wait-nl-') and b'\r\n' not in buff:
            continue
        elif state == 'wait-nl-header':
            line, buff = buff.split(b'\r\n', 1)
            if line.lower() == b'error':
                raise UnsupportedAutoconfMethod()
            cmd, key, flags, nbytes = line.split()
            flags, nbytes = int(flags), int(nbytes)
            state = 'read-body'
        elif state == 'ready-body':
            if len(buff) < nbytes:
                continue
            config, buff = buff[:nbytes], buff[nbytes+2:]
            state = 'wait-nl-end'
        elif state == 'wait-nl-end':
            break
        else:
            raise RuntimeError(state)
    return config

def _parse_elasticache_config(cfg):
    ver, nodes = cfg.split(b'\n')
    ver, nodes = int(ver), [n.decode('ascii').split('|') for n in nodes.split()]
    # NOTE Should probably verify ver == 12, but why not try anyways
    return [f'{addr or cname}:{port}' for (cname, addr, port) in nodes]

def elasticache(address='127.0.0.1:11211', config_key=b'cluster',
                mc_key='AmazonElastiCache:cluster'):
    try:
        config = _elasticache_config_get(address, config_key)
    except UnsupportedAutoconfMethod:
        config = pylibmc.Client([address]).get(mc_key)
        if config is None:
            raise NoAutoconfFound
    hosts = _parse_elasticache_config(config)
    return pylibmc.Client(hosts)
