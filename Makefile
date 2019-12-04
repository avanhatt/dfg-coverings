BUILD_DIR := ./build

clean:
	rm -f ./tests/*.ll

%.ll: %.c
	clang $(CFLAGS) -emit-llvm -Xclang -disable-O0-optnone -S $< -o $@
	opt -load $(BUILD_DIR)/dfg-pass/libDFGPass.* -dfg-pass -S $@ -o /dev/null