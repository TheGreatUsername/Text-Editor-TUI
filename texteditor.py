import curses
import sys
import os.path
import os
import re
import inputfunc
import json
import terminal

filelist = []
posmems = {}

class editor:
    def __init__(self, scr, file):
        self.mode = 'edit'
        self.terminal = terminal.terminal()
        self.terminal.filename = file
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
        #restore previous positions of screen and caret
        if file in posmems.keys():
            p = posmems[file]
            self.cx = p.cx
            self.cy = p.cy
            self.sx = p.sx
            self.sy = p.sy
        self.key = 0
        self.ck = ''
        f = open(file, 'r')
        txt = f.read().replace('\t', ' ' * 4)
        f.close()
        self.filename = file
        self.lines = txt.split('\n')
        #move current working file to top of filelist
        if self.filename in filelist : filelist.remove(self.filename)
        filelist.insert(0, self.filename)
        
        self.filelist = filelist
        self.filecol = []
        self.fi = 0
        self.newfname = ''
        self.keystrokes = 0
        self.message = 'Welcome! Press ctrl-q for help'
        self.showkeycodes = False

        helppath = os.path.join(os.path.dirname(__file__), 'help.txt')
        self.helplines = open(helppath).read().split('\n')
        self.ishelpon = False

        #set up undo queue and redo queue
        self.undoq = [inputfunc.ministate(self.lines, self.cx, self.cy)]
        self.redoq = []

        #handle highlighting
        l = re.findall('(.+?)(\.[^\.]+$|$)', self.filename)
        extension = '' if len(l) == 0 else l[-1][-1][1:]
        highlightpath = os.path.join(os.path.dirname(__file__),
                                  'highlight_{}.txt'.format(extension))
        self.highlight = filetext(highlightpath).split('\n')

        #autocompletion stuff
        self.isautocomp = False
        self.acword = ''
        self.acwordx = 0
        self.acwords = []
        self.linewords = re.findall('[_a-zA-Z][_a-zA-Z0-9]*',
                                    (self.lines + [''])[0])
        self.aci = 0 #autocomplete index
        freqmap = {}
        words = re.findall('[_a-zA-Z][_a-zA-Z0-9]*', txt)

        #load autocomplete suggestions file
        try:
            suggestedpath = os.path.join(os.path.dirname(__file__),
                                  'suggest_{}.txt'.format(extension))
            suggested = open(suggestedpath).read().split('\n')
        except: suggested = []
        
        for w in words + self.highlight + suggested:
            if w in freqmap.keys() : freqmap[w] += 1
            else : freqmap[w] = 1
        self.freqmap = freqmap
        d = freqmap
        self.lastwords = [pair[0] for pair in sorted(d.items(), key=lambda item: item[1])][::-1]

        self.localcpy = ''
        self.foreigncpy = ''

        self.adjustcoords()

    def doinput(self) : inputfunc.doinput(self, curses)
    
    def refresh(self):
        height, width = self.scr.getmaxyx()
        #store height and width in editor object for use later
        self.scrw = width
        self.scrh = height
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
            #alphanumerics
            found = {m.start() : m.group() for m in
                     re.finditer('\\b[_a-zA-Z]+[_a-zA-Z0-9]*\\b',
                                 line[self.sx:self.sx+self.editw])}
            for f in found.keys():
                h = found[f]
                x = lnlen + f
                #if x >= 0 and x <= self.editw - len(h):
                self.scr.addstr(i, x, h, curses.color_pair(2))
            #highlighting
            for h in self.highlight:
                found = [m.start() for m in re.finditer('\\b{}\\b'.format(h),
                                                        line)]
                for f in found:
                    x = lnlen + f - self.sx
                    if x >= 0 and x <= self.editw - len(h):
                        self.scr.addstr(i, x, h, curses.color_pair(9))
            self.scr.addstr(i+1, lnlen, ' ', curses.color_pair(1))
            ln = str(self.sy + i + 1)
            #strings
            tocomment = []
            l = line[self.sx:self.sx+self.editw]
            strposs = []
            state = 'none'
            skip = False
            oldc = ''
            for j in range(len(line)):
                c = line[j]
                if not skip:
                    if c == '\\':
                        if state in ['instr', 'inchar'] : strposs[-1].s += c
                        skip = True
                    elif c == '"':
                        if state == 'none':
                            state = 'instr'
                            strposs.append(strpos(j))
                            strposs[-1].s += c
                        else:
                            if state == 'instr' : state = 'none'
                            strposs[-1].s += c
                    elif c == "'":
                        if state == 'none':
                            state = 'inchar'
                            strposs.append(strpos(j))
                            strposs[-1].s += c
                        else:
                            if state == 'inchar' : state = 'none'
                            strposs[-1].s += c
                    else:
                        if state in ['instr', 'inchar'] : strposs[-1].s += c
                else:
                    if state in ['instr', 'inchar'] : strposs[-1].s += c
                    skip = False
                if state == 'none':
                    if c == '#':
                        tocomment.append(j)
                    elif c == '/' and oldc == '/':
                        tocomment.append(j-1)
                oldc = c
            for sp in strposs:
                sp.x -= self.sx
                if sp.x + len(sp.s) >= 0 and sp.x < self.editw:
                    x = sp.x
                    s = sp.s
                    if x < 0:
                        s = s[-x:]
                        x = 0
                    if x + len(s) > self.editw:
                        s = s[:self.editw-x]
                    self.scr.addstr(i, lnlen + x, s, curses.color_pair(12))
            #comments
            for x in tocomment:
                self.scr.addstr(i, lnlen + x, l[x:], curses.color_pair(13))
            #draw line numbers
            self.scr.addstr(i, 0, ' ' * (lnlen - len(ln) - 1) + ln + '|',
                            curses.color_pair(5))
        #draw carot
        px = self.cx
        py = self.cy
        if px > len(self.lines[py]) : px = len(self.lines[py])
        l = self.lines[py] if py < len(self.lines) else self.lines[-1]
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
            if len(l) > 1 and self.acword in l : l.remove(self.acword)
            if self.aci < 0 : self.aci = 0
            elif self.aci >= len(l) : self.aci = len(l) - 1
            x = self.cx - 1
            line = self.lines[self.cy]
            if x >= len(line) : x = len(line) - 1
            while x >= 0 and isalnum(line[x]): x -= 1
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
            l = t.getlines(self.scrw - 1)
            l += [''] * h
            li = len(l) - h * 2
            if t.sy < 0 : t.sy = 0
            elif t.sy >= len(l) - h * 2: t.sy = len(l) - h * 2
            li -= t.sy
            if li < 0 : li = 0
            for i in range(h):
                self.scr.addstr(h - 1 + i, 0, spacebuf(l[li + i], self.scrw)[:self.scrw], curses.color_pair(6))
            self.scr.addstr(self.scrh - 2, 0, spacebuf((t.pref + t.s)[:self.scrw], self.scrw)[:self.scrw], curses.color_pair(6))
            x = t.cx + len(t.pref)
            if x >= self.scrw : x = self.scrw - 1
            self.scr.addstr(self.scrh - 2, x, (t.s + ' ')[t.cx], curses.color_pair(7))

        #fileselect
        elif self.mode == 'fileselect':
            collen = self.edith - 3
            if len(self.filecol) == 0 : self.filecol = self.filelist[0:collen]
            fl = self.filecol
            while len(fl) > collen and len(fl) > 0: fl.pop()
            banner = 'Choose file:'
            maxc = len(banner)
            for s in fl:
                if len(s) > maxc : maxc = len(s)
            self.scr.addstr(0, 0, spacebuf(banner, maxc), curses.color_pair(8))
            for i in range(len(fl)):
                s = fl[i]
                c = 6
                if self.fi == i : c = 7
                #self.scr.addstr(i + 1, 0, '.' * (maxc + 1), curses.color_pair(6))
                self.scr.addstr(i + 1, 0, spacebuf(s, maxc), curses.color_pair(c))
            nc = 6
            if self.fi == len(fl) : nc = 7
            self.scr.addstr(len(fl) + 1, 0, spacebuf('New...', maxc), curses.color_pair(nc))
        elif self.mode == 'newfilename':
            self.scr.addstr(0, 0, 'Enter file name: ' + self.newfname, curses.color_pair(7))

        #help display
        if self.ishelpon:
            maxlen = 0
            for l in self.helplines:
                if len(l) > maxlen : maxlen = len(l)
            for i in range(len(self.helplines)):
                if i >= self.scrh - 1 : break
                l = self.helplines[i]
                self.scr.addstr(i, self.scrw - maxlen, spacebuf(l, maxlen),
                                curses.color_pair(6))

        #message banner
        m = spacebuf(self.message, self.scrw)[:self.scrw-1]
        self.scr.addstr(self.scrh - 1, 0, m, curses.color_pair(8))

        #keycode display for debugging purposes
        if self.showkeycodes:
            #debug('{} {}'.format(self.ck, self.key))
            self.scr.addstr(0, 0, '{} {}'.format(self.ck, self.key), curses.color_pair(4))

    def adjustcoords(self):
        #make carot behave
        if self.cx < 0 : self.cx = 0
        if self.cy < 0 : self.cy = 0
        if self.cy >= len(self.lines) : self.cy = len(self.lines) - 1

        #scroll screen
        if self.cx < self.sx : self.sx = self.cx
        if self.cy < self.sy : self.sy = self.cy
        if self.cx > self.sx + self.editw - 1 : self.sx = self.cx - (self.editw-1)
        if self.cy > self.sy + self.edith - 2 : self.sy = self.cy - (self.edith-2)

    def save(self):
        file = open(self.filename, 'w')
        file.write('\n'.join(self.lines))
        file.close()

    def changefile(self, filename):
        file = open(self.filename, 'w')
        file.write('\n'.join(self.lines))
        file.close()

        posmems[self.filename] = posmem(self.sx, self.sy, self.cx, self.cy)
        
        open(filename, 'a').close()
        global e
        e = editor(screen, filename)
        e.terminal = self.terminal
        e.terminal.filename = filename

    def updatefilelist(self):
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        for f in files:
            if not f in filelist:
                filelist.append(f)
        for f in filelist[:]:
            try : open(f).read()
            except : filelist.remove(f)

