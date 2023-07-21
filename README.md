# event-prediction

To reproduce the experiment described in [the bachelor thesis](./bachelor_thesis_final.pdf), run the scripts in the following order:

Most documentation can be found in the code itself, but if something is not clear, please feel free to contact me.

### Training the model:
1. Start by annotating data using [./label_studio/](./label_studio/) .  There, [a readme file](./label_studio/README.md) can be found that explains the setup process. This folder also contains the [annotation guidelines](./label_studio/annotation_guidelines.pdf) and [annotation flowchart](./label_studio/annotation_flowchart.md).
1. Use [inter_annotator.py](./inter_annotator.py) to compute the inter-annotator agreement between different annotations. Do not forget to use the different options if you only use a selection of the annotations.
1. Use [merge_annotations.py](./merge_annotations.py) to merge annotations made by multiple people. Our merged annotations are in [data/annotations](./data/annotations/all_annotations.json).
1. Pass the annotations to [finetune_bertje.py](./finetune_bertje.py) to train the model.

### Events & canonicity
1. Then use [select_novels.ipynb](./select_novels.ipynb) to select novels based on the criteria, save their names to a file, and copy the selection from a restricted corpus to a working folder. Access to the corpus can be requested [here](https://zenodo.org/record/5887620). This is also where [the metadata file](./data/novels/_metadata.tsv) originates.
1. Use [format_novels.sh](./format_novels.sh) to unpack the novels and tokenize them using [Alpino tokenizer](https://www.let.rug.nl/vannoord/alp/Alpino/) which is stored in the [Alpino folder](./Alpino/Tokenization/).
1. Use [predict_events.py](./predict_events.py) to predict events on the selected novels.
1. Run [compute_correlations_large.ipynb] to load the predictions and compute all the correlations and regression models.


_Notes: Below are some files that were not mentioned above and their function:_
* [util.py](./util.py) contains the Annotation class used for inter-annotator agreement calculation and event prediction.  
* [compute_correlation_small.ipynb](./compute_correlation_small.ipynb) is used to compute the correlation for a smaller set of novels with 29 canonical and 29 non-canonical novels, but this set was too small so we abandoned it.  
* [visualizations.ipynb](./visualizations.ipynb) is used to plot some visualizations that did not belong anywhere else, like the plot of computational resource usage while training the model.
