import json
import argparse
import itertools

from collections import namedtuple
from graphviz import Digraph
import networkx as nx
from networkx import isomorphism

Vertex = namedtuple('Vertex', ['id', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

acceptable_identifiers = ['template_id', 'template_ID', 'name']

class Align:
	by_op = lambda data1, data2: data1['opcode'] == data2['opcode']
	by_op_arity = lambda data1, data2: data1['opcode'] == data2['opcode']  and data1['arity'] == data2['arity']


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

def graph2nx(V, E, **graphattrs):
	G = nx.DiGraph();
	for e in E:
		G.add_edge(e[0], e[1], **e._asdict())


	for v in V:
		## add lone nodes?
		#if v.id in G:
			G.add_node(v[0], **v._asdict())

	for v in G:
		G.nodes[v]['arity'] = G.in_degree(v)

	G.graph = graphattrs
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

	# Returns "if a subgraph of G1 is isomorphic to G2", so pass the
	# (presumably larger) graph G2 first
	gm = isomorphism.DiGraphMatcher(bigG, littleG, node_match=Align.by_op)

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


	matches = []

	gm = isomorphism.DiGraphMatcher(bigG, littleG, node_match=Align.by_op)
	for i,match in enumerate(gm.subgraph_isomorphisms_iter()):
		matches.append( dict(
				template_id = littleGName,
				match_idx = i,
				node_matches = match
			))

	return matches

find_matches.counter = 0


"""
return a collection of graphs like the chains from earlier, that are small and cover the most
"""
def guess_best_subgraphs( G ) :
	pass


def estimate_coverage(Hs, G_original) :
	G = G_original.copy()

	for H in Hs:
		matches = find_matches(H, G)

		for m in matches:
			G.remove_nodes_from( m['node_matches'].keys() )

	print(len(G_original), len(G))
	return 1 - (len(G) / len(G_original))

'''
Returns: list of mutually exclusive matches from all matches
'''
def pick_mutually_exclusive_matches(matches, G):
	# heuristic: sort matches by size
	# pick matches one by one if they don't overlap any previous matches
	# TODO: exhaustively try all combinations of subgraphs,
	#       picking the combo with the most coverage
	#       because biggest first doesn't guarantee best coverage
	matches_longest_to_shortest = sorted(matches, reverse=True, key=lambda m: len(m['node_matches']))
	matches_exclusive = []
	covered_nodes = set()
	for match in matches_longest_to_shortest:
		pointers = match['node_matches'].keys()
		if any(p in covered_nodes for p in pointers):
			continue
		covered_nodes.update(pointers)
		matches_exclusive.append(match)
	return matches_exclusive

# Prints the number of times each 2-node subgraph appears in the graph
unacceptable_subgraph_nodes = ['argument', 'constant', 'external', 'out']
def find_two_node_matches(G):
	subgraph_to_number_of_matches = {}

	node_pointer_to_opcode = {}
	for v, v_data in G.nodes(data=True):
	 	node_pointer_to_opcode[v] = v_data['opcode']
	checked_subgraphs = set()
	for s, t, e_data in G.edges(data=True):
		s_op = node_pointer_to_opcode[s]
		t_op = node_pointer_to_opcode[t]
		if any(prefix in s_op for prefix in unacceptable_subgraph_nodes) \
		or any(prefix in t_op for prefix in unacceptable_subgraph_nodes):
			continue

		subgraph_opcode_edges = '[(%s, %s)]' % (s_op, t_op)
		if subgraph_opcode_edges in checked_subgraphs:
			continue


		H = G.edge_subgraph([(s, t)]).copy()
		matches = []

		gm = isomorphism.DiGraphMatcher(G, H, node_match=Align.by_op)
		for i, match in enumerate(gm.subgraph_isomorphisms_iter()):
			matches.append( dict(
				template_id = subgraph_opcode_edges,
				match_idx = i,
				node_matches = match
			))

		matches_exclusive = pick_mutually_exclusive_matches(matches, G)

		checked_subgraphs.add(subgraph_opcode_edges)
		subgraph_to_number_of_matches[subgraph_opcode_edges] = {'full': len(matches), 'exclusive': len(matches_exclusive)}

	for k, v in subgraph_to_number_of_matches.items():
		print('%s: %d / %d' % (k, v['exclusive'], v['full']))


""" Used in function below """


"""
find subgraphs of `G` with `size` new nodes, connected to `base`.
"""
def find_subgraphs(G, max_size, track_search=True):
	nodeOp = { v : v_data['opcode'] for v, v_data in G.nodes(data=True) }
	tracking = {}
	searched = []

	def amalg(subgraph_iter):
		for H in subgraph_iter:
			H_name = 'GEN%d: {'% len(H) + ";".join(nodeOp[s] for s in H.nodes()) \
				+ " | "  \
				+ ";".join( nodeOp[s]+"->"+nodeOp[t] for (s,t) in sorted(H.edges()) ) \
				+ "}"

			gm = isomorphism.DiGraphMatcher(G, H, node_match=Align.by_op);

			matches = [ dict(
							template_id = H_name,
							match_idx = i,
							node_matches = match
						)  for i, match in enumerate(gm.subgraph_isomorphisms_iter()) ]

			matches_exclusive = pick_mutually_exclusive_matches(matches, G)
			tracking[H_name] = dict(
				graph = H,
				n_matches = {
					'full': len(matches),
					'exclusive': len(matches_exclusive)
				}
			)
			searched.append(H)
			# print('%s: %d / %d' % (H_name, len(matches), len(matches_exclusive)))



		# return [s for s in subgraph]
		# TODO: sampling or exhaustive check.
		# return [ next(iter(scores.values())) ]
		return [ data['graph'] for data in tracking.values() ]

	def extend_subgraphs(size, base=[]):
		if size == 0: return [G.subgraph(base)]

		accept = lambda n : not(n in base or any(substr in nodeOp[n] for substr in unacceptable_subgraph_nodes) )
		candidate_nodes = [n for b in base for n in G.successors(b) if accept(n)] \
				if len(base) > 0 else [n for n in G.nodes() if accept(n)] # covers base case where base = []

		options = []
		for n in candidate_nodes:
			for H in extend_subgraphs(size-1, [n, *base]):
				# checking for equality of graphs is harder than edges. We can do it with isomorphism,
				# 'cuz these are small subgraphs. But there are a lot of isomorphism tests. We can also
				# not check at all; this can be commented out if necessary and we'll rely more heavily on
				# selecting exclusive subgrahps (but it will be much bigger)

				if not any(isomorphism.is_isomorphic(o, H, node_match=Align.by_op) \
					for o in itertools.chain(options, searched) ):
						options.append(H)

		# print(options)

		return amalg(options)

	Hs = extend_subgraphs(max_size)
	print("Tracking %d"%len(tracking), "\tHs: %d"%len(Hs))
	for k,v in tracking.items():
		print('%s: %d / %d' % (k, v['n_matches']['exclusive'], v['n_matches']['full']))
	return Hs


"""Write json [ <list of matches>
	{"template_ID" : <>,
	 "match_idx" : 0, 1, 2, ...,
	 node_matches: { id -> id} }]
"""
def write_matches(matches, filename, extra_filename=''):
	filename = filename.replace(".json", "-matches%s.json" % extra_filename, 1)

	with open(filename, "w") as file:
		file.write(json.dumps(matches, indent=4))

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
		["load", "mul"],
	]

	Hs = [ graph2nx(*construct_chain(l), name= "[" + ", ".join(l) + "]") for l in chains ]

	# For colored printing
	g = "\033[92m"
	r = "\033[91m"
	b = "\033[00m"

	matches = []
	for H in Hs:
		matches.extend(find_matches(H, G))

	matches_exclusive = pick_mutually_exclusive_matches(matches, G)
	# save all matches (which might overlap)
	write_matches(matches, args.input, extra_filename='-full')
	# save mutually exclusive matches for the LLVM pass to read
	write_matches(matches_exclusive, args.input)

	visualize_graph(G, matches_exclusive)
