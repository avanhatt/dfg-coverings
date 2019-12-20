import os
import subprocess

EMBENCH_DIR = 'tests/embench/'

def run_embench_benchmark(benchmark):

    c_files = []
    for filename in os.listdir(benchmark):
        f_root, ext = os.path.splitext(filename)
        if ext == '.c':
            c_files.append(f_root)

    # Benchmarks with multiple files need to be combined into one IR file before
    # running our pass
    if len(c_files) > 1:
        ll_files = []
        for file in c_files:
            f_target = os.path.join(benchmark, file + '.ll')
            ll_files.append(f_target)
            subprocess.call(['make', f_target])

        comb_target = os.path.join(benchmark, 'combined.ll')
        subprocess.call(['llvm-link'] + ll_files + ["-S", "-o", comb_target])

        target = os.path.join(benchmark, 'combined-profiling-em.o')
    else:
        target = os.path.join(benchmark, c_files[0] + '-profiling-em.o')

    # Run make
    subprocess.call(['make', target])

    # Run the executable
    subprocess.call([target])

def profile_embench():

    contents = [os.path.join(EMBENCH_DIR, v) for v in os.listdir(EMBENCH_DIR)]
    benchmarks = [v for v in contents if os.path.isdir(v) and "support" not in v]
    for benchmark in benchmarks:
        run_embench_benchmark(benchmark)

if __name__ == '__main__':
    profile_embench()