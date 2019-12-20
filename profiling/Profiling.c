#include <stdio.h>
#include <stdlib.h>

#ifndef FILENAME
#define FILENAME "profiling.csv"
#endif

// Global count variables, atomic to support multithreaded code
_Atomic long DynamicMatched = 0;
_Atomic long DynamicTotal = 0;

_Atomic long StaticMatched = 0;
_Atomic long StaticTotal = 0;

// To be called once, on module begin
void saveStaticCounts(int Matched, int Total) {
  StaticMatched = Matched;
  StaticTotal = Total;
}

// To be called per basic block
void incremementCounts(int Matched, int Total) {
  DynamicMatched += Matched;
  DynamicTotal += Total;
}

// To be called once, on module end
void printDynamicProfiling() {
  float StaticPercent = (float)StaticMatched/StaticTotal*100;
  printf("%ld/%ld (%.2f %%) static instructions matched\n",
    StaticMatched,
    StaticTotal,
    StaticPercent);

  float DynamicPercent = (float)DynamicMatched/DynamicTotal*100;
  printf("%ld/%ld (%.2f %%) dynamic instructions matched\n",
    DynamicMatched,
    DynamicTotal,
    DynamicPercent);

  // Write out profiling results to a csv
  FILE *f = fopen(FILENAME, "w");
  if (f == NULL) {
      printf("Error opening file!\n");
      exit(1);
  }

  fprintf(f, "static matched,static total,static percent,");
  fprintf(f, "dynamic matched,dynamic total,dynamic percent\n");

  fprintf(f, "%ld,%ld,%f,%ld,%ld,%f\n",
    StaticMatched,
    StaticTotal,
    StaticPercent,
    DynamicMatched,
    DynamicTotal,
    DynamicPercent
    );

  fclose(f);
}
