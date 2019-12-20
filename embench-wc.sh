#!/usr/bin/env bash

for d in tests/embench/*/ ;
    # echo $d
    do find $d -name *.c | xargs cat | wc -l; echo $d
done