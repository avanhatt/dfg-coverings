# Finding redundancies in data flow graph

This project uses [LLVM][] to find redundant subgraphs in programs' static data
flow graphs. The high level motivation and details are described [here][TODO].

[llvm]: https://llvm.org

## Dependencies

We require C++17, LLVM 8, and Python 3.

Additional dependencies are (for OSX):

    brew install graphviz
    pip install graphviz
    pip install networkx

## Testing and usage

First, build the LLVM pass with:

    mkdir build
    cd build; cmake ..; cd ..
    make pass

To find common subgraphs in a single source file and generate dynamic profiling
results, run:

    make <filename base>-profiling.o
    <filename base>-profiling.o

We use the [Embench] embedded profiling benchmark suite.

To generate subgraph stencils for each Embench benchmark:

	python3 profiling.py

To check coverage of specific stencils in `<stencil_file>` for each Embench
benchmark:

	python3 profiling.py --stencil_json <stencil_file>

[embench]: https://embench.org