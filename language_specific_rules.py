# Copyright 2021 msg systems ag
# Modifications Copyright 2021 Valentin-Gabriel Soumah

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
    
class LanguageSpecificRulesAnalyzer(RulesAnalyzer):

    maximum_coreferring_nouns_sentence_referential_distance = 20

    maximum_anaphora_sentence_referential_distance = 5

    random_word = 'albatros'

    dependent_sibling_deps = ('conj',)

    conjunction_deps =  ('cd', 'cc', 'punct')

    adverbial_clause_deps =  ('advcl', 'advmod', 'dep')

    or_lemmas = ('ou')
    
    entity_noun_dictionary = {
        'PER': ['personne', 'homme', 'femme','garçon','fille', 'individu',"type","gars","dame",
                'demoiselle', "garçonnet","fillette", "monsieur","madame","mec","meuf","nana",
                'enfant',"père","mère",'fils',"frère","soeur","oncle","tante","neveu","nièce",
                'cousin','ami', "mari","époux","épouse"],
                
        'LOC': ["lieu","endroit","terrain","secteur","ville","village","zone","site","pays",
                "région","département","commune","quartier","arrondissement","hammeau","continent"],
                
        'ORG': ['entreprise','société','organisation','association','fédération','compagnie',
                'organisme','établissement','institution',"communauté",'groupe','groupement']
    }


    quote_tuples = [("'", "'"), ('"', '"'), ('«', '»'), ('‹', '›'), ('‘', '’'), ('“', '”')]

    term_operator_pos = ('DET', 'ADJ')
    
    term_operator_dep = ('det','amod','nmod','nummod')

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
      
        if (token.lemma_ in {"un", "certains", "certain"} or self.has_morph(token,'NumType','Card')) and \
            (any([child for child in token.head.children if child.dep_ == 'case' and token.i < child.i < token.head.i ]) or \
            any([child for child in token.children if child.pos_ == 'NOUN' and child.dep_ == 'nmod'])): 
            # Une des filles, certains des garçons...
            pass
        elif self.is_quelqun_head(token):
            pass
        elif token.pos_ not in self.noun_pos + ('ADJ','PRON') or \
            token.dep_ in ('fixed','flat:name',"flat:foreign",'amod') or \
           (token.pos_ in ('ADJ','PRON') and not any([child for child in token.children if child.dep_ == 'det'])):
            return False
        return not self.is_token_in_one_of_phrases(token, self.blacklisted_phrases)
        
    def is_potential_anaphor(self, token:Token) -> bool:

        #Ce dernier, cette dernière...
        if token.lemma_ == "dernier" and any([ self.has_morph(child, 'PronType','Dem') for child in token.children]) and \
                token.dep_ not in ('amod','appos'):
            return True
        if self.is_emphatic_reflexive_anaphor(token):
            return True
        if token.lemma_ == 'celui':
            return True
        if not ((token.pos_  == 'PRON' and  \
                (self.has_morph(token, 'Person', '3') or self.has_morph(token, 'PronType','Dem'))) or \
                (token.pos_  == 'ADV' and token.lemma_ in {"ici","là"}) or \
                (token.pos_ == 'DET' and self.has_morph(token, 'Poss','Yes'))):
            return False
        if token.pos_ == 'DET' and self.has_morph(token, 'Poss','Yes') and \
                token.lemma_ in {"mon","ton","notre","votre"}:
            return False
        #When anaphoric , the demonstrative refers almost always to a whole proposition and not a noun phrase
        if token.lemma_ in {"ce","ça","cela"} :
            return False
        
        if token.lemma_ == 'on':
            return False
        #Il y a... 
        if (token.text == 'y' and token.dep_ == 'fixed'):
            return False
        if any([child for child in token.children if child.dep_ == 'fixed' and child.lemma_ == 'y']):
            return False
            
        try :    
            if token.lemma_ == 'là'  and token.nbor(1).lemma_ == 'bas' or \
                (token.nbor(1).lemma_ == '-' and token.nbor(2).lemma_ == 'bas'):
                #Typically deictic
                return False
        except IndexError:pass
        if token.lemma_ in ('-','ci','-ci','-là'):
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
        if token.head.text.lower() == 'fait' or token.head.lemma_ == "faire":
            weather_words = {'beau','mauvais', 'gris', 'chaud', 'froid',
                        'doux', 'frais', 'nuageux', 'orageux', 'frisquet'}
            objects = [child for child in  token.head.children if child.dep_ in \
            {'amod','obj','xcomp','ccomp','dep','det','cop','fixed'}]
            for obj in objects:
                if obj.lemma_ in weather_words:
                    return False
                    
        if self.has_morph(token, 'NumType','Card'):
            return False
        
        return True
        
    def is_emphatic_reflexive_anaphor(self,token:Token) -> bool:
        if token.lemma_ in {'lui-même','elle-même','soi-même'}:
            return True
        try:
            if (token.nbor(1).lemma_ == '-' and token.nbor(2).lemma_ == 'même') and\
                token.lemma_.lower() in {'lui','elle', 'elles','eux','soi'}:
                return True
        except IndexError:
            pass
        return False
        
    def is_quelqun_head(self, token:Token) -> bool:
        #Special case that is analyzed differently in all the models (due to incorrect tokenisation)
        if token.lemma_ == 'un' and  token.i > 0 and token.nbor(-1).lower_ in ("quelqu'",'quelqu','quelque'):
            return True
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
        
        def refers_to_person(token):
            if      token.ent_type_ == 'PER' or self.is_quelqun_head(token) or \
                token.lemma_ in self.entity_noun_dictionary['PER']+self.person_roles \
                or (token.pos_ == self.propn_pos and token.lemma_ in self.male_names+self.female_names):
                return True
            if token.dep_ in ('nsubj', 'nsubj:pass') and \
                token.head.lemma_ in self.verbs_with_personal_subject:
                return True

            
            return False     
        def get_gender_number_info(token):
            
            masc = fem = sing = plur = False
            if self.is_quelqun_head(token):
                sing = masc = fem = True
            elif self.has_morph(token,'Poss','Yes'):
                if self.is_potential_anaphor(token):
                    #the plural morphs of poss determiner don't mark the owner but the owned
                    if token.lemma_ == 'leur':
                        plur = True
                    if token.lemma_ == 'son':
                        sing = True
                    masc = fem = True
            else:
                if self.has_morph(token, 'Number', 'Sing'):
                    sing = True
                if self.has_morph(token, 'Number', 'Plur'):
                    plur = True
                if self.has_morph(token, 'Gender', 'Masc'):
                    masc = True
                if self.has_morph(token, 'Gender', 'Fem'):
                    fem = True
                
                if token.lemma_ in {"ici","là","y",'en'}:
                    masc = fem = sing = plur = True
    
                    
                elif self.is_potential_anaphor(token) :
                    # object pronouns are not well recognized by the  models
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
                    elif token.lower_.startswith('soi'):
                        masc = fem = sing = plur = True
                        
                    if self.has_morph(token, 'Reflex','Yes'):
                        if token.head.pos_ in self.clause_root_pos:
                            sing = self.has_morph(token.head, 'Number', 'Sing')
                            plur = self.has_morph(token.head, 'Number', 'Plur')
                        masc = fem  = True
                        
                elif token.pos_ == 'PROPN':

                    if token.lemma_ in self.male_names:
                        masc = True
                    if token.lemma_ in self.female_names:
                        fem = True
                    if token.lemma_ not in self.male_names+self.female_names:
                        masc = fem  = True
                    if not plur:
                        # proper nouns without plur mark are typically singular
                        sing = True
                    if not directly : 
                        masc = fem = sing = plur = True
                        
 
            if token.pos_ == 'PRON' and token.lower_ == 'le'  and plur:
                #Je les vois
                masc = fem = True
            if not any([sing,plur]):
                sing = plur = True
            if not any([fem,masc]):
                fem = masc = True
            return masc, fem, sing, plur
            
        doc = referring.doc
        referred_root = doc[referred.root_index]
        uncertain = False

        if self.is_quelqun_head(referred_root) and referred.root_index > referring.i:
            #qqn can't be cataphoric
            return 0
        if self.has_morph(referring, 'Pos','Yes') and referring.head == referred_root and \
            referred_root.lemma_ != 'personne':
            #possessive can't be determiner of its own reference
            # * mon moi-même. 
            return 0
        referring_masc, referring_fem, referring_sing, referring_plur = get_gender_number_info(referring)
        # e.g. 'les hommes et les femmes' ... 'ils': 'ils' cannot refer only to
        # 'les hommes' or 'les femmes'
        if len(referred.token_indexes) == 1 and referring_plur  and not referring_sing and \
                self.is_involved_in_non_or_conjunction(referred_root) and not \
                (len(referred_root._.coref_chains.temp_dependent_siblings) > 0 and \
                referring.i > referred.root_index and \
                referring.i < referred_root._.coref_chains.temp_dependent_siblings[-1].i) and \
                referring.lemma_ not in ("dernier","celui","celui-ci","celui-là"):
            return 0

        referred_masc = referred_fem = referred_sing = referred_plur = False
        
        # e.g. 'l'homme et la femme... 'il' : 'il' cannot refer to both
        if len(referred.token_indexes) > 1 and \
                self.is_involved_in_non_or_conjunction(referred_root):
            referred_plur = True
            referred_sing = False
            if not referring_plur:
                return 0
           
        for working_token in (doc[index] for index in referred.token_indexes):
            working_masc, working_fem, working_sing, working_plur = get_gender_number_info(working_token)
            referred_masc = referred_masc or working_masc 
            referred_fem = referred_fem or working_fem 
            referred_sing = referred_sing or working_sing
            referred_plur = referred_plur or working_plur
            
            if referred_masc and not referred_fem and not referring_masc and referring_fem: 
            # "Le Masculin l'emporte" rule :
            # If there is any masc in the dependent referred, the referring has to be masc only
                return 0
        
        if not ( (referred_masc and referring_masc) or (referred_fem and referring_fem) ):
            return 0

        if not( (referred_plur and referring_plur) or (referred_sing and referring_sing) ):
            return 0

        #'ici , là... cannot refer to person. only loc and  possibly orgs
        #y needs more conditions
        if self.is_potential_anaphor(referring) and referring.lemma_ in ('ici','là',"y"):
            if not self.is_independent_noun(referred_root) and referred_root.lemma_ != referring.lemma_:
                return 0
            if refers_to_person(referred_root):# or working_token.lemma_ in self.animal_names:
                return 0
            if referred_root.ent_type_ == 'ORG' and referring.lemma_ != 'y':
                uncertain = True

        
        if directly:
            if self.is_potential_anaphor(referring)>0:
                try :
                    if referring.lemma_ == 'celui-ci' or referring.lemma_.lower() == 'dernier' or \
                        (referring.lemma_.lower() == 'celui' and  \
                        (referring.nbor(1).lemma_.lower() in ('-ci','ci') or \
                        (referring.nbor(1).text == '-' and referring.nbor(2).lemma_.lower() == 'ci'))):
                        #'celui-ci' and 'ce dernier' can only refer to last noun phrase
                        if referring.i ==0 : return 0
                        for previous_token_index in range(referring.i-1, 0, -1):
                            if previous_token_index == referring.i : continue
                            if self.is_independent_noun(doc[previous_token_index]):
                                if previous_token_index not in (referred.token_indexes):
                                    return 0
                                else:
                                    break
                
                
                    if referring.lemma_ == 'celui' and len(doc)>= referring.i+1 and \
                        referring.nbor(1).lemma_.lower() in ('-là','là'):
                        #'celui-là' refers to second to last noun phrase or before (but not too far)
                        noun_phrase_count = 0
                        if referring.i == 0 : return 0
                        for previous_token_index in range(referring.i -1, 0, -1):
                        
                            if self.is_independent_noun(doc[previous_token_index]) and \
                            previous_token_index in referred.token_indexes:
                                if noun_phrase_count<1:
                                    return 0
                            elif self.is_independent_noun(doc[previous_token_index]):
                                noun_phrase_count += 1
                            if noun_phrase_count > 2:
                                return 0
                except IndexError:
                    #doc shorter than the compared index
                    pass
                if referring.lemma_ == 'en':
                    #requires list of mass/countable nouns to be implemented
                    '''
                    if  not referred_plur and referred_root.lemma_ not in self.mass_nouns
                        and referring.dep_ != 'iobj':
                        return 0
                    '''
                    if not referred_plur and (refers_to_person(referred_root) ):
                        uncertain = True
                    
            if self.is_potential_reflexive_pair(referred, referring) and \
                    self.is_reflexive_anaphor(referring) == 0 and \
                    not self.has_morph(referred_root, 'Poss','Yes'):
                # * Les hommes le voyaient. "le" can't refer to "hommes"
                return 0
            
            if self.is_potential_reflexive_pair(referred, referring) == 0 and \
                    (self.is_reflexive_anaphor(referring) == 2) :
                # * Les hommes étaient sûrs qu'ils se trompaient. "se" can't directly refer to "hommes"
                return 0

        referring_governing_sibling = referring
        if referring._.coref_chains.temp_governing_sibling is not None:
            referring_governing_sibling = referring._.coref_chains.temp_governing_sibling
        if referring_governing_sibling.dep_ in ('nsubj:pass','nsubj') and \
                referring_governing_sibling.head.lemma_ in self.verbs_with_personal_subject:
            for working_token in (doc[index] for index in referred.token_indexes):
                if refers_to_person(working_token):
                    return 2
            uncertain = True

        return 1 if uncertain else 2

    def has_operator_child_with_any_morph(self, token:Token, morphs:dict):
        for child in (child for child in token.children if child.pos_ in self.term_operator_pos):
            for morph in morphs:
                if self.has_morph(child, morph, morphs.get(morph)):
                    return True
        return False

    def is_potentially_indefinite(self, token:Token) -> bool:
        return self.has_operator_child_with_any_morph(token, {'Definite':'Ind'}) or \
        self.is_quelqun_head(token)

    def is_potentially_definite(self, token:Token) -> bool:
        return self.has_operator_child_with_any_morph(token, {'Definite':'Def',"PronType":"Dem"})
        
    def is_reflexive_anaphor(self, token:Token) -> int:
        if token.lemma_ == 'personne' and \
            len([det for det in token.children and \
            det.pos_ == 'DET' and self.has_morph('Poss','Yes') and \
            self.has_morph(token,'Person','3')]):
            # sa personne...
            return 2
        if self.is_emphatic_reflexive_anaphor(token):
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
        return head
    
    def is_potential_reflexive_pair(self, referred:Mention, referring:Token) -> bool:
        if referring.pos_ != 'PRON' and not self.is_emphatic_reflexive_anaphor(referring) and \
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
    
    '''Methods from the parent class that need to be overridden because 
    some cases are not suitable for the french parse tree
    '''
    def is_potential_cataphoric_pair(self, referred:Mention, referring:Token) -> bool:
        """ Checks whether *referring* can refer cataphorically to *referred*, i.e.
            where *referring* precedes *referred* in the text. That *referring* precedes
            *referred* is not itself checked by the method.
        """
        '''
            Overrides the method of the parent class which is not suitable for be clause in french
        '''
        
        doc = referring.doc
        referred_root = doc[referred.root_index]

        if referred_root.sent != referring.sent:
            return False
        if self.is_potential_anaphor(referred_root):
            return False

        referred_verb_ancestors = []
        # Find the ancestors of the referent that are verbs, stopping anywhere where there
        # is conjunction between verbs
        for ancestor in referred_root.ancestors:
            if ancestor.pos_ in self.clause_root_pos or \
                any([child for child in ancestor.children if child.dep_ =='cop']):
                referred_verb_ancestors.append(ancestor)
            if ancestor.dep_ in self.dependent_sibling_deps:
                break

        # Loop through the ancestors of the referring pronoun that are verbs,  that are not
        # within the first list and that have an adverbial clause dependency label
        referring_inclusive_ancestors = [referring]
        referring_inclusive_ancestors.extend(referring.ancestors)
        if len([1 for ancestor in referring_inclusive_ancestors if ancestor.dep_ in \
                self.adverbial_clause_deps]) == 0:
            return False
        for referring_verb_ancestor in (t for t in
                referring_inclusive_ancestors if  t not in
                referred_verb_ancestors and t.pos_ in self.clause_root_pos+self.noun_pos+('ADJ',) ):
            # If one of the elements of the second list has one of the elements of the first list
            # within its ancestors, we have subordination and cataphora is permissible
            if len([t for t in referring_verb_ancestor.ancestors
                    if t in referred_verb_ancestors]) > 0:
                return True
        return False
        
    def is_potentially_referring_back_noun(self, token:Token) -> bool:

        if self.is_potentially_definite(token) and len([1 for c in token.children if
                c.pos_ not in self.term_operator_pos and c.dep_ not in self.conjunction_deps
                and c.dep_ not in self.dependent_sibling_deps and c.dep_ not in self.term_operator_dep]) == 0:
            return True

        return token._.coref_chains.temp_governing_sibling is not None and len([1 for c in
                token.children if c.dep_ not in self.conjunction_deps and c.dep_ not in
                self.dependent_sibling_deps]) == 0 and \
                self.is_potentially_referring_back_noun(token._.coref_chains.temp_governing_sibling)
                
    def is_potential_coreferring_noun_pair(self, referred:Token, referring:Token) -> bool:
        """ Returns *True* if *referred* and *referring* are potentially coreferring nouns.
            The method presumes that *is_independent_noun(token)* has
            already returned *True* for both *referred* and *referring* and that
            *referred* precedes *referring* within the document.
        """
        def get_sent_index(token:Token)->int:
            for i,sent in enumerate(token.doc.sents):
                if token.sent == sent:
                    return i
        if len(referred.text) == 1 and len(referring.text) == 1:
            return False # get rid of copyright signs etc.

        if referred.pos_ not in self.noun_pos or referring.pos_ not in self.noun_pos:
            return False

        if referring in referred._.coref_chains.temp_dependent_siblings:
            return False

        if referring._.coref_chains.temp_governing_sibling is not None and \
                referring._.coref_chains.temp_governing_sibling == \
                referred._.coref_chains.temp_governing_sibling:
            return False

        # If *referred* and *referring* are names that potentially consist of several words,
        # the text of *referring* must correspond to the end of the text of *referred*
        # e.g. 'Richard Paul Hudson' -> 'Hudson'
        referred_propn_subtree = self.get_propn_subtree(referred)
        if referring in referred_propn_subtree:
            return False
        if len(referred_propn_subtree) > 0:
            referring_propn_subtree = self.get_propn_subtree(referring)
            if len(referring_propn_subtree) > 0 and \
                    ' '.join(t.text for t in referred_propn_subtree).endswith(
                    ' '.join(t.text for t in referring_propn_subtree)):
                return True
            if len(referring_propn_subtree) > 0 and \
                    ' '.join(t.lemma_.lower() for t in referred_propn_subtree).endswith(
                    ' '.join(t.lemma_.lower() for t in referring_propn_subtree)):
                return True

        # e.g. 'Peugeot' -> 'l'entreprise'
        new_reverse_entity_noun_dictionary = {noun:'PER' for noun in self.person_roles}|\
            self.reverse_entity_noun_dictionary
        if referring.lemma_.lower() in new_reverse_entity_noun_dictionary \
                and referred.pos_ in self.propn_pos and referred.ent_type_ == \
                new_reverse_entity_noun_dictionary[referring.lemma_.lower()] and \
                self.is_potentially_definite(referring):
            return True
        
            
        if not self.is_potentially_referring_back_noun(referring):
            return False
        if not self.is_potentially_introducing_noun(referred) and not \
                self.is_potentially_referring_back_noun(referred):
            return False
        if referred.lemma_ == referring.lemma_ and \
                referred.morph.get(self.number_morph_key) == \
                referring.morph.get(self.number_morph_key):
            return True
        return False
