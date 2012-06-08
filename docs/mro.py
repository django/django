""" 
Undocumented and crazy, with a silly workflow, but it turns <class>.mro() into
formatted RestructuredText.

Documentation to come soon.
"""

from django.conf import settings
settings.configure()

def print_mro(cls):
    """ If passed in a class will return a string that turns the MRO for
        that class into an attractive RestructuredText snippet.
    """
    print cls.mro()
        
def clean(text):
    text = text.replace("[","").replace("]","")
    items = text.split(',')
    for item in items:
        item = item.strip()
        if item == "<type 'object'>":
            continue
        item = item.replace("'", "`")
        item = item.replace("<class ", "* :class:")
        item = item.replace(">", "")
        print(item)
            
if __name__=='__main__':
    class A(object): pass
    class B(A): pass
    print_mro(B)

    