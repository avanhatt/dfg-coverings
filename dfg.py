import json
import argparse
from collections import namedtuple
from graphviz import Digraph

Vertex = namedtuple('Vertex', ['pointer', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

# Returns:
#	V: list of Vertices
#	E: list of Edges 
#   (n.b. 'constant' is a placeholder for a constant, not a
#    vertex named 'constant', same for 'argument')
def graph_from_json(fn):
	instructions = {}
	with open(fn, 'r') as f:
		instructions = json.load(f)
	V = set()
	E = []
	# all constants are unique for now
	const_num = 0
	for instruction in instructions:
		instruction_ptr = instruction['pointer']
		V.add((Vertex(instruction_ptr, instruction['opcode'])))
		if not instruction['operands']:
			continue
		for i, operand in enumerate(instruction['operands']):
			if operand['description'] == 'instruction':
				E.append(Edge(operand['value'], instruction_ptr, i))
			elif operand['description'] == 'constant':
				constant_name = 'constant_%d' % const_num
				V.add((Vertex(constant_name, constant_name)))
				E.append(Edge(constant_name, instruction_ptr, i))
				const_num += 1
			elif operand['description'] == 'argument':
				V.add((Vertex(operand['value'], 'argument_%d' % i)))
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

def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	args = parser.parse_args();
	V, E = graph_from_json(args.input)
	print_graph(V, E)
	visualize_graph(V, E)

if __name__ == '__main__':
	main()