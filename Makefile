BUILD_DIR := ./build
TOP_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

DFG_COVERINGS_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
TEST_DIR = $(DFG_COVERINGS_DIR)/tests
EMBENCH_DIR = $(TEST_DIR)/embench
EMBENCH_SUPPORT_DIR = $(EMBENCH_DIR)/support

EMBENCH_SUPPORT_SRC = $(EMBENCH_SUPPORT_DIR)/main.c $(EMBENCH_SUPPORT_DIR)/beebsc.c
EMBENCH_SUPPORT_LL = $(EMBENCH_SUPPORT_SRC:.c=.ll)

PROFILING_SRC = $(DFG_COVERINGS_DIR)/profiling/Profiling.c
PROFILING_LL = $(PROFILING_SRC:.c=.ll)

CFLAGS += -I $(EMBENCH_DIR)/support/ -DCPU_MHZ=1

.PHONY: pass clean

default: pass

%-profiling-em.o: $(EMBENCH_SUPPORT_LL) %-matched.ll
	clang $(CFLAGS) -DFILENAME='"$*-profiling.csv"' -S -emit-llvm $(PROFILING_SRC) -o $(PROFILING_LL)
	clang $(PROFILING_LL) $^ -o $@

%-profiling.o: %-matched.ll
	clang $(CFLAGS) -DFILENAME='"$*-profiling.csv"' -S -emit-llvm $(PROFILING_SRC) -o $(PROFILING_LL)
	clang $(PROFILING_LL) $^ -o $@

pass:
	cd $(BUILD_DIR); make; cd $(TOP_DIR)

clean:
	rm -f {*,*/*,*/*/*}/*.{ll,json,gv,gv.pdf,o,csv}

%.ll: %.c
	clang $(CFLAGS) -S -emit-llvm $^ -o $@

%-matched.ll: %.c pass
	clang $(CFLAGS) -O1 -emit-llvm -Xclang -disable-O0-optnone -S $< -o $@
	opt -mem2reg -inline -S $@ -o $@
	opt -load $(BUILD_DIR)/dfg-pass/libDFGPass.* -dfg-pass $(ADD_PASS_FLAGS) -S $@ -o $@ -json-output $*.json

%-matched.ll: %.ll pass
	clang $(CFLAGS) -O1 -emit-llvm -Xclang -disable-O0-optnone -S $< -o $@
	opt -mem2reg -inline -S $@ -o $@
	opt -load $(BUILD_DIR)/dfg-pass/libDFGPass.* -dfg-pass $(ADD_PASS_FLAGS) -S $@ -o $@ -json-output $*.json