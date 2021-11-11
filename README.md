# coreferee_french


Adding support for french models on coreferee, a coreference resolution python 3 library:
This repository contains the code and the ressources developped to add support for french in the library. 

## Road Mad
Done :
- Designing Language specific rules to identify potential coreference
- Testing the rules
- Locating a ccorpus annotated with coreference (DEMOCRAT)
- Making class to load the corpus
- Trained the three models ('fr_core_news_sm','fr_core_news_md','fr_core_news_lg')
- Installed the Models



Currently:
- Doing Smoke tests

## What is covered
Coreferee uses both a rule-based system to identify the potential coreference candidates and a neural network ensemble to determine the most probable coreferring pairs.
Below we will present the specificities of the french model.
For more details on how coreferee works, see the [repository of the library](https://github.com/msg-systems/coreferee).

The potential candidates for coreference are divided in two categories , the inpendent nouns and anaphors:

- Independent nouns :
  - Proper Nouns : Person names, city names, organisation names ...
  - Common Nouns : Whether Definitie or indefinite
  - Substantive adjectives : Adjectived used in noun position ('Le beau','Le petit','L'autre'...)
  - Numerals substracting part of a plural nouns : ('un des garçons', 'trois des filles'...)
  - third person Possessive pronouns : Refer to an entity different from the marker owner ('Le sien', 'Le leur', ...)

- Anaphors :
  - Third person personal pronoun : Whether subject, object, or else ("il","elle","lui","le", ...)
  - Proadverbs/ Adverbial pronouns : ("y","en")
  - Deictic  with potential use as proadverbs : ("ici","là")
  - Demonstrative Pronouns :  As head of a relative clause ("celui que je vois") or compound ('ceux-ci','celle-là'...)
  - Third person Possessive Determiners : ("sa","leur",...)
  - Reflexive pronoun : ("se")
  - Emphatic third person pronoun : Typically used to double reflexivity ('lui-même','eux-mêmes', ...)

Elements that are typically *not* covered but could potentially corefer in a text :
- First and second persons : Elements that are deictically anchored ("Je", "nous", "tu", "toi", "me", "mon", "le tien", ...)
- Pronoun "on" 
- Relative pronouns : ("que", "dont","lesquels",...)
- Interrogative pronouns : ("quoi","qui",...)
- 'neuter' demonstrative pronoun and its derivative : Generally Either deictic or refers to proposition, not noun phrase ("ça","cela","c","ce")

## The Corpus

The Corpus used for the training, the development and the test is [DEMOCRAT](https://www.ortolang.fr/market/corpora/democrat/v1.1)
It was converted to the CONLL format and split into training, dev and test in [a previous project](https://github.com/Pantalaymon/neuralcoref-for-french) .


## Model Performance
The results
