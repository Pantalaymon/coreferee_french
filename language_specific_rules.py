# Copyright 2021 msg systems ag

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from string import punctuation
from spacy.tokens import Token
from ...rules import RulesAnalyzer
from ...data_model import Mention

'''
acl     |        clausal modifier of noun (adjectival clause)
acl:relcl       |        None
advcl   |        adverbial clause modifier
advmod  |        adverbial modifier
amod    |        adjectival modifier
appos   |        appositional modifier
aux:pass        |        None
aux:tense       |        None
case    |        case marking
cc      |        coordinating conjunction
ccomp   |        clausal complement
conj    |        conjunct
cop     |        copula
dep     |        unclassified dependent
det     |        determiner
expl:comp       |        None
expl:pass       |        None
expl:subj       |        None
fixed   |        fixed multiword expression
flat:foreign    |        None
flat:name       |        None
iobj    |        indirect object
mark    |        marker
nmod    |        modifier of nominal
nsubj   |        nominal subject
nsubj:pass      |        None
nummod  |        numeric modifier
obj     |        object
obl:agent       |        None
obl:arg         |        None
obl:mod         |        None
parataxis       |        parataxis
punct   |        punctuation
vocative        |        vocative
xcomp   |        open clausal complement
'''
class LanguageSpecificRulesAnalyzer(RulesAnalyzer):

    random_word = 'albatros'

    dependent_sibling_deps = ('conj','appos',)

    conjunction_deps =  ('cd', 'cc', 'punct')

    adverbial_clause_deps =  ('advcl', 'advmod')

    or_lemmas = ('ou')

    entity_noun_dictionary = {
        'PER': ['personne', 'homme', 'femme','garçon','fille', 'individu'],
        'LOC': ["lieu","endroit","terrain","secteur","ville"],
        'ORG': ['entreprise','société','organisation','association','fédération']
    }

    quote_tuples = [("'", "'"), ('"', '"'), ('«', '»'), ('‹', '›'), ('‘', '’'), ('“', '”')]

    term_operator_pos = ('DET', 'ADJ')

    clause_root_pos = ('VERB', 'AUX')

    def get_dependent_siblings(self, token:Token) -> list:

        def add_siblings_recursively(recursed_token:Token, visited_set:set) -> None:
            visited_set.add(recursed_token)
            siblings_set = set()
            if recursed_token.lemma_ in self.or_lemmas:
                token._.coref_chains.temp_has_or_coordination = True
            if recursed_token.dep_ in self.dependent_sibling_deps:
                siblings_set.add(recursed_token)
            for child in (child for child in recursed_token.children if child not in visited_set and
                    (child.dep_ in self.dependent_sibling_deps or child.dep_ in
                    self.conjunction_deps)):
                child_siblings_set = add_siblings_recursively(child, visited_set)
                siblings_set |= child_siblings_set
            return siblings_set

        if token.dep_ not in self.conjunction_deps and token.dep_ not in \
                self.dependent_sibling_deps:
            siblings_set = add_siblings_recursively(token, set())
        else:
            siblings_set = set()
        return sorted(siblings_set)

    def is_independent_noun(self, token:Token) -> bool:
        # Une des filles, certains des garçons...
        if (token.lemma_ in {"un", "certains", "certain"} or self.has_morph(token,'NumType','Card')) and \
            len([child for child in token.children if child.pos_ == 'NOUN'])>0: 
            pass
        elif token.pos_ not in self.noun_pos + ('ADJ',) or token.dep_ in ('fixed') or \
           (token.dep_ == 'ADJ' and len([child for child in token.children if child.pos_ == 'DET'])<1):
            return False
        return not self.is_token_in_one_of_phrases(token, self.blacklisted_phrases)
        
    def is_potential_anaphor(self, token:Token) -> bool:

        #Ce dernier, cette dernière...
        if token.lemma_ == "dernier" and any([ self.has_morph(child, 'PronType','Dem') for child in token.children]) and \
                token.head.pos_ not in self.noun_pos:
            return True
        if token.lemma_ in ('lui-même', 'elle-même'):
            return True
        if not ((token.pos_  == 'PRON' and  self.has_morph(token, 'Person', '3')) or \
                (token.pos_  == 'ADV' and token.lemma_ in {"ici","là"}) or \
                (token.pos_ == 'DET' and self.has_morph(token, 'Poss','Yes'))):
            return False
        
        if token.pos_ == 'DET' and self.has_morph(token, 'Poss','Yes') and \
                token.lemma_ in {"mon","ton","notre","votre"}:
            return False
        #When anaphoric , the demonstrative refers almost always to a whole proposition and not a noun phrase
        if token.lemma_ in {"ce","ça","cela"} or self.has_morph(token, 'PronType','Dem'):
            return False
        
        if token.lemma_ == 'on':
            return False
        #Il y a... 
        if (token.text == 'y' and token.dep_ == 'fixed'):
            return False
            
        #Avalent Il. In case some are not marked as expletive
        if token.dep_ != self.root_dep and token.head.pos_ in ('AUX', 'VERB') and len(
                [child for child in token.head.subtree if child.lemma_ in self.avalent_verbs]) > 0:
            return False
            
        #impersonal constructions
        if token.dep_ in {'expl:comp','expl:pass','expl:subj'} and token.lemma_ != 'en' and \
            not self.has_morph(token,'Reflex','Yes'):
            return False
        
        
        #Il fait froid/chaud/soleil/beau
        if token.head.text.lower() == 'fait' or token.lemma_ == "faire":
            weather_words = {'beau','mauvais', 'gris', 'chaud', 'froid',
                        'doux', 'frais', 'nuageux', 'orageux', 'frisquet'}
            objects = [child for child in  token.head.children if child.dep_ in {'amod','obj'}]
            for obj in objects:
                if obj.lemma_ in weather_words:
                    return False
                    
        if self.has_morph(token, 'NumType','Card'):
            return False
        
        return True
        
    def is_emphatic_reflexive(self,token:Token) -> bool:
        if token.lemma_ in {'lui-même','elle-même'}:
            return True
        if len(token.doc) >= ((token.i)+2) and \
            (token.nbor(1).lemma_ == '-' and token.nbor(2).lemma_ == 'même'):
            return True

        
        # AJOUTER CONDITION pos_ == PRON
        return False
        
    def is_potential_anaphoric_pair(self, referred:Mention, referring:Token, directly:bool) -> bool:

        def get_governing_verb(token:Token) -> Token:
            for ancestor in token.ancestors:
                if ancestor.pos_ in ('VERB', 'AUX'):
                    return ancestor
            return None

        def lemma_ends_with_word_in_list(token, word_list):
            lower_lemma = token.lemma_.lower()
            for word in word_list:
                if word.lower().endswith(lower_lemma):
                    return True
            return False
        
        def get_closest_common_ancestor(token1,token2) -> Token:
            for ancestor1 in token1.ancestors:
                if ancestor1 in token2.ancestors:
                    return ancestor1
            return None
                    
        def get_gender_number_info(token):
            masc = fem = sing = plur = False
            if self.has_morph(token, 'Number', 'Sing'):
                sing = True
            if self.has_morph(token, 'Number', 'Plur'):
                plur = True
            if self.has_morph(token, 'Gender', 'Masc'):
                masc = True
            if self.has_morph(token, 'Gender', 'Fem'):
                fem = True
            if token.pos_ == 'PROPN':
                if token.lemma_ in self.male_names:
                    masc = True
                elif token.lemma_ in self.female_names:
                    fem = True
                else:
                    masc = fem  = True
                    
            if token.lemma_ in {"ici","là","y",'en'}:
                masc = fem = sing = plur = True

            if token.pos_ == 'PROPN' and not directly:
                # common noun and proper noun in same chain may have different genders
                masc = fem = sing = plur = True
            if self.is_potential_anaphor(token) and self.has_morph(token, 'Reflex','Yes'):
                masc = fem = sing = plur = True
                
         
            if self.is_emphatic_reflexive(token) :
                # Those reflexives are not well recognized by the smaller models
                no_info = not any([masc,fem,sing,plur ])
                if token.lower_.startswith('lui'):
                    masc = True
                    sing = True
                elif token.lower_.startswith('eux'):
                    masc = True
                    plur = True
                elif token.lower_.startswith('elles'):
                    fem = True
                    plur = True
                elif token.lower_.startswith('elle') :
                    fem = True
                    sing = True
                    
                elif no_info :
                    masc = fem = sing = plur = True
                
            if self.is_potential_anaphor(token) and \
                token.pos_ == 'PRON' and plur and \
                not masc and not fem:
                #Les, leur can be both masc and fem
                masc = fem = True
                    
            return masc, fem, sing, plur
            
        doc = referring.doc
        referred_root = doc[referred.root_index]
        DEBUG_PHRASE =  'L\'opinion de mon amie sur elle-même était exagérée.'
        #DEBUG_PHRASE =  'Pierre et Marie les voyaient lui et elle.'
        referring_masc, referring_fem, referring_sing, referring_plur = \
            get_gender_number_info(referring)
        if doc.text == DEBUG_PHRASE:
            print("DEBUG alpha:",[referred_root,referred.token_indexes,'|',referring, \
                self.is_potential_reflexive_pair(referred, referring), self.is_reflexive_anaphor(referring) ])

        # e.g. 'les hommes et les femmes' ... 'ils': 'ils' cannot refer only to
        # 'les hommes' or 'les femmes'
        if len(referred.token_indexes) == 1 and referring_plur  and \
                not referring_sing and \
                self.is_involved_in_non_or_conjunction(referred_root) and not \
                (len(referred_root._.coref_chains.temp_dependent_siblings) > 0 and
                referring.i > referred.root_index and
                referring.i < referred_root._.coref_chains.temp_dependent_siblings[-1].i):
            if doc.text == DEBUG_PHRASE:
                print("DEBUG 0:",[referred_root,referred.token_indexes,'|', referring, referring_plur, referring_sing])

            return 0

        referred_masc = referred_fem = referred_sing = referred_plur = False
        
        # e.g. 'l'homme et la femme... 'il' : 'il' cannot refer to both
        if len(referred.token_indexes) > 1 and \
                self.is_involved_in_non_or_conjunction(referred_root):
            referred_plur = True
            referred_sing = False
            if not referring_plur:
                if doc.text == DEBUG_PHRASE:
                    print("DEBUG 1:",[referred_root,referred.token_indexes,referred_plur, referred_sing ,'|', referring_plur, referring_sing])

                return 0
           
        for working_token in (doc[index] for index in referred.token_indexes):
            working_masc, working_fem, working_sing, working_plur = get_gender_number_info(working_token)
            referred_masc = referred_masc or working_masc 
            referred_fem = referred_fem or working_fem 
            if referred_masc and not referred_fem and not referring_masc and referring_fem: 
            # "Le Masculin l'emporte" rule :
            # If there is any masc in the dependent referred, the referring has to be masc only
                if doc.text == DEBUG_PHRASE:
                    print("DEBUG 2:",[referred_root,referred.token_indexes,referred_plur, referred_sing ,'|', referring_plur, referring_sing])

                return 0
            referred_sing = referred_sing or working_sing
            referred_plur = referred_plur or working_plur
        
        if not ( (referred_masc and referring_masc) or (referred_fem and referring_fem) ):
            if doc.text == DEBUG_PHRASE:
                print("DEBUG 3:",[referred_root,referred.token_indexes,referred_plur, referred_sing ,'|', referring_plur, referring_sing])

            return 0

        if not( (referred_plur and referring_plur) or (referred_sing and referring_sing) ):
            if doc.text == DEBUG_PHRASE:
                print("DEBUG 4:",[referred_root,referred.token_indexes,referred_plur, referred_sing ,'|', referring, referring_plur, referring_sing])

            return 0
        '''    
        if (referred_masc != referring_masc) or (referred_fem != referring_fem) \
                 or (referred_plur != referring_plur):
            return 0
        '''

        #'ici , là... cannot refer to person. only loc and  possibly orgs
        if self.is_potential_anaphor(referring) and referring.lemma_ in ('ici','là','y'):
            for working_token in (doc[index] for index in referred.token_indexes):
                if working_token.lemma_ in self.male_names or \
                        working_token.lemma_ in self.female_names or \
                        working_token.ent_type_ in ('PER') or \
                        working_token.lemma_ in self.person_words or \
                        working_token.lemma_ in self.animal_names :
                    if doc.text == DEBUG_PHRASE:
                        print("DEBUG 6:",[referred_root,referred_plur, referred_sing ,'|', referring_plur, referring_sing])
       
                    return 0
                if working_token.ent_type_ in ('ORG') and referring.lemma_ != 'y':
                    if doc.text == DEBUG_PHRASE:
                        print("DEBUG 7:",[referred_root,referred_plur, referred_sing ,'|', referring_plur, referring_sing])
       
                    return 1

        
        if directly:
            #en , du chocolat nom avec préposition
            # Ce dernier, celui-là ... etc
            # incompatible genders/plur
            if self.is_potential_anaphor(referring)>0:
                if referring.lemma_ == 'celui-ci' or referring.lemma_.lower() == 'dernier' or \
                    (referring.lemma_.lower() == 'celui' and referring.nbor(1).lemma_.lower() in ('-ci','ci')) or \
                    (referring.nbor(1).text == '-' and referring.nbor(2).lemma_.lower() == 'ci'):
                    #'celui-ci' and 'ce dernier' can only refer to last noun phrase
                    for previous_token_index in range(referring.i, 0, -1):
                        if self.is_independent_noun(doc[previous_token_index]):
                            if previous_token_index not in (referred.token_indexes):
                                return 0
                            else:
                                break
                if referring.lemma_ == 'celui' and referring.nbor(1).lemma_.lower() == '-là':
                    #'celui-là' refers to second to last noun phrase or before (but not too far)
                    noun_phrase_count = 0
                    for previous_token_index in range(referring.i, 0, -1):
                        if self.is_independent_noun(doc[previous_token_index]) and \
                        previous_token_index in referred.token_indexes:
                            if noun_phrase_count<1:
                                return 0
                        elif self.is_independent_noun(doc[previous_token_index]):
                            noun_phrase_count += 1
                        if noun_phrase_count > 2:
                            return 0
                                 
                if referring.lemma_ == 'en':
                    if not referred_plur and doc[referred.token_indexes[0]].pos_ != 'ADP':
                        return 0
                        

            if self.is_potential_reflexive_pair(referred, referring) and \
                    self.is_reflexive_anaphor(referring) == 0:
                # * Les hommes le voyaient. "le" can't refer to "hommes"
                return 0
            
            if self.is_potential_reflexive_pair(referred, referring) == 0 and \
                    (self.is_reflexive_anaphor(referring) == 2) :
                # * Les hommes étaient sûrs qu'ils se trompaient. "se" can't directly refer to "hommes"
                   
                try:
                    if self.get_closest_common_ancestor(referred_root,referring).pos_ != "NOUN":
                        return 0
                        # But can be when they are in the same noun phrase 
                except AttributeError:
                        # no common ancestor
                    return 0
            
            if referred_root.dep_ in ('nk') and referred_root.head.pos_ == 'ADP' and \
                    self.is_reflexive_anaphor(referring) == 0:
                referred_governing_verb = get_governing_verb(referred_root)
                if referred_governing_verb is not None and referred_governing_verb == \
                        get_governing_verb(referring):
                    # In welchem Raum ist er?
                    return 0



        referring_governing_sibling = referring
        if referring._.coref_chains.temp_governing_sibling is not None:
            referring_governing_sibling = referring._.coref_chains.temp_governing_sibling
        if referring_governing_sibling.dep_ in ('nsubj', 'nsubj:pass') and \
                referring_governing_sibling.head.lemma_ in self.verbs_with_personal_subject:
            for working_token in (doc[index] for index in referred.token_indexes):
                if working_token.pos_ == self.propn_pos or working_token.ent_type_ == 'PER':
                    return 2
            return 1

        return 2

    def has_operator_child_with_lemma_beginning(self, token:Token, lemma_beginnings:tuple):
        for child in (child for child in token.children if child.pos_ in self.term_operator_pos):
            for lemma_beginning in lemma_beginnings:
                if child.lemma_.lower().startswith(lemma_beginning):
                    return True
        return False
    
    def has_operator_child_with_morphs(self, token:Token, morphs:dict):
        for child in (child for child in token.children if child.pos_ in self.term_operator_pos):
            for morph in morphs:
                if self.has_morph(child, morph, morphs.get(morph)):
                    return True
        return False

    def is_potentially_indefinite(self, token:Token) -> bool:
        return self.has_operator_child_with_morphs(token, {'Definite':'Ind'})

    def is_potentially_definite(self, token:Token) -> bool:
        return self.has_operator_child_with_morphs(token, {'Definite':'Def',"PronType":"Dem"})
        
    def is_reflexive_anaphor(self, token:Token) -> int:
        # AJOUTER sa personne
        if token.lemma_ == 'personne' and \
            len([det for det in token.children and \
            det.pos_ == 'DET' and self.has_morph('Poss','Yes') and \
            self.has_morph(token,'Person','3')]):
            return 2
        if self.is_emphatic_reflexive(token):
            return 2
        if self.has_morph(token, 'Reflex', 'Yes') :
            if self.has_morph(token,'Person','3') :
                return 2
  
        return 0

    @staticmethod
    def get_ancestor_spanning_any_preposition(token:Token) -> Token:
        if token.dep_ == 'ROOT':
            return None
        head = token.head
        '''
        if token.dep_ == 'nmod':
            head = token.head
            
            #if child.pos_ == 'ADP' and token.dep_ == 'case':
            if head.dep_ == 'ROOT':
                return None

            return head
        '''
        return head
    
    def is_potential_reflexive_pair(self, referred:Mention, referring:Token) -> bool:
        # RAJOUTER sa personne
        if referring.pos_ != 'PRON' and not self.is_emphatic_reflexive(referring) and \
            referring.lemma_ != 'personne':
            return False

        referred_root = referring.doc[referred.root_index]

        if referred_root._.coref_chains.temp_governing_sibling is not None:
            referred_root = referred_root._.coref_chains.temp_governing_sibling

        if referring._.coref_chains.temp_governing_sibling is not None:
            referring = referring._.coref_chains.temp_governing_sibling

        if referred_root.dep_ in ('nsubj', 'nsubj:pass'):
            for referring_ancestor in referring.ancestors:
                # Loop up through the verb ancestors of the pronoun

                if referred_root in referring_ancestor.children:
                    return True

                # Relative clauses
                if referring_ancestor.pos_ in ('VERB', 'AUX') and \
                        referring_ancestor.dep_ in ('acl:relcl','acl') and \
                        (referring_ancestor.head == referred_root or \
                        referring_ancestor.head.i in referred.token_indexes):
                    return True

                # The ancestor has its own subject, so stop here
                if len([t for t in referring_ancestor.children if t.dep_ in ('nsubj', 'nsubj:pass')
                        and t != referred_root]) > 0:
                    return False
            return False

        if referring.i < referred_root.i:
            return False
        

        referring_ancestor = self.get_ancestor_spanning_any_preposition(referring)
        referred_ancestor = referred_root.head
        return referring_ancestor is not None and (referring_ancestor == referred_ancestor
            or referring_ancestor.i in referred.token_indexes)
            
