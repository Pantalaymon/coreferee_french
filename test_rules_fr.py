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

import unittest
import spacy
import coreferee
from coreferee.rules import RulesAnalyzerFactory
from coreferee.test_utils import get_nlps
from coreferee.data_model import Mention

class FrenchRulesTest(unittest.TestCase):

    def setUp(self):

        self.nlps = get_nlps('fr', add_coreferee=False)
        self.rules_analyzers = [RulesAnalyzerFactory.get_rules_analyzer(nlp) for
            nlp in self.nlps]

    def all_nlps(self, func):
        for nlp in self.nlps:
            func(nlp)

    def compare_get_dependent_sibling_info(self, doc_text, index, expected_dependent_siblings,
        expected_governing_sibling, expected_has_or_coordination):

        def func(nlp):

            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            self.assertEqual(expected_dependent_siblings, str(
                doc[index]._.coref_chains.temp_dependent_siblings), nlp.meta['name'])
            for sibling in (sibling for sibling in
                    doc[index]._.coref_chains.temp_dependent_siblings if sibling.i != index):
                self.assertEqual(doc[index], sibling._.coref_chains.temp_governing_sibling,
                    nlp.meta['name'])
            if expected_governing_sibling is None:
                self.assertEqual(None, doc[index]._.coref_chains.temp_governing_sibling,
                    nlp.meta['name'])
            else:
                self.assertEqual(doc[expected_governing_sibling],
                    doc[index]._.coref_chains.temp_governing_sibling, nlp.meta['name'])
            self.assertEqual(expected_has_or_coordination,
                doc[index]._.coref_chains.temp_has_or_coordination, nlp.meta['name'])

        self.all_nlps(func)

    def test_get_dependent_sibling_info_no_conjunction(self):
        self.compare_get_dependent_sibling_info('Richard rentra à la maison',
            0, '[]', None, False)

    def test_get_dependent_sibling_info_two_member_conjunction_phrase_and(self):
        self.compare_get_dependent_sibling_info('Richard et Christine rentrent à la maison',
            0,'[Christine]', None, False)

    def test_get_governing_sibling_info_two_member_conjunction_phrase_and(self):
        self.compare_get_dependent_sibling_info('Richard et Christine rentrent à la maison', 2,
            '[]', 0, False)

    def test_get_dependent_sibling_info_two_member_conjunction_phrase_or(self):
        self.compare_get_dependent_sibling_info('Richard ou Christine rentre à la maison', 0,
            '[Christine]', None, True)

    def test_get_dependent_sibling_info_three_member_conjunction_phrase_with_comma_and(self):
        self.compare_get_dependent_sibling_info('Carol, Richard et Ralf avaient une réunion', 0,
            '[Richard, Ralf]', None, False)

    def test_get_dependent_sibling_info_three_member_conjunction_phrase_with_comma_or(self):
        self.compare_get_dependent_sibling_info('Carol, Richard ou Ralf avait une réunion', 0,
            '[Richard, Ralf]', None, True)

    def test_get_dependent_sibling_info_three_member_conjunction_phrase_with_and(self):
        self.compare_get_dependent_sibling_info(
            'Il y avait une réunion avec Carol et Ralf et Richard', 6,
            '[Ralf, Richard]', None, False)

    def test_get_dependent_sibling_info_three_member_conjunction_phrase_with_or(self):
        self.compare_get_dependent_sibling_info(
            'Une réunion avec Carol ou Ralf ou Richard avait lieu', 3,
            '[Ralf, Richard]', None, True)

    def test_get_dependent_sibling_info_three_member_conjunction_phrase_with_and_and_or(self):
        self.compare_get_dependent_sibling_info(
            'Il y avait une réunion avec Carol ou Ralf et Richard', 6,
            '[Ralf, Richard]', None, True)

    def test_get_dependent_sibling_info_conjunction_itself(self):
        self.compare_get_dependent_sibling_info(
            'Il y avait une réunion avec Carol et Ralf et Richard', 7,
            '[]', None, False)

    def test_get_dependent_sibling_info_dependent_sibling(self):
        self.compare_get_dependent_sibling_info(
            'Il y avait une réunion avec Carol et Ralf et Richard', 8,
            '[]', 6, False)
            

    def compare_independent_noun(self, doc_text, expected_per_indexes, *,
        excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            per_indexes = [token.i for token in doc if
                    rules_analyzer.is_independent_noun(token)]
            self.assertEqual(expected_per_indexes, per_indexes, nlp.meta['name'])

        self.all_nlps(func)

    def test_independent_noun_simple(self):
        self.compare_independent_noun('Ils ont regardé les grands lions',
            [5])

    def test_independent_noun_conjunction(self):
        self.compare_independent_noun(
            'Ils ont regardé les grands lions, les tigres et les éléphants',
            [5, 8, 11])
            
    def test_multi_word_determiner(self):
        self.compare_independent_noun(
            'Il va au cinéma. C\'est un fan absolu du nouveau film',
            [3, 8, 12])
    def test_substituting_indefinite_pronoun(self):
        self.compare_independent_noun(
            'Un des garçons est parti',
            [0, 2])

    def test_independent_noun_numerals(self):
        self.compare_independent_noun('Une des deux personnes voit deux des trois personnes',
            [0, 3, 5, 8], excluded_nlps='core_news_sm')

    def test_blacklisted(self):
        self.compare_independent_noun(
            'Au fait j\'aimerais avoir un animal. Un chien par exemple',
            [6, 9])

    def test_blacklisted_control(self):
        self.compare_independent_noun(
            'C\'est un mauvais exemple',
            [4], excluded_nlps='core_news_sm')

    def test_proper_noun_component(self):
        self.compare_independent_noun(
            "J'admire Jacques Chirac.",
            [2])
            
    def test_possessive_pronouns(self):
        self.compare_independent_noun("C'est le tien. Non c'est la mienne.",
            [3, 9])
            

    def test_punctuation(self):
        self.compare_independent_noun(
            '[ Oiseau ]',
            [1], excluded_nlps=['core_news_sm'])
            
    def test_substantive_adjective(self):
        self.compare_independent_noun(
            'Le troisième est arrivé. L\'autre n\'est pas là',
            [1, 6], excluded_nlps=['core_news_sm'])
        self.compare_independent_noun(
            'Les premiers ont pris un petit chat. Le petit est mignon.',
            [1, 6, 9])
          
            
    def compare_potential_anaphor(self, doc_text, expected_per_indexes, *,
        excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            per_indexes = [token.i for token in doc if
                    rules_analyzer.is_potential_anaphor(token)]
            self.assertEqual(expected_per_indexes, per_indexes, nlp.meta['name'])

        self.all_nlps(func)

    def test_third_person_pronouns(self):
        self.compare_potential_anaphor('Elle est sortie pour voir sa voiture',
            [0,5])

    def test_first_and_second_person_pronouns(self):
        self.compare_potential_anaphor('Je sais que tu le connais',
            [4], excluded_nlps=['core_news_md', 'core_news_sm'])
            
    def test_pronouns(self):
        self.compare_potential_anaphor('On y va demain',
            [1], excluded_nlps=['core_news_sm'])        

    def test_demonstrative_pronouns(self):
        self.compare_potential_anaphor(
            'C\'est des oiseaux dont je parlais. Ceux-ci sont plus gros que ceux-là',
            [8, 15])
            
    def test_demonstratives_pronouns_2(self):
        self.compare_potential_anaphor(
            'Je choisis celui qui est vert. Vous prenez celles qui sont jaunes.',
            [2, 9])
                  
    def test_demonstrative_pronoun_neuter(self):
        self.compare_independent_noun(
            'Ca suffit. Cela dépend. C\'est ça.',
            [], excluded_nlps=['core_news_sm'])
    

    def test_location_proadverbs(self):
        self.compare_potential_anaphor(
            'Je suis ici. Tu es là. Nous venons de là-bas.',
            [2, 6])

    def test_explicit_anaphor(self):
        self.compare_potential_anaphor(
            'Ce dernier vient de rejoindre Camille. Cette dernière est en retard',
            [1, 8], excluded_nlps=['core_news_sm']) 
            
    def test_relative_pronouns(self):
        self.compare_potential_anaphor(
            'La maison dont tu m\'as parlé est à côté de l\'immeuble que j\'ai vu',
            [], excluded_nlps=["core_news_sm"]) #a finir        


    def test_pleonastic_il_1(self):
        self.compare_potential_anaphor(
            'Il pleuvait. Il fait très beau. Il a fait froid. Il fit chaud. Il avait fait frisquet.',
            [], excluded_nlps=['core_news_sm'])
            
    def test_pleonastic_il_2(self):
        self.compare_potential_anaphor(
            'Il faut bien manger. Il vaut mieux y aller. Il y a deux fleurs. ',
            [8])
            
    def test_pleonastic_il_3(self):
        self.compare_potential_anaphor(
            'Il pleut très fort. Il neige encore. Il grêle.',
            [], excluded_nlps=['core_news_sm'])
            
    def test_pleonastic_il_4(self):
        self.compare_potential_anaphor(
            'Il est vrai que ce jeu est dur. Il en existe trois sortes. Il manque deux pièces.',
            [10], excluded_nlps=['core_news_sm','core_news_md'])
            
    def test_possessive_determiners(self):
        self.compare_potential_anaphor('Ma maison, ta maison, sa maison, leur maison.',
            [6, 9])
        
       
    '''
    No model analyses those sentences properly
    def test_pleonastic_il_interrogative(self):
        self.compare_potential_anaphor('Que faut-il faire ? Vaut-il mieux abandonner ?', [])
    '''
    def compare_potentially_indefinite(self, doc_text, index, expected_truth, *,
            excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            self.assertEqual(expected_truth,
                rules_analyzer.is_potentially_indefinite(doc[index]),
                nlp.meta['name'])

        self.all_nlps(func)

    def test_potentially_indefinite_proper_noun(self):
        self.compare_potentially_indefinite('Je parlais avec Pierre', 3, False)

    def test_potentially_indefinite_definite_noun(self):
        self.compare_potentially_indefinite('Je parlais avec l\'homme', 4, False)

    def test_potentially_indefinite_indefinite_noun(self):
        self.compare_potentially_indefinite('Je parlais avec quelque femme', 4, True)

    def test_potentially_indefinite_common_noun_conjunction_first_member(self):
        self.compare_potentially_indefinite('Je parlais avec un homme et une femme', 4, True)

    def test_potentially_indefinite_common_noun_conjunction_second_member(self):
        self.compare_potentially_indefinite('Je parlais avec un homme et une femme', 7, True)

    def test_potentially_indefinite_common_noun_conjunction_first_member_control(self):
        self.compare_potentially_indefinite('Je parlais avec l\'homme et la femme', 4, False)

    def test_potentially_indefinite_common_noun_conjunction_second_member_control(self):
        self.compare_potentially_indefinite('Je parlais avec l\'homme et la femme', 7, False)

    def compare_potentially_definite(self, doc_text, index, expected_truth, *,
            excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            self.assertEqual(expected_truth,
                rules_analyzer.is_potentially_definite(doc[index]),
                nlp.meta['name'])

        self.all_nlps(func)

    def test_potentially_definite_proper_noun(self):
        self.compare_potentially_definite('Je parlais avec Pierre',
            3, False)

    def test_potentially_definite_definite_noun(self):
        self.compare_potentially_definite('Je parlais avec cet homme.',
            4, True)

    def test_potentially_definite_indefinite_noun(self):
        self.compare_potentially_definite('Je parlais avec un certain homme',
            5, False)

    def test_potentially_definite_common_noun_conjunction_first_member(self):
        self.compare_potentially_definite('Je parlais avec cet homme et une femme',
            4, True)

    def test_potentially_definite_common_noun_conjunction_second_member(self):
        self.compare_potentially_definite('Je parlais avec un homme et cette femme',
            7, True)

    def test_potentially_definite_common_noun_conjunction_first_member_control(self):
        self.compare_potentially_definite('Je parlais avec l\'homme et une femme',
            7, False)

    def test_potentially_definite_common_noun_conjunction_second_member_control(self):
        self.compare_potentially_definite('Je parlais avec un homme et la femme',
            4, False)

    def compare_potential_pair(self, doc_text, referred_index, include_dependent_siblings,
        referring_index, expected_truth, *, excluded_nlps=[], directly=True):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            assert rules_analyzer.is_independent_noun(doc[referred_index]) or \
                rules_analyzer.is_potential_anaphor(doc[referred_index])
            assert rules_analyzer.is_potential_anaphor(doc[referring_index]) ,(nlp.meta['name'],referred_index,referring_index)
            referred_mention = Mention(doc[referred_index], include_dependent_siblings)
            self.assertEqual(expected_truth, rules_analyzer.is_potential_anaphoric_pair(
                referred_mention, doc[referring_index], directly),(nlp.meta['name'],referred_index,referring_index))

        self.all_nlps(func)

    def test_potential_pair_trivial_masc(self):
        self.compare_potential_pair('Je voyais un homme. Il courait', 3, False, 5, 2)

    def test_potential_pair_trivial_masc_control(self):
        self.compare_potential_pair('Je voyais un homme. Elle courait', 3, False, 5, 0)

    def test_potential_pair_trivial_plural(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Ils couraient',
            3, True, 8, 2,
        excluded_nlps=['core_news_sm'])


    def test_potential_pair_trivial_plural_control(self):
        self.compare_potential_pair('Je voyais un homme. Ils couraient', 3, True, 5, 0)

    def test_potential_pair_plurals_with_coordination_first(self):
        self.compare_potential_pair('Je voyais des hommes et des femmes. Ils couraient',
            3, False, 8, 0)

    def test_potential_pair_plurals_with_coordination_second(self):
        self.compare_potential_pair('Je voyais des hommes et des femmes. Ils couraient',
            6, False, 8, 0)


    def test_potential_pair_trivial_possessive(self):
        self.compare_potential_pair('Je voyais un homme. Son chien courait',
            3, False, 5, 2)

    def test_potential_pair_trivial_masc_possessive_control_1(self):
        self.compare_potential_pair('Je voyais un homme. Leur chien courait',
            3, False, 5, 0)
           
    def test_potential_pair_possessive_coordinated_sibling(self):
        self.compare_potential_pair(
            'Gérard et sa femme traversent la rue',
            0, False, 2, 2)
            
    def test_potential_pair_possessive_coordinated_sibling_control(self):
        self.compare_potential_pair(
            'Gérard et sa femme traversent la rue',
            0, True, 2, 0)

    def test_potential_pair_trivial_fem(self):
        self.compare_potential_pair('Je voyais une femme. Elle courait', 3, False, 5, 2)

    def test_potential_pair_trivial_fem_control_1(self):
        self.compare_potential_pair('Je voyais une femme. Il courait', 3, False, 5, 0)

    def test_potential_pair_trivial_plur_single_element(self):
        self.compare_potential_pair('Je voyais quelques femmes. Elles dormaient',
            3, False, 5, 2)

    def test_potential_pair_trivial_plur_single_element_control_1(self):
        self.compare_potential_pair('Je voyais quelques femmes. Il dormait', 3, False, 5, 0)

    def test_potential_pair_trivial_plur_single_element_control_2(self):
        self.compare_potential_pair('Je voyais quelques femmes. Elle dormait', 3, False, 5, 0)

    def test_potential_pair_trivial_plur_single_element_possessive(self):
        self.compare_potential_pair('Je voyais quelques femmes. Leur chien dormait',
            3, False, 5, 2)

    def test_potential_pair_trivial_plur_single_element_possessive_control(self):
        self.compare_potential_pair('Je voyais quelques femmes. Son chien dormait',
            3, False, 5, 0)

    def test_potential_pair_trivial_plur_coordination(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Ils dormaient',
            3, True, 8, 2, 
        excluded_nlps=['core_news_sm'])

    def test_potential_pair_trivial_plur_coordination_control_1(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Il dormait', 3, True, 8, 0, 
        excluded_nlps=['core_news_sm'])

    def test_potential_pair_trivial_plur_coordination_control_2(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Elles dormaient',
            3, True, 8, 0)

    def test_potential_pair_trivial_plur_coordination_possessive(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Leur chien dormait',
            3, True, 8, 2)
        
    def test_potential_pair_trivial_plur_coordination_possessive_control(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Son chien dormaient',
            3, True, 8, 0)

    def test_potential_pair_trivial_plur_coordination_elements_plural_1(self):
        self.compare_potential_pair('Je voyais quelques femmes et quelques hommes. Ils dormaient',
            3, False, 8, 0)
            
    def test_potential_pair_trivial_plur_coordination_elements_plural_2(self):
        self.compare_potential_pair('Je voyais quelques femmes et quelques hommes. Ils dormaient',
            6, False, 8, 0)
            
    def test_potential_pair_trivial_plur_coordination_elements_plural_3(self):
        self.compare_potential_pair('Je voyais quelques femmes et quelques hommes. Ils dormaient',
            3, True, 8, 2)
            
    def test_potential_pair_trivial_plur_coordination_elements_plural_2(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Ils dormaient',
            6, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_first_element(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Il dormait',
            3, False, 8, 2)

    def test_potential_pair_trivial_sing_coordination_first_element_control_1(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Elle dormait',
            3, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_first_element_control_2(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Ils dormaient',
            3, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_first_element_possessive(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Son chien dormait',
            3, False, 8, 2)

    def test_potential_pair_trivial_sing_coordination_first_element_possessive_control(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Leur chien dormait',
            3, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_second_element(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Elle dormait',
            6, False, 8, 2)

    def test_potential_pair_trivial_sing_coordination_second_element_control_1(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Il dormait',
            6, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_second_element_control_3(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Ils dormaient',
            6, False, 8, 0)

    def test_potential_pair_trivial_sing_coordination_second_element_possessive(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Son chien dormait',
            6, False, 8, 2)

    def test_potential_pair_trivial_sing_coordination_second_element_possessive(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Leur chien dormait',
            6, False, 8, 0)
    
    def test_potential_pair_masc_trumps_et_control_1(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Elles dormaient',
            3, True, 8, 0)
    
    def test_potential_pair_masc_trumps_et_2(self):
        self.compare_potential_pair('Je voyais une femme et un homme. Ils dormaient',
            3, True, 8, 2)

    def test_potential_pair_masc_trumps_et_control_2(self):
        self.compare_potential_pair('Je voyais un homme et une femme. Elles dormaient',
            3, True, 8, 0)
    
    def test_potential_pair_masc_trumps_et_2(self):
        self.compare_potential_pair('Je voyais une femme et un homme. Ils dormaient',
            3, True, 8, 2)
    
    def test_potential_pair_masc_trumps_ou_control_1(self):
        self.compare_potential_pair('Je voyais un homme ou une femme. Elle dormait',
            3, True, 8, 0)
    
    def test_potential_pair_masc_trumps_ou_2(self):
        self.compare_potential_pair('Je voyais une femme ou un homme. Il dormait',
            3, True, 8, 2)

    def test_potential_pair_masc_trumps_ou_control_2(self):
        self.compare_potential_pair('Je voyais un homme ou une femme. Elle dormait',
            3, True, 8, 0)
    
    def test_potential_pair_masc_trumps_ou_2(self):
        self.compare_potential_pair('Je voyais une femme ou un homme. Il dormait',
            3, True, 8, 2)
        
    def test_potential_pair_apposition(self):
        self.compare_potential_pair('Alexandre, roi de Macédoine devient empereur. Il meurt à 33 ans.',
            0, True, 8, 2,
            excluded_nlps = ['core_news_md','core_news_sm'])     
    
    def test_potential_pair_apposition_2(self):
        self.compare_potential_pair('Alexandre, roi de Macédoine devient empereur. Il meurt à 33 ans.',
            2, True, 8, 2,
            excluded_nlps=['core_news_md','core_news_sm'])     
    
        
    def test_potential_pair_male_name(self):
        self.compare_potential_pair('Je voyais Pierre. Il dormait', 2, False, 4, 2)

    def test_potential_pair_male_name_control_1(self):
        self.compare_potential_pair('Je voyais Pierre. Elle dormait', 2, False, 4, 0)

    def test_potential_pair_male_name_control_2(self):
        self.compare_potential_pair('Je voyais Pierre. Ils dormaient', 2, False, 4, 0)

    def test_potential_pair_female_name(self):
        self.compare_potential_pair('Je voyais Julie. Elle dormait', 2, False, 4, 2)

    def test_potential_pair_female_name_control_1(self):
        self.compare_potential_pair('Je voyais Julie. Il dormait', 2, False, 4, 0)

    def test_potential_pair_female_name_control_3(self):
        self.compare_potential_pair('Je voyais Julie. Ils dormaient', 2, False, 4, 0)

    def test_potential_pair_female_name_control_3(self):
        self.compare_potential_pair('Je voyais Julie. Elles dormaient', 2, False, 4, 0)

    def test_potential_pair_male_female_name_1(self):
        self.compare_potential_pair('Je voyais Charlie. Il dormait', 2, False, 4, 2)

    def test_potential_pair_male_female_name_2(self):
        self.compare_potential_pair('Je voyais Charlie. Elle dormait', 2, False, 4, 2)

    def test_potential_pair_male_female_name_control_1(self):
        self.compare_potential_pair('Je voyais Charlie. Ils dormaient', 2, False, 4, 0)

    def test_potential_pair_male_female_name_control_2(self):
        self.compare_potential_pair('Je voyais Charlie. Elles dormaient', 2, False, 4, 0)

    def test_potential_pair_fem_acc_anaphor_1(self):
        self.compare_potential_pair('Je voyais une femme. Je la préviens', 3, False, 6, 2,
            excluded_nlps=['core_news_sm'])

    def test_potential_pair_fem_acc_anaphor_2(self):
        self.compare_potential_pair('Je voyais quelques femmes. Je les salue',
            3, False, 6, 2)

    def test_potential_pair_fem_acc_anaphor_control_1(self):
        self.compare_potential_pair('Je voyais un sac. Je la prends', 3, False, 6, 0,
            excluded_nlps= ['core_news_sm'])

    def test_potential_pair_fem_acc_anaphor_control_2(self):
        self.compare_potential_pair('Je voyais une maison. Je le vois', 3, False, 6, 0)

    def test_potential_pair_fem_acc_anaphor_3(self):
        self.compare_potential_pair('Je voyais une femme. Je l\'ai vue', 3, False, 6, 2)
            
    def test_potential_pair_fem_acc_anaphor_control_3(self):
        self.compare_potential_pair('Je voyais des maisons. Je l\'ai vu', 3, False, 6, 0)
            
    def test_potential_pair_fem_acc_anaphor_4(self):
        self.compare_potential_pair('Je prends la valise. Je l\'ai', 3, False, 6, 2)
            
    def test_potential_pair_fem_acc_anaphor_control_4(self):
        self.compare_potential_pair('Je prends les valises. Je l\'ai', 3, False, 6, 0)
        
    def test_potential_pair_dislocation_left_cataphor(self):
        self.compare_potential_pair("Elle est bleue, la valise", 5, False, 0, 2)
        
    def test_potential_pair_dislocation_right_anaphor(self):
        self.compare_potential_pair("La valise, elle est bleue", 1, False, 3, 2,
            excluded_nlps=['core_news_sm','core_news_md'])
                                        
    def test_potential_pair_location_anaphor_1(self):
        self.compare_potential_pair('Je viens de France. C\'est là que j\'ai grandi',
        3 , False, 7, 2,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_location_anaphor_2(self):
        self.compare_potential_pair('J\'arrive en France. C\'est ici que je veux vivre',
        3 , False, 7, 2,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_location_anaphor_ici(self):
        self.compare_potential_pair('Voici ma maison. Je vis ici', 2 , False, 6, 2,
            excluded_nlps=['core_news_sm'])
                   
    def test_potential_pair_location_anaphor_en(self):
        self.compare_potential_pair('Je viens de France. J\'en viens.',3 , False, 6, 2,
            excluded_nlps=['core_news_sm'])
 
    def test_potential_pair_location_anaphor_y(self):
        self.compare_potential_pair('J\'habite en France. J\'y habite.',3 , False, 6, 2,
            excluded_nlps=['core_news_sm'])   
        
    def test_potential_pair_location_anaphor_y_control(self):
        self.compare_potential_pair('J\'aime beaucoup Pierre. J\'y habite.',3 , False, 6, 0,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_location_anaphor_ici_control(self):
        self.compare_potential_pair('J\'aime cette femme. Elle habite ici',3 , False, 7, 0,
            excluded_nlps=['core_news_sm'])   
        
    def test_potential_pair_location_anaphor_la_control(self):
        self.compare_potential_pair('J\'aime cette femme. Elle habite là',3 , False, 7, 0,
            excluded_nlps=['core_news_sm'])  
        
    '''
    def test_potential_pair_location_anaphor_en_control(self):
        # hard to implement. needs list of massive nouns
        self.compare_potential_pair('Je prends le baton. J\'en veux.',3 , False, 6, 0,
        excluded_nlps=['core_news_sm'])   
    '''
    
    def test_potential_pair_massive_noun_en(self):
        self.compare_potential_pair('J\'aime le chocolat. J\'en mange.',3 , False, 6, 2,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_group_part_en(self):
        self.compare_potential_pair('Je collectionne les billes. J\'en ai beaucoup.',
            3, False, 6, 2,
            excluded_nlps=['core_news_sm'])
        
 
    def test_potential_pair_demonstrative_pronoun_closer(self):
        self.compare_potential_pair(
            'Les professeurs et les élèves sont arrivés. Ceux-ci sont bruyants.',
            4, False, 8, 2,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_demonstrative_dernier(self):
        self.compare_potential_pair(
            'Les professeurs et les élèves sont arrivés. Ces derniers sont bruyants.', 4, False, 9, 2,
            excluded_nlps=['core_news_sm'])       
        
    def test_potential_pair_demonstrative_pronoun_closer_control(self):
        self.compare_potential_pair(
            'Les professeurs et les élèves sont arrivés. Ceux-ci sont bruyants.', 1, False, 8, 0,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_demonstrative_pronoun_further(self):
        self.compare_potential_pair(
            'Les professeurs et les élèves sont arrivés. Ceux-là sont bruyants.', 1, False, 8, 2,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_demonstrative_pronoun_further_control(self):
        self.compare_potential_pair(
            'Les professeurs et les élèves sont arrivés. Ceux-là sont bruyants.', 4, False, 8, 0,
            excluded_nlps=['core_news_sm'])
        
    def test_potential_pair_quelqun(self):
        self.compare_potential_pair(
            'Quelqu\'un est arrivé hier. Il dort dans la chambre.', 1, False, 6, 2)
    
    def test_potential_pair_quelqun_control(self):
        self.compare_potential_pair(
            'Quelqu\'un est arrivé hier. Ils dorment dans la chambre.', 1, False, 6, 0)
        
    def test_potential_posessive_determiner_1(self):
        self.compare_potential_pair(
            'Il a acheté une nouvelle maison. C\'est là qu\'il parlera à ses enfants.',
            0, False, 14, 2)
        
    def test_potential_posessive_determiner_2(self):
        self.compare_potential_pair(
            'Il a acheté une nouvelle maison. C\'est là qu\'il parlera à son enfant.',
            11, False, 14, 2)

    def test_potential_posessive_determiner_control(self):
        self.compare_potential_pair(
            'Il a acheté une nouvelle maison. C\'est là qu\'il parlera à leurs enfants.',
            0, False, 14, 0)
        
    def test_potential_reflexive_doubled(self):
        self.compare_potential_pair(
            'La panthère se chassait elle-même',
            1, False, 4, 2,
            excluded_nlps='core_news_sm')
            
    def test_potential_reflexive_emphatic(self):
        self.compare_potential_pair(
            'La panthère chassait elle-même',
            1, False, 3, 2,
            excluded_nlps='core_news_sm')
            
    def test_potential_reflexive_doubled_control(self):
        self.compare_potential_pair(
            'La panthère chassait, et la loutre nageait elle-même',
            1, False, 8, 0,
            excluded_nlps='core_news_sm')
                        
    def test_potential_conjunction_different_pronouns(self):
        self.compare_potential_pair(
            'J\'ai vu Jacques et Julie, et elle et lui chassaient un chat',
            8, False, 10, 0,
            excluded_nlps=['core_news_sm'])
      
    def test_potential_pair_reflexive_noun(self):
        self.compare_potential_pair(
            'Il est passioné par la rotation de la Terre sur elle-même',
            8, False, 10, 2)
            
    def test_potential_pair_reflexive_noun_control(self):
        self.compare_potential_pair(
            'Il est passioné par la rotation de la Terre sur elle-même.',
            0, False, 10, 0)
            
    def test_potential_pair_subordinate_clause(self):
        self.compare_potential_pair(
            'Même s\'il était très occupé par son travail, Jacques s\'en lassait.',
            10, False, 2, 2)


    def compare_potential_reflexive_pair(self, doc_text, referred_index, include_dependent_siblings,
        referring_index, expected_truth, expected_reflexive_truth,
        is_reflexive_anaphor_truth, *, excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            assert rules_analyzer.is_independent_noun(doc[referred_index]) or \
                rules_analyzer.is_potential_anaphor(doc[referred_index])
            assert rules_analyzer.is_potential_anaphor(doc[referring_index])
            referred_mention = Mention(doc[referred_index], include_dependent_siblings)
            self.assertEqual(expected_truth, rules_analyzer.is_potential_anaphoric_pair(
                referred_mention, doc[referring_index], True), nlp.meta['name'])
            self.assertEqual(expected_reflexive_truth, rules_analyzer.is_potential_reflexive_pair(
                referred_mention, doc[referring_index]), nlp.meta['name'])
            self.assertEqual(is_reflexive_anaphor_truth, rules_analyzer.is_reflexive_anaphor(
                doc[referring_index]), nlp.meta['name'])

        self.all_nlps(func)

    def test_reflexive_in_wrong_situation_different_sentence(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme. L\'Homme se voyait',
            3, False, 7, 0, False, 2)

    def test_reflexive_in_wrong_situation_different_sentence_control(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme. L\'autre homme le voyait',
            3, False, 8, 2, False, 0)

    def test_reflexive_in_wrong_situation_same_sentence_1(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme pendant que l\'autre homme se voyait lui-même.',
            3, False, 9, 0, False, 2) # AJOUTER EXEMPLES lui-même
    
    def test_reflexive_in_wrong_situation_same_sentence_control(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme pendant que l\'autre homme le voyait',
            3, False, 9, 2, False, 0)
            
    def test_reflexive_emphasis(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme pendant que l\'autre homme se voyait lui-même.',
            8, False, 11, 2, True, 2) # AJOUTER EXEMPLES lui-même

    def test_reflexive_emphasis_control(self):
        self.compare_potential_reflexive_pair('Je voyais l\'homme pendant que l\'autre homme se voyait lui-même.',
            3, False, 11, 0, False, 2) # AJOUTER EXEMPLES lui-même

    def test_non_reflexive_in_wrong_situation_same_sentence(self):
        self.compare_potential_reflexive_pair('L\'homme le voyait.',
            1, False, 2, 0, True, 0)

    def test_non_reflexive_in_wrong_situation_same_sentence_control(self):
        self.compare_potential_reflexive_pair('L\'homme se voyait.',
            1, False, 2, 2, True, 2)

    def test_non_reflexive_in_same_sentence_with_verb_conjunction(self):
        self.compare_potential_reflexive_pair('L\'homme entendait tout et se voyait.',
            1, False, 5, 2, True, 2)

    def test_reflexive_in_right_situation_modal(self):
        self.compare_potential_reflexive_pair('L\'homme voulait se voir.',
            1, False, 3, 2, True, 2)

    def test_reflexive_in_right_situation_a_clause(self):
        self.compare_potential_reflexive_pair('L\'homme pensait à se voir',
            1, False, 4, 2, True, 2)

    def test_reflexive_in_right_situation_au_fait_clause(self):
        self.compare_potential_reflexive_pair('L\'homme pensait au fait de se voir',
            1, False, 6, 2, True, 2)

    def test_reflexive_in_right_situation_within_subordinate_clause(self):
        self.compare_potential_reflexive_pair('Il souhaitait que l\'homme se voie.',
            4, False, 5, 2, True, 2)

    def test_reflexive_in_right_situation_within_subordinate_clause_control(self):
        self.compare_potential_reflexive_pair('Il souhaitait que l\'homme se voie',
            0, False, 5, 0, False, 2)

    def test_reflexive_with_conjuction(self):
        self.compare_potential_reflexive_pair('La maison et la propriété se vendent',
            1, True, 5, 2, True, 2)

    def test_reflexive_with_conjuction_control(self):
        self.compare_potential_reflexive_pair('La maison et la voiture se vendent',
            1, False, 5, 0, True, 2)

    def test_reflexive_with_passive(self):
        self.compare_potential_reflexive_pair('L\'organisation est sauvée par elle-même',
            1, False, 5, 2, True, 2)

    def test_reflexive_with_passive_and_conjunction(self):
        self.compare_potential_reflexive_pair(
            'La maison et la voiture furent achetées par elles-mêmes',
            1, True, 8, 2, True, 2)

    def test_reflexive_with_object_antecedent(self):
        self.compare_potential_reflexive_pair('Elle mélangea le produit avec lui-même',
            3, False, 5, 2, True, 2, excluded_nlps=['core_news_sm'])
        self.compare_potential_reflexive_pair('Elle mélangea le produit avec lui-même',
            0, False, 5, 0, True, 2, excluded_nlps=['core_news_sm','core_news_md'])

    def test_reflexive_with_object_antecedent_and_coordination(self):
        self.compare_potential_reflexive_pair(
            'Elle mélangea le produit et le sel avec eux-mêmes',
            3, True, 8, 2, True, 2, excluded_nlps=['core_news_sm'])
        self.compare_potential_reflexive_pair(
            'Elle mélangea le produit et le sel avec eux-mêmes.',
            0, False, 8, 0, True, 2, excluded_nlps=['core_news_sm'])

    def test_reflexive_with_verb_coordination_one_subject(self):
        self.compare_potential_reflexive_pair('Il le voyait et se félicitait',
            0, False, 4, 2, True, 2, excluded_nlps=['core_news_sm'])

    def test_reflexive_with_verb_coordination_two_subjects(self):
        self.compare_potential_reflexive_pair('Il le voyait et son chef se félicitait',
            0, False, 6, 0, False, 2, excluded_nlps=['core_news_sm'])

    def test_reflexive_with_to(self):
        self.compare_potential_reflexive_pair(
            'Ils voulaient que le garçon se connaisse',
            4, False, 5, 2, True, 2)

    def test_reflexive_with_referent_within_noun_phrase(self):
        self.compare_potential_reflexive_pair(
            'Ils discutèrent de la possibilité qu\'un individu se voie.',
            7, False, 8, 2, True, 2)

    def test_non_reflexive_in_wrong_situation_subordinate_clause(self):
        self.compare_potential_reflexive_pair('Même s\'il le voyait, il était content.',
            2, False, 3, 0, True, 0, excluded_nlps=['core_news_sm','core_news_md'])
            

    def test_reflexive_completely_within_noun_phrase_1(self):
        self.compare_potential_reflexive_pair(
            'L\'opinion de mon amie sur elle-même était exagérée.',
            4, False, 6, 2, True, 2)

    def test_reflexive_completely_within_noun_phrase_1_control(self):
        self.compare_potential_reflexive_pair(
            "L\'opinion de mon amie sur elle était exagérée.",
            4, False, 6, 0, True, 0, excluded_nlps="core_news_sm")

    def test_reflexive_double_coordination_without_preposition(self):

        self.compare_potential_reflexive_pair('Jean et Marie les voyaient lui et elle.',
            0, False, 5, 0, True, 0, excluded_nlps=['core_news_sm'])
        self.compare_potential_reflexive_pair('Jean et Marie les voyaient lui et elle.',
            2, False, 7, 0, True, 0, excluded_nlps=['core_news_sm'])

    def test_reflexive_double_coordination_with_preposition(self):
        self.compare_potential_reflexive_pair(
            'Jean et Marie parlaient avec lui et avec elle.',
            0, False, 5, 0, True, 0, excluded_nlps=['core_news_sm'])
        self.compare_potential_reflexive_pair(
            'Jean et Marie parlaient avec lui et avec elle.',
            2, False, 8, 0, True, 0, excluded_nlps=['core_news_sm'])

    def test_reflexive_relative_clause_subject(self):
        self.compare_potential_reflexive_pair('L\'homme qui le voyait, est rentré.',
            1, False, 3, 0, True, 0)

    def test_reflexive_relative_clause_object_1(self):
        self.compare_potential_reflexive_pair('L\'homme qu\'il voyait, est rentré.',
            1, False, 3, 0, True, 0)

    def test_reflexive_relative_clause_subject_with_conjunction(self):
        self.compare_potential_reflexive_pair(
            "L'homme et la femme qui les voyaient, sont rentrés",
            1, True, 6, 0, True, 0, excluded_nlps=['core_news_sm','dep_news_trf'])

    def test_reflexive_relative_clause_object_with_conjunction(self):
        self.compare_potential_reflexive_pair(
            "L'homme et la femme qu'ils voyaient, sont rentrés",
            1, True, 6, 0, True, 0, excluded_nlps=['core_news_sm','dep_news_trf'])

    
    def compare_potential_cataphoric_pair(self, doc_text, referred_index,
        include_dependent_siblings, referring_index, expected_truth, *, excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            assert rules_analyzer.is_independent_noun(doc[referred_index]) or \
                rules_analyzer.is_potential_anaphor(doc[referred_index])
            assert rules_analyzer.is_potential_anaphor(doc[referring_index])
            assert referred_index > referring_index
            referred_mention = Mention(doc[referred_index], include_dependent_siblings)
            self.assertEqual(expected_truth, rules_analyzer.is_potential_cataphoric_pair(
                referred_mention, doc[referring_index]) and rules_analyzer.is_potential_anaphoric_pair(
                referred_mention, doc[referring_index], True) > 0, nlp.meta['name'])
        self.all_nlps(func)

    def test_cataphora_simple_case(self):
        self.compare_potential_cataphoric_pair("Bien qu'il passait un bon moment, Tom est rentré.",
            8, False, 2, True, excluded_nlps=['core_news_sm'])

    def test_cataphora_with_conjunction(self):
        self.compare_potential_cataphoric_pair(
            "Bien qu'ils passaient un bon moment, le garçon et la fille partirent.",
            9, True, 2, True)

    def test_cataphora_with_conjunction_control(self):
        self.compare_potential_cataphoric_pair(
            "Bien qu'ils passaient un bon moment, le garçon et la fille partirent.",
            9, False, 2, False)

    def test_cataphora_tokens_deeper_in_tree_1(self):
        self.compare_potential_cataphoric_pair(
            'Bien que tous ses fans parlaient de le voir, la presse avait depuis longtemps cessé de déranger Gérard.',
            18 , False , 3, True,
            excluded_nlps=['core_news_sm'])
    def test_cataphora_tokens_deeper_in_tree_2(self):
        self.compare_potential_cataphoric_pair(
            'Bien que tous ses fans parlaient de le voir, la presse avait depuis longtemps cessé de déranger Gérard.',
            18 , False , 7, True,
            excluded_nlps=['core_news_sm'])
            
    def test_cataphora_tokens_deeper_in_tree_conjunction_1(self):
        self.compare_potential_cataphoric_pair(
            'Bien que tous leurs fans parlaient de les voir, la presse avait depuis longtemps cessé de déranger Gérard et Hélène.',
            18, True, 3, True,
            excluded_nlps=['core_news_sm'])
            
    def test_cataphora_tokens_deeper_in_tree_conjunction_2(self):
        self.compare_potential_cataphoric_pair(
            'Bien que tous leurs fans parlaient de les voir, la presse avait depuis longtemps cessé de déranger Gérard et Hélène.',
            18, True, 7, True,
            excluded_nlps=['core_news_sm'])

    def test_cataphora_tokens_deeper_in_tree_conjunction_control(self):
        self.compare_potential_cataphoric_pair(
            'Bien que tous leurs fans parlaient de les voir, la presse avait depuis longtemps cessé de déranger Gérard et Hélène.',
            18, False, 7, False)

    def test_cataphora_wrong_structure_1(self):
        self.compare_potential_cataphoric_pair(
            'La presse avait depuis longtemps cessé de le suivre, bien que tous ses fans parlaient de voir Gérard',
            18, False, 7, False)

    def test_cataphora_wrong_structure_2(self):
        self.compare_potential_cataphoric_pair(
            'Tous ses fans parlaient de vouloir voir James', 7 , False, 1, False)

    def test_cataphora_conjunction_at_verb_level(self):
        self.compare_potential_cataphoric_pair(
            'Même s\'il était disponible, Jacques mangeait et Gérard rentra à la maison',
            9, False, 2, False, excluded_nlps=['core_news_sm'])
            
    def test_cataphora_referred_is_pronoun(self):
        self.compare_potential_cataphoric_pair(
            "Même s'il était disponible, il rentra à la maison", 6, False, 2, False)
            
    def test_cataphora_referred_is_pronoun_control(self):
        self.compare_potential_cataphoric_pair(
            "Même s'il était disponible, Gérard rentra à la maison", 6, False, 2, True)

    def test_cataphora_not_advcl(self):
        self.compare_potential_cataphoric_pair(
            'Il était libre ; il rentra à la maison', 4, False, 0, False)

    def compare_potential_referreds(self, doc_text, index, expected_potential_referreds, *,
        excluded_nlps=[]):

        def func(nlp):

            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory.get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            if expected_potential_referreds is None:
                self.assertFalse(hasattr(doc[index]._.coref_chains,
                    'temp_potential_referreds'))
            
                
            else:
                if not hasattr(doc[index]._.coref_chains,'temp_potential_referreds'):
                    potential_referreds = []
                else:
                    potential_referreds = [referred.pretty_representation for referred in
                        doc[index]._.coref_chains.temp_potential_referreds]
                self.assertEqual(expected_potential_referreds, potential_referreds,
                    nlp.meta['name'])

        self.all_nlps(func)

    def test_potential_referreds_same_sentence(self):
        self.compare_potential_referreds("Richard rentra et il cria", 0, None)
        self.compare_potential_referreds("Richard rentra et il cria", 1, None)
        self.compare_potential_referreds("Richard rentra et il cria", 3, ['Richard(0)'])

    def test_potential_referreds_conjunction_same_sentence(self):
        self.compare_potential_referreds("Richard et Julie vinrent et ils hurlèrent", 5,
            ['[Richard(0); Julie(2)]'])

    def test_potential_referreds_maximum_sentence_referential_distance(self):
        self.compare_potential_referreds(
            "Richard vint. Un homme. Un homme. Un homme. Un homme. Il parla.", 15,
                ['Richard(0)','homme(4)', 'homme(7)', 'homme(10)', 'homme(13)'])

    def test_potential_referreds_over_maximum_sentence_referential_distance(self):
        self.compare_potential_referreds(
            "Richard vint. Un homme. Un homme. Un homme. Un homme. Un homme. Il parla.", 18,
                ['homme(4)', 'homme(7)', 'homme(10)', 'homme(13)', 'homme(16)'])
                
    def test_potential_referreds_last_token(self):
        self.compare_potential_referreds("Richard entra et un homme le vit", 5,
            ['Richard(0)'], excluded_nlps=["core_news_sm"])

    def test_potential_referreds_cataphora_simple(self):
        self.compare_potential_referreds(
            "Même s'il rentra, un homme voyait Richard", 2,
            ["homme(6)", 'Richard(8)'], excluded_nlps='core_news_sm')

    def test_potential_referreds_cataphora_conjunction(self):
        self.compare_potential_referreds(
            "Bien qu'ils rentrèrent, un homme voyait Richard et Julie", 2,
            ['[Richard(8); Julie(10)]'], excluded_nlps='core_news_sm')
 
    
    def compare_potential_noun_pair(self, doc_text, referred_index, referring_index,
            expected_truth, *, excluded_nlps=[]):

        def func(nlp):
            if nlp.meta['name'] in excluded_nlps:
                return
            doc = nlp(doc_text)
            rules_analyzer = RulesAnalyzerFactory().get_rules_analyzer(nlp)
            rules_analyzer.initialize(doc)
            self.assertEqual(expected_truth,
                rules_analyzer.is_potential_coreferring_noun_pair(doc[referred_index],
                doc[referring_index]), nlp.meta['name'])

        self.all_nlps(func)

    def test_potential_noun_pair_proper_noun_test(self):
        self.compare_potential_noun_pair('De Bach à Beethoven, Brahms et Mozart',
            5, 7, False)

    def test_potential_noun_pair_apposition_same_lemma(self):
        self.compare_potential_noun_pair(
            'Un roi de Macédoine devient empereur. Le roi de Macédoine meurt à 33 ans.',
            1, 8, True)     
                             
    def test_potential_noun_pair_proper_noun_noun(self):
        self.compare_potential_noun_pair(
            'EDF existe depuis 20 ans. La compagnie a plusieurs fois changé de nom.',
            0, 7, True)
            
    def test_potential_noun_pair_proper_noun_noun_control(self):
        self.compare_potential_noun_pair(
            'EDF existe depuis 20 ans. La femme a plusieurs fois changé de nom.',
            0, 7, False)  
            
    def test_potential_noun_pair_proper_noun_noun_2(self):
        self.compare_potential_noun_pair(
            'Je voyais Mme Dupont. Tout le monde aimait cette femme aimable.',
            3, 10, True,
            excluded_nlps='core_news_sm')            
    def test_potential_noun_pair_proper_definite_noun_relative_clause(self):
        self.compare_potential_noun_pair(
            'Le roi que tu as vu est arrivé. Ce roi s\'appelle Alexandre',
            1, 10, True)   
 
    def test_potential_noun_pair_proadverb_location(self):
        self.compare_potential_noun_pair(
            'Il a acheté une nouvelle maison. C\'est là qu\'il va élever ses enfants.',
            5, 15, False)

    def test_potential_noun_pair_apposition(self):
        self.compare_potential_noun_pair('Alexandre, le roi de Macédoine devient empereur. Le roi de Macédoine meurt à 33 ans.',
            0, 3, True)     
            
    def test_potential_noun_pair_apposition_2(self):
        self.compare_potential_noun_pair('Alexandre, le roi de Macédoine devient empereur. Le roi de Macédoine meurt à 33 ans.',
            0, 10, True) 


