import os
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--stencil-json', type=str, required=False)
args = parser.parse_args();
additional_flags = ''
csv_filename = 'embench-profiling.csv'
if args.stencil_json:
    additional_flags = 'ADD_PASS_FLAGS=-stencil-json %s' % args.stencil_json
    csv_filename = 'embench-profiling_%s.csv' % (args.stencil_json.split('/')[-1]).replace('.json', '', 1)

EMBENCH_DIR = 'tests/embench/'

BY_SIZE = [
            "cubic/",
            "st/",
            "crc32/",
            "ud/",
            "matmult-int/",
            "nbody/",
            "minver/",
            "sglib-combined/",
            "aha-mont64/",
            "edn/",
            "nettle-sha256/",
            "huffbench/",
            "slre/",
            "qrduino/",
            "wikisort/",
            "nettle-aes/",
            "statemate/",
            "picojpeg/",
            "nsichneu/",
            ]

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
            make_command = ['make', f_target]
            if additional_flags:
                make_command.append(additional_flags)
            subprocess.call(make_command)

        comb_target = os.path.join(benchmark, 'combined.ll')
        subprocess.call(['llvm-link'] + ll_files + ["-S", "-o", comb_target])

        target = os.path.join(benchmark, 'combined-profiling-em.o')
    else:
        target = os.path.join(benchmark, c_files[0] + '-profiling-em.o')

    # Run make
    make_command = ['make', target]
    if additional_flags:
        make_command.append(additional_flags)
    subprocess.call(make_command)

    # Run the executable
    subprocess.call([target])

    print(target[:-5] + ".csv")
    with open(target[:-5] + ".csv", "r") as csv_file:
        with open(csv_filename, "a") as f:
            for l in csv_file:
                pass

            f.write(benchmark.split('/')[-2] + "," + l)

def profile_embench():
    with open(csv_filename, "w") as f:
        f.write("benchmark,static matched,static total,static percent,dynamic matched,dynamic total,dynamic percent\n")

    # contents = [os.path.join(EMBENCH_DIR, v) for v in os.listdir(EMBENCH_DIR)]
    # benchmarks = [v for v in contents if os.path.isdir(v) and "support" not in v]
    benchmarks = [os.path.join(EMBENCH_DIR, v) for v in BY_SIZE]
    for benchmark in benchmarks:
        run_embench_benchmark(benchmark)

if __name__ == '__main__':
    profile_embench()