'''
POS=NUM         |        numeral
POS=ADV         |        adverb
POS=PROPN       |        proper noun
VerbForm=Part   |        None
Person=3        |        None
POS=SCONJ       |        subordinating conjunction
VerbForm=Inf    |        None
Gender=Masc     |        None
POS=SYM         |        symbol
Definite=Def    |        None
Polarity=Neg    |        None
Reflex=Yes      |        None
POS=X   |        other
POS=PUNCT       |        punctuation
Person=2        |        None
PronType=Art    |        None
Tense=Imp       |        None
Mood=Sub        |        None
Mood=Cnd        |        None
Voice=Pass      |        None
Poss=Yes        |        None
PronType=Rel    |        None
POS=ADJ         |        adjective
POS=NOUN        |        noun
Tense=Fut       |        None
POS=CCONJ       |        coordinating conjunction
Tense=Past      |        None
POS=ADP         |        adposition
Tense=Pres      |        None
PronType=Prs    |        None
PronType=Dem    |        None
Definite=Ind    |        None
VerbForm=Fin    |        None
POS=PART        |        particle
NumType=Card    |        None
Mood=Ind        |        None
PronType=Int    |        None
Mood=Imp        |        None
POS=INTJ        |        interjection
POS=AUX         |        auxiliary
Number=Plur     |        None
POS=DET         |        determiner
NumType=Ord     |        None
Person=1        |        None
Number=Sing     |        None
Gender=Fem      |        None
POS=PRON        |        pronoun
POS=VERB        |        verb
'''
