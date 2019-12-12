BUILD_DIR := ./build
TOP_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

DFG_COVERINGS_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))
TEST_DIR = $(DFG_COVERINGS_DIR)/tests
EMBENCH_DIR = $(TEST_DIR)/embench

CFLAGS += -I $(EMBENCH_DIR)/support/ -DCPU_MHZ=1

pass:
	cd $(BUILD_DIR); make; cd $(TOP_DIR)

clean:
	rm -f {./tests/*,./tests/*/*,./tests/*/*/*}.{ll,json}
	rm -f *.gv *.gv.pdf

%.ll: %.c pass
	clang $(CFLAGS) -O1 -emit-llvm -Xclang -disable-O0-optnone -S $< -o $@
	opt -mem2reg -S $@ -o $@
	opt -load $(BUILD_DIR)/dfg-pass/libDFGPass.* -dfg-pass -S $@ -o /dev/null -json-output $@.json
	python3 -i dfg.py --input $@.json
