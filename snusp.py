"""
This program is a complete Windows Bloated SNUSP interpreter.
Copyright (C) 2004  John Bauman

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""
"""
Changes:

- added `and version >= 2` for currchar == ";" and ":" because these instructions are supported only in Bloated SNUSP
- swapped code for ";" and ":", see comment there
- added check for `currindex < 0` and `currlevel < 0`
- renamed stack to mem because it is not a stack
- added ability to choose SNUSP version from command line
- fixed % (rand)
- removed input from stdin (Windows specific implementation), input only from file (-i option)

Notes:

- returning current cell value as exit code is not implemented

"""
Usage="""
Usage: python2 snusp.py <mode> <sourcefile> [-i <inputfile>]
where <mode> == -c or -m or -b (core/modular/bloated)
"""

import sys
import random

try:
    import psyco #greatly speeds it up
    psyco.full()
except:
    pass

#0 = core, 1 = modular, 2 = bloated
version = 2

class Thread:
    """Store data (instruction pointer, etc.) for a thread)"""
    def __init__(self, insp, dire, memindex, memlevel, callstack):
        self.insp = insp
        self.dire = dire
        self.memindex = memindex
        self.memlevel = memlevel
        self.callstack = callstack
            
            
def findnext(dire, x, y):
    """Find where to go to next."""
    if dire == 0:
        return x + 1, y
    if dire == 1:
        return x, y + 1
    if dire == 2:
        return x - 1, y
    if dire == 3:
        return x, y - 1
    print "Invalid direction"
    
def gotonext():
    """Go to the next location."""
    global currx, curry, dire
    currx, curry = findnext(dire, currx, curry)

if len(sys.argv) < 3:
    print Usage
    exit(1)

mode = sys.argv[1]
if   mode == "-c": version = 0  # core
elif mode == "-m": version = 1  # modular
elif mode == "-b": version = 2  # bloated
else:
    print "Invalid mode:", mode
    exit(1)

input = ""
if len(sys.argv) == 5 and sys.argv[3] == "-i":
    input = open(sys.argv[4]).read()

program = []
currx = curry = 0
maxlen = 0
for line in open(sys.argv[2]):
    n = [c for c in line]
    if currx == 0 and curry == 0 and line.find("$") >= 0:
        currx = line.index("$")
        curry = len(program)
    program.append(n)
    if maxlen < len(n):
        maxlen = len(n)

for line in range(len(program)): #pad the lines out
    program[line] += " " * (maxlen - len(program[line]))

dire = 0
mem = [[0]]
currindex = 0
currlevel = 0
callstack = []

threads = [Thread((currx, curry), dire, currindex, currlevel, callstack)]

currthread = 0



def savethreaddata():
    """Save all of the exposed thread data into the thread object."""
    threads[currthread].insp = (currx, curry)
    threads[currthread].dire = dire
    threads[currthread].memindex = currindex
    threads[currthread].memlevel = currlevel
    threads[currthread].callstack = callstack
    
def loadnextthread():
    """Load all of a thread's data from its associated object."""
    global currthread, currx, curry, dire, currindex, callstack, currlevel
    
    if not threads:
        return
        
    currthread = (currthread + 1) % len(threads)
    
    currx = threads[currthread].insp[0]
    curry = threads[currthread].insp[1]
    dire = threads[currthread].dire
    currindex = threads[currthread].memindex
    currlevel = threads[currthread].memlevel
    callstack = threads[currthread].callstack 

while threads:

    loadnextthread()
    
    if curry < 0 or curry >= len(program) or currx < 0 or currx >= len(program[curry]):
        del(threads[currthread])
        continue
        
        
    currchar = program[curry][currx]
    #print currx, curry, mem[currindex]
    
    blocked = 0
    if currchar == ">":
        currindex += 1
        if len(mem[currlevel]) <= currindex: #lengthen the memory if it's not long enough
            mem[currlevel].append(0)
            
    elif currchar == "<":
        currindex -= 1
        if currindex < 0: # it is easier to check it here instead of all places where it is used, see also ":" instruction
            print "Error: memory x coord < 0"
            exit(1)
        
    elif currchar == "+":
        mem[currlevel][currindex] += 1
        
    elif currchar == "-":
        mem[currlevel][currindex] -= 1
        
    elif currchar == "/":
        dire = 3 - dire #rotate
        
    elif currchar == "\\":
        dire = dire ^ 1 #rotate a different way
        
    elif currchar == "!": #skip a space
        gotonext()
        
    elif currchar == "?": #skip a space if the current space has a zero
        if not mem[currlevel][currindex]:
            gotonext()
            
    elif currchar == ",": #read input 
        if input != "":
            mem[currlevel][currindex] = ord(input[0])
            input = input[1:]
        else:
            #blocked = 1  # there is no sense in blocking - there is not going to be any additional input
            mem[currlevel][currindex] = -1  # just input a EOF value
    elif currchar == ",":
        print "Error: input not implemented"
        exit(1)
        
    elif currchar == ".": #write output
        #print currindex
        #print mem[currlevel]
        #print mem[currlevel][currindex]
        sys.stdout.write(chr(mem[currlevel][currindex]))
        
    elif currchar == "@" and version >= 1: #append the current location
        callstack.append((dire, currx, curry))
        
    elif currchar == "#" and version >= 1: #pop off the current location and move there
        if len(callstack) == 0:
            del(threads[currthread])
            continue
        dire, currx, curry = callstack.pop()
        gotonext()
        
    elif currchar == "&" and version >= 2: #make a new thread
        gotonext()
        threads.append(Thread((currx, curry), dire, currindex, currlevel, []))
    
    elif currchar == "%" and version >= 2: #get a random number
        val = mem[currlevel][currindex]
        if val >= 0: r = range(0, val+1)  # +1 because range does not include stop value
        else: r = range(val, 1)
        mem[currlevel][currindex] = random.choice(r)

## According to spec, "The number of moves upwards must not exceed the number of moves downwards."
## This means that memory grows downwards, so ';' must increase `currlevel`, not decrease it.
    
    elif currchar == ";" and version >= 2: #move down memory, increase memory level (y)
        currlevel += 1
        if len(mem) <= currlevel:
            mem.append([0] * (currindex + 1))
            
        if len(mem[currlevel]) <= currindex:
            mem[currlevel].extend([0] * (currindex + 1 - len(mem[currlevel])))
    
    elif currchar == ":" and version >= 2: #move up memory, decrease memory level (y)
        currlevel -= 1
        if currlevel < 0:
            print "Error: memory y coord < 0"
            exit(1)
        if len(mem[currlevel]) <= currindex:
            mem[currlevel].extend([0] * (currindex + 1 - len(mem[currlevel])))           
    
      
    if not blocked:
        gotonext()
        
    savethreaddata()
