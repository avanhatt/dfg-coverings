#include <stdio.h>

int redefine_add(int a, int b) {
	return (a + b) * (a + b);
}

int main(int argc, char const *argv[]) {
	int sum = redefine_add(21, 37);
	printf("%d\n", sum);
	return 0;
}