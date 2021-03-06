import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tensorflow as tf
import keras.backend as K
from keras.models import load_model

def import_model(path):
    """Import model from given path and assign it to appropriate devices"""
    K.clear_session()
    config = tf.compat.v1.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    config.gpu_options.allow_growth = True
    tfsess = tf.compat.v1.Session(config=config)
    tf.compat.v1.keras.backend.set_session(tfsess)
    model = load_model(path)
    return model

def sample(preds, temperature=1.0):
        preds = np.asarray(preds).astype('float64')
        preds = np.log(preds) / temperature
        exp_preds = np.exp(preds)
        preds = exp_preds / np.sum(exp_preds)
        probas = np.random.multinomial(1, preds, 1)
        return np.argmax(probas)

def visitize(seq, termination):
    patient = []
    code_active = -1
    visit = []
    for i, code in enumerate(seq):
        if i == len(seq)-1:
            break
        if code == 0:
            continue
        else:
            code -= 1
        code_type = (int)(code/3)
        if code_active >= code_type:
            patient.append(visit)
            visit = []

        visit.append(code)
        code_active = code_type

    patient.append(visit)
    if seq[-1] == termination[0]:
        mort = 1
    else:
        mort = 0

    return patient, mort


def main(ARGS):
    model = import_model(ARGS.path_model)
    patients = []
    morts = []

    step = int(ARGS.num_generate/10)

    # experiment 1: Give med2 only then give 1 med1.
    # Start off with either 3 med2's, or 2 med2's and both.

    temperature = 0.8
        
    if ARGS.simple:
        med2_codes = np.arange(4, 7)
        med1_codes = np.arange(1, 4)
        termination = [13, 14]
    else:
        med2_codes = np.arange(19, 37)
        med1_codes = np.arange(1, 19)
        termination = [64, 65]

    for i in range(ARGS.num_generate):
        if i % step == 0:
            print('Generating %d out of %d' % (i, ARGS.num_generate))


        med1_sequence = np.zeros((1, ARGS.maxlen))
        med1_sequence[0, -ARGS.duration:] = np.random.choice(med1_codes, ARGS.duration)

        med1_sequence = med1_sequence.astype(int)

        med1_list = med1_sequence.copy().tolist()[0]

        for n in range(ARGS.max_visits):
            preds = model.predict(med1_sequence, verbose = 0)[0]
            next_code = sample(preds, temperature)
            med1_list.append(next_code)
            if next_code in termination:
                break
            med1_sequence[0, :ARGS.maxlen-1] = med1_sequence[0, 1:]
            med1_sequence[0, ARGS.maxlen-1] = next_code

      
        if med1_list[-1] not in termination:
            med1_list.append(termination[1])

        med1_patient, mort = visitize(med1_list, termination)
        morts.append(mort)

        patients.append(med1_patient)
        
    all_data = pd.DataFrame(data={'codes': patients}, columns=['codes']).reset_index()
    all_targets = pd.DataFrame(data={'target': morts},columns=['target']).reset_index()

    all_data.sort_index().to_pickle(ARGS.directory+'/data_med1_test.pkl')
    all_targets.sort_index().to_pickle(ARGS.directory+'/target_med1_test.pkl')


def parse_arguments(parser):
    """Read user arguments"""
    parser.add_argument('--path_model', type=str, default='data/data_train.pkl',
                        help='Path to train data')
    parser.add_argument('--directory', type=str, default='./',
                        help='Path to output, if any')
    parser.add_argument('--maxlen', type=int, default=3,
                        help='Maximum length of LSTM')
    parser.add_argument('--num_generate', type=int, default=100,
                        help='Number of samples to generate * 2')
    parser.add_argument('--max_visits', type=int, default=30,
                        help='Number of visits to generate')
    parser.add_argument('--decodify', type=bool, default=False,
                        help='Decode if codified already')
    parser.add_argument('--simple', type=bool, default=False,
                        help='If simple, then process differently')
    parser.add_argument('--duration', type=int, default=2,
                        help='Duration of experiment treatment')
    args = parser.parse_args()

    return args


if __name__ == '__main__':

    PARSER = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ARGS = parse_arguments(PARSER)
    main(ARGS)