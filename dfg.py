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
	# all constants, "external", and "out" nodes are unique for now
	# TODO: abstract this away better
	const_num = 0
	ext_num = 0
	out_num = 0
	for instruction in instructions:
		# Special case out nodes
		if 'description' in instruction and instruction['description'] == 'out':
			out_name = 'out%d' % out_num
			V.add((Vertex(out_name, out_name)))
			E.append(Edge(instruction['value'], out_name, 0))
			out_num += 1
			continue

		instruction_ptr = instruction['pointer']
		V.add((Vertex(instruction_ptr, instruction['opcode'])))

		if not instruction['operands']:
			continue
		for i, operand in enumerate(instruction['operands']):
			if operand['description'] == 'instruction':
				E.append(Edge(operand['value'], instruction_ptr, i))
			elif operand['description'] == 'instruction-external':
				external_name = 'external_%d' % ext_num
				V.add((Vertex(external_name, external_name)))
				E.append(Edge(external_name, instruction_ptr, i))
				ext_num += 1
			elif operand['description'] == 'constant':
				constant_name = 'constant_%d' % const_num
				V.add((Vertex(constant_name, constant_name)))
				E.append(Edge(constant_name, instruction_ptr, i))
				const_num += 1
			elif operand['description'] == 'argument':
				V.add((Vertex(operand['value'], 'argument_%d' % operand['argument_number_in_function'])))
				E.append(Edge(operand['value'], instruction_ptr, i))
			elif operand['description'] == 'pointer':
				# some pointers point to existing instructions that
				# have already been added as vertices
				# others appear to point to external functions
				# and need to be added now
				V.add((Vertex(operand['value'], 'pointer')))
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
	# dot.attr(rankdir='LR')
	for vertex in V:
		# Hacky, should fix at some point
		if "out" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled', color='pink')
		elif "external" in vertex.opcode or "argument" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightgreen')
		elif "constant" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightblue')
		else:
			dot.attr('node', shape='oval', style='solid', color='black')
		dot.node(vertex.pointer, vertex.opcode)
	for edge in E:
		dot.edge(edge.source, edge.dest)
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
	# print_graph(V, E)
	visualize_graph(V, E)
	is_subgraph((V, E), (V, E))


if __name__ == '__main__':
	main()