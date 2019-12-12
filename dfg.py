import json
import argparse
from collections import namedtuple
from graphviz import Digraph
import networkx as nx
from networkx import isomorphism

Vertex = namedtuple('Vertex', ['pointer', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])
#Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])



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
			out_name = 'out_%d' % out_num
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

def graph2nx(V, E):
	G = nx.DiGraph();
	for e in E:
		G.add_edge(e[0], e[1], **e._asdict() )


	for v in V:
		## add lone nodes?
		#if v.pointer in G:
			G.add_node(v[0], **v._asdict() )

	for v in G:
		G.nodes[v]['arity'] = G.in_degree(v)

	return G

""" Updated for networkx representation. """
def print_graph(G):
	if(type(G) is nx.DiGraph):
		print('Vertices:')
		for v,data in G.nodes(data=True):
			print('\t%s (%s)' % (v, data))
		print('Edges:')
		for edge,edat in G.nodes(data=True):
			print('\t(%s, %s), data %s' % (edge[0], edge[1], edat))
	elif type(G) is tuple:
		print('Vertices:')
		for vertex in G[0]:
			print('\t%s (%s)' % (vertex.pointer, vertex.opcode))
		print('Edges:')
		for edge in G[1]:
			print('\t(%s, %s), argument %d' % (edge.source, edge.dest, edge.arg_num_at_dest))
	else:
		print("Graph format not recognized")

def visualize_graph(G):
	dot = Digraph()
	if type(G) is nx.DiGraph:
		node_gen = ((v, dat['opcode']) for v,dat in G.nodes(data=True))
		edge_gen = G.edges
	elif type(G) is tuple:
		node_gen, edge_gen = G

	for n in node_gen:
		vertex = Vertex(*n)
		# Hacky, should fix at some point
		if "out" in vertex.opcode or "ret" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled', color='pink')
		elif "external" in vertex.opcode or "argument" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightgreen')
		elif "constant" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightblue')
		else:
			dot.attr('node', shape='oval', style='solid', color='black')
	for e in edge_gen:
		dot.edge(*e)

	try:
		dot.render('output.gv', view=True)
	except Exception as e:
		print("viewer error", e)


######### HELPERS FOR SUBGRAPH ######

"""
	Ideally: G1 and G2 are in networkx format, otherwise we'll have to convert, which could be expensive.
	G1 is a subgraph of G2
	- instruction nodes should be the same if they have the same opcode and
	  number of args
	- constants and arguments can always be considered the same
"""
def is_subgraph(G1, G2):
	if not (type(G1) is nx.DiGraph): G1 = graph2nx(G1)
	if not (type(G2) is nx.DiGraph): G2 = graph2nx(G2)

	def nodes_R_equalish(data1, data2):
		return data1['opcode'] == data2['opcode'] and data1['arity'] == data2['arity']


	gm = isomorphism.DiGraphMatcher(G1,G2, node_match = nodes_R_equalish);
	return gm.subgraph_is_isomorphic();

	# start with brute force version:
	#for v

	# return False

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	args = parser.parse_args();

	G = graph2nx(*graph_from_json(args.input))
	# print_graph(V, E)
	visualize_graph(G)
	print(is_subgraph(G, G))
