

import os , re
import argparse
from statistics import harmonic_mean

from spacy.tokens import Doc
from coreferee.data_model import Mention
import spacy, coreferee

from build_mentions import build_mention, create_mentions

def parse_conll(file_name):
    '''Parses a conll file in 2012 shared task format
    returns two dicts with the doc ids as key :
    As values for the two dicts :
    - text of the doc following french word association rules
    - its respective token boundaries'''
    txt_file_contents = {}
    all_tokens_spans_list = {} 
    with open(file_name, 'r', encoding='UTF8') as conll_file:
        for line in conll_file:
            if line.startswith("#begin document"):
                doc_id = line.strip("\n")
                j = re.search('part (\d+)',line).group(1)
                token_start, token_end = 0, -1
                first_token = True
                tokens = []
                tokens_spans = []
                sentence_break_spans = []
            elif line.startswith('#end document'):
                txt_file_contents[doc_id] = ''.join(tokens)
                all_tokens_spans_list[doc_id] = (tokens_spans, sentence_break_spans)
            elif line != '\n':
                columns = line.split()
                token = columns[3]
                sep = ' '
                if token in (".",",",")","'") or first_token or\
                    tokens[-1].endswith("'") or re.match('\-\w+',token) or \
                    tokens[-1].endswith("-") or token.startswith('-'):
                    sep = ''
                
                token_start = token_end + len(sep) + 1
                token_end = token_start + len(token) -1
                tokens.append(sep + token)
                tokens_spans.append((token_start,token_end))
                first_token = False
            else :
                sentence_break_spans.append(token_end)

    return txt_file_contents, all_tokens_spans_list

def make_conll(doc, add_singletons, doc_id = None, tokens_sentence_boundaries = None):
    '''
        Produce a conll part (string) from a spacy doc already parsed by coreferee
        If tokens_sentence_boundaries are given, the output conll will have them as tokens
        (one per line)
        Otherwise, the tokens will follow spacy's tokenization
    '''
    if tokens_sentence_boundaries:
        tokens_boundaries, sentence_breaks = tokens_sentence_boundaries
    else:
        tokens_boundaries = [(t.idx, t.idx+len(t)) for t in doc]
        sentence_breaks = [s.end for s in doc.sents][:-1]

    if doc_id :
        doc_name = re.search("\((.*?)\)", doc_id).group(1)
        doc_part = re.search("part (\d+)", doc_id).group(1)
    else:
        doc_name , doc_part = "_", "_"
    mentions = create_mentions(doc, nlp, add_singletons=add_singletons)
    lines = [doc_id]
    token_count = 0
    size_doc = len(tokens_boundaries)
    unclosed_corefs = []
    for i, token_boundary in enumerate(tokens_boundaries):
        token_start, token_end = token_boundary
        spacy_tokens = doc.char_span(token_start, token_end+1, alignment_mode="expand")
        #print(token_start, token_end+1, doc.text[token_start:token_end+1])
        spacy_token_root = spacy_tokens.root
        next_token_start = tokens_boundaries[i+1][0] if i < size_doc -1 else len(doc.text)
        text = doc.text[token_start:token_end+1]
        lemma = spacy_token_root.lemma_
        pos = spacy_token_root.pos_
        corefs = []
        if token_count == 0:
            corefs.extend(f"({chain_index}" for chain_index in unclosed_corefs)
        duplicate = False
        for mention, chain_index in mentions.items():
            mention_start = mention[0].idx
            mention_end = mention[-1].idx + len(mention[-1]) -1
            if token_start <= mention_start  <= token_end and\
                token_start <= mention_end  < next_token_start:
                if duplicate : continue
                corefs.append(f"({chain_index})")
                duplicate = True
            elif token_start <= mention_start  <= token_end:
                corefs.append(f"({chain_index}")
                unclosed_corefs.append(chain_index)
            elif token_start <= mention_end  < next_token_start:
                corefs.append(f"{chain_index})")
                unclosed_corefs.remove(chain_index)

        if i < size_doc -1 and \
            any(token_end <= b < tokens_boundaries[i+1][0] for b in sentence_breaks):
            corefs.extend(f"{chain_index})" for chain_index in unclosed_corefs)
        coref = "|".join(corefs) if corefs else '_'

        line = (" "*10).join([doc_name, doc_part, str(token_count), text, pos] + ["_"]*7 + [coref])
        lines.append(line)
        token_count +=1
        if i< size_doc-1 and\
            any(token_end <= b < tokens_boundaries[i+1][0] for b in sentence_breaks):
            lines.append("")
            token_count = 0
            if unclosed_corefs:
                print("mentions across two sentences :",unclosed_corefs)
    if unclosed_corefs:
        print("unclosed mentions :",unclosed_corefs)
    lines.append("#end document\n")
    return "\n".join(lines)


def write_conll(texts, output_file, nlp, docs_boundaries = None, add_singletons=False):
    '''Takes a list of texts as input and produced a conll file 
    following conll 2012 shared task format (with coreference)'''
    with open(output_file, "w", encoding="utf8") as output:
        size_texts = len(texts)
        for i, doc_id in enumerate(texts):
            print(doc_id, f": document {i+1} out of {size_texts}")
            doc = nlp(texts[doc_id])
            doc_boundaries = docs_boundaries[doc_id] if docs_boundaries else None
            print("\t\t\t-----------------\n")
            conll_part = make_conll(doc, add_singletons, doc_id, doc_boundaries)
            output.write(conll_part+"\n")
            #break

  
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate several metrics on\
                                     the performance of the model on a corpus')
    parser.add_argument('--input_file', type=str,
                        help='The path to the directory containing the conll test corpus')

    parser.add_argument('--output_file', type=str,
                        help='The path to the output conll file')

    parser.add_argument('--spacy_model', type= str,
                        help='name of the spacy model to use. Ex: fr_core_news_md')
    
    parser.add_argument('--keep_original_tokenisation', type=bool,
                        default = True,
                        help='keep the tokenisation of the original file or use\
                                spacy\'s tokenisation in the output file'          
    )

    parser.add_argument('--add_singletons', 
                        action="store_true",
                        help='include mentions of singleton entities in the output'          
    )
    parser.add_argument('--max_anaphora_dist', type=int,
                        default=5,
                        help='maximum anaphora sentence referential distance for coreferee'          
    )
    parser.add_argument('--max_coreferring_noun_dist', type=int,
                        default=3,
                        help='maximum coreferring noun sentence referential distance for coreferee'          
    )
    args = parser.parse_args()

    INPUT_FILE = args.input_file

    nlp = spacy.load(args.spacy_model)
    nlp.add_pipe('coreferee')
    nlp.get_pipe("coreferee").annotator.rules_analyzer.maximum_anaphora_sentence_referential_distance\
        = args.max_anaphora_dist
    nlp.get_pipe('coreferee').annotator.rules_analyzer.maximum_coreferring_nouns_sentence_referential_distance\
        = args.max_coreferring_noun_dist
    if INPUT_FILE.endswith("conll"):
        txt_file_contents, all_tokens_spans_list = parse_conll(INPUT_FILE)
        if args.keep_original_tokenisation == True:
            token_boundaries = all_tokens_spans_list
        else :
            token_boundaries = None
    else:
        txt_file_contents = {"doc":open(INPUT_FILE,encoding="utf8").read()}
    write_conll(txt_file_contents, args.output_file, nlp, token_boundaries, args.add_singletons)