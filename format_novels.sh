# uses alpino tokenizer tools to format the DBNL novels in ./data/novels, 
# to get them ready for predicting events on

# unzip novels
for novel_zip in ./data/novels/*.txt.gz; do
    gzip -dkf $novel_zip
done

# use Alpino to format and tokenize the file
for novel_txt in ./data/novels/*01.txt; do
    tok_filename=$(echo $novel_txt | cut -d'.' -f 2)
    tok_filename=".${tok_filename}.tok"
    if [ ! -f $tok_filename ]; then
        ./Alpino/Tokenization/paragraph_per_line $novel_txt | ./Alpino/Tokenization/tokenize.sh > $tok_filename
        echo "${novel_txt} > ${tok_filename}"
    fi
done