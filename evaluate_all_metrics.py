
import os 
from spacy.tokens import Doc
from coreferee.data_model import Mention
from coreferee.training.loaders import DEMOCRATConllLoader
import spacy, coreferee
from coreferee.rules import RulesAnalyzerFactory
import argparse
from statistics import harmonic_mean, mean
from coreferee.data_model import Mention



class Scorer :
    def __init__(self, nlp, rules_analyzer):
        self.all_key_chains , self.all_response_chains = {}, {}
        self.working_doc_start = 0
        self.nlp = nlp
        self.rules_analyzer = rules_analyzer
        self.tokens = []
        self.all_response_docs = []
        self.potential_pairs = set()
        self.all_mentions = set()

        
        
    def evaluate(self,key_docs, docs_chains):
        self.all_key_docs = key_docs
        for doc_index in range(len(key_docs)):
            print(f'processing doc {doc_index}')
            key_doc = docs[doc_index]
            key_chains =  {k:v for k,v in docs_chains.items() if k.startswith(f'{doc_index}:')}
            response_doc = self.nlp(key_doc.text)

            response_chains = {f'{doc_index}:{j}':{tuple([i + self.working_doc_start for i in mention.token_indexes])
                                for mention in chain} for j,chain in enumerate(response_doc._.coref_chains)}
            
            self.all_response_chains |= response_chains
            self.all_key_chains |= key_chains
            self.potential_pairs |= self.get_potential_pairs(key_doc)
            self.all_mentions |= self.get_all_mentions(key_doc)
            
            self.working_doc_start += len(key_doc)
            self.tokens.extend([token for token in response_doc])
            self.all_response_docs.append(response_doc)
            #response_doc._.coref_chains.print()
            if doc_index > 5 and 0:
                break

        self.all_key_links = self.get_all_links(self.all_key_chains)
        self.all_response_links = self.get_all_links(self.all_response_chains)
        print('scoring')
        muc_precision, muc_recall, muc_f1 = self.score_MUC()
        print('MUC',muc_precision, muc_recall, muc_f1 )
        precision_c, recall_c, f1_c, \
        precision_n, recall_n, f1_n, \
        blanc_p, blanc_r, blanc =  self.score_BLANC()
        print('BLANC',precision_c, recall_c, f1_c, precision_n, recall_n, f1_n, blanc_p, blanc_r, blanc)
        b_cubed_p, b_cubed_r, b_cubed =  self.score_B_Cubed()
        print('B-Cubed',b_cubed_p, b_cubed_r, b_cubed)
        accuracy, precision, recall, f1 = self.score_pairwise_metrics()
        print('Pairwise Metrics', precision, recall, f1, accuracy)
        
    def get_potential_pairs(self,key_doc):
        potential_pairs = set()
        for token in key_doc:
            
            if hasattr(token._.coref_chains, 'temp_potential_referreds'):
                for potential_referred in token._.coref_chains.temp_potential_referreds:
                    potential_referring_i = (token.i + self.working_doc_start,)
                    j = potential_referred.root_index
                    if hasattr(key_doc[j]._.coref_chains, 'temp_potential_referreds'):
                        #print(key_doc[j])
                        for potential_referring in key_doc[j]._.coref_chains.temp_potential_referreds:
                            if token.i in potential_referring.token_indexes:
                                potential_referring_i = tuple([i + self.working_doc_start \
                                                               for i in potential_referring.token_indexes])
                            
                    potential_referred_i = tuple([i + self.working_doc_start for i in potential_referred.token_indexes])
                    ordered_pair = tuple(sorted([potential_referring_i,potential_referred_i],key=lambda X:X[0]))
                    potential_pairs.add(ordered_pair)
                    
        return potential_pairs
    
    def get_all_mentions(self,doc):
        all_mentions = set()
        for token in doc:
            if self.rules_analyzer.is_independent_noun(token) or \
                        self.rules_analyzer.is_potential_anaphor(token):
                for get_dependent_siblings in [False,True]:
                    mention = Mention(token, get_dependent_siblings)
                    all_mentions.add(tuple([i + self.working_doc_start for i in mention.token_indexes]))
        return all_mentions
                                

    def get_all_links(self,chains)->set:
        links = set()
        for chain in chains.values():
            for mention_1 in chain:
                for mention_2 in chain:
                    if mention_1 != mention_2:
                        ordered_pair = tuple(sorted([mention_1,mention_2],key=lambda X:X[0]))
                        links.add(ordered_pair)
                        
        return links
            
    def score_pairwise_metrics(self):
        true_positives = true_negatives = false_positives = false_negatives = 0
        for potential_pair in self.potential_pairs:
            if potential_pair in self.all_key_links:
                if potential_pair in self.all_response_links:
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                if potential_pair in self.all_response_links:
                    false_positives += 1
                else:
                    true_negatives += 1

        all_pairs_count = true_positives + false_negatives + false_positives + true_negatives
        print(true_positives , false_negatives , false_positives , true_negatives)
        accuracy = (true_positives + true_negatives) / all_pairs_count
        precision = true_positives / (true_positives + false_positives)
        recall = true_positives / (true_positives + false_negatives)
        f1 = harmonic_mean([precision, recall])
        return accuracy, precision, recall, f1
            
    def score_B_Cubed(self) -> tuple:
        '''
            Based on https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.47.5848&rep=rep1&type=pdf
        '''
        key_chains, response_chains = self.all_key_chains, self.all_response_chains
        key_mention_count = sum(1 for chain in key_chains.values() for mention in chain)
        response_mention_count = sum(1 for chain in response_chains.values() for mention in chain)

        all_recalls = []
        for key_chain in key_chains.values() :
            for key_mention in key_chain :
                #individual_recall = sum(if mention )
                
                response_chains_containing_mention = [chain for chain in response_chains.values() \
                                                      if key_mention in chain]
                
                if response_chains_containing_mention != []:
                    key_mention_individual_count = len(key_chain & response_chains_containing_mention[0])
                    mention_individual_credit = key_mention_individual_count / len(key_chain)
                else:
                    #Absence in all chains of the response means it's considered a singleton
                    mention_individual_credit = 1 / len(key_chain)
                all_recalls.append(mention_individual_credit)
                
        all_precisions = []          
        for response_chain in response_chains.values() :
            for response_mention in response_chain :
                key_chains_containing_mention = [chain for chain in key_chains.values() \
                                                 if response_mention in chain]
                
                if key_chains_containing_mention != []:
                    response_mention_individual_count = len(key_chain & key_chains_containing_mention[0])
                    mention_individual_credit = response_mention_individual_count / len(response_chain)
                else:
                    mention_individual_credit = 1 / len(response_chain)
                    #Absence in all chains of key means it is a singleton
                    
                all_precisions.append(mention_individual_credit)

        recall = mean(all_recalls)
        precision = mean(all_precisions)
        f1 = harmonic_mean([recall,precision])
        return precision, recall, f1

        
                            
        
    
    def score_MUC(self) -> tuple:
        '''
            r = correct links / expected links
            p = correct links / output links
        '''
        def get_minimum_links(chains)-> set:
            minimum_links = set()
            for chain in chains.values():
                sorted_mentions = sorted(chain, key=lambda X:X[0])
                for i in range(len(sorted_mentions)-1):
                    minimum_links.add((sorted_mentions[i],sorted_mentions[i+1]))
            return minimum_links
                    
        def get_correct_links_count(links, chains):
            count = 0
            for link in links:
                for chain in chains.values():
                    if link[0] in chain and link[1] in chains:
                        count += 1
                        break
            return count
        #key_chains, response_chains = self.all_key_chains, self.all_response_chains
        key_minimum_links = get_minimum_links(self.all_key_chains)
        response_minimum_links = get_minimum_links(self.all_response_chains)
        correct_links = self.all_key_links & response_minimum_links
        recall = len(correct_links) / len(key_minimum_links)
        precision = len(correct_links) / len(response_minimum_links)
        '''
        https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5667668/
        '''
        f1 = harmonic_mean ([recall, precision])

        return recall, precision, f1

    def score_BLANC(self)->tuple:
        '''
            Based on : https://www.cs.cmu.edu/~hovy/papers/10BLANC-coref-metric.pdf
        '''

        
        def get_mention_link_type(coreference_links, all_mentions):
            labeled_links = {}
            for mention_1 in all_mentions:
                for mention_2 in all_mentions:
                    pair = tuple(sorted([mention_1,mention_2],key=lambda X:X[0]))
                    if pair in coreference_links and mention_1 != mention_2:
                        labeled_links[pair] = 'coreference'
                    else:
                        labeled_links[pair] = 'non-coreference'
            return labeled_links
        
        key_coreference_links = self.all_key_links
        response_coreference_links = self.all_response_links
        all_mentions = self.all_mentions
        key_mentions_link_dict = get_mention_link_type(key_coreference_links, all_mentions)
        response_mentions_link_dict = get_mention_link_type(response_coreference_links, all_mentions)
        self.all_potential_pairs = key_mentions_link_dict
        
        rc = wc = rn = wn = 0 
        for pair in key_mentions_link_dict:
            true_label = key_mentions_link_dict[pair]
            pred_label = response_mentions_link_dict[pair]
            if pred_label == 'coreference':
                if true_label == pred_label:
                    rc+=1
                    #print('RIGHT RC', [self.tokens[i] for i in pair[0]], '->', [self.tokens[i] for i in pair[1]] ,' : ', self.tokens[pair[0][0]-2:pair[1][0]+2])
                else:
                    wc+=1
                    #print('WRONG WC', [self.tokens[i] for i in pair[0]], '->', [self.tokens[i] for i in pair[1]] ,' : ', self.tokens[pair[0][0]:pair[1][0]])
            else:
                if true_label == pred_label:
                    rn +=1
                    #print('RIGHT RN', [self.tokens[i] for i in pair[0]], '->', [self.tokens[i] for i in pair[1]] ,' : ', self.tokens[pair[0][0]:pair[1][0]])
                else:
                    wn+=1
                    #print('WRONG WN', [self.tokens[i] for i in pair[0]], '->', [self.tokens[i] for i in pair[1]],' : ', self.tokens[pair[0][0]-2:pair[1][0]+2])
      
        print('rc, wc, rn, wn',rc, wc, rn, wn)
        precision_c = rc / (rc + wc)
        recall_c = rc / (rc + wn)
        f1_c = harmonic_mean([precision_c,recall_c])
        precision_n = rn / (rn + wn)
        recall_n = rn / (rn + wc)
        f1_n = harmonic_mean([precision_n,recall_n])

        blanc_p = (precision_c + precision_n) / 2
        blanc_r = (recall_c + recall_n) / 2
        blanc = (f1_c + f1_n) / 2
        return precision_c, recall_c, f1_c, \
               precision_n, recall_n, f1_n, \
               blanc_p, blanc_r, blanc
    
            
    

