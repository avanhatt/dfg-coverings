import os
import subprocess
import glob
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import math
# don't let matplotlib use xwindows
matplotlib.use('Agg')

plt.rcParams['patch.linewidth'] = 0
plt.rcParams['patch.edgecolor'] = 'none'
plt.rcParams["patch.force_edgecolor"] = False
sns.set(style="whitegrid")

benchmark_names = ['cubic',
				'st',
				'crc32',
				'ud',
				'matmult-int',
				'nbody',
				'minver',
				'sglib-combined',
				'aha-mont64',
				'edn',
				'nettle-sha256',
				'huffbench',
				'slre',
				'qrduino',
				'wikisort',
				'nettle-aes',
				'statemate',
				'picojpeg',
				'nsichneu'
				]

stencils = ['aha-mont64/mont64',
			'crc32/crc_32',
			'cubic/combined',
			'edn/libedn',
			'huffbench/libhuffbench',
			'matmult-int/matmult-int',
			'minver/libminver',
			'nbody/nbody',
			'nettle-aes/nettle-aes',
			'nettle-sha256/nettle-sha256',
			'nsichneu/libnsichneu',
			'picojpeg/combined',
			'qrduino/combined',
			'sglib-combined/combined',
			'slre/libslre',
			'st/libst',
			'statemate/libstatemate',
			'ud/libud'
			'wikisort/libwikisort'
			]
stencils = ['./tests/embench/%s_2-to-2-edge-subgraphs_combos-stencils.json' % s for s in stencils]

def plot_all_static_dynamic_coverage(data, half, figsize):
	plt.rcParams['figure.figsize']=figsize
	ax = sns.barplot(x="Benchmark", y="Percent of instructions covered", hue='Variable', data=data)
	# write values above bars
	for p in ax.patches:
	    height = p.get_height()
	    ax.text(p.get_x()+p.get_width()/2.,
	            height + 1,
	            '{:1.2f}%'.format(height),
	            ha="center", fontsize='x-small') 
	#locs, labels = plt.xticks()
	#plt.xticks(locs, labels, rotation='vertical')
	ax.set_ylim((0,60))
	ax.set_yticks(np.arange(0, 61, 10), minor=False)
	ax.set_yticks(np.arange(0, 61, 5), minor=True)
	ax.grid(which='minor', alpha=0.4)
	plt.legend(framealpha=1)
	plt.savefig('embench-profiling-half-%d.png' % half, bbox_inches='tight', dpi=400)
	plt.close()

def run_all_benchmarks_with_given_stencils(stencils):
	for stencil in stencils:
		print(stencil)
		subprocess.call(['python', 'profiling.py', '--stencil-json', stencil])

def main():
	data = pd.read_csv('embench-profiling.csv').rename(columns={'static percent': 'Static', 'dynamic percent': 'Dynamic'})
	data = data.melt(id_vars='benchmark').rename(columns=str.title).rename(columns={'Value': 'Percent of instructions covered'})
	data = data.loc[data['Variable'].isin(['Static', 'Dynamic'])]
	halfway = math.floor(len(benchmark_names)/2)
	data_first_half = data.loc[data['Benchmark'].isin(benchmark_names[:halfway])]
	data_second_half = data.loc[data['Benchmark'].isin(benchmark_names[halfway:])]
	plot_all_static_dynamic_coverage(data_first_half, half=1, figsize=(12,3))
	plot_all_static_dynamic_coverage(data_second_half, half=2, figsize=(12,3))
	run_all_benchmarks_with_given_stencils(stencils)

if __name__ == '__main__':
	main()