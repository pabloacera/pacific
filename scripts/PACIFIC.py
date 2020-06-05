#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 09:32:02 2020

PACIFIC takes as input a FASTA/FASTQ file and predict presence of viruses:
    SARS-CoV-2
    128 taxonomic units from Influenza
    5 from metapneumovirus
    130 species from rhinovirus 
    11 species from Coronaviridae (non-SARS-CoV-2).

@author: Pablo Acera

"""

import argparse

parser = argparse.ArgumentParser(description=
                                 """
                                 PACIFIC takes as input a FASTA/FASTQ file and predict presence of viruses:
                                 SARS-CoV-2
                                 128 taxonomic units from Influenza
                                 5 from metapneumovirus
                                 130 species from rhinovirus 
                                 11 species from Coronaviridae (non-SARS-CoV-2).
                                 
                                 We recommend to keep default parameters to ensure high accuracy.
                                 """)

OPTIONAL = parser._action_groups.pop()
REQUIRED = parser.add_argument_group('required arguments')

#Inputs
REQUIRED.add_argument("--FILE_IN",
                      help="FASTA/FASTQ file path to use PACIFIC",
                      required=True)

REQUIRED.add_argument("--model",
                      help="PACIFIC model path PACIFIC",
                      required=True)

REQUIRED.add_argument("--tokenizer",
                      help="Tokenizer file path",
                      required=True)

REQUIRED.add_argument("--label_maker",
                      help="Label maker object file path",
                      required=True)

REQUIRED.add_argument("--file_type",
                      help='fasta or fastq training files format (all files should have same format)',
                      default='fasta',
                      )

#arguments
OPTIONAL.add_argument("--FILE_OUT",
                      help='path to the output file',
                      default="./pacific_output.txt")

OPTIONAL.add_argument("--k_mers",
                      help='K-mer number use to train the model',
                      default=9,
                      type=int)

OPTIONAL.add_argument("--prediction_threshold",
                      help='Threshold to use for the prediction',
                      default=0.95,
                      type=int
                      )

parser._action_groups.append(OPTIONAL)

ARGS = parser.parse_args()

# Inputs
FILE_IN = ARGS.FILE_IN
MODEL = ARGS.model
TOKENIZER = ARGS.tokenizer
LABEL_MAKER = ARGS.label_maker


# Arguments
K_MERS = ARGS.k_mers
MODEL = ARGS.model
FILE_TYPE = ARGS.file_type
FILE_OUT = ARGS.FILE_OUT
THRESHOLD_PREDICTION = ARGS.prediction_threshold

# import other packages
from Bio import SeqIO

import pickle
from keras.models import load_model
import random
import numpy as np
import pandas as pd
import tensorflow as tf


def prepare_read(trancriptome, file_type):
    '''
    function will take tranciprtome and make reads
    '''
    fasta_sequences = SeqIO.parse(open(trancriptome),file_type)
    sequences = []
    names = []
    for fasta in fasta_sequences:
        name, sequence = fasta.id, str(fasta.seq)
        sequences.append(sequence)
        names.append(name)
    return sequences, names


def process_reads(sequences, length, kmer, names):
    '''
    '''
    r_reads = []
    new_names = []
    for i in enumerate(sequences):
        # check the reads does not contain weird characters
        if all(c in 'AGCT' for c in i[1].upper()) and len(i[1]) >= 150:
            read = i[1][:150]
            r_reads.append(' '.join(read[x:x+kmer].upper() for x in range(len(read) - kmer + 1)))
            new_names.append(names[i[0]])
    return r_reads, new_names


def main(file, size_lenght, k_mer_size, file_type):
    '''
    '''
   
    all_transcripts, names = prepare_read(file,
                                   file_type)
    reads, names = process_reads(all_transcripts, 
                           size_lenght,
                           k_mer_size,
                           names)
    return reads, names

def accuracy(labels, predictions):
    '''
    calculate accuracy
    '''
    try:
        if labels.shape != predictions.shape:
            print('labels and predictions does not have same dimentions')
            return False
        
        correct = 0
        for i in range(len(labels)):
            if labels[i] == predictions[i]:
                correct +=1
    except:
        return 0
    
    return correct/len(labels)


if __name__ == '__main__':

    seed_value = 42
    random.seed(seed_value)# 3. Set `numpy` pseudo-random generator at a fixed value
    np.random.seed(seed_value)# 4. Set `tensorflow` pseudo-random generator at a fixed value
    tf.set_random_seed(seed_value)# 5. For layers that introduce randomness like dropout, make sure to set seed values 
    
    '''
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    '''
    
    model = load_model(MODEL)
    
    # Keras loading sequences tokenizer 
    with open(TOKENIZER, 'rb') as handle:
        tokenizer = pickle.load(handle)
        
    # loading label maker
    with open(LABEL_MAKER, 'rb') as handle:
        label_maker = pickle.load(handle)
    
    print()    
    print('Converting reads into k-mers...')
    print()
    
    # Convert reads into k-mers
    kmer_sequences, names = main(FILE_IN,
                                 150, 
                                 K_MERS,
                                 FILE_TYPE)
    
    sequences = tokenizer.texts_to_sequences(kmer_sequences)
    print()
    print('Making predictions...')
       
    predictions = model.predict(np.array(sequences))
    
    print()
    print('Using '+str(THRESHOLD_PREDICTION)+' thresholds to filter predictions...')
    
    predictions_high_acc = []
    names_high_acc = []
    for i in enumerate(predictions):
        if max(i[1]) > THRESHOLD_PREDICTION:
            predictions_high_acc.append(i[1])
            names_high_acc.append(names[i[0]])

    labels = label_maker.inverse_transform(np.array(predictions_high_acc), threshold=THRESHOLD_PREDICTION)
    
    df = pd.DataFrame(predictions_high_acc, columns = ['Coronaviridae',
                                                       'Human',
                                                       'Influenza',
                                                       'Metapneumovirus',
                                                       'Rhinovirus',
                                                       'Sars_cov_2'])
    
    df['Read_id'] = names_high_acc
    
    df['Labels'] = labels
    
    cols = ['Read_id',
            'Coronaviridae',
            'Human',
            'Influenza',
            'Metapneumovirus',
            'Rhinovirus',
            'Sars_cov_2',
            'Labels'
            ]
    
    df = df[cols]
    
    Cornidovirineae = len(labels[labels == 'Coronaviridae']) / len(labels) * 100
    Human = len(labels[labels == 'Human']) / len(labels) * 100
    Influenza =  len(labels[labels == 'Influenza']) / len(labels) * 100
    Metapneumovirus =  len(labels[labels == 'Metapneumovirus']) / len(labels) * 100
    Rhinovirus =  len(labels[labels == 'Rhinovirus']) / len(labels) * 100
    Sars_cov_2 =  len(labels[labels == 'Sars_cov_2']) / len(labels) * 100
    
    results = {Influenza,
               Coronaviridae,
               Metapneumovirus,
               Rhinovirus,
               SARS_CoV_2, 
               }
    
    
    print()
    print('Saving output file to ', FILE_OUT)
    
    df.to_csv(FILE_OUT, sep='\t')
    
    print()
    print('Relative proportion of virus in the sample')
    print()
    
    # specify the number of discarted reads
    
    print('Cornidovirineae: ', Cornidovirineae)
    
    print('Human: ', Human)
    
    print('Influenza', Influenza)
    
    print('Metapneumovirus', Metapneumovirus)
    
    print('Rhinovirus', Rhinovirus)
    
    print('Sars_cov_2', Sars_cov_2)
    
    print('Virus group proportions that overpass the empirical threshold are: ')
    
    limit_detection = {'Influenza': 0.001,
                       'Coronaviridae': 0.007,
                       'Metapneumovirus': 0.001,
                       'Rhinovirus': 0.0242,
                       'SARS_CoV_2': 0.017 
                      }
    
    for virus in results:
        if virus > limit_detection[str(virus)]:
            print(str(virus))
    
    print()
    print('Thank you for using PACIFIC')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

