class strpos:
    def __init__(self, x):
        self.x = x
        self.s = ''

class posmem:
    def __init__(self, sx, sy, cx, cy):
        self.sx = sx
        self.sy = sy
        self.cx = cx
        self.cy = cy

def spacebuf(s, n) : return s + ' ' * (n - len(s)) if n > len(s) else s

def isalnum(s):
    return re.match('[_a-zA-Z][_a-zA-Z0-9]*', s)

def filetext(filename):
    if not os.path.isfile(filename) : open(filename, 'a').close()
    return open(filename).read()

def debug(s):
    f = open('debug.txt', 'a')
    f.write(str(s) + '\n')
    f.close()
            
def draw(scr):
    global screen
    global filelist
    screen = scr
    curses.raw() #disable certain keybindings
    curses.curs_set(0)
    #set up colors
    curses.use_default_colors()
    white = -1
    black = 0
    #white, black = black, white #uncomment to invert black and white
    curses.init_pair(1, black, white)
    curses.init_pair(2, 4, white)
    curses.init_pair(3, black, 2)
    curses.init_pair(4, 7, black)
    curses.init_pair(5, 6, white)
    curses.init_pair(6, 4, 7)
    curses.init_pair(7, 7, 4)
    curses.init_pair(8, 6, 7) 
    curses.init_pair(9, 5, white)
    curses.init_pair(10, 5, 7)
    curses.init_pair(11, 7, 5)
    curses.init_pair(12, 2, white)
    curses.init_pair(13, 7, white)
    scr.erase()
    scr.refresh()
    height, width = scr.getmaxyx()
    for i in range(height-1):
        scr.addstr(i, 0, ' ' * (width), curses.color_pair(1))

    files = [f for f in os.listdir('.') if os.path.isfile(f)]
    for f in files : filelist.append(f)
    filelist = sorted(filelist, key=str.lower)

    if not os.path.isfile(filename) : open(filename, 'a').close()
    global e
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
        

