import json
import argparse
from collections import namedtuple, defaultdict
from graphviz import Digraph
import networkx as nx
from networkx import isomorphism
import itertools
import time
import csv

Vertex = namedtuple('Vertex', ['id', 'opcode'])
Edge = namedtuple('Edge', ['source', 'dest', 'arg_num_at_dest'])

acceptable_identifiers = ['template_id', 'template_ID', 'name']
opcodes_with_side_effects = ["ret", "br", "call", "out", "store", "load"]
unacceptable_subgraph_nodes = ['argument', 'constant', 'external'] + opcodes_with_side_effects

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
	return any([o in opcode for o in opcodes_with_side_effects])


def visualize_graph(G, matches=None, filename='output.gv'):
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
			if vertex.id in pointer_matches:
				dot.attr('node', shape='diamond', style='filled', color='red')
			else:
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
		dot.render(filename, view=True)
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
def pick_mutually_exclusive_matches(matches):
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
		if any([p in covered_nodes for p in pointers]):
			continue
		covered_nodes.update(pointers)
		matches_exclusive.append(match)
	return matches_exclusive

# pick collection exactly r subgraph stencils
# that statically covers the most instructions
def pick_r_stencils(subgraph_to_matches, r, filename):
	best_matches = []
	best_combo_with_counts = None
	for combo in itertools.combinations(subgraph_to_matches.keys(), r):
		stencil_matches = [match for subgraph in combo for match in subgraph_to_matches[subgraph]]
		exclusive_matches = pick_mutually_exclusive_matches(stencil_matches)
		if len(exclusive_matches) > len(best_matches):
			best_matches = exclusive_matches
			best_combo_with_counts = defaultdict(int)
			for match in exclusive_matches:
				best_combo_with_counts[match['template_id']] += 1
	# save best combo in csv
	with open(filename, "w") as csvfile:
		csvwriter = csv.writer(csvfile, delimiter='\t')
		csvwriter.writerow(['subgraph', 'exclusive'])
		for stencil, count in sorted(best_combo_with_counts.items()):
			csvwriter.writerow([stencil, count])
	# save best combo stencil jsons for matching to other programs
	stencil_jsons = []
	for stencil_canonical_string in best_combo_with_counts.keys():
		stencil_jsons.append(subgraph_to_matches[stencil_canonical_string][0]['template_json'])
	with open(filename.replace(".csv", "-stencils.json", 1), "w") as file:
		file.write(json.dumps(list(stencil_jsons), indent=4))
	# and print for ease
	print('Best stencil combination:')
	for stencil, count in best_combo_with_counts.items():
		print('\t%s: %d' % (stencil, count))
	print("Total number of times stencils matched: %d" % len(best_matches))
	return best_matches

