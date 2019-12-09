import json
import argparse
from collections import namedtuple
from graphviz import Digraph

Vertex = namedtuple('Vertex', ['pointer', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

# Returns:
#	V: list of Vertices
#	E: list of Edges (n.b. 'constant' is a placeholder for a constant, not a
#      vertex named 'constant')
def graph_from_json(fn):
	instructions = {}
	with open(fn, 'r') as f:
		instructions = json.load(f)
	V = []
	E = []
	for instruction in instructions:
		instruction_ptr = instruction['pointer']
		V.append(Vertex(instruction_ptr, instruction['opcode']))
		if not instruction['operands']:
			continue
		for i, operand in enumerate(instruction['operands']):
			if operand['instr_or_constant'] == 'instruction':
				E.append(Edge(operand['value'], instruction_ptr, i))
			elif operand['instr_or_constant'] == 'constant':
				E.append(Edge('constant', instruction_ptr, i))
	return V, E

def print_graph(V, E):
	print('Vertices:')
	for vertex in V:
		print('\t%s (%s)' % (vertex.pointer, vertex.opcode))
	print('Edges:')
	for edge in E:
		print('\t(%s, %s), argument %d' % (edge.source, edge.dest, edge.arg_num_at_dest))

def visualize_graph(V, E):
	dot = Digraph()
	for vertex in V:
		dot.node(vertex.pointer, vertex.opcode)
	for edge in E:
		dot.edge(edge.source, edge.dest, constraint='false')
	dot.render('output.gv', view=True)

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	args = parser.parse_args();
	V, E = graph_from_json(args.input)
	print_graph(V, E)
	visualize_graph(V, E)

if __name__ == '__main__':
	main()