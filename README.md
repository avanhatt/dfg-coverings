# dfg-coverings
Data flow graph coverings

Dependencies:

    pip install graphviz

Generate stencils for each embench benchmark:

	python profiling.py

Check coverage of specific stencils in `<stencil_file>` for each embench benchmark:

	python profiling.py --stencil_json <stencil_file>