from spacy.language import Language
from spacy.tokens import Span, Token, Doc

def build_mention(
    heads : list[Token], 
    nlp: Language, 
    extra_detached_dep:list[str] = None
    ) -> Span:
    '''Builds a mention span from the heads of a mention
    the mention is built using spacy's french parse tree
    detached_dep : list of dependencies of the head of the mention to exclude from the span
    '''
    rules_analyzer = nlp.get_pipe("coreferee").annotator.rules_analyzer
    if isinstance(heads, Token):
        heads = [heads]
    doc = heads[0].doc
    mention_pos_before = ("PROPN","NOUN","ADJ","DET","NUM")
    mention_pos_after = ("PROPN","NOUN","ADJ","NUM", "PRON", "PART", "ADV", "VERB", "AUX")
    detached_dep = ["appos","dislocated","advmod","obl:mod",
        "obl:arg","obl:agent","obl","orphan","parataxis"]
    detached_dep = ["appos","dislocated","advmod","obl:mod",
        "obl:arg","obl:agent","obl","orphan","parataxis"]
    if extra_detached_dep is not None:
        detached_dep.extend(extra_detached_dep)
    start = heads[0].left_edge.i
    end = heads[-1].right_edge.i
    siblings = rules_analyzer.get_dependent_siblings(heads[0])
    unincluded_siblings_tokens = set()
    for sibling in siblings:
        if sibling not in heads:
            unincluded_siblings_tokens.update(sibling.subtree)
            unincluded_siblings_tokens.update(doc[sibling.i:end+1])
    #be clauses are parsed differently
    subj_attr_subtree = set()
    cops = [cop for cop in heads[0].children if cop.dep_ == "cop"]
    if cops:
        # We will trim all the tokens that are in the copula or subj attribute
        subjs = [s for s in heads[0].children if s.dep_ == "nsubj"]
        cop_subtree = set(cops[0].subtree)
        subj_subtree = set(subjs[0].subtree) if subjs else set()
        subj_attr_subtree = cop_subtree | subj_subtree
        if cops[0].i < heads[0].i:
            subj_attr_subtree.update(doc[start:cops[0].i])
        if cops[0].i > heads[-1].i:
            subj_attr_subtree.update(doc[cops[0].i:end+1])
        if subjs and subjs[0].i < heads[0].i:
            subj_attr_subtree.update(doc[start:subjs[0].i])
        if subjs and subjs[0].i > heads[-1].i:
            subj_attr_subtree.update(doc[subjs[0].i:end+1])

    detached_tokens = set()
    for c in heads[0].children:
        if (c.dep_ in detached_dep or
        c.dep_ == "acl" and "VerbForm=Inf" in c.morph):
            detached_tokens.update(c.subtree)
            if c.i < heads[0].i:
                detached_tokens.update(doc[start:c.i])
            if c.i > heads[-1].i:
                detached_tokens.update(doc[c.i:end+1])
    # Trims the mentions 
    # left
    for i in range(start, heads[0].i, 1):
        if (
            (doc[i].pos_ not in mention_pos_before and doc[i].lemma_ != "-")
            or doc[i] in subj_attr_subtree|detached_tokens|unincluded_siblings_tokens):
            start = i + 1
        else:
            break
    #right
    for j in range(end, heads[-1].i, -1):
        if (
            (doc[j].pos_ not in mention_pos_after )
            or doc[j] in subj_attr_subtree|detached_tokens|unincluded_siblings_tokens):
            end = j - 1
        else:
            break
    return doc[start:end+1]

def create_mentions(
    doc: Doc, 
    nlp: Language, 
    add_singletons: bool =False, 
    add_coordinated_singletons: bool=False
    ) -> dict[Span, int]:
    '''
    Return a dict with:
        key: all the mention phrases found in a document 
        value : the index of the coreference chain they are part of
    By default only  corefering mentions are included
    set add_singletons = True to include singleton mentions as well
    '''
    rules_analyzer = nlp.get_pipe("coreferee").annotator.rules_analyzer

    def is_mention_head(token):
        return (rules_analyzer.is_independent_noun(token) or
        rules_analyzer.is_potential_anaphor(token))

    indexed_mentions = {}
    for chain in doc._.coref_chains:
        for mention in chain:
            mention_heads = [doc[i] for i in mention.token_indexes]
            mention_phrase = build_mention(mention_heads, nlp)
            #print(mention_phrase, (mention_start, mention_end), chain.index)
            indexed_mentions[mention_phrase] = chain.index
    if add_singletons:
        try:
            last_chain_index = chain.index
        except NameError:
            last_chain_index = 0
        for token in doc:
            if not is_mention_head(token): continue
            mention_phrase = build_mention([token], nlp)
            if mention_phrase not in indexed_mentions:
                last_chain_index +=1
                indexed_mentions[mention_phrase] = last_chain_index
            if not add_coordinated_singletons : continue
            siblings = rules_analyzer.get_dependent_siblings(token)
            if not siblings or not all(is_mention_head(s) for s in siblings):continue
            mention_phrase = build_mention([token]+siblings, nlp)
            if mention_phrase not in indexed_mentions:
                last_chain_index +=1
                indexed_mentions[mention_phrase] = last_chain_index

    return indexed_mentions
            
def make_new_chains(new_mentions):
    new_chains = {}
    for new_mention, chain_index in new_mentions.items():
        if chain_index in new_chains:
            new_chains[chain_index].append(new_mention)
        else:
            new_chains[chain_index] = [new_mention]
    return new_chains
