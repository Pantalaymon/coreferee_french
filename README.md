# coreferee_french


Adding support for french models on [coreferee](https://github.com/msg-systems/coreferee), a coreference resolution extensible python 3 library:
This repository contains the code and the ressources developped to add support for french in the library. 

## The models
The currently supported french models are : 

- fr_core_news_sm
- fr_core_news_md
- fr_core_news_lg

We plan to add support for the transformers-based spacy model in the future. Although fr_dep_news_trf produces considerably better sentence analysis than the other models, it does not come with a named entity recogniser, which is necessary to identify noun pairs (as well as a helpful features of the neural ensemble).

## Road Map
Done :
- Designing Language specific rules to identify potential coreference
- Testing the rules
- Locating a ccorpus annotated with coreference (DEMOCRAT)
- Making class to load the corpus
- Trained the three models ('fr_core_news_sm','fr_core_news_md','fr_core_news_lg')
- Installed the Models
- Smoke tests

Currently:
- Working on evaluation of the models

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
  - third person Possessive pronouns : Refer to an entity different from the marked owner ('Le sien', 'Le leur', ...)

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
- Dates : hours, days, years, or centuries... 


## The Corpus

The Corpus used for the training, the development and the test is [DEMOCRAT](https://www.ortolang.fr/market/corpora/democrat/v1.1)
It was converted to the CONLL format and split into training, dev and test in [a previous project](https://github.com/Pantalaymon/neuralcoref-for-french) .
Here are a few facts that ought to be relevant for the training and evaluation and model performance: 
- The corpus is pretokenised. Some of the token limits don't match with the tokenization made by spacy. This inevitably leads to some badly recognized words and thus coreference errors.
- The documents in the original corpus are split in documents of 15 sentences for processing reasons (Parsing entire books with spacy takes too much time and memory). Very long coreference chains spanning entire texts are thus not considered. The longer the document, the least likely the coreference chains will be accurate.
- DEMOCRAT as well as the corpus the spacy pipeline was trained on([Sequoia](http://deep-sequoia.inria.fr/)) are written french corpora. Hence why the models will have a subpar performance on oral data.
- A mention must have at least one coreferring mention. Which means singletons are not considered in the following table

|             | Number of mentions | Number of covered mentions | Proportion of covered mentions | Number of documents|
| :----------:|       :-:          |           :-:              |           :-:                  |         :-:       |
| Train + Dev |       55921        |           40063            |           71.6 %               |       903          |
| Test        |        2669        |           3834             |           69.6 %               |         85        |



## Model Performance

As always with coreference resolution, the choice of the metrics to evaluate the performance of the system is a non obvious, and non trivial task.

It is worth mentioning that in the metrics below, the key mentions considered are the mentions identifies by coreferee. Which means that it only covers the phrases mentions above but it is also not totally accurate (possibly because of a case ignored by the rules and more probably because it builds upon spacy's analysis of the sentences which itself is not totally accurate, especially in the smaller models).


### PairWise Anaphor Metrics

Knowing the working process of coreferee for anaphors (broadly):
- rule-based system identify mentions
- rule-based system identify potential anaphoric pairs
- neural network ensemble scores the pairs and selects the most probable ones

The anaphor resolution task could be constructed as task as a binary classification task of all potential anaphoric pairs. With that in mind we get the following definitions :
- true positive : System outputs the mentions as an anaphoric pair and both mentions are in the same coreference chain in the manually annotated corpus
- false positive : System outputs as the mentions an anaphoric pair and but the mentions are in differents chains (or singletons) in the manually annotated corpus
- true negative : The mentions are not in the same chain either in the system output or in the manually annotated corpus
- false negative : System misses an anaphoric pair that was present in the manually annotated corpus


In the test corpus (not used at all during development) we obtain :

|             | fr_core_news_lg | fr_core_news_md | fr_core_news_sm |
| :----------:|       :-:       |    :-:          |    :-:          | 
|  precision  |      54.7       |      53.6       |      46.7       |
|   recall    |     59.9        |       60.5      |      55.2       |
|      f1     |     57.1        |       56.9      |       50.6     |
|  accuracy   |     83.3        |        84.3     |       76.9      |

### BLANC

We chose to use [https://aclanthology.org/P14-2005/](BLANC) as we find the details of the metric are precise enough to give a good idea of the strong points and weak points of the system. Unlike the previous metric that was computed on anaphoric pairs, this metric considers the whole coreference chains.

On the test corpus we obtain :


|  fr_core_news_lg   | coreference links| non-coreference links | BLANC |
|    :----------:    |       :-:   |      :-:        |  :-:  | 
|     precision      |     54.4    |    99.9         | 75.1  |
|     recall         |    26.4     |    99.9         | 63.1  | 
|      f1            |     34.4    |    99.9         | 67.22 | 

|  fr_core_news_md   | coreference links | non-coreference links | BLANC |
|    :----------:    |       :-:   |      :-:        |  :-:  | 
|     precision      |     49.4    |    99.9         |  74.6 |
|     recall         |     25.1    |    99.9         |  62.5 | 
|      f1            |      33.2   |    99.9         |  66.6 | 

|  fr_core_news_sm   | coreference links | non-coreference links | BLANC |
|    :----------:    |       :-:   |      :-:        |  :-:  | 
|     precision      |     42.9    |    99.9         |   71.4|
|     recall         |       22.9  |    99.9         |   61.4| 
|      f1            |      29.9   |    99.9         | 99.9  | 


The comparison of the results show that , as coreferee is primarily based on anaphor resolution, the models appear to be more suited to detect anaphoric pairs and non pairs in limited distance  rather than identifying whole chains spanning entire documents.
Specifically, entities tend to be "undermerged" which explains the low "coreference links" recall (when one chain is split into two consecutive chains, it produces a considerable amount of missed coreference links).
