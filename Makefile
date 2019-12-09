BUILD_DIR := ./build
TOP_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

pass:
	cd $(BUILD_DIR); make; cd $(TOP_DIR)

clean:
	rm -f ./tests/*.ll
	rm -f ./tests/*.json

%.ll: %.c pass
	clang $(CFLAGS) -emit-llvm -Xclang -disable-O0-optnone -S $< -o $@
	opt -load $(BUILD_DIR)/dfg-pass/libDFGPass.* -dfg-pass -S $@ -o /dev/null -json-output $@.json
	python dfg.py --input $@.json 