def get_entity_chains(docs:list, doc_mentions_spans:list, rules_analyzer):
    docs_chains = {}
    working_doc_start = 0
    for i , doc in enumerate(docs):
        for mention in doc_mentions_spans[i]:
            chain_index = f'{i}:{doc_mentions_spans[i][mention]}'
            start_char , end_char = mention
            mention_span = doc.char_span(start_char, end_char+1)
            if not mention_span:
                dict_idx = {(token.idx,token.idx+len(token.text)-1):token.i for token in doc}
                
                #print("before",mention_span, doc.text[start_char:end_char])
                for token_start_char_index, token_end_char_index in dict_idx:
                    if token_start_char_index <=  mention[0] <= token_end_char_index:
                      
                        start_token = dict_idx[(token_start_char_index,token_end_char_index)]
                    if token_start_char_index <=  mention[1] <= token_end_char_index:
                        j = dict_idx[(token_start_char_index,token_end_char_index)]
                        end_token =  j
                mention_span = doc[start_token: end_token+1]
                #print("after",mention_span, mention_span.text)
                
            mention_head = mention_span.root
            
           #if hasattr(mention_head._.coref_chains, 'temp_potential_referreds') or \
            #           mention_head._.coref_chains.temp_potentially_referring:
            if rules_analyzer.is_independent_noun(mention_head) or rules_analyzer.is_potential_anaphor(mention_head):
                mention_indexes = tuple([mention_head.i + working_doc_start] + \
                                        [sibling.i + working_doc_start for sibling in mention_head._.coref_chains.temp_dependent_siblings])
                if mention_span.end -1 < mention_indexes[-1]:
                    mention_indexes = (mention_head.i + working_doc_start,)
                    
                if chain_index in docs_chains:
                    docs_chains[chain_index].add(mention_indexes)
                else:
                    docs_chains[chain_index] = {mention_indexes}
        working_doc_start += len(doc)
        
    return docs_chains

    
