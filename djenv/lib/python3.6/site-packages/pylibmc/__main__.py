"""Interactive shell"""

import sys
import code
import random
import pylibmc

tips = [
    "Want to use 127.0.0.1? Just hit Enter immediately.",
    "Hit Enter immediately and you'll connect to 127.0.0.1.",
    "Did you know there's a --binary flag? Try it!",
    "Want to use binary mode? Pass --binary as a sole argument."
]

def print_header(outf=sys.stdout):
    outf.write("pylibmc interactive shell\n\n")
    outf.write("Input list of servers, terminating by a blank line.\n")
    outf.write(random.choice(tips) + "\n")

def collect_servers():
    try:
        in_addr = raw_input("Address [127.0.0.1]: ")
    except NameError:
        in_addr = input("Address [127.0.0.1]: ")
    if in_addr:
        while in_addr:
            yield in_addr
            try:
                in_addr = raw_input("Address [<stop>]: ")
            except NameError:
                in_addr = input("Address [<stop>]: ")
    else:
        yield "127.0.0.1"

banner = "\nmc client available as `mc`\n"
def interact(servers, banner=banner, binary=False):
    mc = pylibmc.Client(servers, binary=binary)
    local = {"pylibmc": pylibmc,
             "mc": mc}
    code.interact(banner=banner, local=local)

def main():
    binary = False
    if sys.argv[1:] == ["--binary"]:
        binary = True
    print_header()
    interact(list(collect_servers()), binary=binary)

if __name__ == "__main__":
    main()
