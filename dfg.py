import json
import argparse
from collections import namedtuple
from graphviz import Digraph

Vertex = namedtuple('Vertex', ['pointer', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

# Returns:
#	V: list of Vertices
#	E: list of Edges (n.b. 'constant' is a placeholder for a constant, not a
#      vertex named 'constant', same for 'argument')
def graph_from_json(fn):
	instructions = {}
	with open(fn, 'r') as f:
		instructions = json.load(f)
	V = set()
	E = []
	for instruction in instructions:
		instruction_ptr = instruction['pointer']
		V.add((Vertex(instruction_ptr, instruction['opcode'])))
		if not instruction['operands']:
			continue
		for i, operand in enumerate(instruction['operands']):
			if operand['description'] == 'instruction':
				E.append(Edge(operand['value'], instruction_ptr, i))
			elif operand['description'] == 'constant':
				E.append(Edge('constant', instruction_ptr, i))
			elif operand['description'] == 'argument':
				V.add((Vertex(operand['value'], 'argument')))
				E.append(Edge(operand['value'], instruction_ptr, i))
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


""" G1 is a subgraph of G2
	- instruction nodes should be the same if they have the same opcode and
	  number of args
	- constants and arguments can always be considered the same
"""
def is_subgraph(G1, G2):
	(V1, E1), (V2, E2) = G1, G2

	return False

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	args = parser.parse_args();
	V, E = graph_from_json(args.input)
	print_graph(V, E)
	visualize_graph(V, E)
	is_subgraph((V, E), (V, E))

if __name__ == '__main__':
	main()