# coreferee_french


Adding support for french models on [coreferee](https://github.com/msg-systems/coreferee), a coreference resolution extensible python 3 library:
This repository contains the code and the ressources developped to add support for french in the library. 

## The models
The currently supported french models are : 

- fr_core_news_sm
- fr_core_news_md
- fr_core_news_lg

We plan to add support for the transformers-based spacy model in the future. Although fr_dep_news_trf produces considerably better sentence analysis than the other models, it does not come with neither a named entity recogniser, which is necessary to identify noun pairs, nor token vectors (both of which ared used as features of the neural ensemble).

## Using a french model

To use a model you will need to first download one of the french spacy models mentioned above. The following example will use the model 'fr_core_news_lg'.

Coreferee is currently supported with python 3.9. Using a virtual environment is recommanded :
```
python3.9 -m venv coreferee-env
source coreferee-env/bin/activate

```
You will need to download coreferee and the french models (both spacy and coreferee ones). 

```
python3 -m pip install coreferee
python3 -m spacy download fr_core_news_lg
python3 -m coreferee install fr
```

And in a the python 3.9 prompt
```
>>> import coreferee, spacy
>>> nlp = spacy.load('fr_core_news_lg')
>>> nlp.add_pipe('coreferee')
<coreferee.manager.CorefereeBroker object at 0x000001F556B4FF10>
>>>
>>> doc = nlp("Même si elle était très occupée par son travail, Julie en avait marre. Alors, elle et son mari décidèrent qu'ils avaient besoin de vacances. Ils allèrent en Espagne car ils adoraient le pays")
>>>
>>> doc._.coref_chains.print()
0: elle(2), son(7), Julie(10), elle(17), son(19)
1: travail(8), en(11)
2: [elle(17); mari(20)], ils(23), Ils(29), ils(34)
3: Espagne(32), pays(37)
>>>
>>> doc[17]._.coref_chains.print()
0: elle(2), son(7), Julie(10), elle(17), son(19)
2: [elle(17); mari(20)], ils(23), Ils(29), ils(34)
>>>
>>> doc._.coref_chains.resolve(doc[34])
[Julie, mari]
>>>
```


## What is covered
Coreferee uses both a rule-based system to identify the potential coreference candidates and a neural network ensemble to determine the most probable coreferring pairs.
Below we will present the specificities of the french model.
For more details on how coreferee works, see the [repository of the library](https://github.com/msg-systems/coreferee).

The potential candidates for coreference are divided in two categories , the inpendent nouns and anaphoras:

- Independent nouns :
  - Proper Nouns : Person names, city names, organisation names ...
  - Common Nouns : Whether Definitie or indefinite
  - Substantive adjectives : Adjectived used in noun position ('Le beau','Le petit','L'autre'...)
  - Numerals substracting part of a plural nouns : ('un des garçons', 'trois des filles'...)
  - third person Possessive pronouns : Refer to an entity different from the marked owner ('Le sien', 'Le leur', ...)

- Anaphoras :
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

## More advanced operations
### Changing referential distance
While out of the score of the original intended use of coreferee, it may be useful to adapt the range of coreference chains depending on the type of textual data that is processed. Beware that increasing the range will likely lead to reduce the precision of the model while reducing it will likely lead to reduce the recall.
You may want to increase or reduce the potential sentence distance between a noun/anaphora and an anaphora. By default this distance is 5 sentences.
```
>>> nlp("Les enfants reviennent de l'école. Elle est au nord. Elle est sur une colline. Celle-ci est haute. Et verte aussi. Mais pas trop loin. Ils arrivent bientôt")._.coref_chains.print()
0: école(5), Elle(7), Elle(12)
1: colline(16), Celle(18)
```
```
>>> nlp.get_pipe("coreferee").annotator.rules_analyzer.maximum_anaphora_sentence_referential_distance
5
>>> nlp.get_pipe("coreferee").annotator.rules_analyzer.maximum_anaphora_sentence_referential_distance = 6
>>> nlp("Les enfants reviennent de l'école. Elle est au nord. Elle est sur une colline. Celle-ci est haute. Et verte aussi. Mais pas trop loin. Ils arrivent bientôt")._.coref_chains.print()
0: enfants(1), Ils(33)
1: école(5), Elle(7), Elle(12)
2: colline(16), Celle(18)
```
You may want to increase or reduce the potential sentence distance between two corefering nouns. By default this distance is 3 sentences.
```
>>> nlp("Les enfants reviennent de l'école. Elle est au nord. Elle est sur une colline. Celle-ci est haute. Les enfants arrivent bientôt")._.coref_chains.print()
0: école(5), Elle(7), Elle(12)
1: colline(16), Celle(18)
```
```
>>> nlp.get_pipe("coreferee").annotator.rules_analyzer.maximum_coreferring_nouns_sentence_referential_distance
3
>>> nlp.get_pipe("coreferee").annotator.rules_analyzer.maximum_anaphora_sentence_referential_distance = 4
>>> nlp("Les enfants reviennent de l'école. Elle est au nord. Elle est sur une colline. Celle-ci est haute. Les enfants arrivent bientôt")._.coref_chains.print()
0: enfants(1), enfants(25)
1: école(5), Elle(7), Elle(12)
2: colline(16), Celle(18)
```

### Retrieving mention phrases
As shown above, coreferee does not output the whole noun phrases of the mentions. It only outputs the heads of those phrases (including the coordinated heads when they are part of the mention).
To retrieve the noun phrases of the mentions, you may use the functions in ```build_mentions.py``` in this repository. This file is not part of coreferee so you will need to import it separately.
Keep in mind that those functions operate entirely based on spacy's parse tree, which means that when the tree is not accurate, the resulting mentions may be unsatisfactory.
You may either pass in a list of token heads to build_mention() 
```
>>> from build_mentions import build_mention, create_mentions
>>> rules_analyzer = nlp.get_pipe("coreferee").annotator.rules_analyzer
>>> doc = nlp("Les enfants de l'école primaire rentrent chez leurs parents")
>>> for chain in doc._.coref_chains:
...     for mention in chain:
...             heads = [doc[i] for i in mention.token_indexes]
...             mention_phrase = build_mention(heads, rules_analyzer)
...             print(heads, '->', mention_phrase)
...
[enfants] -> Les enfants de l'école primaire
[leurs] -> leurs
```
Alternatively you can directly get a dict all the mention phrases in the doc and their associated chain index, including the singletons or not.
```
>>> create_mentions(doc, rules_analyzer)
{Les enfants de l'école primaire: 0, leurs: 0}
>>> create_mentions(doc, rules_analyzer, add_singletons=True)
{Les enfants de l'école primaire: 0, leurs: 0, l'école primaire: 1, leurs parents: 2}
```
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


### PairWise Anaphor Metrics
It is worth mentioning that in the metric below, the key mentions considered are the mentions identifies by coreferee. Which means that it only covers the phrases mentions above but it is also not totally accurate (possibly because of a case ignored by the rules and more probably because it builds upon spacy's analysis of the sentences which itself is not totally accurate, especially in the smaller models).

Knowing the working process of coreferee for anaphors (broadly):
- rule-based system identify mentions
- rule-based system identify potential anaphoric pairs
- neural network ensemble scores the pairs and selects the most probable ones

The anaphor resolution task could be constructed as task as a binary classification task of all potential anaphoric pairs. With that in mind we get the following definitions :
- true positive : System outputs the mentions as an anaphoric pair and both mentions are in the same coreference chain in the manually annotated corpus
- false positive : System outputs as the mentions an anaphoric pair and but the mentions are in differents chains (or singletons) in the manually annotated corpus
- true negative : The mentions are not in the same chain either in the system output or in the manually annotated corpus
- false negative : System misses an anaphoric pair that was present in the manually annotated corpus


In the test corpus (not used at all during development) we obtain (in percent):

|             | fr_core_news_lg | fr_core_news_md | fr_core_news_sm |
| :----------:|       :-:       |    :-:          |    :-:          | 
|  precision  |      54.7       |      53.6       |      46.7       |
|   recall    |     59.9        |       60.5      |      55.2       |
|      f1     |     57.1        |       56.9      |       50.6     |
|  accuracy   |     83.3        |        84.3     |       76.9      |

### Traditional Coreference Metrics

To obtain comparable performance metrics, we needed to produce a output format similar to those traditionally used for coreference resolution benchmarks. Using the test corpus, we produced a file in conll format, following [Conll 2012 shared task guidelines](https://conll.cemantix.org/2012/data.html). The file to produce such output is ```coreferee_to_conll.py```. 
Since the mentions in conll format are not just heads but whole phrases, we had to use the functions from ```build_mentions.py``` to convert the heads outputted by coreferee to mention phrases. For this reason, the following metrics evaluate as much the coreference resolution as the quality of spacy's sentence analysis.
Unlike the previous metric that was computed on anaphoric pairs, the following more usual metrics consider the whole coreference chains, including the cases that are not covered by coreferee by design.

[The reference implementation of the coreference scorers](https://github.com/conll/reference-coreference-scorers) was used to compute the following scores :
Mention Identification
|      fr_core_news_lg     |      Precision  |      Recall    |       F1        |
|        :----------:      |       :-:       |       :-:      |       :-:       | 
|  Mention Identification  |      60.74      |      56.83     |      58.72      |
|          MUC             |     47.12       |      26.19     |      33.67      |
|        B-Cubed           |     51.43       |      41.32     |      45.83      |
|         CEAF-m           |     48.06       |      45.01     |      46.49      |
|         CEAF-e           |     44.79       |      53.38     |      48.71      |
|  BLANC non-coreference   |     33.46       |      32.34     |      32.89      |
|    BLANC coreference     |     49.03       |      14.2      |      22.03      |
|         BLANC            |     41.25       |      23.27     |      27.46      |

A few specificities of the test corpus as well as coreferee and the evaluation may explain a number of the false negatives and false positives :
- the mentions are only considered as valid if the token boundaries in the response match the token boundaries in the key. When there is no exact match, the mention is considered missed/invented and ignored altogether in the subsequent scorings. This is shown by the difference between the recall of the identification of mentions (56.83) and the proportion of covered mentions (69.6) which ought to be the same if the partial matches were considered valid.
- The test corpus is a subset of DEMOCRAT. Many documents that are part of DEMOCRAT are novels or short stories. coreferee (as such) is not very well suited to such genres for several reasons :
   - In those genres, the coreference chains tend to span very long distances. Some entities are first mentioned much earlier in the same chapter or even in previous chapter and resolving coreference in those cases may require information that were established much earlier on the entity. In a nutshell, those genres include coreference that operates on a global level (typically information that the reader keeps in his long term memory). Since coreferee operates on a local level, by connecting close mentions to each others in order to build longer chains, such types of coreference cannot be captured by coreferee. 
   - Those genres include a large amount of reported speech, whether between quotes or not. This means that the anaphora may have a change of point of view between first person, second person and third person. Besides the fact that those types of coreference is extremely hard to resolve in general, since only the third person is covered by coreferee,  this causes a lot of missed mentions.
- As we already mentioned, the corpus is divided arbitrarily is shorter documents of 15 sentences. This means that a previous mention that was necessary to connect two subsequent mentions may not be present in the new document. In this example, the slash marks an arbitrary split between documents that were originally only one document :
  -  "Madame Dupont est arrivée" / "Elle est bien habillée aujourd'hui. Madame Dupont est sur son 31". Since the first mention of the entity in the document is an anaphora it is not possible to determine to which noun it refers to.
- For processing as well as pragmatic reasons, the maximum coreferring noun sentence referential distance (see more advanced use section) includes the pairing of obviously corefering proper noun. Two mentions of "Charles de Gaulle" that are many sentences apart would be included in two different chains although this would be easy to merge the two chains after processing. As a consequence entities tend to be "undermerged" which impacts the recall.
- 
### Advice for use
Based on our observation and understanding of the model, the optimal genres to use the model on would be genres with the following characteristics :
- written text. The models were not tested yet on oral data but since all the development corpus were written data, we are not very confident in the performance of the model on oral data.
- prose. same as above, this was not tested but we expect a decreased performance on never seen before poetry genres.
- not too complex sentence structures. Typically , long compound sentences with embedded dependent clauses that are found in literary genres would not be welcome
- relatively short documents. Documents that do not require callback to much earlier information for coreference resolution
- Few changes of voices in the documents. Reported speech is taken into account to some extent but since coreferee is focused on third person mentions, it would underperform on texts with frequent changes of voices such as dialogues.


Examples of genres that we believe coreferee would be well suited for include : press articles, social media, encyclopedia articles, reports ...


## List of files in this repository

This repository includes the major scripts that were developed during this project. 
- config.cfg : config file listing the supported spacy models
- language_specific_rules.py : rules specific to the french models of coreferee. Those rules define the mentions (independent noun and anaphora) and ensure grammatical, syntactic and semantic compatibility between the potentially coreferring mentions.
- loaders.py : contains classes to load the corpus that were used for training
- test_rules_fr.py : unit test with a set of examples to test the rules developed in language_specific_rules.py
- test_smoke_tests_fr.py :  unit test with a set of examples to test the rules and the output of the neural ensemble
- coreferee_to_conll.py : takes a conll file as input and writes a new conll with the last column being the coreference annotation made by spacy and coreferee. Alternatively you can pass a text file as input to produce a conll output.
- build_mentions.py : contains useful functions to build mention phrases from the output of coreferee

