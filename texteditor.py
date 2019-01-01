import curses
import sys
import os.path
import re
import inputfunc
import json
import terminal

class editor:
    def __init__(self, scr, file):
        self.mode = 'edit'
        self.terminal = terminal.terminal()
        self.scr = scr
        height, width = scr.getmaxyx()
        self.scrh = height
        self.scrw = width
        self.edith = height
        self.editw = width
        #caret positioning
        self.cx = 0
        self.cy = 0
        #screen positioning
        self.sx = 0
        self.sy = 0
        self.key = 0
        self.ck = ''
        f = open(file, 'r')
        txt = f.read()
        f.close()
        self.filename = file
        self.lines = txt.split('\n')
        self.keystrokes = 0
        self.message = 'Welcome! Press ctrl-q for help'
        self.showkeycodes = False

        self.helplines = open('help.txt').read().split('\n')
        self.ishelpon = False

        self.undoq = [inputfunc.ministate(self.lines, self.cx, self.cy)]
        self.redoq = []

        #handle highlighting
        l = re.findall('(.+?)(\.[^\.]+$|$)', self.filename)
        extension = '' if len(l) == 0 else l[-1][-1][1:]
        self.highlight = filetext('highlight_{}.txt'.format(extension)).split('\n')

        #autocompletion stuff
        self.isautocomp = False
        self.acword = ''
        self.acwordx = 0
        self.acwords = []
        self.linewords = re.findall('[_a-zA-Z][_a-zA-Z0-9]*', (self.lines + [''])[0])
        self.aci = 0 #autocomplete index
        freqmap = {}
        words = re.findall('[_a-zA-Z][_a-zA-Z0-9]*', txt)
        for w in words:
            if w in freqmap.keys() : freqmap[w] += 1
            else : freqmap[w] = 1
        self.freqmap = freqmap
        d = freqmap
        self.lastwords = [pair[0] for pair in sorted(d.items(), key=lambda item: item[1])][::-1]

    def doinput(self) : inputfunc.doinput(self, curses)
    
    def refresh(self):
        lnlen = (len(str(len(self.lines))) + 1) #width of line numbers
        self.editw = self.scrw - lnlen
        self.edith = self.scrh
        #clear screen
        for i in range(self.edith-1):
            self.scr.addstr(i, 0, ' ' * (self.scrw), curses.color_pair(1))
        for i in range(self.edith - 1):
            if self.sy + i >= len(self.lines) : break
            #draw edit window
            self.scr.addstr(i, lnlen, (self.lines[self.sy+i] + ' ' *
                                   (self.editw - len(self.lines[i])))
                            [self.sx:self.sx+self.editw], curses.color_pair(1))
            line = self.lines[self.sy + i]
            for h in self.highlight:
                found = [m.start() for m in re.finditer('\\b{}\\b'.format(h),
                                                        line)]
                for f in found:
                    self.scr.addstr(i, lnlen + f, h, curses.color_pair(9))
            self.scr.addstr(i+1, lnlen, ' ', curses.color_pair(1))
            ln = str(self.sy + i + 1)
            #draw line numbers
            self.scr.addstr(i, 0, ' ' * (lnlen - len(ln) - 1) + ln + '|',
                            curses.color_pair(5))
        #draw carot
        px = self.cx
        py = self.cy
        if px > len(self.lines[py]) : px = len(self.lines[py])
        l = self.lines[py] if py < len(self.lines) else lines[-1]
        c = l[px] if px < len(l) else ' '
        px -= self.sx
        py -= self.sy
        px += lnlen
        if py < 0 : py = 0
        if px < 0 : px = 0
        self.scr.addstr(py, px, c, curses.color_pair(4))

        #autocomplete 
        if self.isautocomp:
            l = self.acwords
            if self.aci < 0 : self.aci = 0
            elif self.aci >= len(l) : self.aci = len(l) - 1
            x = self.cx - 1
            line = self.lines[py]
            if x >= len(line) : x = len(line) - 1
            while x >= 0 and line[x].isalpha() : x -= 1
            x += 1
            maxc = 0
            for s in l:
                if len(s) > maxc : maxc = len(s)
            for i in range(len(l)):
                y = py + i + 1
                if y >= self.edith-1 : break
                if i == self.aci : col = curses.color_pair(7)
                else : col = curses.color_pair(6)
                self.scr.addstr(y, lnlen + x, spacebuf(l[i], maxc), col)

        #terminal
        if self.mode == 'terminal':
            h = int(self.edith / 2)
            t = self.terminal
            l = t.getlines()
            l += [''] * h
            li = len(l) - h * 2
            if t.sy < 0 : t.sy = 0
            elif t.sy >= len(l) - h * 2: t.sy = len(l) - h * 2
            li -= t.sy
            if li < 0 : li = 0
            for i in range(h):
                self.scr.addstr(h - 1 + i, 0, spacebuf(l[li + i], self.scrw)[:self.scrw], curses.color_pair(6))
            self.scr.addstr(self.scrh - 2, 0, spacebuf(t.pref + t.s, self.scrw)[:self.scrw], curses.color_pair(6))
            self.scr.addstr(self.scrh - 2, t.cx + len(t.pref), (t.s + ' ')[t.cx], curses.color_pair(7))

        #help display
        if self.ishelpon:
            maxlen = 0
            for l in self.helplines:
                if len(l) > maxlen : maxlen = len(l)
            for i in range(len(self.helplines)):
                if i >= self.scrh - 1 : break
                l = self.helplines[i]
                self.scr.addstr(i, self.scrw - maxlen, spacebuf(l, maxlen), curses.color_pair(7))

        #message banner
        m = spacebuf(self.message, self.scrw)[:self.scrw-1]
        self.scr.addstr(self.scrh - 1, 0, m, curses.color_pair(8))

        #keycode display for debugging purposes
        if self.showkeycodes:
            #debug('{} {}'.format(self.ck, self.key))
            self.scr.addstr(0, 0, '{} {}'.format(self.ck, self.key), curses.color_pair(4))

def spacebuf(s, n) : return s + ' ' * (n - len(s)) if n > len(s) else s

def filetext(filename):
    if not os.path.isfile(filename) : open(filename, 'a').close()
    return open(filename).read()

def debug(s):
    f = open('debug.txt', 'a')
    f.write(str(s) + '\n')
    f.close()
            
def draw(scr):
    curses.raw() #disable certain keybindings
    #set up colors
    curses.init_pair(1, 0, 7)
    curses.init_pair(2, 4, 7)
    curses.init_pair(3, 0, 2)
    curses.init_pair(4, 7, 0)
    curses.init_pair(5, 6, 7)
    curses.init_pair(6, 2, 0)
    curses.init_pair(7, 0, 2)
    curses.init_pair(8, 6, 0) 
    curses.init_pair(9, 5, 7) 
    scr.erase()
    scr.refresh()
    height, width = scr.getmaxyx()
    for i in range(height-1):
        scr.addstr(i, 0, ' ' * (width), curses.color_pair(1))
    if not os.path.isfile(filename) : open(filename, 'a').close()
    e = editor(scr, filename)
    while e.key != 27: #quit on escape
        e.refresh()
        e.doinput()
    #save before quitting
    file = open(e.filename, 'w')
    file.write('\n'.join(e.lines))
    file.close()

args = sys.argv[1:]
if len(args) > 1 : print('Too many arguments')
elif len(args) == 1:
    filename = args[0]
    curses.wrapper(draw)
else:
    filename = input('Enter file name: ')
    curses.wrapper(draw)
        

