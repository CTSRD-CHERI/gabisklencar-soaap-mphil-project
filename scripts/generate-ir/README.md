# Compiler wrappers for generating LLVM bitcode

The scripts in this directory allow generating LLVM IR from projects without
directly modifying their build system. This is done by wrapping the compiler
linker or ar invocation with a python script that first generates the IR file
and then performs the actual compiler command. While this takes approximately
twice as long it is the only solution that works in cases where binaries are
created during the build and then run to generate other files (e.g. moc, uic
from the qtbase build system)

## Generated files:

For every object file `foo.o` it will generated a corresponding LLVM bitcode
file `foo.o.bc`. Every static library `foo.a` will also have a corresponding
`foo.a.bc` that contains all linked object files.

Shared libraries (`foo.so` -> `foo.so.bc`) and executables (`foo` -> `foo.bc`)
will only contain the linked object files as well as any static libraries that
were passed on the link command line. Any `.so` files as well as `-lfoo` passed
to the linker will not be included since this can result in duplicate symbols
which will cause `llvm-link` to fail.

Before running a SOAAP analysis on the generated binaries you should run
`# llvm-nm foo | grep 'U '` to see whether there are any important unresolved
symbols.

## Supported build systems

Currently the following build systems have been tested:

- CMake
- Autotools (openSSH)
- QMake
- Custom Makefiles (as long as they use common variable names)


## Instructions:
**Important**: Currently you must set`SOAAP_LLVM_BINDIR` to point to the
LLVM build directory (`$SOAAP_LLVM_BINDIR/clang` must exist)

### CMake

CMake is the build system that is most likely to work without any problems.
A script that wraps around the CMake command and sets the necessary variables
can be found in this directory (`cmake-for-llvm-ir.py`). It will ensure that
the right (evironment and CMake) variables are set during the configure step
so that a plain `ninja` or `make` invocation will be enough.
If no `-G` argument is passed to the script it will automatically instruct
CMake to use the `ninja` generator.

To build a CMake project execute the following:
```
    # <script-dir>/cmake-for-llvm-ir.py <cmake args> <source dir>
    # ninja # or make if you passed -G'Unix Makefiles' above
```

### Autotools or anything with a `./configure` script

The script `configure-for-llvm-ir.py` will set the neccessary environment
variables so that `./configure` will use the wrapper compiler instead.
There are many arguments that can be passed to it to override the defaults
in case that doesn't work for the given build system (see `--help` option
for details). The most important ones are:

- `-f <file>`: The executable to run with the modified environment. Defaults
to `./configure`
- `--cpp-linker`: Ensures that clang++ is used instead of clang for linking.
This is required in C++ projects to ensure the standard library is added
automatically
- `--confirm`: Display command line and changed environment vars and request
confirmation before running it.
- `"--ld=[LD_CMD]"`: set the LD environment variable to
`"<scripts-dir>/<LD_CMD>-and-emit-llvm-ir.py"`. By default `LD_CMD` will be
clang, but some build systems link using ld directly. In that case you should
run `configure-for-llvm-ir.py --ld=ld`. If `LD_COMMAND` contains spaces the
first word will be treated as the command and everything after the first space
will be treated as parameters. E.g. `configure-for-llvm-ir.py "--ld=ld -m elf_x86_64"`
will set `LD=<script-dir/ld-and-emit-llvm-ir.py -m elf_x86_64`.
- `--ar=`[AR]`, `--link=[LINK]`, `--ranlib=[RANLIB]`: these work the same way as `--ld`
- `--env VAR=VALUE`: set environment variable `VAR` to `VALUE` for the duration
of the script

In most cases it will be sufficient to run the following commands:

    # ./autogen.sh # required for some projects to generate ./configure
    # configure-for-llvm-ir.py <configure args>
    # make -j8

#### qtbase `./configure` script

The qtbase.git project can be build using the `configure-for-llvm-ir.py` script
if you apply the following patch: https://codereview.qt-project.org/#/c/109807/
The binaries need to be linked using clang++ (`--cpp-linker`) since otherwise
the C++ standard library is not added automatically.

To build all the qtbase libraries as LLVM IR run the following:

    # configure-for-llvm-ir.py --cpp-linker <configure arguments>
    # make -j8

This has been tested with the 5.5 branch of qtbase.git, but should also work
with any other branch where the patch applies cleanly.

# QMake

In order to build a QMake project you must have built qtbase using the configure
wrapper script. If that is the case you can run the qmake binary from that
directory and the make.

    # <path-to-qtbase>/bin/qmake
    # make -j8

If you don't have the qmake binary from qtbase configured for LLVM IR you can
also try following the instructions from *Plain Makefile build system*.
It should also work, but is not recommended.

### Other build systems with a configure step

If for some reason the `configure-for-llvm-ir.py` script doesn't work
you can perform the steps manually.

```
    # export CC=<script-dir>/clang-and-emit-llvm-ir.py
    # export CXX==<script-dir>/clang-and-emit-llvm-ir.py
    # export NO_EMIT_LLVM_IR=1
    # ./my-configure-command
    # unset NO_EMIT_LLVM_IR
    # make -j8
```

Exporting `NO_EMIT_LLVM_IR` during the configure step is very important since
during the configure step the compiler output is often parsed. Since the
additional IR generation step (and debug output) will interfere with this many
compiler features will not be detected correctly.

**Note:**  The python script can be configured to set all these variables (see
`--help option`) and also use a different script from `./configure` by using the
`-f` option. Consider opening an issue instead of running these steps manually.

### Plain Makefile build system

**WARNING:** Experimental

If the build system uses hand written Makefiles or for some reason the configure
step does not instruct make to use set the compiler wrappers there is also a
script that wraps `make`:

```
    # <script-dir>/make-for-llvm-ir.py <make-options>.
```

This method has been tested with the qtbase build system and the openSSH build system.

**Note**: this has only been tested with **GNU make**.

## Important environment variables

### SOAAP_LLVM_BINDIR

This variable must point to the directory where the SOAAP fork of LLVM was built.

### LLVM_IR_WRAPPER_DELEGATE_TO_SYSTEM_COMPILER
If this variable is set the native compile step will use the clang/clang++ binary from
`$PATH` instead of from the SOAAP LLVM build directory.

This is useful if you only have
a Debug build of SOAAP available and want to speed up the build or if there are any issues
with the SOAAP clang binary.

### NO_EMIT_LLVM_IR
If this variable is set the wrappers will delegate directly to the native compiler and
skip the LLVM IR build step.

This is useful when running the configure step for a build system since these scripts
often parse the raw compiler output and having additional output would confuse them.

## Current limitations

- Any build system that uses `libtool` does not work since libtool is a weird shell
script that moves files around and deletes the generated IR files.
- Build systems that directly invoke the linker instead of using the compiler for
the linking step do not work yet
- Symbols for any shared libraries are not included in the resulting binaries yet.
They need to be added manually if whole-program-analysis is desired.
In the future some LLVM metadata might be added to solve this issue

## Urgent TODO:
- if `SOAAP_LLVM_BINDIR` is not set it will assume that the LLVM binaries are located at
 /home/alex/devel/soaap/llvm/release-build/bin/