# generate all stencils with numbers of edges between bottom_k and top_k
def generate_all_stencils_between_ks(G, bottom_k, top_k, filename):
	node_pointer_to_opcode = {}
	for v, v_data in G.nodes(data=True):
	 	node_pointer_to_opcode[v] = v_data['opcode']

	def node_match(data1, data2):
		return data1['opcode'] == data2['opcode'] # and data1['arity'] == data2['arity']

	def has_acceptable_nodes(edge_list):
		acceptable = []
		for (s, t) in edge_list:
			s_op = node_pointer_to_opcode[s]
			t_op = node_pointer_to_opcode[t]
			acceptable.append(not any([prefix in s_op for prefix in unacceptable_subgraph_nodes]) \
			                  and not any([prefix in t_op for prefix in unacceptable_subgraph_nodes]))
		return all(acceptable)


	def canonicalize_name(edge_list, node_list):
		opcode_to_num = defaultdict(int)
		pointer_to_id = {}
		pointer_to_canonical = {}
		canonicalized = []
		def pointer_to_string(s):
			s_op = node_pointer_to_opcode[s]
			s_op_num = -1
			if s in pointer_to_id:
				s_op_num = pointer_to_id[s]
			else:
				s_op_num = opcode_to_num[s_op]
				pointer_to_id[s] = s_op_num
				opcode_to_num[s_op] += 1
			s_final = '%s_%d' % (s_op, s_op_num)
			pointer_to_canonical[s] = s_final
			return s_final
		canonicalized = sorted([('(%s, %s)' % (pointer_to_string(s), pointer_to_string(t))) for s, t in edge_list])
		canonical_edges = ', '.join(canonicalized)
		canonical_nodes = ', '.join(sorted([pointer_to_canonical[v] for v in node_list]))
		H_name = '%s | %s' % (canonical_nodes, canonical_edges) 
		return H_name, pointer_to_canonical

	def canonicalize_json(H, pointer_to_canonical):
		H_renamed = H.copy()
		for v in H.nodes():
			H_renamed.nodes[v]['id'] = pointer_to_canonical[v]
		for e in H.edges():
			H_renamed.edges[e]['source'] = pointer_to_canonical[H_renamed.edges[e]['source']]
			H_renamed.edges[e]['dest'] = pointer_to_canonical[H_renamed.edges[e]['dest']]
		H_renamed = nx.relabel_nodes(H_renamed, {v: pointer_to_canonical[v] for v in H_renamed.nodes()})
		return nx.readwrite.json_graph.node_link_data(H_renamed)
		
	def edges_to_nodes(edge_list):
		nodes = set()
		for s, t in edge_list:
			nodes.add(s)
			nodes.add(t)
		return sorted(list(nodes))

	def H_to_name_and_match(H, match_idx, mapping=None):
		H_name, pointer_to_canonical = canonicalize_name(H.edges(), H.nodes())
		if mapping == None:
			mapping = {v: pointer_to_canonical[v] for v in H.nodes()}
		else:
			mapping = {v1: pointer_to_canonical[v2] for v1, v2 in mapping.items()}
		H_json = canonicalize_json(H, pointer_to_canonical)
		match = dict(
			template_id = H_name,
			template_json = H_json,
			match_idx = match_idx,
			node_matches = mapping
		)
		return H_name, match

	def find_k_edge_subgraph_matches(G, bottom_k, top_k, current_k=1, prev_candidates=[]):
		# generate all k-edge subgraphs, including those unacceptable nodes
		candidates = [edge_list + [(s,t)] for edge_list in prev_candidates for s, t, e_data in G.edges(data=True)]
		# first case
		if not len(prev_candidates):
			candidates = [[(s, t)] for s, t, e_data in G.edges(data=True)]
		# filter out unacceptable nodes
		candidates = [edge_list for edge_list in candidates if has_acceptable_nodes(edge_list)]
		# keep only connected subgraphs with k edges
		Hs = [G.edge_subgraph(edge_list) for edge_list in candidates]
		connected = [nx.is_connected(H.to_undirected()) for H in Hs]
		num_edges = [len(H.edges()) for H in Hs]
		edge_lists = [edge_list for edge_list, con, num in zip(candidates, connected, num_edges) if con and num == current_k]
		Hs = [H for H, con, num in zip(Hs, connected, num_edges) if con and num == current_k]

		# remove duplicates
		edges_without_duplicates = set()
		final_edge_lists = []
		final_Hs = []
		for edge_list, H in zip(edge_lists, Hs):
			alphabetized = tuple(sorted(['%s_%s' % (s, t) for s, t in edge_list]))
			if alphabetized not in edges_without_duplicates:
				edges_without_duplicates.add(alphabetized)
				final_edge_lists.append(edge_list)
				final_Hs.append(H)

		# compare all current_k-edge subgraphs to each other to find matches
		canonical_H_to_num = defaultdict(int)
		canonical_H_to_matches = defaultdict(list)
		for current_H in final_Hs:
			found = False
			for canonical_H in canonical_H_to_num.keys():
				gm = isomorphism.DiGraphMatcher(current_H, canonical_H, node_match=node_match);
				if gm.subgraph_is_isomorphic():
					mapping = next(gm.isomorphisms_iter())
					H_name, match = H_to_name_and_match(canonical_H, canonical_H_to_num[canonical_H], mapping)
					canonical_H_to_matches[H_name].append(match)
					found = True
					canonical_H_to_num[canonical_H] += 1
					break
			if not found:
				H_name, match = H_to_name_and_match(current_H, canonical_H_to_num[current_H])
				canonical_H_to_matches[H_name].append(match)
				canonical_H_to_num[current_H] += 1

		subgraph_to_number_of_matches = {}
		for edge_list, H_matches in canonical_H_to_matches.items():
			exclusive_matches = pick_mutually_exclusive_matches(H_matches)
			subgraph_to_number_of_matches[edge_list] = \
			  {'total': len(H_matches), 'exclusive': len(exclusive_matches)}

		if current_k < top_k:
			if current_k < bottom_k:
				# don't return these intermediate subgraphs
				return find_k_edge_subgraph_matches(G, bottom_k, top_k, current_k+1, final_edge_lists)
			# otherwise keep track of all these smaller subgraphs, too
			next_H_to_matches, next_k_counts = find_k_edge_subgraph_matches(G, bottom_k, top_k, current_k+1, final_edge_lists)
			canonical_H_to_matches.update(next_H_to_matches)
			subgraph_to_number_of_matches.update(next_k_counts)
		return canonical_H_to_matches, subgraph_to_number_of_matches
	
	t1 = time.time()
	subgraph_to_matches, subgraph_to_number_of_matches = find_k_edge_subgraph_matches(G, bottom_k, top_k)
	t2 = time.time()
	print('Seconds: %.4f' % (t2 - t1))

	# save the stencils, number of mutually exclusive matches, total number of matches
	# as both human-readable csv and json for possible later use
	with open(filename.replace(".json", "-matches_%d-to-%d-edge-subgraphs.csv" % (bottom_k, top_k), 1), "w") as csvfile:
		csvwriter = csv.writer(csvfile, delimiter='\t')
		csvwriter.writerow(['subgraph', 'exclusive', 'total'])
		for k, v in sorted(subgraph_to_number_of_matches.items()):
			csvwriter.writerow([k, v['exclusive'], v['total']])
	with open(filename.replace(".json", "-matches_%d-to-%d-edge-subgraphs.json" % (bottom_k, top_k), 1), "w") as file:
		file.write(json.dumps(subgraph_to_number_of_matches, indent=4))
	# and print number of stencils found
	if bottom_k == top_k:
		print('Total stencils with %d edges: %d' % (top_k, len(subgraph_to_matches)))
	else:
		print('Total stencils with between %d and %d edges: %d' % (bottom_k, top_k, len(subgraph_to_matches)))

	return subgraph_to_matches


