import json
import argparse
from collections import namedtuple
from graphviz import Digraph
import networkx as nx
from networkx import isomorphism

Vertex = namedtuple('Vertex', ['id', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

acceptable_identifiers = ['template_id', 'template_ID', 'name']

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

def construct_chain(opcodes):
	V = set()
	E = []

	for i, op in enumerate(opcodes):
		V.add((Vertex(str(i), op)))
		if i != 0:
			E.append(Edge(str(i-1), str(i), 0))

	return V, E

def graph2nx(V, E):
	G = nx.DiGraph();
	for e in E:
		G.add_edge(e[0], e[1], **e._asdict())


	for v in V:
		## add lone nodes?
		#if v.id in G:
			G.add_node(v[0], **v._asdict())

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
			print('\t%s (%s)' % (vertex.id, vertex.opcode))
		print('Edges:')
		for edge in G[1]:
			print('\t(%s, %s), argument %d' % (edge.source, edge.dest, edge.arg_num_at_dest))
	else:
		print("Graph format not recognized")


def has_side_effects(opcode):
	opcodes = ["ret", "br", "call", "out", "store"]
	return any([o in opcode for o in opcodes])


def visualize_graph(G, matches=None):
	if not (type(G) is nx.DiGraph): G = graph2nx(*G)

	dot = Digraph()
	node_gen = ((v, dat['opcode']) for v,dat in G.nodes(data=True))
	edge_gen = G.edges

	# pull out pointers of instructions that match a subgraph
	pointer_matches = []
	if matches:
		pointer_matches = [p for m in matches for p in m['node_matches']]

	for n in node_gen:
		vertex = Vertex(*n)
		# Hacky, should fix at some point
		if has_side_effects(vertex.opcode):
			dot.attr('node', shape='diamond', style='filled', color='pink')
		elif "external" in vertex.opcode or "argument" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightgreen')
		elif "constant" in vertex.opcode:
			dot.attr('node', shape='diamond', style='filled',
				color='lightblue')
		else:
			# color operations of all subgraph matches at once for now
			# TODO may need to save a different file for each subgraph
			# if matches overlap
			# TODO different colors for different chains
			if vertex.id in pointer_matches:
				dot.attr('node', shape='oval', style='filled', color='red')
			else:
				dot.attr('node', shape='oval', style='solid', color='black')
		dot.node(vertex.id, vertex.opcode)
	for e in edge_gen:
		dot.edge(*e)

	try:
		dot.render('output.gv', view=True)
	except Exception as e:
		print("viewer error", e)


def is_subgraph(littleG, bigG):
	if not (type(littleG) is nx.DiGraph): littleG = graph2nx(*littleG)
	if not (type(bigG) is nx.DiGraph): bigG = graph2nx(*bigG)

	def node_match(data1, data2):
		return data1['opcode'] == data2['opcode'] # and data1['arity'] == data2['arity']

	# Returns "if a subgraph of G1 is isomorphic to G2", so pass the
	# (presumably larger) graph G2 first
	gm = isomorphism.DiGraphMatcher(bigG, littleG, node_match=node_match);

	return gm.subgraph_is_isomorphic()

"""
	Ideally: G1 and G2 are in networkx format, otherwise we'll have to convert, which could be expensive.
	G1 is a subgraph of G2
	- instruction nodes should be the same if they have the same opcode and
	  number of args
	- constants and arguments can always be considered the same
"""
def find_matches(littleG, bigG):
	if not (type(littleG) is nx.DiGraph): littleG = graph2nx(*littleG)
	if not (type(bigG) is nx.DiGraph): bigG = graph2nx(*bigG)

	for ident in acceptable_identifiers:
		if ident in littleG.graph:
			littleGName = littleG.graph[ident]
			break
	else:
		littleGName = '[UNNAMED%d]' % find_matches.counter
		find_matches.counter += 1


	def node_match(data1, data2):
		return data1['opcode'] == data2['opcode'] # and data1['arity'] == data2['arity']

	matches = []

	gm = isomorphism.DiGraphMatcher(bigG, littleG, node_match=node_match);
	for i,match in enumerate(gm.subgraph_isomorphisms_iter()):
		matches.append( dict(
				template_id = littleGName,
				match_idx = i,
				node_matches = match
			))
		print(match)

	return matches

find_matches.counter = 0

"""Write json [ <list of matches>
	{"template_ID" : <>,
	 "match_idx" : 0, 1, 2, ...,
	 node_matches: { id -> id} }]
"""
def write_matches(matches, filename):
	filename = filename.replace(".json", "-matches.json", 1)

	with open(filename, "w") as file:
		file.write(json.dumps(matches, indent=4))
	pass

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	args = parser.parse_args();

	G = graph2nx(*graph_from_json(args.input))
	# print_graph(V, E)
	visualize_graph(G)

	chains = [
		["mul", "add", "srem"],
		["shl", "add"],
		["sdiv", "mul", "add"],
	]

	# For colored printing
	g = "\033[92m"
	r = "\033[91m"
	b = "\033[00m"

	print("\nChain matches:")

	matches = []
	for l in chains:
		chain = graph2nx(*construct_chain(l))
		s = "[" + ", ".join(l) + "]"
		print(s)
		chain.name = s

		matches.extend(find_matches(chain, G))

		# sj = s.ljust(20)
		# match = is_subgraph(chain, G)
		# print((g if match else r), sj, match, b)
		# if match:
		# 	matches.append({
		# 		"template_id" : s,
		# 		"match_idx" : 0,
		# 		"node_matches" : [], # TODO fill in id -> id from isomorphism
		# 	})

	write_matches(matches, args.input)

	visualize_graph(G, matches)
