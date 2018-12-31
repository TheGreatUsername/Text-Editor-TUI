import os
import subprocess

class terminal:
    def __init__(self):
        self.out = ''
        self.err = ''
        self.record = ''
        self.pref = '>>'
        self.cx = 0
        self.sy = 0
        self.hi = -1
        self.s = ''
        self.history = []
    def command(self, inpt):
        self.history.append(inpt)
        self.record += self.pref + inpt + '\n'
        process = subprocess.Popen(inpt, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)                               
        
        out, err = process.communicate()
        out = out.decode('utf-8')
        err = err.decode('utf-8')
        self.out += out
        self.err += err
        self.record += out + err + '\n'
        if inpt.strip() == 'clear':
            self.record = ''
        return out, err
    def run(self):
        result = self.command(self.s)
        self.s = ''
        self.cx = 0
        return result
    def getlines(self):
        return self.record.split('\n')
