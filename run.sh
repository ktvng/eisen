clear
if python3 main.py $1 ; then
    llc -filetype=obj build/test.ll -o build/test.o
    gcc build/test.o -o build/test
    ./build/test
    echo
fi
