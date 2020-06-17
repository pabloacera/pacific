#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 09:32:02 2020

PACIFIC takes a FASTA/FASTQ input file and predicts the presence of the following viruses and their relative sample proportions:
        SARS-CoV-2,
        128 taxonomic units from Influenza,
        5 species from Metapneumovirus,
        130 species from Rhinovirus, and
        11 species from Coronaviridae (non-SARS-CoV-2).                                

@author: Pablo Acera

"""

import argparse

parser = argparse.ArgumentParser(prog='PACIFIC v0.1', description=
                                 """ 
                                 PACIFIC takes a FASTA/FASTQ input file and predicts the presence of the following viruses and their relative sample proportions:
                                 SARS-CoV-2,
                                 128 taxonomic units from Influenza,
                                 5 species from Metapneumovirus,
                                 130 species from Rhinovirus, and
                                 11 species from Coronaviridae (non-SARS-CoV-2).
                                 
                                 We recommend that users use default parameters to ensure high accuracy.
                                 """, usage='python PACIFIC.py [options] -i <in.fa>|<in.fq> -m <model> -t <tokenizer> -l <label-maker>\nversion: %(prog)s')

OPTIONAL = parser._action_groups.pop()
REQUIRED = parser.add_argument_group('required arguments')

#Inputs
## CHANGE -m  -t -l -f to OPTIONAL and CREATE RELATIVE PATHS FOR THESE FILES

REQUIRED.add_argument("-i", "--input_file",
                      help="FASTA/FASTQ input file path",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-m", "--model",
                      help="PACIFIC model file path",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-t", "--tokenizer",
                      help="Tokenizer file path",
                      metavar='\b',
                      required=True)

REQUIRED.add_argument("-l", "--label_maker",
                      help="Label maker object file path",
                      metavar='\b',
                      required=True)

#arguments
OPTIONAL.add_argument("-f", "--file_type",
                      help='FASTA or FASTQ training file format [fasta]',
                      metavar='<fasta/fastq>',
                      default='fasta',
                      )

OPTIONAL.add_argument("-o", "--outputdir",
                      help='Path to output directory [.]',
                      metavar='<dir>',
                      default=".")

#OPTIONAL.add_argument("-k", "--k_mers",
#                      help='K-mer number use to train the model [9]',
#                      default=9,
#                      type=int)

OPTIONAL.add_argument("-T", "--prediction_threshold",
                      help='Threshold/cutoff for predictions [0.95]',
                      metavar='<float>',
                      default=0.95,
                      type=int
                      )

OPTIONAL.add_argument("-c", "--chunk_size",
                      help='Number of reads per chunk [10000]',
                      metavar='<int>',
                      default=50000,
                      type=int
                      )                      

OPTIONAL.add_argument("-O", "--output_fasta",
                      help='If this option is "True", a FASTA file containing predictions for each read will be provided [False]',
                      default=False,
                      action='store_true'
                      )

OPTIONAL.add_argument('-v', '--version', 
                        action='version', 
                        version='%(prog)s')


parser._action_groups.append(OPTIONAL)

ARGS = parser.parse_args()

# Inputs
FILE_IN = ARGS.input_file
MODEL = ARGS.model
TOKENIZER = ARGS.tokenizer
LABEL_MAKER = ARGS.label_maker


# Arguments
MODEL = ARGS.model
FILE_TYPE = ARGS.file_type
OUTPUTDIR = ARGS.outputdir
THRESHOLD_PREDICTION = ARGS.prediction_threshold
OUTPUT_FASTA = ARGS.output_fasta
CHUNK_SIZE = ARGS.chunk_size

# import other packages
from Bio import SeqIO

import pickle
from keras.models import load_model
import random
import numpy as np
import pandas as pd
import tensorflow as tf
import os
import sys

# hardcode paths to tokenizer and label maker
dirname = os.path.dirname(__file__)
#TOKENIZER = os.path.join(dirname, '../model', 'tokenizer.01.pacific_9mers.pickle')
#LABEL_MAKER = os.path.join(dirname, '../model', 'label_maker.01.pacific_9mers.pickle')


def process_reads(sequences, kmer, names):
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


def main(all_transcripts, names, k_mer_size):
    '''
    '''
    reads, names_p = process_reads(all_transcripts, 
                                   k_mer_size,
                                   names)

    return all_transcripts, reads, names_p

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

def predict_chunk(sequences,
                 names,
                 K_MERS,
                 FILE_TYPE,
                 total_results,
                 total_sequences):
    '''
    Predicting and write a chunk of reads
    '''
    
    total_sequences += len(sequences)
    
    reads, kmer_sequences, names = main(sequences,
                                        names,
                                        K_MERS,
                                        )
    
    kmer_sequences = tokenizer.texts_to_sequences(kmer_sequences)
       
    predictions = model.predict(np.array(kmer_sequences))
    labels = label_maker.inverse_transform(np.array(predictions), threshold=THRESHOLD_PREDICTION)
        
    if OUTPUT_FASTA is True:
        print()
        fasta_name_out = OUTPUTDIR+'/tmp_output_'+str(counter)
        print('writting temporary output file '+fasta_name_out)
        with open(fasta_name_out,'w') as output:
            for i in enumerate(names):
                print('>'+i[1]+':'+str(max(predictions[i[0]]))+':'+labels[i[0]], file=output)
                print(reads[i[0]], file=output)
                total_results[labels[i[0]]] += [max(predictions[i[0]])]
                
    return total_results, total_sequences


if __name__ == '__main__':

    seed_value = 42
    random.seed(seed_value)# 3. Set `numpy` pseudo-random generator at a fixed value
    np.random.seed(seed_value)# 4. Set `tensorflow` pseudo-random generator at a fixed value
    try:
        tf.random.set_seed(seed_value)# 5. For layers that introduce randomness like dropout, make sure to set seed values 
    except:
        tf.set_random_seed(seed_value)
    
    config = tf.compat.v1.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.compat.v1.Session(config=config)
    
    K_MERS = 9
    
    model = load_model(MODEL)
    
    # Keras loading sequences tokenizer 
    with open(TOKENIZER, 'rb') as handle:
        tokenizer = pickle.load(handle)
        
    # loading label maker
    with open(LABEL_MAKER, 'rb') as handle:
        label_maker = pickle.load(handle)
    
    print()    
    print('Reading input file...')
    print()
    
    total_results = {'Sars_cov_2': [],
                     'Coronaviridae': [],
                     'Influenza': [],
                     'Metapneumovirus': [],
                     'Rhinovirus': [],
                     'Human': []
                     }
    
    total_sequences = 0
    fasta_sequences = SeqIO.parse(open(FILE_IN), FILE_TYPE)
    sequences = []
    names = []
    counter = 0
    for fasta in fasta_sequences:
        name, sequence = fasta.id, str(fasta.seq)
        sequences.append(sequence)
        names.append(name)
        counter +=1
        if counter%CHUNK_SIZE == 0:
            
            total_results, total_sequences = predict_chunk(sequences,
                                                           names,
                                                           K_MERS,
                                                           FILE_TYPE,
                                                           total_results,
                                                           total_sequences)
            sequences = []
            names = []
            print()
            print('predictig reads: '+str(counter-CHUNK_SIZE)+' '+str(counter))
            
    total_results, total_sequences = predict_chunk(sequences,
                                                   names,
                                                   K_MERS,
                                                   FILE_TYPE,
                                                   total_results,
                                                   total_sequences)
    
    tmp_files = os.listdir(OUTPUTDIR)
    tmp_files = [i for i in tmp_files if i.startswith('tmp_output')]
    import shutil
    
    if OUTPUT_FASTA is True:
        print()
        print('Writting final output FASTA '+OUTPUTDIR+'/output_pacific.fasta')
        with open('output_PACIFIC.fasta','wb') as wfd:
            for f in tmp_files:
                with open(OUTPUTDIR+'/'+f,'rb') as fd:
                    shutil.copyfileobj(fd, wfd)

    for delete_file in tmp_files:
        os.remove(OUTPUTDIR+'/'+delete_file)
        print()
        print('Deleting temporary file '+delete_file)
    
    
    processed_reads = len(total_results['Influenza'])+\
                      len(total_results['Coronaviridae'])+\
                      len(total_results['Metapneumovirus'])+\
                      len(total_results['Rhinovirus'])+\
                      len(total_results['Sars_cov_2'])+\
                      len(total_results['Human'])
                      
    if len(processed_reads) == 0:
        print('None processed reads')
        sys.exit()
    
    
    print()
    print('From a total of '+str(total_sequences)+' reads, '+str(total_sequences - processed_reads)+\
          ' were discarded, (probabbly due to non-standart nucleotides or too short reads)')
    
    df_results = pd.DataFrame()
    
    df_results['Class'] = ['SARS-CoV-2', 'Coronaviridae', 
                           'Influenza', 'Metapneumovirus', 
                           'Rhinovirus','Human']

    df_results['# predicted reads'] = [len(total_results['Sars_cov_2']),
                                       len(total_results['Coronaviridae']),
                                       len(total_results['Influenza']),
                                       len(total_results['Metapneumovirus']),
                                       len(total_results['Rhinovirus']),
                                       len(total_results['Human'])
                                          ]
    
    percentage = {}
    for classes in total_results:
        number_class = len(total_results[classes])
        percentage[classes] = (number_class/processed_reads) *100
    
    df_results['# predicted reads (%)'] = [percentage['Sars_cov_2'],
                                           percentage['Coronaviridae'],
                                           percentage['Influenza'],
                                           percentage['Metapneumovirus'],
                                           percentage['Rhinovirus'],
                                           percentage['Human']
                                          ]
    threshold_reads = {}
    total_threshold_reads = 0
    for classes in total_results:
        numpy_class = np.array(total_results[classes])
        threshold_reads[classes] = len(numpy_class[numpy_class > THRESHOLD_PREDICTION])
        total_threshold_reads +=threshold_reads[classes]
    
    df_results['# predicted reads above '+str(THRESHOLD_PREDICTION)] = [threshold_reads['Sars_cov_2'],
                                                                        threshold_reads['Coronaviridae'],
                                                                        threshold_reads['Influenza'],
                                                                        threshold_reads['Metapneumovirus'],
                                                                        threshold_reads['Rhinovirus'],
                                                                        threshold_reads['Human']
                                                                       ]
    
    df_results['# predicted reads above '+str(THRESHOLD_PREDICTION)+' (%)'] = \
               [threshold_reads['Sars_cov_2']/total_threshold_reads*100 ,
                threshold_reads['Coronaviridae']/total_threshold_reads*100,
                threshold_reads['Influenza']/total_threshold_reads*100,
                threshold_reads['Metapneumovirus']/total_threshold_reads*100,
                threshold_reads['Rhinovirus']/total_threshold_reads*100,
                threshold_reads['Human']/total_threshold_reads*100
               ]
    
    
    print()
    print(df_results)
    df_results.to_csv(OUTPUTDIR+'/output_PACIFIC.txt')
    print()
    print('Thank you for using PACIFIC =^)')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

