def compare_mentions(docs:list, docs_mentions_spans:list, rules_analyzer):
    anaphors_number = 0
    missing_anaphors = 0
    missed_tokenisation = 0
    for i , doc in enumerate(docs):
        #doc = docs[i]
        for mention in docs_mentions_spans[i]:
            start_char , end_char = mention
            mention_span = doc.char_span(start_char, end_char+1)
            if not mention_span:
                dict_idx = {(token.idx,token.idx+len(token.text)-1):token.i for token in doc}
                missed_tokenisation +=1
                #print("before",mention_span, doc.text[start_char:end_char])
                for token_start_char_index, token_end_char_index in dict_idx:
                    if token_start_char_index <=  mention[0] <= token_end_char_index:
                      
                        start_token = dict_idx[(token_start_char_index,token_end_char_index)]
                        
                    if token_start_char_index <=  mention[1] <= token_end_char_index:
                        j = dict_idx[(token_start_char_index,token_end_char_index)]
                        end_token =  j
                mention_span = doc[start_token: end_token+1]
                #print("after",mention_span, mention_span.text)
                
            mention_head = mention_span.root
            
            if hasattr(mention_head._.coref_chains, 'temp_potential_referreds') or \
                mention_head._.coref_chains.temp_potentially_referring:
                anaphors_number+=1
            else:
                missing_anaphors+=1
                print(mention_head,'|',mention_span)
    
    print('anaphors',anaphors_number)
    print('anaphor proportion', anaphors_number/(anaphors_number+missing_anaphors))
    print("total:",anaphors_number+missing_anaphors, "ndocs",len(docs))
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Calculate several metrics on\
                                     the performance of the model on a corpus')
    parser.add_argument('--corpus_directory', type=str,
                        help='The path to the directory containing the conll test corpus')

    parser.add_argument('--spacy_model', type= str,
                        help='name of the spacy model to use. Ex: fr_core_news_md')
    

    args = parser.parse_args()

    nlp = spacy.load(args.spacy_model)
    rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
    loader = DEMOCRATConllLoader()
    docs, docs_mentions_spans = loader.load(args.corpus_directory, nlp=nlp,
                                           rules_analyzer=rules_analyzer,verbose=False, return_spans=True)
    
    #compare_mentions(docs, docs_mentions_spans, rules_analyzer)

    
    nlp_coreferee = spacy.load('_'.join([args.language, args.spacy_model]))
    nlp_coreferee.add_pipe('coreferee')

    docs_chains = get_entity_chains(docs, docs_mentions_spans,rules_analyzer)
    scorer = Scorer(nlp_coreferee, rules_analyzer)
    scorer.evaluate(docs, docs_chains)
    
    


#https://web.stanford.edu/class/archive/cs/cs224n/cs224n.1162/handouts/cs224n-lecture11-coreference.pdf
#coreference metrics muc ceaf blanc lea
#https://hal.archives-ouvertes.fr/hal-02750222v3/document
#https://www.cs.cmu.edu/~./hovy/paper--
# s/14ACL-coref-scoring-standard.pdf
#https://www.cs.cmu.edu/~hovy/papers/10BLANC-coref-metric.pdf
#python evaluate.py --corpus_directory D:\Utilisateurs\souma\Documents\Projets_Perso\Coreference\corpus\test_french_corpus --language fr --spacy_model core_news_lg

