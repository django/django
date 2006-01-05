from django.core.template import Library

register = Library()

def path_breadcrumbs(path, overrides="", front=0, back=0):
    overs = overrides.split('/')
    comps = [""] * int(front) + path.split('/')[:-1]
    backs = int(back) + len(comps)
    overs.extend([None for x in range(len(overs) -1, len(comps))])
    text = []
    for comp, ov in zip(comps, overs):
        label = ov or comp
        text.append("<a href='%s'>%s</a> &rsaquo; \n" % ("../" * backs, label))
        backs -= 1
    return "".join(text)
path_breadcrumbs = register.simple_tag(path_breadcrumbs)