"""Write json [ <list of matches>
	{"template_ID" : <>,
	 "match_idx" : 0, 1, 2, ...,
	 node_matches: { id -> id} }]
"""
def write_matches(matches, filename, extra_filename=''):
	filename = filename.replace(".json", "-matches%s.json" % extra_filename, 1)

	with open(filename, "w") as file:
		file.write(json.dumps(matches, indent=4))

# if no --stencil-json argument, then the default is to generate stencils
if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--input', type=str, required=True)
	parser.add_argument('--stencil-json', type=str, required=False)
	args = parser.parse_args();

	G = graph2nx(*graph_from_json(args.input))
	# print_graph(V, E)

	chains = [
		["mul", "add", "srem"],
		["shl", "add"],
		["sdiv", "mul", "add"],
		["load", "mul"],
	]

	Hs = [ graph2nx(*construct_chain(l), name= "[" + ", ".join(l) + "]") for l in chains ]

	extra_filename = ''
	if args.stencil_json:
		with open(args.stencil_json, 'r') as jsonfile:
			Hs = []
			for H_json in json.load(jsonfile):
				Hs.append(nx.readwrite.json_graph.node_link_graph(H_json))
		extra_filename = '_' + (args.stencil_json.split('/')[-1]).replace('.json', '', 1)

	# For colored printing
	g = "\033[92m"
	r = "\033[91m"
	b = "\033[00m"

	matches = []
	for H in Hs:
		matches.extend(find_matches(H, G))

	matches_exclusive = pick_mutually_exclusive_matches(matches)
	# save all matches (which might overlap)
	write_matches(matches, args.input, extra_filename='%s-full' % (extra_filename))
	write_matches(matches_exclusive, args.input)
	
	if args.stencil_json:
		exit()

	# this finds candidate stencils within a dfg
	# instead of relying on the hand-specified chains
	bottom_k = 2
	top_k = 2
	subgraph_to_matches = generate_all_stencils_between_ks(G, bottom_k=bottom_k, top_k=top_k, filename=args.input)
	best_combo_matches = pick_r_stencils(subgraph_to_matches, r=2, filename=args.input.replace(".json", "_%d-to-%d-edge-subgraphs_combos.csv" % (bottom_k, top_k), 1))
	write_matches(best_combo_matches, args.input)
	visualize_graph(G, best_combo_matches, filename=args.input.replace(".json", "_%d-to-%d-edge-subgraphs_combos.gv" % (bottom_k, top_k), 1))

