#include <stdio.h>
#include <stdlib.h>

#ifndef FILENAME
#define FILENAME "profiling.csv"
#endif

// Global count variables, atomic to support multithreaded code
_Atomic long MatchedInstructions = 0;
_Atomic long TotalInstructions = 0;

// To be called per basic block
void incremementCounts(int Matched, int Total) {
  MatchedInstructions += Matched;
  TotalInstructions += Total;
}

// To be called once, on module end
void printDynamicProfiling() {
  float Percent = (float)MatchedInstructions/TotalInstructions*100;
  printf("%ld/%ld (%.2f %%) dynamic instructions matched\n",
    MatchedInstructions,
    TotalInstructions,
    Percent);

  // Write out profiling results to a csv
  FILE *f = fopen(FILENAME, "w");
  if (f == NULL) {
      printf("Error opening file!\n");
      exit(1);
  }

  fprintf(f, "matched,total,percent\n");

  fprintf(f, "%ld,%ld,%f\n",
    MatchedInstructions,
    TotalInstructions,
    Percent);

  fclose(f);
}
