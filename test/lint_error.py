import sys
import os,json

def badFunction( x,y ):
    z=x+y
    unused_var = 100
    return z

class badly_named_class:
    def __init__(self):
        self.CONSTANT = []
    
    def Badly_Named_Method(self):
        print ('poorly spaced string')
        return None