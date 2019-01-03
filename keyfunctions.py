import tkinter

def upfunc(self):
    if self.isautocomp : self.aci -= 1
    else:
        if self.cy == 0 : self.cx = 0
        else : self.cy -= 1
        
def downfunc(self):
    if self.isautocomp : self.aci += 1
    else:
        if self.cy == len(self.lines) - 1 : self.cx = len(self.lines[-1])
        else : self.cy += 1
        
def leftfunc(self):
    if self.cx == 0 and self.cy >= 1:
        self.cy -= 1
        self.cx = len(self.lines[self.cy])
    else:
        self.cx -= 1
        l = len(self.lines[self.cy])
        if self.cx >= l : self.cx = l - 1
        
def rightfunc(self):
    l = len(self.lines[self.cy])
    if self.cx < l : self.cx += 1
    elif self.cy < len(self.lines) - 1:
        self.cx = 0
        self.cy += 1
        
def backfunc(self):
    if self.cx > 0:
        l = self.lines[self.cy]
        self.lines[self.cy] = l[:self.cx-1] + l[self.cx:]
        self.cx -= 1
    elif self.cx == 0 and self.cy > 0:
        self.cx = len(self.lines[self.cy - 1])
        self.lines[self.cy - 1] += self.lines[self.cy]
        self.lines.pop(self.cy)
        self.cy -= 1
        
def enterfunc(self):
    l = self.lines[self.cy]
    if self.isautocomp:
        l1 = l[:self.acwordx]
        l2 = l[self.acwordx + len(self.acword):]
        newword = self.acwords[self.aci]
        self.lines[self.cy] = l1 + newword + l2
        self.cx = len(l1 + self.acwords[self.aci])
        self.lastwords.remove(newword)
        self.lastwords.insert(0, newword)
        self.acword = ''
        self.isautocomp = False
    else:
        ind = ''
        for i in range(len(l)):
            if not l[i].isspace() or i >= self.cx: break
            else : ind += l[i]
        nind = ind
        if self.cx > 0 and self.cx <= len(l) and l[self.cx-1] in [':', '{'] : nind += ' ' * 4
        self.lines[self.cy] = l[:self.cx]
        if self.cx < len(l) and l[self.cx] == '}':
            self.lines.insert(self.cy + 1, ind + l[self.cx:])
            l = l[:self.cx]
        self.lines.insert(self.cy + 1, nind + l[self.cx:])
        self.cx = len(nind)
        self.cy += 1
        
def parenfunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + ')' + l[self.cx:]
    self.cx += 1
    
def squarebracketfunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + ']' + l[self.cx:]
    self.cx += 1
    
def bracketfunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + '}' + l[self.cx:]
    self.cx += 1
    
def quotefunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + '"' + l[self.cx:]
    self.cx += 1
    
def apostrophefunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + "'" + l[self.cx:]
    self.cx += 1

def rightparenfunc(self):
    l = self.lines[self.cy]
    if self.cx < len(l) and l[self.cx] == self.ck : self.cx += 1
    else : defaultfunc(self)
    
def tabfunc(self):
    l = self.lines[self.cy]
    if self.cx > len(l) : self.cx = len(l)
    if False and not self.isautocomp and self.cx > 0 and l[self.cx-1].isalpha():
        self.isautocomp = True
    else:
        #self.isautocomp = False
        line = self.lines[self.cy]
        if True or line[:self.cx].isspace():
            ind = 4
            self.lines[self.cy] = ' ' * ind + line
            self.cx += ind
            
def shifttabfunc(self):
    line = self.lines[self.cy]
    ind = 4
    if not line[:ind].isspace():
        ind = len(line) - len(line.lstrip())
    self.lines[self.cy] = line[ind:]
    self.cx -= ind
    
def ctrlspacefunc(self):
    l = self.lines[self.cy]
    if self.cx > len(l) : self.cx = len(l)
    if not self.isautocomp: #and l[self.cx-1].isalpha():
        self.isautocomp = True
    else : self.isautocomp = False

def ctrlvfunc(self):
    r = tkinter.Tk()
    s = r.clipboard_get()
    s = s.replace('\t', ' ' * 4)
    r.withdraw()
    r.update()
    r.destroy()
    self.message = 'Pasting {} chars: {}...'.format(len(s),
                                                    s[:30].replace('\n', ' '))
    curline = self.lines[self.cy]
    newlines = s.split('\n')
    newlines[0] = curline[:self.cx] + newlines[0]
    nx = len(newlines[-1])
    newlines[-1] = newlines[-1] + curline[self.cx:]
    self.lines.pop(self.cy)
    for l in newlines[::-1]:
        self.lines.insert(self.cy, l)
    self.cy += len(newlines) - 1
    self.cx = nx

def ctrlufunc(self):
    if len(self.undoq) > 1:
        self.message = 'Undo'
        self.redoq.append(self.undoq.pop())
        old = self.undoq.pop()
        self.lines = old.lines
        self.cx = old.cx
        self.cy = old.cy
    else:
        self.undoq.pop()
        self.message = 'Cannot undo any further back'

def ctrlyfunc(self):
    if len(self.redoq) > 0:
        self.message = 'Redo'
        old = self.redoq.pop()
        self.lines = old.lines
        self.cx = old.cx
        self.cy = old.cy
    else : self.message = 'Cannot redo'

def ctrlkfunc(self):
    if self.cx > 0:
        self.lines[self.cy] = self.lines[self.cy][:self.cx]
    else:
        if len(self.lines) > 1:
            self.lines.pop(self.cy)
        else:
            self.lines[0] = ''

def ctrlpfunc(self):
    if self.mode != 'terminal':
        self.message = 'Opened terminal'
        self.mode = 'terminal'
    else : self.mode = 'edit'

def ctrlsfunc(self):
    file = open(self.filename, 'w')
    file.write('\n'.join(self.lines).strip())
    file.close()
    self.message = 'Saved {}'.format(self.filename)

def ctrlqfunc(self):
    self.ishelpon = not self.ishelpon

def ctrlxfunc(self):
    line = self.lines[self.cy]
    r = tkinter.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(line)
    r.update() # now it stays on the clipboard after the window is closed
    r.destroy()
    if len(self.lines) > 1:
        self.lines.pop(self.cy)
    else:
        self.lines[0] = ''

def ctrlrbfunc(self):
    self.sy -= self.edith
    if self.sy < 0 : self.sy = 0
    self.cy = self.sy
    
def ctrlbsfunc(self):
    self.sy += self.edith
    if self.sy > len(self.lines) - self.edith + 1:
        self.sy = len(self.lines) - self.edith + 1
    self.cy = self.sy

def ctrlcfunc(self):
    line = self.lines[self.cy]
    r = tkinter.Tk()
    r.withdraw()
    r.clipboard_clear()
    r.clipboard_append(line)
    r.update() # now it stays on the clipboard after the window is closed
    r.destroy()
    self.message = 'Copied: {}...'.format(line[:30])

def altzfunc(self):
    self.showkeycodes = not self.showkeycodes
    
def defaultfunc(self):
    l = self.lines[self.cy]
    self.lines[self.cy] = l[:self.cx] + self.ck + l[self.cx:]
    self.cx += 1

