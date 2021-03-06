# coding = 'utf-8'
from sklearn.metrics import accuracy_score
from sklearn.metrics import precision_score
from sklearn.metrics import recall_score
from sklearn.metrics import f1_score
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
from ..general.util import get_var_type
from .encoder import CategoryEncoder, DiscreteEncoder, to_str
from copy import deepcopy
import numpy as np
from collections import OrderedDict


def get_eval_index(y, y_predict, metric='acc'):
    if metric == 'acc':
        return accuracy_score(y, y_predict)
    elif metric == 'precision':
        return precision_score(y, y_predict)
    elif metric == 'recall':
        return recall_score(y, y_predict)
    elif metric == 'macro_f1':
        return f1_score(y, y_predict, average='macro')
    elif metric == 'micro_f1':
        return f1_score(y, y_predict, average='micro')
    elif metric == 'auc':  # TODO: Add a warning checking if y_predict is all [0, 1], it should be probability
        return roc_auc_score(y, y_predict)
    else:
        raise Exception("Not implemented yet.")


def fit_and_predict(train, test, target, nbin=10, smoothing=0.8, predict_prob=False):
    """
    We assume that 'target' variable have no prefix
    :param train:
    :param test:
    :param target:
    :return:
    """
    var_type_dict = get_var_type(train)
    continuous_var = var_type_dict['continuous']
    discrete_encoder = DiscreteEncoder()

    discrete_encoder.fit(train, continuous_var, [('quantile', nbin)])
    train_new = discrete_encoder.transform(train)
    test_new = discrete_encoder.transform(test)

    var_type_dict_new = get_var_type(train_new)
    discrete_var_new = var_type_dict_new['discrete']
    all_var = deepcopy(discrete_var_new)
    all_var.append(target)
    category_encoder = CategoryEncoder()

    train_discrete = train_new[all_var]
    test_discrete = test_new[all_var]
    for column in train.columns:
        train_discrete[column] = train_discrete[column].map(to_str)
        test_discrete[column] = test_discrete[column].map(to_str)

    category_encoder.fit(train_discrete, target, discrete_var_new, [('target', {'smoothing': smoothing})])
    train_transformed = category_encoder.transform(train_discrete)
    test_transformed = category_encoder.transform(test_discrete)

    var_type_transformed = get_var_type(train_transformed)
    continuous_var = var_type_transformed['continuous']

    train_x = train_transformed[continuous_var]
    test_x = train_transformed[continuous_var]
    train_y = test_transformed[target]

    clf = LogisticRegression()
    clf.fit(train_x, train_y)

    if predict_prob:
        return clf.predict_proba(test_x)
    else:
        return clf.predict(test_x)


def get_perm_importance(train, test, target, metric='acc', nbins=10, smoothing=0.8, predict_prob=False):
    columns = list(train.columns)
    columns.remove(target)
    result = OrderedDict()

    y_pred = fit_and_predict(train, test, target, nbins, smoothing, predict_prob)
    orig_metric = get_eval_index(test[target], y_pred, metric)

    for x_var in columns:
        train_copy = train.copy(deep=True)
        train_copy[x_var] = np.random.permutation(train_copy[x_var])
        y_pred = fit_and_predict(train_copy, test, target, nbins, smoothing, predict_prob)
        result[x_var] = get_eval_index(test[target], y_pred, metric)

    for k, v in result.items():
        result[k] -= orig_metric
    return result
