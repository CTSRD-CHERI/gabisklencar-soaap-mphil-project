#!/usr/bin/env python3

import argparse
import os
import re
import subprocess
import sys

#TODO: simplify by understanding the same arguments as configure-for-llvm-ir

scriptDir = os.path.dirname(os.path.realpath(__file__))


# make sure it is quoted in case the dir contains spaces
def overrideCmd(name):
    return '"' + os.path.join(scriptDir, name + '-and-emit-llvm-ir.py') + '"'

fullArgs = list(sys.argv)  # copy of original args
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('options', nargs='*', help='Arguments to pass to make')
parser.add_argument('-f', required=False, default='./Makefile', help='Makefile override')
parser.add_argument('--confirm', action='store_true', help='Confirm before running make')
parser.add_argument('-C', required=False, help='CWD override')
# TODO: handle dir
# parser.print_help()
parsedArgs, unknownArgs = parser.parse_known_args()
print(parsedArgs)
makefile = parsedArgs.f
print('Makefile is:', makefile)
# try and override all relevant make variables with the wrapper script
# CC and CXX are always valid, all others depend on the build system
varOverrides = {
    'CC': overrideCmd('clang'),
    'CXX': overrideCmd('clang++'),
    'AR': overrideCmd('ar'),
    # most build systems seem to link with the compiler instead of calling ld directly
    'LD': overrideCmd('clang++'),
}

buildSystem = 'generic'

# we (currently?) only care about upper case variables
varAssignmentRegex = re.compile(r'^([A-Z_]+)\s*[?:]?=(.*)')
varExpansionRegex = re.compile(r'^(\$[\{\(][\w_]+[\)\}])(.*)')
# TODO: quoted paths with spaces no handled
# dash must not be the first char otherwise it's an option
pathRegex = re.compile(r'^([/\w][/\w-]*)(.*)')


def getAssignmentType(assigment):
    expansion = re.match(varExpansionRegex, value)
    path = re.match(pathRegex, value)
    if expansion:
        print('Variable expansion of', expansion.group(1))
    elif path:
        print('path/cmd assignment', path.group(1))
    else:
        print('other var assign:', assigment)
    return (expansion, path)


def isCommand(path, commands):
    for c in commands:
        if path == c:
            return c
        if path.endswith('/' + c):
            return c
    return None

lineBuffer = ''
lineContinuation = False
# for now just check for qmake, perhaps some other changes will be required for other systems
for index, line in enumerate(open(makefile)):
    if lineContinuation:
        lineBuffer = lineBuffer + line.strip()
    else:
        lineBuffer = line.strip()
    if lineBuffer.endswith('\\'):
        lineBuffer = lineBuffer[:-1]  # remove the backslash
        lineContinuation = True
        continue  # add the next line as well
    else:
        lineContinuation = False

    # print(index, lineBuffer)

    # The qmake generated Makefiles need AR='ar cqs' (i.e. with paramters), autoconf without params
    # Test by looking at the makefile
    if 'Generated by qmake' in lineBuffer:
        varOverrides['LINK'] = overrideCmd('clang++'),
        # for some reason the QMake makefiles expect the cqs inside the AR variable !!
        varOverrides['AR'] = overrideCmd('ar') + ' cqs'
        buildSystem = 'qmake'
        break

    if 'generated by automake' in lineBuffer:
        buildSystem = 'automake'
        # TODO: anything special here?

    m = re.match(varAssignmentRegex, lineBuffer)
    if not m:
        continue

    variable = m.group(1)
    value = m.group(2).strip()

    if variable == 'LINK':
        print('FOUND LINK assignemnt:', variable, value)
        expansion, path = getAssignmentType(value)
        if expansion:
            print('Not overriding LINK since it is a variable expansion:', value)
            continue
        sys.exit('COULD NOT HANDLE LINK assignment: ' + value)
    elif variable == 'LD':
        print('FOUND LD assignment:', variable, value)
        expansion, path = getAssignmentType(value)
        if expansion:
            print('Not overriding LD since it is a variable expansion:', value)
            continue

        # relative/absolute path -> we have to override it
        command = path.group(1)
        commandArgs = path.group(2)
        if isCommand(command, ['clang', 'gcc', 'cc']):
            varOverrides['LD'] = overrideCmd('clang') + commandArgs
        elif isCommand(command, ['clang++', 'g++', 'c++']):
            varOverrides['LD'] = overrideCmd('clang++') + commandArgs
        elif isCommand(command, ['ld', 'lld', 'gold']):
            varOverrides['LD'] = overrideCmd('ld') + commandArgs
        else:
            sys.exit('COULD NOT HANDLE LD assignment: ' + value)

print('Detected build system is', buildSystem)

# TODO: Make vs. gmake?
makeCommandLine = ['gmake']
if makefile != './Makefile':
    makeCommandLine.append('-f')
    makeCommandLine.append(makefile)

for k, v in varOverrides.items():
    makeCommandLine.append(k + '=' + v)

makeCommandLine.extend(parsedArgs.options)

print('Make command line:', makeCommandLine)


if parsedArgs.confirm:
    result = input('Run command? [y/n] (y)').lower()
    if len(result) > 0 and result[0] != 'y':
        sys.exit()

subprocess.check_call(makeCommandLine)
