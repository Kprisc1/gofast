# -*- coding: utf-8 -*-
#   License: BSD-3-Clause
#   Author: LKouadio <etanoyau@gmail.com>
"""
Learning utilities for data transformation, 
model learning and inspections. 
"""
from __future__ import annotations 
import os
import re 
import copy 
import inspect 
import tarfile 
import warnings 
import pickle 
import joblib
import datetime 
import shutil 
from six.moves import urllib 
from collections import Counter 
import numpy as np 
import pandas as pd 
from pathlib import Path
from tqdm import tqdm

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectFromModel, SelectKBest
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, StratifiedShuffleSplit 
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.preprocessing import OneHotEncoder,RobustScaler ,OrdinalEncoder 
from sklearn.preprocessing import StandardScaler,MinMaxScaler,  LabelBinarizer
from sklearn.preprocessing import LabelEncoder,Normalizer, PolynomialFeatures 
from sklearn.utils import all_estimators, resample

from .._gofastlog import gofastlog
from .._typing import List, Tuple, Any, Dict,  Optional,Union, Iterable,Series 
from .._typing import _T, _F, ArrayLike, NDArray,  DataFrame, Set 
# from ._dependency import import_optional_dependency
from ..exceptions import ParameterNumberError, EstimatorError          
from .coreutils import _assert_all_types, _isin,  is_in_if,  ellipsis2false
from .coreutils import smart_format,  is_iterable, get_valid_kwargs
from .coreutils import is_classification_task, to_numeric_dtypes, fancy_printer
from .coreutils import validate_feature, download_progress_hook, exist_features
from .coreutils import contains_delimiter 
from .funcutils import ensure_pkg
from .validator import get_estimator_name, check_array, check_consistent_length
from .validator import  _is_numeric_dtype,  _is_arraylike_1d 
from .validator import  is_frame, build_data_if, check_is_fitted
from .validator import check_mixed_data_types 

_logger = gofastlog().get_gofast_logger(__name__)


__all__=[ 
    "evaluate_model",
    "select_features", 
    "get_global_score", 
    "get_correlated_features", 
    "categorize_target", 
    "resampling", 
    "bin_counting", 
    "labels_validator", 
    "rename_labels_in" , 
    "soft_imputer", 
    "soft_scaler", 
    "select_feature_importances", 
    "load_model", 
    "make_pipe",
    "build_data_preprocessor", 
    "bi_selector", 
    "get_target", 
    "extract_target",  
    "stats_from_prediction", 
    "fetch_tgz", 
    "fetch_model", 
    "load_csv", 
    "discretize_categories", 
    "stratify_categories", 
    "serialize_data", 
    "deserialize_data", 
    "soft_data_split",
    "laplace_smoothing", 
    "laplace_smoothing_categorical", 
    "laplace_smoothing_word", 
    "handle_imbalance", 
    "smart_split",
    "save_dataframes"
    ]


def codify_variables (
    data:DataFrame | ArrayLike, /, 
    columns: list =None, 
    func: _F=None, 
    categories: dict=None, 
    get_dummies:bool=..., 
    parse_cols:bool =..., 
    return_cat_codes:bool=... 
    ) -> DataFrame: 
    """ Encode multiple categorical variables in a dataset. 
    
    Encodes categorical variables in a dataset by applying specified transformations,
    mapping categories, or performing one-hot encoding. Supports DataFrame, 
    array-like, or dictionary inputs for data.

    Parameters 
    -----------
    arr: pd.DataFrame, ArrayLike, dict 
       DataFrame or Arraylike. If simple array is passed, specify the 
       columns argumment to create a dataframe. If a dictionnary 
       is passed, it should be convert to a dataframe. 
       
    columns: list,
       List of the columns to encode the labels 
       
    func: callable, 
       Function to apply the label accordingly. Label must be included in 
       the columns values.
       
    categories: dict, Optional 
       Dictionnary of column names(`key`) and labels (`values`) to 
       map the labels.  
       
    get_dummies: bool, default=False 
      returns a new encoded DataFrame  with binary columns 
      for each category within the specified categorical columns.

    parse_cols: bool, default=False
      If `columns` parameter is listed as string, `parse_cols` can defaultly 
      constructs an iterable objects. 
    
    return_cat_codes: bool, default=False 
       return the categorical codes that used for mapping variables. 
       if `func` is applied, mapper returns an empty dict. 
       
    Return
    -------
    df: New encoded Dataframe 
    
    Examples
    ----------
    >>> from gofast.tools.mlutils import codify_variables 
    >>> # Sample dataset with categorical variables
    >>> data = {'Height': [152, 175, 162, 140, 170], 
        'Color': ['Red', 'Blue', 'Green', 'Red', 'Blue'],
        'Size': ['Small', 'Large', 'Medium', 'Medium', 'Small'],
        'Shape': ['Circle', 'Square', 'Triangle', 'Circle', 'Triangle'], 
        'Weight': [80, 75, 55, 61, 70]
    }
    # List of categorical columns to one-hot encode
    categorical_columns = ['Color', 'Size', 'Shape']
    >>> df_encoded = codify_variables (data)
    >>> df_encoded.head(2) 
    Out[1]: 
       Height  Weight  Color  Size  Shape
    0     152      80      2     2      0
    1     175      75      0     0      1
    >>> # new return_map codes 
    >>> df_encoded , map_codes =codify_variables (
        data, return_cat_codes =True )
    >>> map_codes 
    Out[2]: 
    {'Color': {2: 'Red', 0: 'Blue', 1: 'Green'},
     'Size': {2: 'Small', 0: 'Large', 1: 'Medium'},
     'Shape': {0: 'Circle', 1: 'Square', 2: 'Triangle'}}
    >>> def cat_func (x ): 
        # 2: 'Red', 0: 'Blue', 1: 'Green'
        if x=='Red': 
            return 2 
        elif x=='Blue': 
            return 0
        elif x=='Green': 
            return 1 
        else: return x 
    >>> df_encoded =codify_variables (data, func= cat_func)
    >>> df_encoded.head(3) 
    Out[3]: 
       Height  Color    Size     Shape  Weight
    0     152      2   Small    Circle      80
    1     175      0   Large    Square      75
    2     162      1  Medium  Triangle      55
    >>> 
    >>> # Perform one-hot encoding
    >>> df_encoded = codify_variables (data, get_dummies=True )
    >>> df_encoded.head(3)
    Out[4]: 
       Height  Weight  Color_Blue  ...  Shape_Circle  Shape_Square  Shape_Triangle
    0     152      80           0  ...             1             0               0
    1     175      75           1  ...             0             1               0
    2     162      55           0  ...             0             0               1
    [3 rows x 11 columns]
    >>> codify_variables (data, categories ={'Size': ['Small', 'Large',  'Medium']})
    Out[5]: 
       Height  Color     Shape  Weight  Size
    0     152    Red    Circle      80     0
    1     175   Blue    Square      75     1
    2     162  Green  Triangle      55     2
    3     140    Red    Circle      61     2
    4     170   Blue  Triangle      70     0
    """
    get_dummies, parse_cols, return_cat_codes = ellipsis2false(
        get_dummies, parse_cols, return_cat_codes )
    # build dataframe if arr is passed rather 
    # than a dataframe 
    df = build_data_if( data, to_frame =True, force=True, input_name ='col',
                        raise_warning='silence'  )
    # now check integrity 
    df = to_numeric_dtypes( df )
    if columns is not None: 
        columns = list( 
            is_iterable(columns, exclude_string =True, transform =True, 
                              parse_string= parse_cols 
                              )
                       )
        df = select_features(df, features = columns )
        
    map_codes ={}     
    if get_dummies :
        # Perform one-hot encoding
        # We use the pd.get_dummies() function from the pandas library 
        # to perform one-hot encoding on the specified columns
        return ( ( pd.get_dummies(df, columns=columns) , map_codes )
                  if return_cat_codes else ( 
                          pd.get_dummies(df, columns=columns) ) 
                )
    # ---work with category -------- 
    # if categories is Note , get auto numeric and 
    # categoric variablees 
    num_columns, cat_columns = bi_selector (df ) 
    
    # apply function if 
    if func is not None: 
        # just get only the columns 
        if not callable (func): 
            raise TypeError(
                f"Provided func is not callable. Received: {type(func)}")
        if len(cat_columns)==0: 
            # no categorical data func. 
            warnings.warn(
                "No categorical data were detected. To transform numeric"
                " values into categorical labels, consider using either"
                " `gofast.tools.smart_label_classifier` or"
                " `gofast.tools.categorize_target`."
                )
    
            return df 
        
        for col in  cat_columns: 
            df[col]= df[col].apply (func ) 

        return (df, map_codes) if return_cat_codes else df 
 
    if categories is None: 
        categories ={}
        for col in cat_columns: 
            #categories[col].fillna(pd.NA, inplace =True)
            categories[col] = list(np.unique (df[col]))
            
    # categories should be a mapping data 
    if not isinstance ( categories, dict ): 
        raise TypeError("Expected a dictionary with the format"
                        " {'column name': 'labels'} to categorize data.")

        
    for col, values  in  categories.items():
        if col not in df.columns:
            continue  
        values = is_iterable(
            values, exclude_string=True, transform =True )
        df[col] = pd.Categorical (df[col], categories = values, ordered=True )
        # df[col] = df[col].astype ('category')
        val=df[col].cat.codes
        temp_col = col + '_col'
        df[temp_col] = val 
        map_codes[col] =  dict(zip(df[col].cat.codes, df[col]))
        # drop prevous col in the data frame 
        df.drop ( columns =[col], inplace =True ) 
        # rename the tem colum 
        # to take back to pandas 
        df.rename ( columns ={temp_col: col }, inplace =True ) 
        
    return (df, map_codes) if return_cat_codes else df 

@ensure_pkg ("imblearn", extra= (
    "`imblearn` is actually a shorthand for ``imbalanced-learn``.")
   )
def resampling( 
    X, 
    y, 
    kind ='over', 
    strategy ='auto', 
    random_state =None, 
    verbose: bool=..., 
    **kws
    ): 
    """ Combining Random Oversampling and Undersampling 
    
    Resampling involves creating a new transformed version of the training 
    dataset in which the selected examples have a different class distribution.
    This is a simple and effective strategy for imbalanced classification 
    problems.

    Applying re-sampling strategies to obtain a more balanced data 
    distribution is an effective solution to the imbalance problem. There are 
    two main approaches to random resampling for imbalanced classification; 
    they are oversampling and undersampling.

    - Random Oversampling: Randomly duplicate examples in the minority class.
    - Random Undersampling: Randomly delete examples in the majority class.
        
    Parameters 
    -----------
    X : array-like of shape (n_samples, n_features)
        Training vector, where `n_samples` is the number of samples and
        `n_features` is the number of features.
        
    y: array-like of shape (n_samples, ) 
        Target vector where `n_samples` is the number of samples.
    kind: str, {"over", "under"} , default="over"
      kind of sampling to perform. ``"over"`` and ``"under"`` stand for 
      `oversampling` and `undersampling` respectively. 
      
    strategy : float, str, dict, callable, default='auto'
        Sampling information to sample the data set.

        - When ``float``, it corresponds to the desired ratio of the number of
          samples in the minority class over the number of samples in the
          majority class after resampling. Therefore, the ratio is expressed as
          :math:`\\alpha_{us} = N_{m} / N_{rM}` where :math:`N_{m}` is the
          number of samples in the minority class and
          :math:`N_{rM}` is the number of samples in the majority class
          after resampling.

          .. warning::
             ``float`` is only available for **binary** classification. An
             error is raised for multi-class classification.

        - When ``str``, specify the class targeted by the resampling. The
          number of samples in the different classes will be equalized.
          Possible choices are:

            ``'majority'``: resample only the majority class;

            ``'not minority'``: resample all classes but the minority class;

            ``'not majority'``: resample all classes but the majority class;

            ``'all'``: resample all classes;

            ``'auto'``: equivalent to ``'not minority'``.

        - When ``dict``, the keys correspond to the targeted classes. The
          values correspond to the desired number of samples for each targeted
          class.

        - When callable, function taking ``y`` and returns a ``dict``. The keys
          correspond to the targeted classes. The values correspond to the
          desired number of samples for each class.
          
    random_state : int, RandomState instance, default=None
            Control the randomization of the algorithm.

            - If int, ``random_state`` is the seed used by the random number
              generator;
            - If ``RandomState`` instance, random_state is the random number
              generator;
            - If ``None``, the random number generator is the ``RandomState``
              instance used by ``np.random``.
              
    verbose: bool, default=False 
      Display the counting samples 
      
    Returns 
    ---------
    X, y : NDarray, Arraylike 
        Arraylike sampled 
    
    Examples 
    --------- 
    >>> import gofast as gf 
    >>> from gofast.tools.mlutils import resampling 
    >>> data, target = gf.fetch_data ('bagoue analysed', as_frame =True, return_X_y=True) 
    >>> data.shape, target.shape 
    >>> data_us, target_us = resampling (data, target, kind ='under',verbose=True)
    >>> data_us.shape, target_us.shape 
    Counters: Auto      
                         Raw counter y: Counter({0: 232, 1: 112})
               UnderSampling counter y: Counter({0: 112, 1: 112})
    Out[43]: ((224, 8), (224,))
    
    """
    kind = str(kind).lower() 
    if kind =='under': 
        from imblearn.under_sampling import RandomUnderSampler
        rsampler = RandomUnderSampler(sampling_strategy=strategy, 
                                      random_state = random_state ,
                                      **kws)
    else:  
        from imblearn.over_sampling import RandomOverSampler 
        rsampler = RandomOverSampler(sampling_strategy=strategy, 
                                     random_state = random_state ,
                                     **kws
                                     )
    Xs, ys = rsampler.fit_resample(X, y)
    
    if ellipsis2false(verbose)[0]: 
        print("{:<20}".format(f"Counters: {strategy.title()}"))
        print( "{:>35}".format( "Raw counter y:") , Counter (y))
        print( "{:>35}".format(f"{kind.title()}Sampling counter y:"), Counter (ys))
        
    return Xs, ys 

def bin_counting(
    data: DataFrame, 
    bin_columns: str|List[str, ...], 
    tname:str|Series[int], 
    odds="N+", 
    return_counts: bool=...,
    tolog: bool=..., 
    ): 
    """ Bin counting categorical variable and turn it into probabilistic 
    ratio.
    
    Bin counting is one of the perennial rediscoveries in machine learning. 
    It has been reinvented and used in a variety of applications, from ad 
    click-through rate prediction to hardware branch prediction [1]_, [2]_ 
    and [3]_.
    
    Given an input variable X and a target variable Y, the odds ratio is 
    defined as:
        
    .. math:: 
        
        odds ratio = \frac{ P(Y = 1 | X = 1)/ P(Y = 0 | X = 1)}{
            P(Y = 1 | X = 0)/ P(Y = 0 | X = 0)}
          
    Probability ratios can easily become very small or very large. The log 
    transform again comes to our rescue. Anotheruseful property of the 
    logarithm is that it turns a division into a subtraction. To turn 
    bin statistic probability value to log, set ``uselog=True``.
    
    Parameters 
    -----------
    data: dataframe 
       Data containing the categorical values. 
       
    bin_columns: str or list 
       The columns to applied the bin_countings 
       
    tname: str, pd.Series
      The target name for which the counting is operated. If series, it 
      must have the same length as the data. 
      
    odds: str , {"N+", "N-", "log_N+"}: 
        The odds ratio of bin counting to fill the categorical. ``N+`` and  
        ``N-`` are positive and negative probabilistic computing. Whereas the
        ``log_N+`` is the logarithm odds ratio useful when value are smaller 
        or larger. 
        
    return_counts: bool, default=True 
      return the bin counting dataframes. 
  
    tolog: bool, default=False, 
      Apply the logarithm to the output data ratio. Indeed, Probability ratios 
      can easily  become very small or very large. For instance, there will be 
      users who almost never click on ads, and perhaps users who click on ads 
      much more frequently than not.) The log transform again comes to our  
      rescue. Another useful property of the logarithm is that it turns a 
      division 

    Returns 
    --------
    d: dataframe 
       Dataframe transformed or bin-counting data
       
    Examples 
    ---------
    >>> import gofast as gf 
    >>> from gofast.tools.mlutils import bin_counting 
    >>> X, y = gf.fetch_data ('bagoue analysed', as_frame =True) 
    >>> # target binarize 
    >>> y [y <=1] = 0;  y [y > 0]=1 
    >>> X.head(2) 
    Out[7]: 
          power  magnitude       sfi      ohmS       lwi  shape  type  geol
    0  0.191800  -0.140799 -0.426916  0.386121  0.638622    4.0   1.0   3.0
    1 -0.430644  -0.114022  1.678541 -0.185662 -0.063900    3.0   2.0   2.0
    >>>  bin_counting (X , bin_columns= 'geol', tname =y).head(2)
    Out[8]: 
          power  magnitude       sfi      ohmS  ...  shape  type      geol  bin_target
    0  0.191800  -0.140799 -0.426916  0.386121  ...    4.0   1.0  0.656716           1
    1 -0.430644  -0.114022  1.678541 -0.185662  ...    3.0   2.0  0.219251           0
    [2 rows x 9 columns]
    >>>  bin_counting (X , bin_columns= ['geol', 'shape', 'type'], tname =y).head(2)
    Out[10]: 
          power  magnitude       sfi  ...      type      geol  bin_target
    0  0.191800  -0.140799 -0.426916  ...  0.267241  0.656716           1
    1 -0.430644  -0.114022  1.678541  ...  0.385965  0.219251           0
    [2 rows x 9 columns]
    >>> df = pd.DataFrame ( pd.concat ( [X, pd.Series ( y, name ='flow')],
                                       axis =1))
    >>> bin_counting (df , bin_columns= ['geol', 'shape', 'type'], 
                      tname ="flow", tolog=True).head(2)
    Out[12]: 
          power  magnitude       sfi      ohmS  ...     shape      type      geol  flow
    0  0.191800  -0.140799 -0.426916  0.386121  ...  0.828571  0.364706  1.913043     1
    1 -0.430644  -0.114022  1.678541 -0.185662  ...  0.364865  0.628571  0.280822     0
    >>> bin_counting (df , bin_columns= ['geol', 'shape', 'type'],odds ="N-", 
                      tname =y, tolog=True).head(2)
    Out[13]: 
          power  magnitude       sfi  ...      geol  flow  bin_target
    0  0.191800  -0.140799 -0.426916  ...  0.522727     1           1
    1 -0.430644  -0.114022  1.678541  ...  3.560976     0           0
    [2 rows x 10 columns]
    >>> bin_counting (df , bin_columns= "geol",tname ="flow", tolog=True,
                      return_counts= True )
    Out[14]: 
         flow  no_flow  total_flow        N+        N-     logN+     logN-
    3.0    44       23          67  0.656716  0.343284  1.913043  0.522727
    2.0    41      146         187  0.219251  0.780749  0.280822  3.560976
    0.0    18       43          61  0.295082  0.704918  0.418605  2.388889
    1.0     9       20          29  0.310345  0.689655  0.450000  2.222222

    References 
    -----------
    .. [1] Yeh, Tse-Yu, and Yale N. Patt. Two-Level Adaptive Training Branch 
           Prediction. Proceedings of the 24th Annual International 
           Symposium on Microarchitecture (1991):51–61
           
    .. [2] Li, Wei, Xuerui Wang, Ruofei Zhang, Ying Cui, Jianchang Mao, and 
           Rong Jin.Exploitation and Exploration in a Performance Based Contextual 
           Advertising System. Proceedings of the 16th ACM SIGKDD International
           Conference on Knowledge Discovery and Data Mining (2010): 27–36
           
    .. [3] Chen, Ye, Dmitry Pavlov, and John _F. Canny. “Large-Scale Behavioral 
           Targeting. Proceedings of the 15th ACM SIGKDD International 
           Conference on Knowledge Discovery and Data Mining (2009): 209–218     
    """
    # assert everything
    if not is_frame (data, df_only =True ):
        raise TypeError(f"Expect dataframe. Got {type(data).__name__!r}")
    
    if not _is_numeric_dtype(data, to_array= True): 
        raise TypeError ("Expect data with encoded categorical variables."
                         " Please check your data.")
    if hasattr ( tname, '__array__'): 
        check_consistent_length( data, tname )
        if not _is_arraylike_1d(tname): 
            raise TypeError (
                 "Only one dimensional array is allowed for the target.")
        # create fake bin target 
        if not hasattr ( tname, 'name'): 
            tname = pd.Series (tname, name ='bin_target')
        # concatenate target 
        data= pd.concat ( [ data, tname], axis = 1 )
        tname = tname.name  # take the name 
        
    return_counts, tolog = ellipsis2false(return_counts, tolog)    
    bin_columns= is_iterable( bin_columns, exclude_string= True, 
                                 transform =True )
    tname = str(tname) ; #bin_column = str(bin_column)
    target_all_counts =[]
    
    validate_feature(data, features =bin_columns + [tname] )
    d= data.copy() 
    # -convert all features dtype to float for consistency
    # except the binary target 
    feature_cols = is_in_if (d.columns , tname, return_diff= True ) 
    d[feature_cols] = d[feature_cols].astype ( float)
    # -------------------------------------------------
    for bin_column in bin_columns: 
        d, tc  = _single_counts(d , bin_column, tname, 
                           odds =odds, 
                           tolog=tolog, 
                           return_counts= return_counts
                           )
    
        target_all_counts.append (tc) 
    # lowering the computation time 
    if return_counts: 
        d = ( target_all_counts if len(target_all_counts) >1 
                 else target_all_counts [0]
                 ) 

    return d

def _single_counts ( 
        d,/,  bin_column, tname, odds = "N+",
        tolog= False, return_counts = False ): 
    """ An isolated part of bin counting. 
    Compute single bin_counting. """
    # polish pos_label 
    od = copy.deepcopy( odds) 
    # reconvert log and removetrailer
    odds= str(odds).upper().replace ("_", "")
    # just separted for 
    keys = ('N-', 'N+', 'lOGN+')
    msg = ("Odds ratio or log Odds ratio expects"
           f" {smart_format(('N-', 'N+', 'logN+'), 'or')}. Got {od!r}")
    # check wther log is included 
    if odds.find('LOG')>=0: 
        tolog=True # then remove log 
        odds= odds.replace ("LOG", "")

    if odds not in keys: 
        raise ValueError (msg) 
    # If tolog, then reconstructs
    # the odds_labels
    if tolog: 
        odds= f"log{odds}"
    
    target_counts= _target_counting(
        d.filter(items=[bin_column, tname]),
    bin_column , tname =tname, 
    )
    target_all, target_bin_counts = _bin_counting(target_counts, tname, odds)
    # Check to make sure we have all the devices
    target_all.sort_values(by = f'total_{tname}', ascending=False)  
    if return_counts: 
        return d, target_all 
   
    # zip index with ratio 
    lr = list(zip (target_bin_counts.index, target_bin_counts[odds])
         )
    ybin = np.array ( d[bin_column])# replace value with ratio 
    for (value , ratio) in lr : 
        ybin [ybin ==value] = ratio 
        
    d[bin_column] = ybin 
    
    return d, target_all

def _target_counting(d, / ,  bin_column, tname ):
    """ An isolated part of counting the target. 
    
    :param d: DataFrame 
    :param bin_column: str, columns to appling bincounting strategy 
    :param tname: str, target name. 

    """
    pos_action = pd.Series(d[d[tname] > 0][bin_column].value_counts(),
        name=tname)
    
    neg_action = pd.Series(d[d[tname] < 1][bin_column].value_counts(),
    name=f'no_{tname}')
     
    counts = pd.DataFrame([pos_action,neg_action]).T.fillna('0')
    counts[f'total_{tname}'] = counts[tname].astype('int64') +\
    counts[f'no_{tname}'].astype('int64')
    
    return counts

def _bin_counting (counts, tname, odds="N+" ):
    """ Bin counting application to the target. 
    :param counts: pd.Series. Target counts 
    :param tname: str target name. 
    :param odds: str, label to bin-compute
    """
    counts['N+'] = ( counts[tname]
                    .astype('int64')
                    .divide(counts[f'total_{tname}'].astype('int64')
                            )
                    )
    counts['N-'] = ( counts[f'no_{tname}']
                    .astype('int64')
                    .divide(counts[f'total_{tname}'].astype('int64'))
                    )
    
    items2filter= ['N+', 'N-']
    if str(odds).find ('log')>=0: 
        counts['logN+'] = counts['N+'].divide(counts['N-'])
        counts ['logN-'] = counts ['N-'].divide ( counts['N+'])
        items2filter.extend (['logN+', 'logN-'])
    # If we wanted to only return bin-counting properties, 
    # we would filter here
    bin_counts = counts.filter(items= items2filter)

    return counts, bin_counts  
 
def laplace_smoothing_word(word, class_, /, word_counts, class_counts, V):
    """
    Apply Laplace smoothing to estimate the conditional probability of a 
    word given a class.

    Laplace smoothing (add-one smoothing) is used to handle the issue of 
    zero probability in categorical data, particularly in the context of 
    text classification with Naive Bayes.

    The mathematical formula for Laplace smoothing is:
    
    .. math:: 
        P(w|c) = \frac{\text{count}(w, c) + 1}{\text{count}(c) + |V|}

    where `count(w, c)` is the count of word `w` in class `c`, `count(c)` is 
    the total count of all words in class `c`, and `|V|` is the size of the 
    vocabulary.

    Parameters
    ----------
    word : str
        The word for which the probability is to be computed.
    class_ : str
        The class for which the probability is to be computed.
    word_counts : dict
        A dictionary containing word counts for each class. The keys should 
        be tuples of the form (word, class).
    class_counts : dict
        A dictionary containing the total count of words for each class.
    V : int
        The size of the vocabulary, i.e., the number of unique words in 
        the dataset.

    Returns
    -------
    float
        The Laplace-smoothed probability of the word given the class.

    Example
    -------
    >>> from gofast.tools.mlutils import laplace_smoothing_word
    >>> word_counts = {('dog', 'animal'): 3, ('cat', 'animal'):
                       2, ('car', 'non-animal'): 4}
    >>> class_counts = {'animal': 5, 'non-animal': 4}
    >>> V = len(set([w for (w, c) in word_counts.keys()]))
    >>> laplace_smoothing_word('dog', 'animal', word_counts, class_counts, V)
    0.5
    
    References
    ----------
    - C.D. Manning, P. Raghavan, and H. Schütze, "Introduction to Information Retrieval",
      Cambridge University Press, 2008.
    - A detailed explanation of Laplace Smoothing can be found in Chapter 13 of 
      "Introduction to Information Retrieval" by Manning et al.

    Notes
    -----
    This function is particularly useful in text classification tasks where the
    dataset may contain a large number of unique words, and some words may not 
    appear in the training data for every class.
    """
    word_class_count = word_counts.get((word, class_), 0)
    class_word_count = class_counts.get(class_, 0)
    probability = (word_class_count + 1) / (class_word_count + V)
    return probability

def laplace_smoothing_categorical(
        data, /, feature_col, class_col, V=None):
    """
    Apply Laplace smoothing to estimate conditional probabilities of 
    categorical features given a class in a dataset.

    This function calculates the Laplace-smoothed probabilities for each 
    category of a specified feature given each class.

    Parameters
    ----------
    data : pandas.DataFrame
        The dataset containing categorical features and a class label.
    feature_col : str
        The column name in the dataset representing the feature for which 
        probabilities are to be calculated.
    class_col : str
        The column name in the dataset representing the class label.
    V : int or None, optional
        The size of the vocabulary (i.e., the number of unique categories 
                                    in the feature).
        If None, it will be calculated based on the provided feature column.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing the Laplace-smoothed probabilities for each 
        category of the feature across each class.

    Example
    -------
    >>> import pandas as pd 
    >>> from gofast.tools.mlutils import laplace_smoothing_categorical
    >>> data = pd.DataFrame({'feature': ['cat', 'dog', 'cat', 'bird'],
                             'class': ['A', 'A', 'B', 'B']})
    >>> probabilities = laplace_smoothing_categorical(data, 'feature', 'class')
    >>> print(probabilities)

    Notes
    -----
    This function is useful for handling categorical data in classification
    tasks, especially when the dataset may contain categories that do not 
    appear in the training data for every class.
    """
    is_frame( data, df_only=True, raise_exception=True)
    if V is None:
        V = data[feature_col].nunique()

    class_counts = data[class_col].value_counts()
    probability_tables = []

    # Iterating over each class to calculate probabilities
    for class_value in data[class_col].unique():
        class_subset = data[data[class_col] == class_value]
        feature_counts = class_subset[feature_col].value_counts()
        probabilities = (feature_counts + 1) / (class_counts[class_value] + V)
        probabilities.name = class_value
        probability_tables.append(probabilities.to_frame().T)

    # Using pandas.concat to combine the probability tables
    probability_table = pd.concat(probability_tables, sort=False).fillna(1 / V)
    # Transpose to match expected format: features as rows, classes as columns
    probability_table = probability_table.T

    return probability_table

def laplace_smoothing(
    data: Union[ArrayLike, DataFrame], 
    alpha: float = 1.0, 
    columns: Union[list, None] = None
) -> Union[ArrayLike, DataFrame]:
    """
    Applies Laplace smoothing to  data to calculate smoothed probabilities.

    Parameters
    ----------
    data : ndarray or DataFrame
        An array-like or DataFrame object containing categorical data. Each column 
        represents a feature, and each row represents a data sample.
    alpha : float, optional
        The smoothing parameter, often referred to as 'alpha'. This is 
        added to the count for each category in each feature. 
        Default is 1 (Laplace Smoothing).
    columns: list, optional
        Columns to construct the DataFrame when `data` is an ndarray. The 
        number of columns must match the second dimension of the ndarray.
        
    Returns
    -------
    smoothed_probs : ndarray or DataFrame
        An array or DataFrame of the same shape as `data` containing the smoothed 
        probabilities for each category in each feature.

    Raises
    ------
    ValueError
        If `columns` is provided and its length does not match the number 
        of columns in `data`.

    Examples
    --------
    >>> import numpy as np 
    >>> import pandas as pd 
    >>> from gofast.tools.mlutils import laplace_smoothing
    >>> data = np.array([[0, 1], [1, 0], [1, 1]])
    >>> laplace_smoothing(data, alpha=1)
    array([[0.4 , 0.6 ],
           [0.6 , 0.4 ],
           [0.6 , 0.6 ]])

    >>> data_df = pd.DataFrame(data, columns=['feature1', 'feature2'])
    >>> laplace_smoothing(data_df, alpha=1)
       feature1  feature2
    0       0.4       0.6
    1       0.6       0.4
    2       0.6       0.6
    """
    if isinstance(data, np.ndarray):
        if columns:
            if len(columns) != data.shape[1]:
                raise ValueError("Length of `columns` does not match the shape of `data`.")
            data = pd.DataFrame(data, columns=columns)
        input_type = 'ndarray'
    elif isinstance(data, pd.DataFrame):
        input_type = 'dataframe'
    else:
        raise TypeError("`data` must be either a numpy.ndarray or a pandas.DataFrame.")

    smoothed_probs_list = []
    features = data.columns if input_type == 'dataframe' else range(data.shape[1])

    for feature in features:
        series = data[feature] if input_type == 'dataframe' else data[:, feature]
        counts = np.bincount(series, minlength=series.max() + 1)
        smoothed_counts = counts + alpha
        total_counts = smoothed_counts.sum()
        smoothed_probs = (series.map(lambda x: smoothed_counts[x] / total_counts)
                          if input_type == 'dataframe' else smoothed_counts[series] / total_counts)
        smoothed_probs_list.append(smoothed_probs)

    if input_type == 'dataframe':
        return pd.DataFrame({feature: probs for feature, probs in zip(features, smoothed_probs_list)})
    else:
        return np.column_stack(smoothed_probs_list)

def evaluate_model(
    model: Optional[_F[[NDArray, NDArray], NDArray]] = None,
    X: Optional[Union[NDArray, DataFrame]] = None,
    Xt: Optional[Union[NDArray, DataFrame]] = None,
    y: Optional[Union[NDArray, Series]] = None, 
    yt: Optional[Union[NDArray, Series]] = None,
    y_pred: Optional[Union[NDArray, Series]] = None,
    scorer: Union[str, _F[[NDArray, NDArray], float]] = 'accuracy',
    eval: bool = False,
    **kws: Any
) -> Union[Tuple[Optional[Union[NDArray, Series]], Optional[float]],
           Optional[Union[NDArray, Series]]]:
    """
    Evaluates a predictive model's performance or the effectiveness of predictions 
    using a specified scoring metric.

    Parameters
    ----------
    model : Callable, optional
        A machine learning model that implements fit and predict methods.
        Required if `y_pred` is not provided.
    X : np.ndarray or pd.DataFrame, optional
        Training data features. Required if `model` is provided and `y_pred` is None.
    Xt : np.ndarray or pd.DataFrame, optional
        Test data features. Required if `model` is provided and `y_pred` is None.
    y : np.ndarray or pd.Series, optional
        Training data labels. Required if `model` is provided and `y_pred` is None.
    yt : np.ndarray or pd.Series, optional
        Test data labels. Required if `eval` is True.
    y_pred : np.ndarray or pd.Series, optional
        Predictions for test data. Required if `model` is None.
    scorer : str or Callable, default='accuracy'
        The scoring metric name or a scorer callable object/function with signature 
        scorer(y_true, y_pred, **kws). 
    eval : bool, default=False
        If True, performs evaluation using `scorer` on `yt` and `y_pred`.
    **kws : Any
        Additional keyword arguments to pass to the scoring function.

    Returns
    -------
    predictions : np.ndarray or pd.Series
        The predicted labels or probabilities.
    score : float, optional
        The score of the predictions based on `scorer`. Only returned if `eval` is True.

    Raises
    ------
    ValueError
        If required arguments are missing or if the provided arguments are invalid.
    TypeError
        If `scorer` is not a recognized scoring function.

    Examples
    --------
    >>> from sklearn.datasets import load_iris
    >>> from sklearn.model_selection import train_test_split
    >>> from sklearn.linear_model import LogisticRegression
    >>> from gofast.tools.mlutils import evaluate_model
    >>> iris = load_iris()
    >>> X, y = iris.data, iris.target
    >>> X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    >>> model = LogisticRegression()
    >>> y_pred, score = evaluate_model(model=model, X=X_train, Xt=X_test,
    ...                                y=y_train, yt=y_test, eval=True)
    >>> print(f'Score: {score:.2f}')
    
    >>> # Providing predictions directly
    >>> y_pred, _ = evaluate_model(y_pred=y_pred, yt=y_test, scorer='accuracy',
    ...                            eval=True)
    >>> print(f'Accuracy: {score:.2f}')
    """
    from ..metrics import _SCORERS
    
    if y_pred is None:
        if model is None or X is None or y is None or Xt is None:
            raise ValueError("Model, X, y, and Xt must be provided when y_pred"
                             " is not provided.")
        if not hasattr(model, 'fit') or not hasattr(model, 'predict'):
            raise TypeError("The provided model does not implement fit and "
                            "predict methods.")
        
        # Check model if is fitted
        try: check_is_fitted(model)
        except: 
            # If the model is not fitted, then fit it with X and y
            if X is not None and y is not None:
                if hasattr(X, 'ndim') and X.ndim == 1:
                    X = X.reshape(-1, 1)
                model.fit(X, y)
            else:
                raise ValueError("Model is not fitted, and no training data"
                                 " (X, y) were provided.")
        y_pred = model.predict(Xt)

    if eval:
        if yt is None:
            raise ValueError("yt must be provided when eval is True.")
        if not isinstance(scorer, (str, callable)):
            raise TypeError("scorer must be a string or a callable,"
                            f" got {type(scorer).__name__}.")
            if isinstance (scorer , str) and scorer not in _SCORERS:
                raise ValueError(f"Use {scorer!r} function instead.")
        
        score_func = _SCORERS[scorer] if isinstance(scorer, str) else scorer
        score = score_func(yt, y_pred, **kws)
        return y_pred, score

    return y_pred

def get_correlated_features(
    data:DataFrame ,
    corr:str ='pearson', 
    threshold: float=.95 , 
    fmt: bool= False 
    )-> DataFrame: 
    """Find the correlated features/columns in the dataframe. 
    
    Indeed, highly correlated columns don't add value and can throw off 
    features importance and interpretation of regression coefficients. If we  
    had correlated columns, choose to remove either the columns from  
    level_0 or level_1 from the features data is a good choice. 
    
    Parameters 
    -----------
    data: Dataframe or shape (M, N) from :class:`pandas.DataFrame` 
        Dataframe containing samples M  and features N
    corr: str, ['pearson'|'spearman'|'covariance']
        Method of correlation to perform. Note that the 'person' and 
        'covariance' don't support string value. If such kind of data 
        is given, turn the `corr` to `spearman`. *default* is ``pearson``
        
    threshold: int, default is ``0.95``
        the value from which can be considered as a correlated data. Should not 
        be greater than 1. 
        
    fmt: bool, default {``False``}
        format the correlated dataframe values 
        
    Returns 
    ---------
    df: `pandas.DataFrame`
        Dataframe with cilumns equals to [level_0, level_1, pearson]
        
    Examples
    --------
    >>> from gofast.tools.mlutils import get_correlated_features 
    >>> df_corr = get_correlated_features (data , corr='spearman',
                                     fmt=None, threshold=.95
                                     )
    """
    th= copy.deepcopy(threshold) 
    threshold = str(threshold)  
    try : 
        threshold = float(threshold.replace('%', '')
                          )/1e2  if '%' in threshold else float(threshold)
    except: 
        raise TypeError (
            f"Threshold should be a float value, got: {type(th).__name__!r}")
          
    if threshold >= 1 or threshold <= 0 : 
        raise ValueError (
            f"threshold must be ranged between 0 and 1, got {th!r}")
      
    if corr not in ('pearson', 'covariance', 'spearman'): 
        raise ValueError (
            f"Expect ['pearson'|'spearman'|'covariance'], got{corr!r} ")
    # collect numerical values and exclude cat values
    
    df = select_features(data, include ='number')
        
    # use pipe to chain different func applied to df 
    c_df = ( 
        df.corr()
        .pipe(
            lambda df1: pd.DataFrame(
                np.tril (df1, k=-1 ), # low triangle zeroed 
                columns = df.columns, 
                index =df.columns, 
                )
            )
            .stack ()
            .rename(corr)
            .pipe(
                lambda s: s[
                    s.abs()> threshold 
                    ].reset_index()
                )
                .query("level_0 not in level_1")
        )

    return  c_df.style.format({corr :"{:2.f}"}) if fmt else c_df 
                      
def get_target (df, tname, inplace = True): 
    """ Extract target and modified data in place or not . 
    
    :param df: A dataframe with features including the target name `tname`
    :param tname: A target name. It should be include in the dataframe columns 
        otherwise an error is raised. 
    :param inplace: modified the dataframe inplace. if ``False`` return the 
        dataframe. the *defaut* is ``True`` 
        
    :returns: Tuple of the target and dataframe (modified or not)
    
    :example: 
    >>> from gofast.datasets import fetch_data '
    >>> from gofast.tools.mlutils import exporttarget 
    >>> data0 = fetch_data ('bagoue original').get('data=dfy1') 
    >>> # no modification 
    >>> target, data_no = exporttarget (data0 , 'sfi', False )
    >>> len(data_no.columns ) , len(data0.columns ) 
    ... (13, 13)
    >>> # modified in place 
    >>> target, data= exporttarget (data0 , 'sfi')
    >>> len(data.columns ) , len(data0.columns ) 
    ... (12, 12)
        
    """
    df = _assert_all_types(df, pd.DataFrame)
    validate_feature(df, tname) # assert tname 
    if is_iterable(tname, exclude_string=True): 
        tname = list(tname)
        
    t = df [tname ] 
    df.drop (tname, axis =1 , inplace =inplace )
    
    return t, df

def select_features(
    data: DataFrame,
    features: List[str] =None, 
    include = None, 
    exclude = None,
    coerce: bool=...,
    columns: list=None, 
    verify_integrity:bool=..., 
	parse_features: bool=..., 
    **kwd
    ): 
    """ Select features  and return new dataframe.  
    
    :param data: a dataframe for features selections 
    :param features: list of features to select. List of features must be in the 
        dataframe otherwise an error occurs. 
    :param include: the type of data to retrieve in the dataframe `df`. Can  
        be ``number``. 
    :param exclude: type of the data to exclude in the dataframe `df`. Can be 
        ``number`` i.e. only non-digits data will be keep in the data return.
    :param coerce: return the whole dataframe with transforming numeric columns.
        Be aware that no selection is done and no error is raises instead. 
        *default* is ``False``
    :param columns: list, needs columns to construst a dataframe if data is 
        passed as Numpy object array.
    :param verify_integrity: bool, Control the data type and rebuilt the data 
       to the right type.
    :param parse_features:bool, parse the string and convert to an iterable object.
    :param kwd: additional keywords arguments from `pd.astype` function 
    
    :ref: https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.astype.html
    
    :examples: 
        >>> from gofast.tools.mlutils import select_features 
        >>> data = {"Color": ['Blue', 'Red', 'Green'], 
                    "Name": ['Mary', "Daniel", "Augustine"], 
                    "Price ($)": ['200', "300", "100"]
                    }
        >>> select_features (data, include='number')
        Out[230]: 
        Empty DataFrame
        Columns: []
        Index: [0, 1, 2]
        >>> select_features (data, include='number', verify_integrity =True )
        Out[232]: 
            Price ($)
        0       200.0
        1       300.0
        2       100.0
        >>> select_features (data, features =['Color', 'Price ($)'], )
        Out[234]: 
           color  Price ($)
        0   Blue        200
        1    Red        300
        2  Green        100
    """
    coerce, verify_integrity, parse_features= ellipsis2false( 
        coerce, verify_integrity, parse_features)
    
    data = build_data_if(data, columns = columns, )
  
    if verify_integrity: 
        data = to_numeric_dtypes(data )
        
    if features is not None: 
        features= list(is_iterable (
            features, exclude_string=True, transform=True, 
            parse_string = parse_features)
            )
        validate_feature(data, features, verbose ='raise')
    # change the dataype 
    data = data.astype (float, errors ='ignore', **kwd) 
    # assert whether the features are in the data columns
    if features is not None: 
        return data [features] 
    # raise ValueError: at least one of include or exclude must be nonempty
    # use coerce to no raise error and return data frame instead.
    return data if coerce else data.select_dtypes (include, exclude) 
    
def get_global_score(
    cvres: Dict[str, ArrayLike],
    ignore_convergence_problem: bool = False
) -> Tuple[float, float]:
    """
    Retrieve the global mean and standard deviation of test scores from 
    cross-validation results.

    This function computes the overall mean and standard deviation of test 
    scores from the results of cross-validation. It can also handle situations 
    where convergence issues might have occurred during model training, 
    depending on the `ignore_convergence_problem` flag.

    Parameters
    ----------
    cvres : Dict[str, np.ndarray]
        A dictionary containing the cross-validation results. Expected to have 
        keys 'mean_test_score' and 'std_test_score', with each key mapping to 
        an array of scores.
    ignore_convergence_problem : bool, default=False
        If True, ignores NaN values that might have resulted from convergence 
        issues during model training while calculating the mean. If False, NaN 
        values contribute to the final mean as NaN.

    Returns
    -------
    Tuple[float, float]
        A tuple containing two float values:
        - The first element is the mean of the test scores across all 
          cross-validation folds.
        - The second element is the mean of the standard deviations of the 
          test scores across all cross-validation folds.

    Examples
    --------
    >>> from sklearn.model_selection import cross_val_score
    >>> from sklearn.tree import DecisionTreeClassifier
    >>> from sklearn.datasets import load_iris
    >>> iris = load_iris()
    >>> clf = DecisionTreeClassifier()
    >>> scores = cross_val_score(clf, iris.data, iris.target, cv=5,
    ...                          scoring='accuracy', return_train_score=True)
    >>> cvres = {'mean_test_score': scores, 'std_test_score': np.std(scores)}
    >>> mean_score, mean_std = get_global_score(cvres)
    >>> print(f"Mean score: {mean_score}, Mean standard deviation: {mean_std}")

    Notes
    -----
    - The function is primarily designed to be used with results obtained from 
      scikit-learn's cross-validation functions like `cross_val_score`.
    - It is assumed that `cvres` contains keys 'mean_test_score' and 
      'std_test_score'.
    """
    if ignore_convergence_problem:
        mean_score = np.nanmean(cvres.get('mean_test_score'))
        mean_std = np.nanmean(cvres.get('std_test_score'))
    else:
        mean_score = np.mean( cvres.get('mean_test_score'))
        mean_std = np.mean(cvres.get('std_test_score'))

    return mean_score, mean_std

def cfexist(features_to: List[ArrayLike], 
            features: List[str] )-> bool:      
    """
    Control features existence into another list . List or array can be a 
    dataframe columns for pratical examples.  
    
    :param features_to :list of array to be controlled .
    :param features: list of whole features located on array of `pd.DataFrame.columns` 
    
    :returns: 
        -``True``:If the provided list exist in the features colnames 
        - ``False``: if not 

    """
    if isinstance(features_to, str): 
        features_to =[features_to]
    if isinstance(features, str): features =[features]
    
    if sorted(list(features_to))== sorted(list(
            set(features_to).intersection(set(features)))): 
        return True
    else: return False 

def formatGenericObj(generic_obj :Iterable[_T])-> _T: 
    """
    Format a generic object using the number of composed items. 

    :param generic_obj: Can be a ``list``, ``dict`` or other `TypeVar` 
        classified objects.
    
    :Example: 
        
        >>> from gofast.tools.mlutils import formatGenericObj 
        >>> formatGenericObj ({'ohmS', 'lwi', 'power', 'id', 
        ...                         'sfi', 'magnitude'})
        
    """
    
    return ['{0}{1}{2}'.format('{', ii, '}') for ii in range(
                    len(generic_obj))]

def find_relation_between_generics(
    gen_obj1: Iterable[Any],
    gen_obj2: Iterable[Any],
    operation: str = "intersection"
) -> Set[Any]:
    """
    Computes either the intersection or difference of two generic iterable objects.

    Based on the specified operation, this function finds either common elements 
    (intersection) or unique elements (difference) between two iterable objects 
    like lists, sets, or dictionaries.

    Parameters
    ----------
    gen_obj1 : Iterable[Any]
        The first generic iterable object. Can be a list, set, dictionary, 
        or any iterable type.
    gen_obj2 : Iterable[Any]
        The second generic iterable object. Same as gen_obj1.
    operation : str, optional
        The operation to perform. Can be 'intersection' or 'difference'.
        Defaults to 'intersection'.

    Returns
    -------
    Set[Any]
        A set containing either the common elements (intersection) or 
        unique elements (difference) of the two iterables.

    Examples
    --------
    Intersection:
    >>> from gofast.tools.mlutils import find_relation_between_generics
    >>> result = find_relation_between_generics(
    ...     ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'], 
    ...     {'ohmS', 'lwi', 'power'}
    ... )
    >>> print(result)
    {'ohmS', 'lwi', 'power'}

    Difference:
    >>> result = find_relation_between_generics(
    ...     ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'], 
    ...     {'ohmS', 'lwi', 'power'},
    ...     operation='difference'
    ... )
    >>> print(result)
    {'id', 'sfi', 'magnitude'}

    Notes
    -----
    The function returns the result as a set, irrespective of the
    type of the input iterables. The 'operation' parameter controls
    whether the function calculates the intersection or difference.
    """

    set1 = set(gen_obj1)
    set2 = set(gen_obj2)

    if operation == "intersection":
        return set1.intersection(set2)
    elif operation == "difference":
        if len(gen_obj1) <= len(gen_obj2):
            return set(gen_obj2).difference(set(gen_obj1))
        else:
            return set(gen_obj1).difference(set(gen_obj2))
    else:
        raise ValueError("Invalid operation specified. Choose"
                         " 'intersection' or 'difference'.")

def find_intersection_between_generics(
    gen_obj1: Iterable[Any],
    gen_obj2: Iterable[Any]
) -> Set[Any]:
    """
    Computes the intersection of two generic iterable objects.

    This function finds common elements between two iterable objects 
    (like lists, sets, or dictionaries) and returns a set containing 
    these shared elements. The function is designed to handle various 
    iterable types.

    Parameters
    ----------
    gen_obj1 : Iterable[Any]
        The first generic iterable object. Can be a list, set, dictionary, 
        or any iterable type.
    gen_obj2 : Iterable[Any]
        The second generic iterable object. Same as gen_obj1.

    Returns
    -------
    Set[Any]
        A set containing the elements common to both iterables.

    Example
    -------
    >>> from gofast.tools.mlutils import find_intersection_between_generics
    >>> result = find_intersection_between_generics(
    ...     ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'], 
    ...     {'ohmS', 'lwi', 'power'}
    ... )
    >>> print(result)
    {'ohmS', 'lwi', 'power'}

    Notes
    -----
    The function returns the intersection as a set, irrespective of the
    type of the input iterables.
    """

    # Convert both iterables to sets for intersection calculation
    set1 = set(gen_obj1)
    set2 = set(gen_obj2)

    # Calculate and return the intersection
    return set1.intersection(set2)

def findIntersectionGenObject(
        gen_obj1: Iterable[Any], 
        gen_obj2: Iterable[Any]
                              )-> set: 
    """
    Find the intersection of generic object and keep the shortest len 
    object `type` at the be beginning 
  
    :param gen_obj1: Can be a ``list``, ``dict`` or other `TypeVar` 
        classified objects.
    :param gen_obj2: Idem for `gen_obj1`.
    
    :Example: 
        
        >>> from gofast.tools.mlutils import findIntersectionGenObject
        >>> findIntersectionGenObject(
        ...    ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'], 
        ...    {'ohmS', 'lwi', 'power'})
        [out]:
        ...  {'ohmS', 'lwi', 'power'}
    
    """
    if len(gen_obj1) <= len(gen_obj2):
        objType = type(gen_obj1)
    else: objType = type(gen_obj2)

    return objType(set(gen_obj1).intersection(set(gen_obj2)))

def find_difference_between_generics(
    gen_obj1: Iterable[Any],
    gen_obj2: Iterable[Any]
   ) -> Union[None, Set[Any]]:
    """
    Identifies the difference between two generic iterable objects.

    This function computes the difference between two iterable objects 
    (like lists or sets) and returns a set containing elements that are 
    unique to the larger iterable. If both iterables are of the same length, 
    the function returns None.

    Parameters
    ----------
    gen_obj1 : Iterable[Any]
        The first generic iterable object. Can be a list, set, dictionary, 
        or any iterable type.
    gen_obj2 : Iterable[Any]
        The second generic iterable object. Same as gen_obj1.

    Returns
    -------
    Union[None, Set[Any]]
        A set containing the unique elements from the larger iterable.
        Returns None if both
        iterables are of equal length.

    Example
    -------
    >>> from gofast.tools.mlutils import find_difference_between_generics
    >>> result = find_difference_between_generics(
    ...     ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'],
    ...     {'ohmS', 'lwi', 'power'}
    ... )
    >>> print(result)
    {'id', 'sfi', 'magnitude'}
    """

    # Convert both iterables to sets for difference calculation
    set1 = set(gen_obj1)
    set2 = set(gen_obj2)

    # Calculate difference based on length
    if len(set1) > len(set2):
        return set1.difference(set2)
    elif len(set1) < len(set2):
        return set2.difference(set1)

    # Return None if both are of equal length
    return None

def findDifferenceGenObject(gen_obj1: Iterable[Any],
                            gen_obj2: Iterable[Any]
                              )-> None | set: 
    """
    Find the difference of generic object and keep the shortest len 
    object `type` at the be beginning: 
 
    :param gen_obj1: Can be a ``list``, ``dict`` or other `TypeVar` 
        classified objects.
    :param gen_obj2: Idem for `gen_obj1`.
    
    :Example: 
        
        >>> from gofast.tools.mlutils import findDifferenceGenObject
        >>> findDifferenceGenObject(
        ...    ['ohmS', 'lwi', 'power', 'id', 'sfi', 'magnitude'], 
        ...    {'ohmS', 'lwi', 'power'})
        [out]:
        ...  {'ohmS', 'lwi', 'power'}
    
    """
    if len(gen_obj1) < len(gen_obj2):
        objType = type(gen_obj1)
        return objType(set(gen_obj2).difference(set(gen_obj1)))
    elif len(gen_obj1) > len(gen_obj2):
        objType = type(gen_obj2)
        return objType(set(gen_obj1).difference(set(gen_obj2)))
    else: return 
   
    return set(gen_obj1).difference(set(gen_obj2))
    
def featureExistError(superv_features: Iterable[_T], 
                      features:Iterable[_T]) -> None:
    """
    Catching feature existence errors.
    
    check error. If nothing occurs  then pass 
    
    :param superv_features: 
        list of features presuming to be controlled or supervised
        
    :param features: 
        List of all features composed of pd.core.DataFrame. 
    
    """
    for ii, supff in enumerate([superv_features, features ]): 
        if isinstance(supff, str): 
            if ii==0 : superv_features=[superv_features]
            if ii==1 :features =[superv_features]
            
    try : 
        resH= cfexist(features_to= superv_features,
                           features = features)
    except TypeError: 
        
        print(' Features can not be a NoneType value.'
              'Please set a right features.')
        _logger.error('NoneType can not be a features!')
    except :
        raise ParameterNumberError  (
           f'Parameters number of {features} is  not found in the '
           ' dataframe columns ={0}'.format(list(features)))
    
    else: 
        if not resH:  raise ParameterNumberError  (
            f'Parameters number is ``{features}``. NoneType object is'
            ' not allowed in  dataframe columns ={0}'.
            format(list(features)))

def control_existing_estimator(
    estimator_name: str, 
    predefined_estimators=None, 
    raise_error: bool = False
) -> Union[Tuple[str, str], None]:
    """
    Validates and retrieves the corresponding prefix for a given estimator name.

    This function checks if the provided estimator name exists in a predefined
    list of estimators or in scikit-learn. If found, it returns the corresponding
    prefix and full name. Otherwise, it either raises an error or returns None,
    based on the 'raise_error' flag.

    Parameters
    ----------
    estimator_name : str
        The name of the estimator to check.
    predefined_estimators : dict, default _predefined_estimators
        A dictionary of predefined estimators.
    raise_error : bool, default False
        If True, raises an error when the estimator is not found. Otherwise, 
        emits a warning.

    Returns
    -------
    Tuple[str, str] or None
        A tuple containing the prefix and full name of the estimator, or 
        None if not found.

    Example
    -------
    >>> from gofast.tools.mlutils import control_existing_estimator
    >>> test_est = control_existing_estimator('svm')
    >>> print(test_est)
    ('svc', 'SupportVectorClassifier')
    """
    # Define a dictionary of predefined estimators
    _predefined_estimators ={
            'dtc': ['DecisionTreeClassifier', 'dtc', 'dec', 'dt'],
            'svc': ['SupportVectorClassifier', 'svc', 'sup', 'svm'],
            'sdg': ['SGDClassifier','sdg', 'sd', 'sdg'],
            'knn': ['KNeighborsClassifier','knn', 'kne', 'knr'],
            'rdf': ['RandomForestClassifier', 'rdf', 'rf', 'rfc',],
            'ada': ['AdaBoostClassifier','ada', 'adc', 'adboost'],
            'vtc': ['VotingClassifier','vtc', 'vot', 'voting'],
            'bag': ['BaggingClassifier', 'bag', 'bag', 'bagg'],
            'stc': ['StackingClassifier','stc', 'sta', 'stack'],
            'xgb': ['ExtremeGradientBoosting', 'xgboost', 'gboost', 'gbdm', 'xgb'], 
          'logit': ['LogisticRegression', 'logit', 'lr', 'logreg'], 
          'extree': ['ExtraTreesClassifier', 'extree', 'xtree', 'xtr']
            }
    predefined_estimators = predefined_estimators or _predefined_estimators
    
    estimator_name= estimator_name.lower().strip() if isinstance (
        estimator_name, str) else get_estimator_name(estimator_name)
    
    # Check if the estimator is in the predefined list
    for prefix, names in predefined_estimators.items():
        lower_names = [name.lower() for name in names]
        
        if estimator_name in lower_names:
            return prefix, names[0]

    # If not found in predefined list, check if it's a valid scikit-learn estimator
    if estimator_name in _get_sklearn_estimator_names():
        return estimator_name, estimator_name

    # If XGBoost is installed, check if it's an XGBoost estimator
    if 'xgb' in predefined_estimators and estimator_name.startswith('xgb'):
        return 'xgb', estimator_name

    # If raise_error is True, raise an error; otherwise, emit a warning
    if raise_error:
        valid_names = [name for names in predefined_estimators.values() for name in names]
        raise EstimatorError(f'Unsupported estimator {estimator_name!r}. '
                             f'Expected one of {valid_names}.')
    else:
        available_estimators = _get_available_estimators(predefined_estimators)
        warning_msg = (f"Estimator {estimator_name!r} not found. "
                       f"Expected one of: {available_estimators}.")
        warnings.warn(warning_msg)

    return None

def _get_sklearn_estimator_names():
    # Retrieve all scikit-learn estimator names using all_estimators
    sklearn_estimators = [name for name, _ in all_estimators(type_filter='classifier')]
    sklearn_estimators += [name for name, _ in all_estimators(type_filter='regressor')]
    return sklearn_estimators

def _get_available_estimators(predefined_estimators):
    # Combine scikit-learn and predefined estimators
    sklearn_estimators = _get_sklearn_estimator_names()
    xgboost_estimators = ['xgb' + name for name in predefined_estimators['xgb']]
    
    available_estimators = sklearn_estimators + xgboost_estimators
    return available_estimators

def format_model_score(
    model_score: Union[float, Dict[str, float]] = None,
    selected_estimator: Optional[str] = None
) -> None:
    """
    Formats and prints model scores.

    Parameters
    ----------
    model_score : float or Dict[str, float], optional
        The model score or a dictionary of model scores with estimator 
        names as keys.
    selected_estimator : str, optional
        Name of the estimator to format the score for. Used only if 
        `model_score` is a float.

    Example
    -------
    >>> from gofast.tools.mlutils import format_model_score
    >>> format_model_score({'DecisionTreeClassifier': 0.26, 'BaggingClassifier': 0.13})
    >>> format_model_score(0.75, selected_estimator='RandomForestClassifier')
    """

    print('-' * 77)
    if isinstance(model_score, dict):
        for estimator, score in model_score.items():
            formatted_score = round(score * 100, 3)
            print(f'> {estimator:<30}:{"Score":^10}= {formatted_score:^10} %')
    elif isinstance(model_score, float):
        estimator_name = selected_estimator if selected_estimator else 'Unknown Estimator'
        formatted_score = round(model_score * 100, 3)
        print(f'> {estimator_name:<30}:{"Score":^10}= {formatted_score:^10} %')
    else:
        print('Invalid model score format. Please provide a float or'
              ' a dictionary of scores.')
    print('-' * 77)
    
def stats_from_prediction(y_true, y_pred, verbose=False):
    """
    Generate statistical summaries and accuracy metrics from actual values (y_true)
    and predicted values (y_pred).

    Parameters
    ----------
    y_true : list or numpy.array
        Actual values.
    y_pred : list or numpy.array
        Predicted values.
    verbose : bool, optional
        If True, print the statistical summary and accuracy metrics.
        Default is False.

    Returns
    -------
    dict
        A dictionary containing statistical measures such 
        as MAE, MSE, RMSE, 
        and accuracy (if applicable).

    Examples
    --------
    >>> from gofast.tools.mlutils import stats_from_prediction 
    >>> y_true = [0, 1, 1, 0, 1]
    >>> y_pred = [0, 1, 0, 0, 1]
    >>> stats_from_prediction(y_true, y_pred, verbose=True)
    """
    from sklearn.metrics import ( 
        mean_absolute_error, mean_squared_error, accuracy_score) 
    # Calculating statistics
    check_consistent_length(y_true, y_pred )
    stats = {
        'mean': np.mean(y_pred),
        'median': np.median(y_pred),
        'std_dev': np.std(y_pred),
        'min': np.min(y_pred),
        'max': np.max(y_pred)
    }
    # add the metric stats 
    stats =dict ({
            'MAE': mean_absolute_error(y_true, y_pred),
            'MSE': mean_squared_error(y_true, y_pred),
            'RMSE': np.sqrt(mean_squared_error(y_true, y_pred)),
        }, **stats, 
        )

    # Adding accuracy for classification tasks
    # Check if y_true and y_pred are categories task 
    if is_classification_task(y_true, y_pred ): 
    # if all(map(lambda x: x in [0, 1], y_true + y_pred)): #binary 
        stats['Accuracy'] = accuracy_score(y_true, y_pred)

    # Printing the results if verbose is True
    if verbose:
        fancy_printer(stats, "Prediction Statistics Summary" )

    return stats

def save_dataframes(
    *data: Union[pd.DataFrame, Any],
    file_name_prefix: str = 'data',
    output_format: str = 'excel',
    sep: str = ',',
    start_index: int = 1
    ) -> None:
    """
    Saves multiple dataframes to Excel or CSV files, with each dataframe in a
    separate file.
    
    The files are named using a specified prefix and an index.

    Parameters
    ----------
    *data : Union[pd.DataFrame, Any]
        Variable number of arguments, where each argument is a dataframe or
        data that can be converted to a dataframe.
    file_name_prefix : str, optional
        Prefix for the output file names. Default is 'data'.
    output_format : str, optional
        Output format of the files. Can be 'excel' or 'csv'. Default is 'excel'.
    sep : str, optional
        Separator character for CSV output. Default is ','.
    start_index : int, optional
        Starting index for numbering the output files. Default is 1.

    Examples
    --------
    >>> from gofast.tools.mlutils import save_dataframes
    >>> df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    >>> df2 = pd.DataFrame({'C': [5, 6], 'D': [7, 8]})
    >>> save_dataframes(df1, df2, file_name_prefix='mydata', output_format='csv')
    # This will create 'mydata_1.csv' for df1 and 'mydata_2.csv' for df2

    >>> save_dataframes(df1, output_format='excel', file_name_prefix='test')
    # This will create 'test_1.xlsx' containing df1
    """
    for index, df in enumerate(data, start=start_index):
        # Ensure the argument is a DataFrame
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)

        # Determine the file name
        file_name = f"{file_name_prefix}_{index}"
        if output_format == 'csv':
            df.to_csv(f"{file_name}.csv", sep=sep, index=False)
        elif output_format == 'excel':
            with pd.ExcelWriter(f"{file_name}.xlsx") as writer:
                df.to_excel(writer, index=False)
        else:
            raise ValueError("Unsupported output format. Choose 'excel' or 'csv'.")

def fetch_tgz(
    data_url: str,
    tgz_filename: str,
    data_path: Optional[str] = None,
    show_progress: bool = False
) -> None:
    """
    Fetches and extracts a .tgz file from a specified URL, optionally into 
    a target directory.

    If `data_path` is provided and does not exist, it is created. If `data_path`
    is not provided, a default directory named 'tgz_data' in the current working 
    directory is used and created if necessary.

    Parameters
    ----------
    data_url : str
        The URL where the .tgz file is located.
    tgz_filename : str
        The filename of the .tgz file to download.
    data_path : Optional[str], optional
        The absolute path to the directory where the .tgz file will be extracted.
        If None, uses a directory named ``'tgz_data'`` in the current working 
        directory.
    show_progress : bool, optional
        If True, displays a progress bar during the file download. Default is False.

    Examples
    --------
    >>> from gofast.tools.mlutils import fetch_tgz
    >>> fetch_tgz(
    ...     data_url="http://example.com/data",
    ...     tgz_filename="data.tgz",
    ...     show_progress=True
    ... )

    >>> fetch_tgz(
    ...     data_url="http://example.com/data",
    ...     tgz_filename="data.tgz",
    ...     data_path="/path/to/custom/data",
    ...     show_progress=True
    ... )

    Note
    ----
    The function requires `tqdm` library for showing the progress bar. Ensure
    that `tqdm` is installed if `show_progress` is set to True.
    """
    # Use a default data directory if none is provided
    data_path = data_path or os.path.join(os.getcwd(), 'tgz_data')
    
    if not os.path.isdir(data_path):
        os.makedirs(data_path, exist_ok=True)

    tgz_path = os.path.join(data_path, tgz_filename)
    
    # Define a simple progress function, if needed
    def _progress(block_num, block_size, total_size):
        if show_progress:
            if tqdm is None:
                raise ImportError("`tqdm` library is required for progress output.")
            progress = tqdm(total=total_size, unit='iB', unit_scale=True, ascii=True, 
                            ncols= 100) 
            progress.n = block_num * block_size
            progress.last_print_n = progress.n
            progress.update()

    # Download the .tgz file
    urllib.request.urlretrieve(
        data_url, tgz_path, _progress if show_progress else None)

    # Extract the .tgz file
    with tarfile.open(tgz_path) as data_tgz:
        data_tgz.extractall(path=data_path)
    
    if show_progress:
        print("Download and extraction complete.")

def base_url_tgz_fetch(
    data_url: str, tgz_filename: str,  
    data_path: Optional[str]=None, 
    file_to_retrieve: Optional[str] = None, 
    **kwargs
    ) -> Union[str, None]:
    """
    Fetches a .tgz file from a given URL, saves it to a specified directory, 
    and optionally extracts a specific file from it.

    This function downloads a .tgz file from the specified URL and saves it to 
    the given directory. If a specific file  within the .tgz archive is 
    specified, it attempts to extract this file. If no specific file is 
    mentioned, it will extract all contents of the archive.

    Parameters
    ----------
    data_url : str
        The URL where the .tgz file is located.
    data_path : str
        The absolute path to the directory where the .tgz file will be saved.
    tgz_filename : str
        The name of the .tgz file to be downloaded.
    file_to_retrieve : Optional[str], optional
        The specific file within the .tgz archive to extract. If None, all 
        contents of the archive are extracted, by default None.
    **kwargs : dict
        Additional keyword arguments to be passed to the extraction method.

    Returns
    -------
    Union[str, None]
        The path to the extracted file if a specific file is requested,
        None otherwise.

    Examples
    --------
    >>> from gofast.tools.mlutils import base_url_tgz_fetch
    >>> data_url = 'https://example.com/data.tar.gz'
    >>> data_path = '/path/to/save/data'
    >>> tgz_filename = 'data.tar.gz'
    >>> file_to_retrieve = 'data.csv'
    >>> extracted_file_path = base_url_tgz_fetch(
    ... data_url, tgz_filename, data_path,file_to_retrieve)
    >>> print(extracted_file_path)

    """
    import urllib.request
    # Use a default data directory if none is provided
    data_path = data_path or os.path.join(os.getcwd(), 'tgz_data')
    
    if not os.path.isdir(data_path):
        os.makedirs(data_path, exist_ok=True)
        
    tgz_path = os.path.join(data_path, tgz_filename)

    # Attempt to download the .tgz file
    try:
        urllib.request.urlretrieve(data_url, tgz_path)
    except Exception as e:
        print(f"Failed to download {tgz_filename} from {data_url}. Error: {e}")
        return None

    # If a specific file to retrieve is not specified, extract all contents
    if not file_to_retrieve:
        try:
            with tarfile.open(tgz_path, "r:gz") as tar:
                tar.extractall(path=data_path)
        except Exception as e:
            print(f"Failed to extract {tgz_filename}. Error: {e}")
            return None
        return None

    # If a specific file is specified, attempt to extract just that file
    try:
        with tarfile.open(tgz_path, "r:gz") as tar:
            tar.extract(file_to_retrieve, path=data_path, **kwargs)
            return os.path.join(data_path, file_to_retrieve)
    except Exception as e:
        print(f"Failed to extract {file_to_retrieve} from {tgz_filename}. Error: {e}")
        return None

def fetch_tgz_from_url(
    data_url: str, tgz_filename: str, 
    data_path: Optional[str, Path]=None, 
    file_to_retrieve: Optional[str] = None, 
    **kwargs
    ) -> Optional[Path]:
    """
    Fetches a .tgz file from a given URL, saves it to a specified directory, 
    and optionally extracts a specific file from it.

    This function downloads a .tgz file from the specified URL and saves it to 
    the given directory. If a specific file  within the .tgz archive is 
    specified, it attempts to extract this file. If no specific file is 
    mentioned, it will extract all contents of the archive.

    Parameters
    ----------
    data_url : str
        The URL where the .tgz file is located.
    data_path : str
        The absolute path to the directory where the .tgz file will be saved.
    tgz_filename : str
        The name of the .tgz file to be downloaded.
    file_to_retrieve : Optional[str], optional
        The specific file within the .tgz archive to extract. If None, all 
        contents of the archive are extracted, by default None.
    **kwargs : dict
        Additional keyword arguments to be passed to the extraction method.

    Returns
    -------
    Union[str, None]
        The path to the extracted file if a specific file is requested,
        None otherwise.

    Examples
    --------
    >>> from gofast.tools.mlutils import fetch_tgz_from_url
    >>> data_url = 'https://example.com/data.tar.gz'
    >>> data_path = '/path/to/save/data'
    >>> tgz_filename = 'data.tar.gz'
    >>> file_to_retrieve = 'data.csv'
    >>> extracted_file_path = fetch_tgz_from_url(
    ... data_url, tgz_filename, data_path,file_to_retrieve)
    >>> print(extracted_file_path)

    """
    # Use a default data directory if none is provided
    data_path = data_path or os.path.join(os.getcwd(), 'tgz_data')
    
    if not os.path.isdir(data_path):
        os.makedirs(data_path, exist_ok=True)
        
    data_path = Path(data_path)
    tgz_path = data_path / tgz_filename

    # Setup tqdm progress bar for the download
    with tqdm(unit='B', unit_scale=True, miniters=1, desc=tgz_filename, ncols=100) as t:
        urllib.request.urlretrieve(data_url, tgz_path, reporthook=download_progress_hook(t))

    # Extract specified file or entire archive
    try:
        with tarfile.open(tgz_path, "r:gz") as tar:
            if file_to_retrieve:
                tar.extract(file_to_retrieve, path=data_path, **kwargs)
                return data_path / file_to_retrieve
            else:
                tar.extractall(path=data_path)
    except (tarfile.TarError, KeyError) as e:
        print(f"Error extracting {'file' if file_to_retrieve else 'archive'}: {e}")
        return None

    return None

def _extract_with_progress(
        tar: tarfile.TarFile, member: tarfile.TarInfo, path: Path):
    """
    Extracts a single member from a tarfile with progress reporting.

    Parameters
    ----------
    tar : tarfile.TarFile
        The tarfile object opened in read mode.
    member : tarfile.TarInfo
        The specific member within the tarfile to extract.
    path : Path
        The path to extract the member to.
    """
    # Initialize a progress bar for the extraction process
    with tqdm(total=member.size, desc=f"Extracting {member.name}",
              unit='B', unit_scale=True) as progress_bar:
        # Extract member and update the progress bar accordingly
        def custom_read(size):
            progress_bar.update(size)
            return member_file.read(size)
        
        # Open the member file for reading and wrap the read method for progress updates
        with tar.extractfile(member) as member_file:
            with open(path / member.name, 'wb') as out_file:
                shutil.copyfileobj(member_file, out_file, length=1024*1024,
                                   callback=lambda x: progress_bar.update(1024*1024))

def fetch_tgz_locally(
    tgz_file: str, 
    filename: str, 
    savefile: str = 'tgz', 
    rename_outfile: Optional[str] = None
    ) -> str:
    """
    Fetches and optionally renames a file from a tar archive with progress reporting.
    
    Parameters
    ----------
    tgz_file : str or Path
        The full path to the tar file.
    filename : str
        The target file to fetch from the tar archive.
    savefile : str or Path, optional
        The destination path to save the retrieved file.
    rename_outfile : str or Path, optional
        The new name for the fetched file, if desired.

    Returns
    -------
    str
        The path to the fetched and possibly renamed file.
        
    Example
    -------
    >>> from gofast.tools.mlutils import fetch_tgz_locally
    >>> fetch_tgz_locally('data/__tar.tgz/fmain.bagciv.data.tar.gz',
    ...                      'dataset.csv', 'extracted', 
    ...                      rename_outfile='main.bagciv.data.csv')
    >>> # This will extract 'dataset.csv' from the tar.gz, save it to 
    >>> # 'extracted' directory, and rename it to 'main.bagciv.data.csv'.
    
    """
    tgz_path = Path(tgz_file)
    save_path = Path(savefile)
    save_path.mkdir(parents=True, exist_ok=True)

    if not tgz_path.is_file():
        raise FileNotFoundError(f"Source {tgz_file!r} is not a valid file.")

    with tarfile.open(tgz_path) as tar:
        member = next((m for m in tar.getmembers() if m.name.endswith(filename)), None)
        if member:
            _extract_with_progress(tar, member, save_path)
            extracted_file_path = save_path / member.name
            final_file_path = save_path / (rename_outfile if rename_outfile else filename)
            if extracted_file_path != final_file_path:
                extracted_file_path.rename(final_file_path)
                # Cleanup if the extracted file was within a subdirectory
                if extracted_file_path.parent != save_path:
                    shutil.rmtree(extracted_file_path.parent, ignore_errors=True)
        else:
            raise FileNotFoundError(f"File {filename} not found in {tgz_file}.")

    print(f"--> '{final_file_path}' was successfully decompressed from"
          f" '{tgz_path.name}' and saved to '{save_path}'.")
    
    return str(final_file_path)

def base_local_tgz_fetch(
    tgz_file: str, 
    filename: str, 
    savefile: str = 'tgz', 
    rename_outfile: Optional[str] = None
    ) -> str:
    """
    Fetches a single file from an archived tar file and optionally renames it.

    Parameters
    ----------
    tgz_file : str or Path
        The full path to the tar file.
    filename : str
        The target file to fetch from the tar archive.
    savefile : str or Path, optional
        The destination path to save the retrieved file. Defaults to 'tgz'.
    rename_outfile : str or Path, optional
        The new name for the fetched file. If not provided, the original name is used.

    Returns
    -------
    str
        The path to the fetched (and possibly renamed) file.

    Example
    -------
    >>> fetch_tgz_locally('data/__tar.tgz/fmain.bagciv.data.tar.gz',
    ...                      'dataset.csv', 'extracted', 
    ...                      rename_outfile='main.bagciv.data.csv')
    >>> # This will extract 'dataset.csv' from the tar.gz, save it to 
    >>> # 'extracted' directory, and rename it to 'main.bagciv.data.csv'.
    """
    tgz_path = Path(tgz_file)
    save_path = Path(savefile)
    save_path.mkdir(parents=True, exist_ok=True)

    def retrieve_target_member(tar_obj, target_extension):
        """Retrieve the main member that matches the target filename extension."""
        return next((m for m in tar_obj.getmembers() if Path
                     (m.name).suffix == target_extension), None)

    if not tgz_path.is_file():
        raise FileNotFoundError(f"Source {tgz_file!r} is not a valid file.")

    with tarfile.open(tgz_path) as tar:
        target_extension = Path(filename).suffix
        target_member = retrieve_target_member(tar, target_extension)
        if target_member:
            tar.extract(target_member, path=save_path)
            extracted_file_path = save_path / target_member.name
            final_file_path = save_path / (rename_outfile if rename_outfile else filename)
            if extracted_file_path != final_file_path:
                extracted_file_path.rename(final_file_path)
                # Cleanup if the extracted file was within a subdirectory
                if extracted_file_path.parent != save_path:
                    shutil.rmtree(extracted_file_path.parent)
        else:
            raise FileNotFoundError(f"File {filename} not found in {tgz_file}.")

    print(f"--> '{final_file_path}' was successfully decompressed from"
          f" '{tgz_path.name}' and saved to '{save_path}'.")
    
    return str(final_file_path)


def load_csv(data_path: str, delimiter: Optional[str] = ',', **kwargs
             ) -> DataFrame:
    """
    Loads a CSV file into a pandas DataFrame.

    Parameters
    ----------
    data_path : str
        The file path to the CSV file to be loaded.
    delimiter : str, optional
        The delimiter character used in the CSV file. Defaults to ','.
    **kwargs : dict
        Additional keyword arguments passed to `pandas.read_csv`.

    Returns
    -------
    DataFrame
        A DataFrame containing the loaded data.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If the specified file is not a CSV file.

    Examples
    --------
    Assuming you have a CSV file named 'example.csv' with the following content:
    
    ```
    name,age
    Alice,30
    Bob,25
    ```

    You can load this file into a DataFrame like this:

    >>> from gofast.tools.mlutils import load_csv
    >>> df = load_csv('example.csv')
    >>> print(df)
       name  age
    0  Alice   30
    1    Bob   25
    """
    if not os.path.isfile(data_path):
        raise FileNotFoundError(f"The file '{data_path}' does not exist.")
    
    if not data_path.lower().endswith('.csv'):
        raise ValueError(
            "The specified file is not a CSV file. Please provide a valid CSV file.")
    
    return pd.read_csv(data_path, delimiter=delimiter, **kwargs)

def discretize_categories(
    data: Union[pd.DataFrame, pd.Series],
    in_cat: str,
    new_cat: Optional[str] = None,
    divby: float = 1.5,
    higherclass: int = 5
) -> DataFrame:
    """
    Discretizes a numerical column in the DataFrame into categories. 
    
    Creating a new categorical column based on ceiling division and 
    an upper class limit.

    Parameters
    ----------
    data : DataFrame or Series
        Input data containing the column to be discretized.
    in_cat : str
        Column name in `data` used for generating the new categorical attribute.
    new_cat : str, optional
        Name for the newly created categorical column. If not provided, 
        a default name 'new_category' is used.
    divby : float, default=1.5
        The divisor used in the ceiling division to discretize the column values.
    higherclass : int, default=5
        The upper bound for the discretized categories. Values reaching this 
        class or higher are grouped into this single upper class.

    Returns
    -------
    DataFrame
        A new DataFrame including the newly created categorical column.

    Examples
    --------
    >>> df = pd.DataFrame({'age': [23, 45, 18, 27]})
    >>> discretized_df = discretize_categories(df, 'age', 'age_cat', divby=10, higherclass=3)
    >>> print(discretized_df)
       age  age_cat
    0   23      3.0
    1   45      3.0
    2   18      2.0
    3   27      3.0

    Note: The 'age_cat' column contains discretized categories based on the 
    'age' column.
    """
    if new_cat is None:
        new_cat = 'new_category'
    
    # Discretize the specified column
    data[new_cat] = np.ceil(data[in_cat] / divby)
    # Apply upper class limit
    data[new_cat] = data[new_cat].where(data[new_cat] < higherclass, other=higherclass)
    
    return data

def stratify_categories(
    data: Union[DataFrame, ArrayLike],
    cat_name: str, 
    n_splits: int = 1, 
    test_size: float = 0.2, 
    random_state: int = 42
) -> Tuple[Union[DataFrame, ArrayLike], Union[DataFrame, ArrayLike]]: 
    """
    Perform stratified sampling on a dataset based on a specified categorical column.

    Parameters
    ----------
    data : Union[pd.DataFrame, np.ndarray]
        The dataset to be split. Can be a Pandas DataFrame or a NumPy ndarray.
        
    cat_name : str
        The name of the categorical column in 'data' used for stratified sampling. 
        This column must exist in 'data' if it's a DataFrame.
        
    n_splits : int, optional
        Number of re-shuffling & splitting iterations. Defaults to 1.
        
    test_size : float, optional
        Proportion of the dataset to include in the test split. Defaults to 0.2.
        
    random_state : int, optional
        Controls the shuffling applied to the data before applying the split.
        Pass an int for reproducible output across multiple function calls.
        Defaults to 42.

    Returns
    -------
    Tuple[Union[pd.DataFrame, np.ndarray], Union[pd.DataFrame, np.ndarray]]
        A tuple containing the training and testing sets.

    Raises
    ------
    ValueError
        If 'cat_name' is not found in 'data' when 'data' is a DataFrame.
        If 'test_size' is not between 0 and 1.
        If 'n_splits' is less than 1.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'feature1': np.random.rand(100),
    ...     'feature2': np.random.rand(100),
    ...     'category': np.random.choice(['A', 'B', 'C'], 100)
    ... })
    >>> train_set, test_set = stratify_categories(df, 'category')
    >>> train_set.shape, test_set.shape
    ((80, 3), (20, 3))
    """

    if isinstance(data, pd.DataFrame) and cat_name not in data.columns:
        raise ValueError(f"Column '{cat_name}' not found in the DataFrame.")

    if not (0 < test_size < 1):
        raise ValueError("Test size must be between 0 and 1.")

    if n_splits < 1:
        raise ValueError("Number of splits 'n_splits' must be at least 1.")

    split = StratifiedShuffleSplit(n_splits=n_splits, test_size=test_size,
                                   random_state=random_state)
    for train_index, test_index in split.split(data, data[cat_name] if isinstance(
            data, pd.DataFrame) else data[:, cat_name]):
        if isinstance(data, pd.DataFrame):
            strat_train_set = data.iloc[train_index]
            strat_test_set = data.iloc[test_index]
        else:  # Handle numpy arrays
            strat_train_set = data[train_index]
            strat_test_set = data[test_index]

    return strat_train_set, strat_test_set

def fetch_model(
    file: str,
    path: Optional[str] = None,
    default: bool = False,
    name: Optional[str] = None,
    verbose: int = 0
    ) -> Union[Dict[str, Any], List[Tuple[Any, Dict[str, Any], Any]]]:
    """
    Fetches a model saved using the Python pickle module or joblib module.

    Parameters
    ----------
    file : str
        The filename of the dumped model, saved using `joblib` or Python
        `pickle` module.
    path : Optional[str], optional
        The directory path containing the model file. If None, `file` is assumed
        to be the full path to the file.
    default : bool, optional
        If True, returns a list of tuples (model, best parameters, best scores)
        for each model in the file. If False, returns the entire contents of the
        file.
    name : Optional[str], optional
        The name of the specific model to retrieve from the file. If specified,
        only the named model and its parameters are returned.
    verbose : int, optional
        Verbosity level. More messages are displayed for values greater than 0.

    Returns
    -------
    Union[Dict[str, Any], List[Tuple[Any, Dict[str, Any], Any]]]
        Depending on the `default` flag:
        - If `default` is True, returns a list of tuples containing the model,
          best parameters, and best scores for each model in the file.
        - If `default` is False, returns the entire contents of the file, which
          could include multiple models and their respective information.

    Raises
    ------
    FileNotFoundError
        If the specified model file is not found.
    KeyError
        If `name` is specified but not found in the loaded model file.

    Examples
    --------
    >>> model_info = fetch_model('model.pkl', path='/models',
                                 name='RandomForest', default=True)
    >>> model, best_params, best_scores = model_info[0]
    """
    full_path = os.path.join(path, file) if path else file

    if not os.path.isfile(full_path):
        raise FileNotFoundError(f"File {full_path!r} not found.")

    is_joblib = full_path.endswith('.pkl') or full_path.endswith('.joblib')
    load_func = joblib.load if is_joblib else pickle.load
    with open(full_path, 'rb') as f:
        model_data = load_func(f)

    if verbose > 0:
        lib_used = "joblib" if is_joblib else "pickle"
        print(f"Model loaded from {full_path!r} using {lib_used}.")

    if name:
        try:
            specific_model_data = model_data[name]
        except KeyError:
            available_models = list(model_data.keys())
            raise KeyError(f"Model name '{name}' not found. Available models: {available_models}")
        
        if default:
            if not isinstance(specific_model_data, dict):
                warnings.warn(
                    "The retrieved model data does not follow the expected structure. "
                    "Each model should be represented as a dictionary, with the model's "
                    "name as the key and its details (including 'best_params_' and "
                    "'best_scores_') as nested dictionaries. For instance: "
                    "`model_data = {'ModelName': {'best_params_': <parameters>, "
                    "'best_scores_': <scores>}}`. As the structure is unexpected, "
                    "returning the raw model data instead of the processed tuple."
                )
                return specific_model_data
            # Assuming model data structure for specific named model when default is True
            return [(specific_model_data, specific_model_data.get('best_params_', {}),
                     specific_model_data.get('best_scores_', {}))]
        return specific_model_data

    if default:
        # Assuming model data structure contains 'best_model', 'best_params_', and 'best_scores'
        return [(model, info.get('best_params_', {}), info.get('best_scores_', {})) 
                for model, info in model_data.items()]

    return model_data

def serialize_data(
    data: Any,
    filename: Optional[str] = None,
    savepath: Optional[str] = None,
    to: Optional[str] = None,
    verbose: int = 0
) -> str:
    """
    Serialize and save data to a binary file using either joblib or pickle.

    Parameters
    ----------
    data : Any
        The object to be serialized and saved.
    filename : str, optional
        The name of the file to save. If None, a name is generated automatically.
    savepath : str, optional
        The directory where the file should be saved. If it does not exist, 
        it is created. If None, the current working directory is used.
    to : str, optional
        Specify the serialization method: 'joblib' or 'pickle'. 
        If None, defaults to 'joblib'.
    verbose : int, optional
        Verbosity level. More messages are displayed for values greater than 0.

    Returns
    -------
    str
        The path to the saved file.

    Raises
    ------
    ValueError
        If 'to' is not 'joblib', 'pickle', or None.
    TypeError
        If 'to' is not a string.

    Examples
    --------
    >>> import numpy as np
    >>> data = (np.array([0, 1, 3]), np.array([0.2, 4]))
    >>> filename = serialize_data(data, filename='__XTyT.pkl', to='pickle', 
                                  savepath='gofast/datasets')
    """
    if filename is None:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"__mydumpedfile_{timestamp}.pkl"

    if to:
        if not isinstance(to, str):
            raise TypeError(f"Serialization method 'to' must be a string, not {type(to)}.")
        to = to.lower()
        if to not in ('joblib', 'pickle'):
            raise ValueError("Unknown serialization method 'to'. Must be"
                             " 'joblib' or 'pickle'.")

    if not filename.endswith('.pkl'):
        filename += '.pkl'
    
    full_path = os.path.join(savepath, filename) if savepath else filename
    
    if savepath and not os.path.exists(savepath):
        os.makedirs(savepath)
    
    try:
        if to == 'pickle' or to is None:
            with open(full_path, 'wb') as file:
                pickle.dump(data, file, protocol=pickle.HIGHEST_PROTOCOL)
            if verbose:
                print(f"Data serialized using pickle and saved to {full_path!r}.")
        elif to == 'joblib':
            joblib.dump(data, full_path)
            if verbose:
                print(f"Data serialized using joblib and saved to {full_path!r}.")
    except Exception as e:
        raise IOError(f"An error occurred during data serialization: {e}")
    
    return full_path

def deserialize_data(filename: str, verbose: int = 0) -> Any:
    """
    Deserialize and load data from a serialized file using joblib or pickle.

    Parameters
    ----------
    filename : str
        The name or path of the file containing the serialized data.

    verbose : int, optional
        Verbosity level. More messages are displayed for values greater 
        than 0.

    Returns
    -------
    Any
        The data loaded from the serialized file.

    Raises
    ------
    TypeError
        If 'filename' is not a string.

    FileNotFoundError
        If the specified file does not exist.

    Examples
    --------
    >>> data = deserialize_data('path/to/serialized_data.pkl')
    """

    if not isinstance(filename, str):
        raise TypeError("Expected 'filename' to be a string,"
                        f" got {type(filename)} instead.")
    
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"File {filename!r} does not exist.")

    try:
        data = joblib.load(filename)
        if verbose:
            print(f"Data loaded successfully from {filename!r} using joblib.")
    except Exception as joblib_error:
        try:
            with open(filename, 'rb') as file:
                data = pickle.load(file)
            if verbose:
                print(f"Data loaded successfully from {filename!r} using pickle.")
        except Exception as pickle_error:
            raise IOError(f"Failed to load data from {filename!r}. "
                          f"Joblib error: {joblib_error}, Pickle error: {pickle_error}")
    if data is None:
        raise ValueError(f"Data in {filename!r} could not be deserialized."
                         " The file may be corrupted.")

    return data


def subprocess_module_installation (module, upgrade =True ): 
    """ Install  module using subprocess.
    :param module: str, module name 
    :param upgrade:bool, install the lastest version.
    """
    import sys 
    import subprocess 
    #implement pip as subprocess 
    # refer to https://pythongeeks.org/subprocess-in-python/
    MOD_IMP=False 
    print(f'---> Module {module!r} installation will take a while,'
          ' please be patient...')
    cmd = f'<pip install {module}> | <python -m pip install {module}>'
    try: 

        upgrade ='--upgrade' if upgrade else ''
        subprocess.check_call([sys.executable, '-m', 'pip', 'install',
        f'{module}', f'{upgrade}'])
        reqs = subprocess.check_output([sys.executable,'-m', 'pip',
                                        'freeze'])
        [r.decode().split('==')[0] for r in reqs.split()]
        _logger.info(f"Intallation of `{module}` and dependancies"
                     "was successfully done!") 
        MOD_IMP=True
     
    except: 
        _logger.error(f"Fail to install the module =`{module}`.")
        print(f'---> Module {module!r} installation failed, Please use'
           f'  the following command {cmd} to manually install it.')
    return MOD_IMP 
        
                
def _assert_sl_target (target,  df=None, obj=None): 
    """ Check whether the target name into the dataframe for supervised 
    learning.
    
    :param df: dataframe pandas
    :param target: str or index of the supervised learning target name. 
    
    :Example: 
        
        >>> from gofast.tools.mlutils import _assert_sl_target
        >>> from gofast.datasets import fetch_data
        >>> data = fetch_data('Bagoue original').get('data=df')  
        >>> _assert_sl_target (target =12, obj=prepareObj, df=data)
        ... 'flow'
    """
    is_dataframe = isinstance(df, pd.DataFrame)
    is_ndarray = isinstance(df, np.ndarray)
    if is_dataframe :
        targets = smart_format(
            df.columns if df.columns is not None else [''])
    else:targets =''
    
    if target is None:
        nameObj=f'{obj.__class__.__name__}'if obj is not None else 'Base class'
        msg =''.join([
            f"{nameObj!r} {'basically' if obj is not None else ''}"
            " works with surpervised learning algorithms so the",
            " input target is needed. Please specify the target", 
            f" {'name' if is_dataframe else 'index' if is_ndarray else ''}", 
            " to take advantage of the full functionalities."
            ])
        if is_dataframe:
            msg += f" Select the target among {targets}."
        elif is_ndarray : 
            msg += f" Max columns size is {df.shape[1]}"

        warnings.warn(msg, UserWarning)
        _logger.warning(msg)
        
    if target is not None: 
        if is_dataframe: 
            if isinstance(target, str):
                if not target in df.columns: 
                    msg =''.join([
                        f"Wrong target value {target!r}. Please select "
                        f"the right column name: {targets}"])
                    warnings.warn(msg, category= UserWarning)
                    _logger.warning(msg)
                    target =None
            elif isinstance(target, (float, int)): 
                is_ndarray =True 
  
        if is_ndarray : 
            _len = len(df.columns) if is_dataframe else df.shape[1] 
            m_=f"{'less than' if target >= _len  else 'greater than'}" 
            if not isinstance(target, (float,int)): 
                msg =''.join([f"Wrong target value `{target}`!"
                              f" Object type is {type(df)!r}. Target columns", 
                              " index should be given instead."])
                warnings.warn(msg, category= UserWarning)
                _logger.warning(msg)
                target=None
            elif isinstance(target, (float,int)): 
                target = int(target)
                if not 0 <= target < _len: 
                    msg =f" Wrong target index. Should be {m_} {str(_len-1)!r}."
                    warnings.warn(msg, category= UserWarning)
                    _logger.warning(msg) 
                    target =None
                    
            if df is None: 
                wmsg = ''.join([
                    f"No data found! `{target}` does not fit any data set.", 
                      "Could not fetch the target name.`df` argument is None.", 
                      " Need at least the data `numpy.ndarray|pandas.dataFrame`",
                      ])
                warnings.warn(wmsg, UserWarning)
                _logger.warning(wmsg)
                target =None
                
            target = list(df.columns)[target] if is_dataframe else target
            
    return target

def extract_target(
    data: Union[ArrayLike, DataFrame],/, 
    target_names: Union[str, int, List[Union[str, int]]],
    drop: bool = True,
    columns: Optional[List[str]] = None,
) -> Tuple[Union[ArrayLike, Series, DataFrame], Union[ArrayLike, DataFrame]]:
    """
    Extracts specified target column(s) from a multidimensional numpy array
    or pandas DataFrame. 
    
    with options to rename columns in a DataFrame and control over whether the 
    extracted columns are dropped from the original data.

    Parameters
    ----------
    data : Union[np.ndarray, pd.DataFrame]
        The input data from which target columns are to be extracted. Can be a 
        NumPy array or a pandas DataFrame.
    target_names : Union[str, int, List[Union[str, int]]]
        The name(s) or integer index/indices of the column(s) to extract. 
        If `data` is a DataFrame, this can be a mix of column names and indices. 
        If `data` is a NumPy array, only integer indices are allowed.
    drop : bool, default True
        If True, the extracted columns are removed from the original `data`. 
        If False, the original `data` remains unchanged.
    columns : Optional[List[str]], default None
        If provided and `data` is a DataFrame, specifies new names for the 
        columns in `data`. The length of `columns` must match the number of 
        columns in `data`. This parameter is ignored if `data` is a NumPy array.

    Returns
    -------
    Tuple[Union[np.ndarray, pd.Series, pd.DataFrame], Union[np.ndarray, pd.DataFrame]]
        A tuple containing two elements:
        - The extracted column(s) as a NumPy array or pandas Series/DataFrame.
        - The original data with the extracted columns optionally removed, as a
          NumPy array or pandas DataFrame.

    Raises
    ------
    ValueError
        If `columns` is provided and its length does not match the number of 
        columns in `data`.
        If any of the specified `target_names` do not exist in `data`.
        If `target_names` includes a mix of strings and integers for a NumPy 
        array input.

    Examples
    --------
    >>> import pandas as pd 
    >>> from gofast.tools.mlutils import extract_target
    >>> df = pd.DataFrame({
    ...     'A': [1, 2, 3],
    ...     'B': [4, 5, 6],
    ...     'C': [7, 8, 9]
    ... })
    >>> target, remaining = extract_target(df, 'B', drop=True)
    >>> print(target)
    0    4
    1    5
    2    6
    Name: B, dtype: int64
    >>> print(remaining)
       A  C
    0  1  7
    1  2  8
    2  3  9
    >>> arr = np.random.rand(5, 3)
    >>> target, modified_arr = extract_target(arr, 2, )
    >>> print(target)
    >>> print(modified_arr)
    """
    is_frame = isinstance(data, pd.DataFrame)
    
    if is_frame and columns is not None:
        if len(columns) != data.shape[1]:
            raise ValueError("`columns` must match the number of columns in"
                             f" `data`. Expected {data.shape[1]}, got {len(columns)}.")
        data.columns = columns

    if isinstance(target_names, (int, str)):
        target_names = [target_names]

    if all(isinstance(name, int) for name in target_names):
        if max(target_names, default=-1) >= data.shape[1]:
            raise ValueError("All integer indices must be within the"
                             " column range of the data.")
    elif any(isinstance(name, int) for name in target_names) and is_frame:
        target_names = [data.columns[name] if isinstance(name, int) 
                        else name for name in target_names]

    if is_frame:
        missing_cols = [name for name in target_names 
                        if name not in data.columns]
        if missing_cols:
            raise ValueError(f"Column names {missing_cols} do not match "
                             "any column in the DataFrame.")
        target = data.loc[:, target_names]
        if drop:
            data = data.drop(columns=target_names)
    else:
        if any(isinstance(name, str) for name in target_names):
            raise ValueError("String names are not allowed for target names"
                             " when data is a NumPy array.")
        target = data[:, target_names]
        if drop:
            data = np.delete(data, target_names, axis=1)
            
    if  isinstance (target, np.ndarray): # squeeze the array 
        target = np.squeeze (target)
        
    return target, data

def _extract_target(
        X, target: Union[ArrayLike, int, str, List[Union[int, str]]]):
    """
    Extracts and validates the target variable(s) from the dataset.

    Parameters
    ----------
    X : pd.DataFrame or np.ndarray
        The dataset from which to extract the target variable(s).
    target : ArrayLike, int, str, or list of int/str
        The target variable(s) to be used. If an array-like or DataFrame, 
        it's directly used as `y`. If an int or str (or list of them), it 
        indicates the column(s) in `X` to be used as `y`.

    Returns
    -------
    X : pd.DataFrame or np.ndarray
        The dataset without the target column(s).
    y : pd.Series, np.ndarray, pd.DataFrame
        The target variable(s).
    target_names : list of str
        The names of the target variable(s) for labeling purposes.
    """
    target_names = []

    if isinstance(target, (list, pd.DataFrame)) or (
            isinstance(target, pd.Series) and not isinstance(X, np.ndarray)):
        if isinstance(target, list):  # List of column names or indexes
            if all(isinstance(t, str) for t in target):
                y = X[target]
                target_names = target
            elif all(isinstance(t, int) for t in target):
                y = X.iloc[:, target]
                target_names = [X.columns[i] for i in target]
            X = X.drop(columns=target_names)
        elif isinstance(target, pd.DataFrame):
            y = target
            target_names = target.columns.tolist()
            # Assuming target DataFrame is not part of X
        elif isinstance(target, pd.Series):
            y = target
            target_names = [target.name] if target.name else ["target"]
            if target.name and target.name in X.columns:
                X = X.drop(columns=target.name)
                
    elif isinstance(target, (int, str)):
        if isinstance(target, str):
            y = X.pop(target)
            target_names = [target]
        elif isinstance(target, int):
            y = X.iloc[:, target]
            target_names = [X.columns[target]]
            X = X.drop(columns=X.columns[target])
    elif isinstance(target, np.ndarray) or (
            isinstance(target, pd.Series) and isinstance(X, np.ndarray)):
        y = np.array(target)
        target_names = ["target"]
    else:
        raise ValueError("Unsupported target type or target does not match X dimensions.")
    
    check_consistent_length(X, y)
    
    return X, y, target_names

def smart_split(
    X, 
    target: Optional[Union[ArrayLike, int, str, List[Union[int, str]]]] = None,
    test_size: float = 0.2, 
    random_state: int = 42,
    stratify: bool = False,
    shuffle: bool = True,
    return_df: bool = False,
    **skws
) -> Union[
    Tuple[DataFrame, DataFrame], 
    Tuple[ArrayLike, ArrayLike],
    Tuple[DataFrame, DataFrame, Series, Series], 
    Tuple[DataFrame, DataFrame, DataFrame, DataFrame], 
    Tuple[ArrayLike, ArrayLike, ArrayLike, ArrayLike]
    ]:
    """
    Splits data into training and test sets, with the option to extract and 
    handle multiple target variables. 
    
    Function supports both single and multi-label targets and maintains 
    compatibility with pandas DataFrame and numpy ndarray.

    Parameters
    ----------
    X : np.ndarray or pd.DataFrame
        The input data to be split. This can be either feature data alone or 
        include the target column(s) if the `target` parameter is used to specify 
        target column(s) for extraction.
    target : int, str, list of int/str, pd.Series, pd.DataFrame, optional
        Specifies the target variable(s) for supervised learning problems. 
        It can be:
        - An integer or string specifying the column index or name in `X` to 
          be used as the target variable.
        - A list of integers or strings for multi-label targets.
        - A pandas Series or DataFrame directly specifying the target variable(s).
        If `target` is provided as an array-like object or DataFrame, its 
        length must match the number of samples in `X`.
    test_size : float, optional
        Represents the proportion of the dataset to include in the test split. 
        Must be between 0.0 and 1.0.
    random_state : int, optional
        Sets the seed for random operations, ensuring reproducible splits.
    stratify : bool, optional
        Ensures that the train and test sets have approximately the same 
        percentage of samples of each target class if set to True.
    shuffle : bool, optional
        Determines whether to shuffle the dataset before splitting. 
    return_df : bool, optional
        If True and `X` is a DataFrame, returns the splits as pandas DataFrames/Series. 
        Otherwise, returns numpy ndarrays.
    skws : dict
        Additional keyword arguments for `train_test_split`, allowing customization 
        of the split beyond the parameters explicitly mentioned here.

    Returns
    -------
    Depending on the inputs and `return_df`:
    - If `target` is not specified: X_train, X_test
    - If `target` is specified: X_train, X_test, y_train, y_test
    `X_train` and `X_test` are the splits of the input data, while `y_train` and 
    `y_test` are the splits of the target variable(s) if provided.

    Examples
    --------
    >>> import pandas as pd
    >>> from gofast.tools.mlutils import smart_split
    >>> data = pd.DataFrame({
    ...     'Feature1': [1, 2, 3, 4],
    ...     'Feature2': [4, 3, 2, 1],
    ...     'Target': [0, 1, 0, 1]
    ... })
    >>> # Single target specified as a column name
    >>> X_train, X_test, y_train, y_test = smart_split(
    ... data, target='Target', return_df=True)
    >>> print(X_train.shape, X_test.shape, y_train.shape, y_test.shape)
    """
    if target is not None:
        X, y, target_names = _extract_target(X, target)
    else:
        y, target_names = None, []

    stratify_param = y if stratify and y is not None else None
    if y is not None: 
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, shuffle=shuffle, 
            stratify=stratify_param, **skws)
    else: 
        X_train, X_test= train_test_split(
            X, test_size=test_size, random_state=random_state, shuffle=shuffle, 
            stratify=stratify_param, **skws)

    if return_df and isinstance(X, pd.DataFrame):
        X_train, X_test = pd.DataFrame(X_train, columns=X.columns
                                       ), pd.DataFrame(X_test, columns=X.columns)
        if y is not None:
            if isinstance(y, pd.DataFrame):
                y_train, y_test = pd.DataFrame(
                    y_train, columns=target_names), pd.DataFrame(
                        y_test, columns=target_names)
            else:
                y_train, y_test = pd.Series(
                    y_train, name=target_names[0]), pd.Series(
                        y_test, name=target_names[0])

    return (X_train, X_test, y_train, y_test) if y is not None else (X_train, X_test)

def handle_imbalance(
    X, y=None, strategy='oversample', 
    random_state=42, 
    target_col='target'
    ):
    """
    Handles imbalanced datasets by either oversampling the minority class or 
    undersampling the majority class.
    
    It supports inputs as pandas DataFrame/Series, numpy arrays, and allows 
    specifying the target variable either as a separate argument or as part 
    of the DataFrame.

    Parameters
    ----------
    X : pd.DataFrame, np.ndarray
        The features of the dataset. If `y` is None, `X` is expected to include 
        the target variable.
    y : pd.Series, np.ndarray, optional
        The target variable of the dataset. If None, `target_col` must be 
        specified, and `X` must be a DataFrame containing the target.
    strategy : str, optional
        The strategy to apply for handling imbalance: 'oversample' or 
        'undersample'. Default is 'oversample'.
    random_state : int, optional
        The random state for reproducible results. Default is 42.
    target_col : str, optional
        The name of the target column in `X` if `X` is a DataFrame and 
        `y` is None. Default is 'target'.
    
    Returns
    -------
    X_resampled, y_resampled : Resampled features and target variable.
        The types of `X_resampled` and `y_resampled` match the input types.

    Examples
    --------
    Using with numpy arrays:
    
    >>> import numpy as np 
    >>> import pandas as pd 
    >>> from gofast.tools.mlutils import handle_imbalance
    >>> X = np.array([[1, 2], [2, 3], [3, 4]])
    >>> y = np.array([0, 1, 0])
    >>> X_resampled, y_resampled = handle_imbalance(X, y)
    >>> print(X_resampled.shape, y_resampled.shape)
    (3, 2) (3,)
    Using with pandas DataFrame (including target column):
    
    >>> df = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [2, 3, 4], 'target': [0, 1, 0]})
    >>> X_resampled, y_resampled = handle_imbalance(df, target_col='target')
    >>> print(X_resampled.shape, y_resampled.value_counts())

    Using with pandas DataFrame and Series:
    
    >>> X = pd.DataFrame({'feature1': [1, 2, 3], 'feature2': [2, 3, 4]})
    >>> y = pd.Series([0, 1, 0], name='target')
    >>> X_resampled, y_resampled = handle_imbalance(X, y)
    >>> print(X_resampled.shape, y_resampled.value_counts())
    """
    if y is None:
        if not isinstance(X, pd.DataFrame):
            raise ValueError("`X` must be a DataFrame when `y` is None.")
        exist_features(X, target_col, name =target_col)
        y = X[target_col]
        X = X.drop(target_col, axis=1)

    if not _is_arraylike_1d(y): 
        raise TypeError ("Check `y`. Expect one-dimensional array.")

    if not isinstance (y, pd.Series) : 
        # squeeze y to keep 1d array for skipping value error 
        # when constructing pd.Series and 
        # ensure `y` is a Series with the correct name for 
        # easy concatenation and manipulation
        y =pd.Series (np.squeeze (y), name =target_col ) 
    else : target_col = y.name # reset the default target_col 
 
    # Check consistent length 
    check_consistent_length(X, y )
    
    if isinstance(X, pd.DataFrame):
        data = pd.concat([X, y], axis=1)
    elif isinstance (X, np.ndarray ): 
        # Ensure `data` from `X` is a DataFrame with correct 
        # column names for subsequent operations
        data = pd.DataFrame(
            np.column_stack([X, y]), columns=[*X.columns, y.name]
            if isinstance(X, pd.DataFrame) else [
                    *[f"feature_{i}" for i in range(X.shape[1])], y.name])
    else: 
        TypeError("Unsupported type for X. Must be np.ndarray or pd.DataFrame.")
        
    # Identify majority and minority classes
    majority_class = y.value_counts().idxmax()
    minority_class = y.value_counts().idxmin()

    # Correctly determine the number of samples for resampling
    num_majority = y.value_counts()[majority_class]
    num_minority = y.value_counts()[minority_class]

    # Apply resampling strategy
    if strategy == 'oversample':
        minority_upsampled = resample(
            data[data[target_col] == minority_class],
            replace=True,
            n_samples=num_majority,
            random_state=random_state
            )
        resampled = pd.concat(
            [data[data[target_col] == majority_class], minority_upsampled])
    elif strategy == 'undersample':
        majority_downsampled = resample(
            data[data[target_col] == majority_class],
            replace=False,
            n_samples=num_minority,
            random_state=random_state
            )
        resampled = pd.concat(
            [data[data[target_col] == minority_class], majority_downsampled])

    # Prepare the output
    X_resampled = resampled.drop(target_col, axis=1)
    y_resampled = resampled[target_col]

    # Convert back to the original input type if necessary
    if isinstance(X, np.ndarray):
        X_resampled = X_resampled.to_numpy()
        y_resampled = y_resampled.to_numpy()

    return X_resampled, y_resampled


def soft_data_split(
    X, y=None, *,
    test_size=0.2,
    target_column=None,
    random_state=42,
    extract_target=False,
    **split_kwargs
):
    """
    Splits data into training and test sets, optionally extracting a 
    target column.

    Parameters
    ----------
    X : array-like or DataFrame
        Input data to split. If `extract_target` is True, a target column can be
        extracted from `X`.
    y : array-like, optional
        Target variable array. If None and `extract_target` is False, `X` is
        split without a target variable.
    test_size : float, optional
        Proportion of the dataset to include in the test split. Should be
        between 0.0 and 1.0. Default is 0.2.
    target_column : int or str, optional
        Index or column name of the target variable in `X`. Used only if
        `extract_target` is True.
    random_state : int, optional
        Controls the shuffling for reproducible output. Default is 42.
    extract_target : bool, optional
        If True, extracts the target variable from `X`. Default is False.
    split_kwargs : dict, optional
        Additional keyword arguments to pass to `train_test_split`.

    Returns
    -------
    X_train, X_test, y_train, y_test : arrays
        Split data arrays.

    Raises
    ------
    ValueError
        If `target_column` is not found in `X` when `extract_target` is True.

    Example
    -------
    >>> from gofast.datasets import fetch_data
    >>> data = fetch_data('Bagoue original')['data']
    >>> X, XT, y, yT = split_data(data, extract_target=True, target_column='flow')
    """

    if extract_target:
        if isinstance(X, pd.DataFrame) and target_column in X.columns:
            y = X[target_column]
            X = X.drop(columns=target_column)
        elif hasattr(X, '__array__') and isinstance(target_column, int):
            y = X[:, target_column]
            X = np.delete(X, target_column, axis=1)
        else:
            raise ValueError(f"Target column {target_column!r} not found in X.")

    if y is not None:
        return train_test_split(X, y, test_size=test_size, 
                                random_state=random_state, **split_kwargs)
    else:
        return  train_test_split(
            X, test_size=test_size,random_state=random_state, **split_kwargs)
 
def load_model(
    file_path: str,
    *,
    retrieve_default: bool = True,
    model_name: Optional[str] = None,
    storage_format: Optional[str] = None
    ) -> Union[Any, Tuple[Any, Dict[str, Any]]]:
    """
    Loads a saved model or data using Python's pickle or joblib module.

    Parameters
    ----------
    file_path : str
        The path to the saved model file. Supported formats are `.pkl` and `.joblib`.
    retrieve_default : bool, optional, default=True
        If True, returns the model along with its best parameters. If False,
        returns the entire contents of the saved file.
    model_name : Optional[str], optional
        The name of the specific model to retrieve from the saved file. If None,
        the entire file content is returned.
    storage_format : Optional[str], optional
        The format used for saving the file. If None, the format is inferred
        from the file extension. Supported formats are 'joblib' and 'pickle'.

    Returns
    -------
    Union[Any, Tuple[Any, Dict[str, Any]]]
        The loaded model or a tuple of the model and its parameters, depending
        on the `retrieve_default` value.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    KeyError
        If the specified model name is not found in the file.
    ValueError
        If the storage format is not supported or if the loaded data is not
        a dictionary when a model name is specified.

    Example
    -------
    >>> model, params = load_model('path_to_file.pkl', model_name='SVC')
    >>> print(model)
    >>> print(params)
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File '{file_path}' not found.")

    storage_format = storage_format or os.path.splitext(file_path)[-1].lower().lstrip('.')
    if storage_format not in {"joblib", "pickle"}:
        raise ValueError(f"Unsupported storage format '{storage_format}'. "
                         "Use 'joblib' or 'pickle'.")

    load_func = joblib.load if storage_format == 'joblib' else pickle.load
    with open(file_path, 'rb') as file:
        loaded_data = load_func(file)

    if model_name:
        if not isinstance(loaded_data, dict):
            warnings.warn(
                f"Expected loaded data to be a dictionary for model name retrieval. "
               f"Received type '{type(loaded_data).__name__}'. Returning loaded data.")
            return loaded_data

        model_info = loaded_data.get(model_name)
        if model_info is None:
            available = ', '.join(loaded_data.keys())
            raise KeyError(f"Model '{model_name}' not found. Available models: {available}")

        if retrieve_default:
            if not isinstance(model_info, dict):
                # Check if 'best_model_' and 'best_params_' are among the keys
                main_keys = [key for key in loaded_data if key in (
                    'best_model_', 'best_params_')]
                if len(main_keys) == 0:
                    warnings.warn(
                    "The structure of the default model data is not correctly "
                    "formatted. Expected 'best_model_' and 'best_params_' to be "
                    "present within a dictionary keyed by the model's name. Each key "
                    "should map to a dictionary containing the model itself and its "
                    "parameters, for example: `{'ModelName': {'best_model_': <Model>, "
                    "'best_params_': <Parameters>}}`. Since the expected keys were "
                    "not found, returning the unprocessed model data."
                    )
                    return model_info
                else:
                    # Extract 'best_model_' and 'best_params_' from loaded_data
                    best_model = loaded_data.get('best_model_', None)
                    best_params = loaded_data.get('best_params_', {})
            else:
                # Direct extraction from model_info if it's properly structured
                best_model = model_info.get('best_model_', None)
                best_params = model_info.get('best_params_', {})

            return best_model, best_params

        return model_info

    return loaded_data

def categorize_target(
    arr :ArrayLike |Series , /, 
    func: _F = None,  
    labels: int | List[int] = None, 
    rename_labels: Optional[str] = None, 
    coerce:bool=False,
    order:str='strict',
    ): 
    """ Categorize array to hold the given identifier labels. 
    
    Classifier numerical values according to the given label values. Labels 
    are a list of integers where each integer is a group of unique identifier  
    of a sample in the dataset. 
    
    Parameters 
    -----------
    arr: array-like |pandas.Series 
        array or series containing numerical values. If a non-numerical values 
        is given , an errors will raises. 
    func: Callable, 
        Function to categorize the target y.  
    labels: int, list of int, 
        if an integer value is given, it should be considered as the number 
        of category to split 'y'. For instance ``label=3`` applied on 
        the first ten number, the labels values should be ``[0, 1, 2]``. 
        If labels are given as a list, items must be self-contain in the 
        target 'y'.
    rename_labels: list of str; 
        list of string or values to replace the label integer identifier. 
    coerce: bool, default =False, 
        force the new label names passed to `rename_labels` to appear in the 
        target including or not some integer identifier class label. If 
        `coerce` is ``True``, the target array holds the dtype of new_array. 

    Return
    --------
    arr: Arraylike |pandas.Series
        The category array with unique identifer labels 
        
    Examples 
    --------

    >>> from gofast.tools.mlutils import categorize_target 
    >>> def binfunc(v): 
            if v < 3 : return 0 
            else : return 1 
    >>> arr = np.arange (10 )
    >>> arr 
    ... array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> target = categorize_target(arr, func =binfunc)
    ... array([0, 0, 0, 1, 1, 1, 1, 1, 1, 1], dtype=int64)
    >>> categorize_target(arr, labels =3 )
    ... array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2])
    >>> array([2, 2, 2, 2, 1, 1, 1, 0, 0, 0]) 
    >>> categorize_target(arr, labels =3 , order =None )
    ... array([0, 0, 0, 0, 1, 1, 1, 2, 2, 2])
    >>> categorize_target(arr[::-1], labels =3 , order =None )
    ... array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2]) # reverse does not change
    >>> categorize_target(arr, labels =[0 , 2,  4]  )
    ... array([0, 0, 0, 2, 2, 4, 4, 4, 4, 4])

    """
    arr = _assert_all_types(arr, np.ndarray, pd.Series) 
    is_arr =False 
    if isinstance (arr, np.ndarray ) :
        arr = pd.Series (arr  , name = 'none') 
        is_arr =True 
        
    if func is not None: 
        if not  inspect.isfunction (func): 
            raise TypeError (
                f'Expect a function but got {type(func).__name__!r}')
            
        arr= arr.apply (func )
        
        return  arr.values  if is_arr else arr   
    
    name = arr.name 
    arr = arr.values 

    if labels is not None: 
        arr = _cattarget (arr , labels, order =order)
        if rename_labels is not None: 
            arr = rename_labels_in( arr , rename_labels , coerce =coerce ) 

    return arr  if is_arr else pd.Series (arr, name =name  )

def rename_labels_in (
        arr, new_names, coerce = False): 
    """ Rename label by a new names 
    
    :param arr: arr: array-like |pandas.Series 
         array or series containing numerical values. If a non-numerical values 
         is given , an errors will raises. 
    :param new_names: list of str; 
        list of string or values to replace the label integer identifier. 
    :param coerce: bool, default =False, 
        force the 'new_names' to appear in the target including or not some 
        integer identifier class label. `coerce` is ``True``, the target array 
        hold the dtype of new_array; coercing the label names will not yield 
        error. Consequently can introduce an unexpected results.
    :return: array-like, 
        An array-like with full new label names. 
    """
    
    if not is_iterable(new_names): 
        new_names= [new_names]
    true_labels = np.unique (arr) 
    
    if labels_validator(arr, new_names, return_bool= True): 
        return arr 

    if len(true_labels) != len(new_names):
        if not coerce: 
            raise ValueError(
                "Can't rename labels; the new names and unique label" 
                " identifiers size must be consistent; expect {}, got " 
                "{} label(s).".format(len(true_labels), len(new_names))
                             )
        if len(true_labels) < len(new_names) : 
            new_names = new_names [: len(new_names)]
        else: 
            new_names = list(new_names)  + list(
                true_labels)[len(new_names):]
            warnings.warn("Number of the given labels '{}' and values '{}'"
                          " are not consistent. Be aware that this could "
                          "yield an expected results.".format(
                              len(new_names), len(true_labels)))
            
    new_names = np.array(new_names)
    # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    # hold the type of arr to operate the 
    # element wise comparaison if not a 
    # ValueError:' invalid literal for int() with base 10' 
    # will appear. 
    if not np.issubdtype(np.array(new_names).dtype, np.number): 
        arr= arr.astype (np.array(new_names).dtype)
        true_labels = true_labels.astype (np.array(new_names).dtype)

    for el , nel in zip (true_labels, new_names ): 
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # element comparison throws a future warning here 
        # because of a disagreement between Numpy and native python 
        # Numpy version ='1.22.4' while python version = 3.9.12
        # this code is brittle and requires these versions above. 
        # xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        # suppress element wise comparison warning locally 
        with warnings.catch_warnings():
            warnings.simplefilter(action='ignore', category=FutureWarning)
            arr [arr == el ] = nel 
            
    return arr 

    
def _cattarget (ar , labels , order=None): 
    """ A shadow function of :func:`gofast.tools.mlutils.cattarget`. 
    
    :param ar: array-like of numerical values 
    :param labels: int or list of int, 
        the number of category to split 'ar'into. 
    :param order: str, optional, 
        the order of label to be categorized. If None or any other values, 
        the categorization of labels considers only the length of array. 
        For instance a reverse array and non-reverse array yield the same 
        categorization samples. When order is set to ``strict``, the 
        categorization  strictly considers the value of each element. 
        
    :return: array-like of int , array of categorized values.  
    """
    # assert labels
    if is_iterable (labels):
        labels =[int (_assert_all_types(lab, int, float)) 
                 for lab in labels ]
        labels = np.array (labels , dtype = np.int32 ) 
        cc = labels 
        # assert whether element is on the array 
        s = set (ar).intersection(labels) 
        if len(s) != len(labels): 
            mv = set(labels).difference (s) 
            
            fmt = [f"{'s' if len(mv) >1 else''} ", mv,
                   f"{'is' if len(mv) <=1 else'are'}"]
            warnings.warn("Label values must be array self-contain item. "
                           "Label{0} {1} {2} missing in the array.".format(
                               *fmt)
                          )
            raise ValueError (
                "label value{0} {1} {2} missing in the array.".format(*fmt))
    else : 
        labels = int (_assert_all_types(labels , int, float))
        labels = np.linspace ( min(ar), max (ar), labels + 1 ) #+ .00000001 
        #array([ 0.,  6., 12., 18.])
        # split arr and get the range of with max bound 
        cc = np.arange (len(labels)) #[0, 1, 3]
        # we expect three classes [ 0, 1, 3 ] while maximum 
        # value is 18 . we want the value value to be >= 12 which 
        # include 18 , so remove the 18 in the list 
        labels = labels [:-1] # remove the last items a
        # array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
        # array([0, 0, 0, 0, 1, 1, 1, 2, 2, 2]) # 3 classes 
        #  array([ 0.        ,  3.33333333,  6.66666667, 10. ]) + 
    # to avoid the index bound error 
    # append nan value to lengthen arr 
    r = np.append (labels , np.nan ) 
    new_arr = np.zeros_like(ar) 
    # print(labels)
    ar = ar.astype (np.float32)

    if order =='strict': 
        for i in range (len(r)):
            if i == len(r) -2 : 
                ix = np.argwhere ( (ar >= r[i]) & (ar != np.inf ))
                new_arr[ix ]= cc[i]
                break 
            
            if i ==0 : 
                ix = np.argwhere (ar < r[i +1])
                new_arr [ix] == cc[i] 
                ar [ix ] = np.inf # replace by a big number than it was 
                # rather than delete it 
            else :
                ix = np.argwhere( (r[i] <= ar) & (ar < r[i +1]) )
                new_arr [ix ]= cc[i] 
                ar [ix ] = np.inf 
    else: 
        l= list() 
        for i in range (len(r)): 
            if i == len(r) -2 : 
                l.append (np.repeat ( cc[i], len(ar))) 
                
                break
            ix = np.argwhere ( (ar < r [ i + 1 ] ))
            l.append (np.repeat (cc[i], len (ar[ix ])))  
            # remove the value ready for i label 
            # categorization 
            ar = np.delete (ar, ix  )
            
        new_arr= np.hstack (l).astype (np.int32)  
        
    return new_arr.astype (np.int32)       

def labels_validator (t, /, labels, return_bool = False): 
    """ Assert the validity of the label in the target  and return the label 
    or the boolean whether all items of label are in the target. 
    
    :param t: array-like, target that is expected to contain the labels. 
    :param labels: int, str or list of (str or int) that is supposed to be in 
        the target `t`. 
    :param return_bool: bool, default=False; returns 'True' or 'False' rather 
        the labels if set to ``True``. 
    :returns: bool or labels; 'True' or 'False' if `return_bool` is set to 
        ``True`` and labels otherwise. 
        
    :example: 
    >>> from gofast.datasets import fetch_data 
    >>> from gofast.tools.mlutils import cattarget, labels_validator 
    >>> _, y = fetch_data ('bagoue', return_X_y=True, as_frame=True) 
    >>> # binarize target y into [0 , 1]
    >>> ybin = cattarget(y, labels=2 )
    >>> labels_validator (ybin, [0, 1])
    ... [0, 1] # all labels exist. 
    >>> labels_validator (y, [0, 1, 3])
    ... ValueError: Value '3' is missing in the target.
    >>> labels_validator (ybin, 0 )
    ... [0]
    >>> labels_validator (ybin, [0, 5], return_bool=True ) # no raise error
    ... False
        
    """
    
    if not is_iterable(labels):
        labels =[labels] 
        
    t = np.array(t)
    mask = _isin(t, labels, return_mask=True ) 
    true_labels = np.unique (t[mask]) 
    # set the difference to know 
    # whether all labels are valid 
    remainder = list(set(labels).difference (true_labels))
    
    isvalid = True 
    if len(remainder)!=0 : 
        if not return_bool: 
            # raise error  
            raise ValueError (
                "Label value{0} {1} {2} missing in the target 'y'.".format ( 
                f"{'s' if len(remainder)>1 else ''}", 
                f"{smart_format(remainder)}",
                f"{'are' if len(remainder)> 1 else 'is'}")
                )
        isvalid= False 
        
    return isvalid if return_bool else  labels 
        
def bi_selector (d, /,  features =None, return_frames = False,
                 parse_features:bool=... ):
    """ Auto-differentiates the numerical from categorical attributes.
    
    This is usefull to select the categorial features from the numerical 
    features and vice-versa when we are a lot of features. Enter features 
    individually become tiedous and a mistake could probably happenned. 
    
    Parameters 
    ------------
    d: pandas dataframe 
        Dataframe pandas 
    features : list of str
        List of features in the dataframe columns. Raise error is feature(s) 
        does/do not exist in the frame. 
        Note that if `features` is ``None``, it returns the categorical and 
        numerical features instead. 
        
    return_frames: bool, default =False 
        return the difference columns (features) from the given features  
        as a list. If set to ``True`` returns bi-frames composed of the 
        given features and the remaining features. 
        
    Returns 
    ----------
    - Tuple ( list, list)
        list of features and remaining features 
    - Tuple ( pd.DataFrame, pd.DataFrame )
        List of features and remaing features frames.  
            
    Example 
    --------
    >>> from gofast.tools.mlutils import bi_selector 
    >>> from gofast.datasets import load_hlogs 
    >>> data = load_hlogs().frame # get the frame 
    >>> data.columns 
    >>> Index(['hole_id', 'depth_top', 'depth_bottom', 'strata_name', 'rock_name',
           'layer_thickness', 'resistivity', 'gamma_gamma', 'natural_gamma', 'sp',
           'short_distance_gamma', 'well_diameter', 'aquifer_group',
           'pumping_level', 'aquifer_thickness', 'hole_depth_before_pumping',
           'hole_depth_after_pumping', 'hole_depth_loss', 'depth_starting_pumping',
           'pumping_depth_at_the_end', 'pumping_depth', 'section_aperture', 'k',
           'kp', 'r', 'rp', 'remark'],
          dtype='object')
    >>> num_features, cat_features = bi_selector (data)
    >>> num_features
    ...['gamma_gamma',
         'depth_top',
         'aquifer_thickness',
         'pumping_depth_at_the_end',
         'section_aperture',
         'remark',
         'depth_starting_pumping',
         'hole_depth_before_pumping',
         'rp',
         'hole_depth_after_pumping',
         'hole_depth_loss',
         'depth_bottom',
         'sp',
         'pumping_depth',
         'kp',
         'resistivity',
         'short_distance_gamma',
         'r',
         'natural_gamma',
         'layer_thickness',
         'k',
         'well_diameter']
    >>> cat_features 
    ... ['hole_id', 'strata_name', 'rock_name', 'aquifer_group', 
         'pumping_level']
    """
    parse_features, = ellipsis2false(parse_features )
    _assert_all_types( d, pd.DataFrame, objname=" unfunc'bi-selector'")
    if features is None: 
        d, diff_features, features = to_numeric_dtypes(
            d,  return_feature_types= True ) 
    if features is not None: 
        features = is_iterable(features, exclude_string= True, transform =True, 
                               parse_string=parse_features )
        diff_features = is_in_if( d.columns, items =features, return_diff= True )
        if diff_features is None: diff_features =[]
    return  ( diff_features, features ) if not return_frames else  (
        d [diff_features] , d [features ] ) 

def make_pipe(
    X, 
    y =None, *,   
    num_features = None, 
    cat_features=None, 
    label_encoding='LabelEncoder', 
    scaler = 'StandardScaler' , 
    missing_values =np.nan, 
    impute_strategy = 'median', 
    sparse_output=True, 
    for_pca =False, 
    transform =False, 
    ): 
    """ make a pipeline to transform data at once. 
    
    make a naive pipeline is usefull to fast preprocess the data at once 
    for quick prediction. 
    
    Work with a pandas dataframe. If `None` features is set, the numerical 
    and categorial features are automatically retrieved. 
    
    Parameters
    ---------
    X : pandas dataframe of shape (n_samples, n_features)
        The input samples. Use ``dtype=np.float32`` for maximum
        efficiency. Sparse matrices are also supported, use sparse
        ``csc_matrix`` for maximum efficiency.
    y : array-like of shape (n_samples,) or (n_samples, n_outputs)
        Target relative to X for classification or regression;
        None for unsupervised learning.
    num_features: list or str, optional 
        Numerical features put on the list. If `num_features` are given  
        whereas `cat_features` are ``None``, `cat_features` are figured out 
        automatically.
    cat_features: list of str, optional 
        Categorial features put on the list. If `num_features` are given 
        whereas `num_features` are ``None``, `num_features` are figured out 
        automatically.
    label_encoding: callable or str, default='sklearn.preprocessing.LabelEncoder'
        kind of encoding used to encode label. This assumes 'y' is supplied. 
    scaler: callable or str , default='sklearn.preprocessing.StandardScaler'
        kind of scaling used to scaled the numerical data. Note that for 
        the categorical data encoding, 'sklearn.preprocessing.OneHotEncoder' 
        is implemented  under the hood instead. 
    missing_values : int, float, str, np.nan, None or pandas.NA, default=np.nan
        The placeholder for the missing values. All occurrences of
        `missing_values` will be imputed. For pandas' dataframes with
        nullable integer dtypes with missing values, `missing_values`
        can be set to either `np.nan` or `pd.NA`.
    
    impute_strategy : str, default='mean'
        The imputation strategy.
    
        - If "mean", then replace missing values using the mean along
          each column. Can only be used with numeric data.
        - If "median", then replace missing values using the median along
          each column. Can only be used with numeric data.
        - If "most_frequent", then replace missing using the most frequent
          value along each column. Can be used with strings or numeric data.
          If there is more than one such value, only the smallest is returned.
        - If "constant", then replace missing values with fill_value. Can be
          used with strings or numeric data.
    
           strategy="constant" for fixed value imputation.
           
    sparse_output : bool, default=False
        Is used when label `y` is given. Binarize labels in a one-vs-all 
        fashion. If ``True``, returns array from transform is desired to 
        be in sparse CSR format.
        
    for_pca:bool, default=False, 
        Transform data for principal component ( PCA) analysis. If set to 
        ``True``, :class:`sklearn.preprocessing.OrdinalEncoder`` is used insted 
        of :class:sklearn.preprocessing.OneHotEncoder``. 
        
    transform: bool, default=False, 
        Tranform data inplace rather than returning the naive pipeline. 
        
    Returns
    ---------
    full_pipeline: :class:`gofast.exlib.sklearn.FeatureUnion`
        - Full pipeline composed of numerical and categorical pipes 
    (X_transformed &| y_transformed):  {array-like, sparse matrix} of \
        shape (n_samples, n_features)
        - Transformed data. 
        
        
    Examples 
    ---------
    >>> from gofast.tools.mlutils import make_naive_pipe 
    >>> from gofast.datasets import load_hlogs 
    
    (1) Make a naive simple pipeline  with RobustScaler, StandardScaler 
    >>> from gofast.exlib.sklearn import RobustScaler 
    >>> X_, y_ = load_hlogs (as_frame=True )# get all the data  
    >>> pipe = make_naive_pipe(X_, scaler =RobustScaler ) 
    
    (2) Transform X in place with numerical and categorical features with 
    StandardScaler (default). Returned CSR matrix 
    
    >>> make_naive_pipe(X_, transform =True )
    ... <181x40 sparse matrix of type '<class 'numpy.float64'>'
    	with 2172 stored elements in Compressed Sparse Row format>

    """
    
    from ..transformers import DataFrameSelector
    
    sc= {"StandardScaler": StandardScaler ,"MinMaxScaler": MinMaxScaler , 
         "Normalizer":Normalizer , "RobustScaler":RobustScaler}

    if not hasattr (X, '__array__'):
        raise TypeError(f"'make_naive_pipe' not supported {type(X).__name__!r}."
                        " Expects X as 'pandas.core.frame.DataFrame' object.")
    X = check_array (
        X, 
        dtype=object, 
        force_all_finite="allow-nan", 
        to_frame=True, 
        input_name="Array for transforming X or making naive pipeline"
        )
    if not hasattr (X, "columns"):
        # create naive column for 
        # Dataframe selector 
        X = pd.DataFrame (
            X, columns = [f"naive_{i}" for i in range (X.shape[1])]
            )
    #-> Encode y if given
    if y is not None: 
        # if (label_encoding =='labelEncoder'  
        #     or get_estimator_name(label_encoding) =='LabelEncoder'
        #     ): 
        #     enc =LabelEncoder()
        if  ( label_encoding =='LabelBinarizer' 
                or get_estimator_name(label_encoding)=='LabelBinarizer'
               ): 
            enc =LabelBinarizer(sparse_output=sparse_output)
        else: 
            label_encoding =='labelEncoder'
            enc =LabelEncoder()
            
        y= enc.fit_transform(y)
    #set features
    if num_features is not None: 
        cat_features, num_features  = bi_selector(
            X, features= num_features 
            ) 
    elif cat_features is not None: 
        num_features, cat_features  = bi_selector(
            X, features= cat_features 
            )  
    if ( cat_features is None 
        and num_features is None 
        ): 
        num_features , cat_features = bi_selector(X ) 
    # assert scaler value 
    if get_estimator_name (scaler)  in sc.keys(): 
        scaler = sc.get (get_estimator_name(scaler )) 
    elif ( any ( [v.lower().find (str(scaler).lower()) >=0
                  for v in sc.keys()])
          ):  
        for k, v in sc.items () :
            if k.lower().find ( str(scaler).lower() ) >=0: 
                scaler = v ; break 
    else : 
        msg = ( f"Supports {smart_format( sc.keys(), 'or')} or "
                "other scikit-learn scaling objects, got {!r}" 
                )
        if hasattr (scaler, '__module__'): 
            name = getattr (scaler, '__module__')
            if getattr (scaler, '__module__') !='sklearn.preprocessing._data':
                raise ValueError (msg.format(name ))
        else: 
            name = scaler.__name__ if callable (scaler) else (
                scaler.__class__.__name__ ) 
            raise ValueError (msg.format(name ))
    # make pipe 
    npipe = [
            ('imputerObj',SimpleImputer(missing_values=missing_values , 
                                    strategy=impute_strategy)),                
            ('scalerObj', scaler() if callable (scaler) else scaler ), 
            ]
    
    if len(num_features)!=0 : 
       npipe.insert (
            0,  ('selectorObj', DataFrameSelector(columns= num_features))
            )

    num_pipe=Pipeline(npipe)
    
    if for_pca : 
        encoding=  ('OrdinalEncoder',OrdinalEncoder())
    else:  encoding =  (
        'OneHotEncoder', OneHotEncoder())
        
    cpipe = [
        encoding
        ]
    if len(cat_features)!=0: 
        cpipe.insert (
            0, ('selectorObj', DataFrameSelector(columns= cat_features))
            )

    cat_pipe = Pipeline(cpipe)
    # make transformer_list 
    transformer_list = [
        ('num_pipeline', num_pipe),
        ('cat_pipeline', cat_pipe), 
        ]

    #remove num of cat pipe if one of them is 
    # missing in the data 
    if len(cat_features)==0: 
        transformer_list.pop(1) 
    if len(num_features )==0: 
        transformer_list.pop(0)
        
    full_pipeline =FeatureUnion(transformer_list=transformer_list) 
    
    return  ( full_pipeline.fit_transform (X) if y is None else (
        full_pipeline.fit_transform (X), y ) 
             ) if transform else full_pipeline

@ensure_pkg (
    "imblearn", 
    partial_check=True, 
    condition="balance_classes", 
    extra= (
        "Synthetic Minority Over-sampling Technique (SMOTE) cannot be used."
        " Note,`imblearn` is actually a shorthand for ``imbalanced-learn``."
        ), 
   )
def build_data_preprocessor(
    X: Union [NDArray, DataFrame], 
    y: Optional[ArrayLike] = None, *,  
    num_features: Optional[List[str]] = None, 
    cat_features: Optional[List[str]] = None, 
    custom_transformers: Optional[List[Tuple[str, TransformerMixin]]] = None,
    label_encoding: Union[str, TransformerMixin] = 'LabelEncoder', 
    scaler: Union[str, TransformerMixin] = 'StandardScaler', 
    missing_values: Union[int, float, str, np.nan, None] = np.nan, 
    impute_strategy: str = 'median', 
    feature_interaction: bool = False,
    dimension_reduction: Optional[Union[str, TransformerMixin]] = None,
    feature_selection: Optional[Union[str, TransformerMixin]] = None,
    balance_classes: bool = False,
    advanced_imputation: Optional[TransformerMixin] = None,
    verbose: bool = False,
    output_format: str = 'array',
    transform: bool = False,
    **kwargs: Any
) -> Any:
    """
    Create a preprocessing pipeline for data transformation and feature engineering.

    This function constructs a pipeline to preprocess data for machine learning tasks, 
    accommodating a variety of transformations including scaling, encoding, 
    and dimensionality reduction. It supports both numerical and categorical data, 
    and can incorporate custom transformations.

    Parameters
    ----------
    X : np.ndarray or DataFrame
        Input features dataframe or arraylike. Must be two dimensional array.
    y : array-like, optional
        Target variable. Required for supervised learning tasks.
    num_features : list of str, optional
        List of numerical feature names. If None, determined automatically.
    cat_features : list of str, optional
        List of categorical feature names. If None, determined automatically.
    custom_transformers : list of tuples, optional
        Custom transformers to be included in the pipeline. Each tuple should 
        contain ('name', transformer_instance).
    label_encoding : str or transformer, default 'LabelEncoder'
        Encoder for the target variable. Accepts standard scikit-learn encoders 
        or custom encoder objects.
    scaler : str or transformer, default 'StandardScaler'
        Scaler for numerical features. Accepts standard scikit-learn scalers 
        or custom scaler objects.
    missing_values : int, float, str, np.nan, None, default np.nan
        Placeholder for missing values for imputation.
    impute_strategy : str, default 'median'
        Imputation strategy. Options: 'mean', 'median', 'most_frequent', 'constant'.
    feature_interaction : bool, default False
        If True, generate polynomial and interaction features.
    dimension_reduction : str or transformer, optional
        Dimensionality reduction technique. Accepts 'PCA', 't-SNE', or custom object.
    feature_selection : str or transformer, optional
        Feature selection method. Accepts 'SelectKBest', 'SelectFromModel', or custom object.
    balance_classes : bool, default False
        If True, balance classes in classification tasks.
    advanced_imputation : transformer, optional
        Advanced imputation technique like KNNImputer or IterativeImputer.
    verbose : bool, default False
        Enable verbose output.
    output_format : str, default 'array'
        Desired output format: 'array' or 'dataframe'.
    transform : bool, default False
        If True, apply the pipeline to the data immediately and return transformed data.

    Returns
    -------
    full_pipeline : Pipeline or (X_transformed, y_transformed)
        The constructed preprocessing pipeline, or transformed data if `transform` is True.

    Examples
    --------
    >>> from gofast.tools.mlutils import build_data_preprocessor
    >>> from gofast.datasets import load_hlogs
    >>> X, y = load_hlogs(as_frame=True, return_X_y=True)
    >>> pipeline = build_data_preprocessor(X, y, scaler='RobustScaler')
    >>> X_transformed = pipeline.fit_transform(X)
    
    """
    sc= {"StandardScaler": StandardScaler ,"MinMaxScaler": MinMaxScaler , 
         "Normalizer":Normalizer , "RobustScaler":RobustScaler}

    if not isinstance (X, pd.DataFrame): 
        # create fake dataframe for handling columns features 
        X= pd.DataFrame(X)
    # assert scaler value 
    if get_estimator_name (scaler) in sc.keys(): 
        scaler = sc.get (get_estimator_name(scaler ))() 
        
    # Define numerical and categorical pipelines
    numerical_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy=impute_strategy, missing_values=missing_values)),
        ('scaler', StandardScaler() if scaler == 'StandardScaler' else scaler)
    ])

    categorical_pipeline = Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent', missing_values=missing_values)),
        ('encoder', OneHotEncoder() if label_encoding == 'LabelEncoder' else label_encoding)
    ])

    # Determine automatic feature selection if not provided
    if num_features is None and cat_features is None:
        num_features = make_column_selector(dtype_include=['int', 'float'])(X)
        cat_features = make_column_selector(dtype_include='object')(X)

    # Feature Union for numerical and categorical features
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_pipeline, num_features),
            ('cat', categorical_pipeline, cat_features)
        ])

    # Add custom transformers if any
    if custom_transformers:
        for name, transformer in custom_transformers:
            preprocessor.named_transformers_[name] = transformer

    # Feature interaction, selection, and dimension reduction
    steps = [('preprocessor', preprocessor)]
    
    if feature_interaction:
        steps.append(('interaction', PolynomialFeatures()))
    if feature_selection:
        steps.append(('feature_selection', SelectKBest() 
                      if feature_selection == 'SelectKBest' else feature_selection))
    if dimension_reduction:
        steps.append(('dim_reduction', PCA() if dimension_reduction == 'PCA' 
                      else dimension_reduction))

    # Final pipeline
    pipeline = Pipeline(steps)

   # Advanced imputation logic if required
    if advanced_imputation:
        from sklearn.experimental import enable_iterative_imputer # noqa
        from sklearn.impute import IterativeImputer
        if advanced_imputation == 'IterativeImputer':
            steps.insert(0, ('advanced_imputer', IterativeImputer(
                estimator=RandomForestClassifier(), random_state=42)))
        else:
            steps.insert(0, ('advanced_imputer', advanced_imputation))

    # Final pipeline before class balancing
    pipeline = Pipeline(steps)

    # Class balancing logic if required
    if balance_classes and y is not None:
        if str(balance_classes).upper() == 'SMOTE':
            from imblearn.over_sampling import SMOTE
            # Note: SMOTE works on numerical data, so it's applied after initial pipeline
            pipeline = Pipeline([('preprocessing', pipeline), (
                'smote', SMOTE(random_state=42))])

    # Transform data if transform flag is set
    # if transform:
    output_format = output_format or 'array' # force none to hold array
    if str(output_format) not in ('array', 'dataframe'): 
        raise ValueError(f"Invalid '{output_format}', expect 'array' or 'dataframe'.")
        
    return _execute_transformation(
        pipeline, X, y, transform, output_format, label_encoding)

def _execute_transformation(
        pipeline, X, y, transform, output_format, label_encoding):
    """ # Transform data if transform flag is set or return pipeline"""
    if transform:
        X_transformed = pipeline.fit_transform(X)
        if y is not None:
            y_transformed = _transform_target(y, label_encoding) if label_encoding else y
            return (X_transformed, y_transformed) if output_format == 'array' else (
                pd.DataFrame(X_transformed), pd.Series(y_transformed))
        
        return X_transformed if output_format == 'array' else pd.DataFrame(X_transformed)
    
    return pipeline

def _transform_target(y, label_encoding:BaseEstimator|TransformerMixin ):
    if label_encoding == 'LabelEncoder':
        encoder = LabelEncoder()
        return encoder.fit_transform(y)
    elif isinstance(label_encoding, (BaseEstimator, TransformerMixin)):
        return label_encoding.fit_transform(y)
    else:
        raise ValueError("Unsupported label_encoding value: {}".format(label_encoding)) 
         
def select_feature_importances(
        clf, X, y=None, *, threshold=0.1, prefit=True, 
        verbose=0, return_selector=False, **kwargs
        ):
    """
    Select features based on importance thresholds after model fitting.
    
    Parameters
    ----------
    clf : estimator object
        The estimator from which the feature importances are derived. Must have
        either `feature_importances_` or `coef_` attributes after fitting, unless
        `importance_getter` is specified in `kwargs`.
        
    X : {array-like, sparse matrix} of shape (n_samples, n_features)
        The training input samples.
        
    y : array-like of shape (n_samples,), default=None
        The target values (class labels) as integers or strings.
        
    threshold : float, default=0.1
        The threshold value to use for feature selection. Features with importance
        greater than or equal to this value are retained.
        
    prefit : bool, default=True
        Whether the estimator is expected to be prefit. If `True`, `clf` should
        already be fitted; otherwise, it will be fitted on `X` and `y`.
        
    verbose : int, default=0
        Controls the verbosity: the higher, the more messages.
        
    return_selector : bool, default=False
        Whether to return the selector object instead of the transformed data.
        
    **kwargs : additional keyword arguments
        Additional arguments passed to `SelectFromModel`.
    
    Returns
    -------
    X_selected or selector : array or SelectFromModel object
        The selected features in `X` if `return_selector` is False, or the
        selector object itself if `return_selector` is True.
        
    Examples
    --------
    >>> from sklearn.datasets import make_classification
    >>> from sklearn.ensemble import RandomForestClassifier
    >>> from gofast.tools.mlutils import select_feature_importances
    >>> X, y = make_classification(n_samples=1000, n_features=10, n_informative=3)
    >>> clf = RandomForestClassifier()
    >>> X_selected = select_feature_importances(clf, X, y, threshold="mean", prefit=False)
    >>> X_selected.shape
    (1000, n_selected_features)
    
    Using `return_selector=True` to get the selector object:
    
    >>> selector = select_feature_importances(
        clf, X, y, threshold="mean", prefit=False, return_selector=True)
    >>> selector.get_support()
    array([True, False, ..., True])
    """
    # Check if the classifier is fitted based on the presence of attributes
    if not prefit and (hasattr(clf, 'feature_importances_') or hasattr(clf, 'coef_')):
        warnings.warn(f"The estimator {clf.__class__.__name__} appears to be fitted. "
                      "Consider setting `prefit=True` or refit the estimator.",UserWarning)
    try:threshold = float(threshold ) 
    except: pass 

    selector = SelectFromModel(clf, threshold=threshold, prefit=prefit, **kwargs)
    
    if not prefit:
        selector.fit(X, y)
    
    if verbose:
        n_features = selector.transform(X).shape[1]
        print(f"Number of features meeting the threshold={threshold}: {n_features}")
    
    return selector if return_selector else selector.transform(X)

def soft_imputer(
    X, 
    strategy='mean', 
    missing_values=np.nan, 
    fill_value=None, 
    drop_features=False, 
    mode=None, 
    copy=True, 
    verbose=0, 
    add_indicator=False,
    keep_empty_features=False, 
    **kwargs
    ):
    """
    Impute missing values in a dataset, optionally dropping features and handling 
    both numerical and categorical data.

    This function extends the functionality of scikit-learn's SimpleImputer to 
    support dropping specified features and a ``bi-impute`` mode for handling 
    both numerical and categorical data. It ensures API consistency with 
    scikit-learn's transformers and allows for flexible imputation strategies.

    Parameters
    ----------
    X : array-like or sparse matrix of shape (n_samples, n_features)
        The input data to impute.
        
    strategy : str, default='mean'
        The imputation strategy:
        - 'mean': Impute using the mean of each column. Only for numeric data.
        - 'median': Impute using the median of each column. Only for numeric data.
        - 'most_frequent': Impute using the most frequent value of each column. 
          For numeric and categorical data.
        - 'constant': Impute using the specified `fill_value`.
        
    missing_values : int, float, str, np.nan, None, or pd.NA, default=np.nan
        The placeholder for the missing values. All occurrences of
        `missing_values` will be imputed.
        
    fill_value : str or numerical value, default=None
        When `strategy` == 'constant', `fill_value` is used to replace all
        occurrences of `missing_values`. If left to the default, `fill_value` 
        will be 0 when imputing numerical data and 'missing_value' for strings 
        or object data types.
        For 'constant' strategy, specifies the value used for replacement.
        In 'bi-impute' mode, allows specifying separate fill values for
        numerical and categorical data using a delimiter from the set
        {"__", "--", "&", "@", "!"}. For example, "0.5__missing" indicates
        0.5 as fill value for numerical data and "missing" for categorical.
        
    drop_features : bool or list, default=False
        If True, drops all categorical features before imputation. If a list, 
        drops specified features.
    mode : str, optional
        If set to 'bi-impute', imputes both numerical and categorical features 
        and returns a single imputed dataframe. Only 'bi-impute' is supported.
    copy : bool, default=True
        If True, a copy of X will be created. If False, imputation will
        be done in-place whenever possible.
    verbose : int, default=0
        Controls the verbosity of the imputer.
    add_indicator : bool, default=False
        If True, a `MissingIndicator` transform will be added to the output 
        of the imputer's transform.
    keep_empty_features : bool, default=False
        If True, features that are all missing when `fit` is called are 
        included in the transform output.
    **kwargs : dict
        Additional fitting parameters.

    Returns
    -------
    Xi : array-like or sparse matrix of shape (n_samples, n_features)
        The imputed dataset.

    Examples
    --------
    >>> X = np.array([[1, np.nan, 3], [4, 5, np.nan], [np.nan, np.nan, 9]])
    >>> soft_imputer(X, strategy='mean')
    array([[ 1. ,  5. ,  3. ],
           [ 4. ,  5. ,  6. ],
           [ 2.5,  5. ,  9. ]])
    
    >>> df = pd.DataFrame({'A': [1, 2, np.nan], 'B': ['a', np.nan, 'b']})
    >>> soft_imputer(df, strategy='most_frequent', mode='bi-impute')
               A  B
        0    1.0  a
        1    2.0  a
        2    1.5  b

    Notes
    -----
    The 'bi-impute' mode requires categorical features to be explicitly indicated
    as such by using pandas Categorical dtype or by specifying features to drop.
    """
    X, is_frame  = _convert_to_dataframe(X)
    X = _drop_features(X, drop_features)
    
    if mode == 'bi-impute':
        fill_values, strategies = _enabled_bi_impute_mode (strategy, fill_value)
        try: 
            num_imputer = SimpleImputer(
                strategy=strategies[0], missing_values=missing_values,
                fill_value=fill_values[0])
        except ValueError as e: 
            msg= (" Consider using the {'__', '--', '&', '@', '!'} delimiter"
                  " for mixed numeric and categorical fill values.")
            # Improve the error message 
            raise ValueError(
                f"Imputation failed due to: {e}." +
                msg if check_mixed_data_types(X) else ''
                )
        cat_imputer = SimpleImputer(strategy= strategies[1], 
                                    missing_values=missing_values,
                                    fill_value = fill_values [1]
                                    )
        num_imputed, cat_imputed, num_columns, cat_columns = _separate_and_impute(
            X, num_imputer, cat_imputer)
        Xi = np.hstack((num_imputed, cat_imputed))
        new_columns = num_columns + cat_columns
        Xi = pd.DataFrame(Xi, index=X.index, columns=new_columns)
    else:
        try:
            Xi, imp = _impute_data(
                X, strategy, missing_values, fill_value, add_indicator, copy)
        except Exception as e : 
            raise ValueError( f"Imputation failed due to: {e}. Consider using"
                             " the 'bi-impute' mode for mixed data types.")
        if isinstance(X, pd.DataFrame):
            Xi = pd.DataFrame(Xi, index=X.index, columns=imp.feature_names_in_)
            
    if not is_frame: # revert back to array
        Xi = np.array ( Xi )
    return Xi

def _convert_to_dataframe(X):
    """Ensure input is a pandas DataFrame."""
    is_frame=True 
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(check_array(X, dtype=None, force_all_finite='allow-nan'), 
                         columns=[f'feature_{i}' for i in range(X.shape[1])])
        is_frame=False 
    return X, is_frame 

def _drop_features(X, drop_features):
    """Drop specified features from the DataFrame."""
    if isinstance(drop_features, bool) and drop_features:
        X = X.select_dtypes(exclude=['object', 'category'])
    elif isinstance(drop_features, list):
        X = X.drop(columns=drop_features, errors='ignore')
    return X

def _impute_data(X, strategy, missing_values, fill_value, add_indicator, copy):
    """Impute the dataset using SimpleImputer."""
    imp = SimpleImputer(strategy=strategy, missing_values=missing_values, 
                        fill_value=fill_value, add_indicator=add_indicator, 
                        copy=copy)
    Xi = imp.fit_transform(X)
    return Xi, imp

def _separate_and_impute(X, num_imputer, cat_imputer):
    """Separate and impute numerical and categorical features."""
    X, num_columns, cat_columns= to_numeric_dtypes(X, return_feature_types=True )

    if len(num_columns) > 0:
        num_imputed = num_imputer.fit_transform(X[num_columns])
    else:
        num_imputed = np.array([]).reshape(X.shape[0], 0)
    
    if len(cat_columns) > 0:
        cat_imputed = cat_imputer.fit_transform(X[cat_columns])
    else:
        cat_imputed = np.array([]).reshape(X.shape[0], 0)
    return num_imputed, cat_imputed, num_columns, cat_columns


def _enabled_bi_impute_mode(
    strategy: str, fill_value: Union[str, float, None]
     ) -> Tuple[List[Union[None, float, str]], List[str]]:
    """
    Determines strategies and fill values for numerical and categorical data
    in bi-impute mode based on the provided strategy and fill value.

    Parameters
    ----------
    strategy : str
        The imputation strategy to use.
    fill_value : Union[str, float, None]
        The fill value to use for imputation, which can be a float, string, 
        or None. When a string containing delimiters is provided, it indicates
        separate fill values for numerical and categorical data.

    Returns
    -------
    Tuple[List[Union[None, float, str]], List[str]]
        A tuple containing two lists: the first with fill values for numerical
        and categorical data, and the second with strategies for numerical and
        categorical data.

    Examples
    --------
    >>> from gofast.tools.mlutils import enabled_bi_impute_mode
    >>> enabled_bi_impute_mode('mean', None)
    ([None, None], ['mean', 'most_frequent'])

    >>> enabled_bi_impute_mode('constant', '0__missing')
    ([0.0, 'missing'], ['constant', 'constant'])
    
    >>> enabled_bi_impute_mode (strategy='constant', fill_value="missing")
    ([0.0, 'missing'], ['constant', 'constant'])
    
    >>> enabled_bi_impute_mode('constant', 9.) 
    ([9.0, None], ['constant', 'most_frequent'])
    
    >>> enabled_bi_impute_mode(strategy='constant', fill_value="mean__missing",)
    ([None, 'missing'], ['mean', 'constant'])
    """
    num_strategy, cat_strategy = 'most_frequent', 'most_frequent'
    fill_values = [None, None]
    
    if fill_value is None or isinstance(fill_value, (float, int)):
        if strategy in ["mean", 'median', 'constant']:
            num_strategy = strategy
            fill_values[0] = ( 
                0.0 if strategy == 'constant' 
                and fill_value is None else fill_value
                )
        return fill_values, [num_strategy, cat_strategy]

    if contains_delimiter(fill_value,{"__", "--", "&", "@", "!"} ):
        fill_values, strategies = _manage_fill_value(fill_value, strategy)
    else:
        fill_value = (
            f"{strategy}__{fill_value}" if strategy in ['mean', 'median'] 
            else ( f"0__{fill_value}" if strategy =="constant" else fill_value )
        )
        fill_values, strategies = _manage_fill_value(fill_value, strategy)
    
    return fill_values, strategies

def _manage_fill_value(
    fill_value: str, strategy: str
    ) -> Tuple[List[Union[None, float, str]], List[str]]:
    """
    Parses and manages fill values for bi-impute mode, supporting mixed types.

    Parameters
    ----------
    fill_value : str
        The fill value string potentially containing mixed types for numerical
        and categorical data.
    strategy : str
        The imputation strategy to determine how to handle numerical fill values.

    Returns
    -------
    Tuple[List[Union[None, float, str]], List[str]]
        A tuple containing two elements: the first is a list with numerical and
        categorical fill values, and the second is a list of strategies for 
        numerical and categorical data.

    Raises
    ------
    ValueError
        If the fill value does not contain a proper separator or if the numerical
        fill value is incompatible with the specified strategy.

    Examples
    --------
    >>> from gofast.tools.mlutils import _manage_fill_value
    >>> _manage_fill_value("0__missing", "constant")
    ([0.0, 'missing'], ['constant', 'constant'])

    >>> _manage_fill_value("mean__missing", "mean")
    ([None, 'missing'], ['mean', 'constant'])
    """
    regex = re.compile(r'(__|--|&|@|!)')
    parts = regex.split(fill_value)
    if len(parts) < 3:
        raise ValueError("Fill value must contain a separator (__|--|&|@|!)"
                         " between numerical and categorical fill values.")

    num_fill, cat_fill = parts[0], parts[-1]
    num_fill_value = None if strategy in ['mean', 'median'] and num_fill.lower(
        ) in ['mean', 'median'] else num_fill

    try:
        num_fill_value = float(num_fill) if num_fill.replace('.', '', 1).isdigit() else num_fill
    except ValueError:
        raise ValueError(f"Numerical fill value '{num_fill}' must be a float"
                         f" for strategy '{strategy}'.")
    strategies =[ strategy if strategy in ['mean', 'median', 'constant']
                 else 'most_frequent', 'constant'] 
    if num_fill.lower() in ['mean', 'median'] and strategy=='constant': 
        # Permutate the strategy and fill value. 
        strategies [0]= num_fill.lower()
        num_fill_value =None ; 
    
    return [num_fill_value, cat_fill], strategies

def soft_scaler(
    X, *, 
    kind=StandardScaler, 
    copy=True, 
    with_mean=True, 
    with_std=True, 
    feature_range=(0, 1), 
    clip=False, 
    norm='l2',
    verbose=0, 
    **kwargs
    ):
    """
    Scale data using specified scaling strategy from scikit-learn. 
    
    Function excludes categorical features from scaling and provides 
    feedback via verbose parameter.

    Parameters
    ----------
    X : DataFrame or array-like of shape (n_samples, n_features)
        The data to scale, can contain both numerical and categorical features.
    kind : str, default='StandardScaler'
        The kind of scaling to apply to numerical features. One of 'StandardScaler', 
        'MinMaxScaler', 'Normalizer', or 'RobustScaler'.
    copy : bool, default=True
        If False, avoid a copy and perform inplace scaling instead.
    with_mean : bool, default=True
        If True, center the data before scaling. Only applicable when kind is
        'StandardScaler' or 'RobustScaler'.
    with_std : bool, default=True
        If True, scale the data to unit variance. Only applicable when kind is
        'StandardScaler' or 'RobustScaler'.
    feature_range : tuple (min, max), default=(0, 1)
        Desired range of transformed data. Only applicable when kind 
        is 'MinMaxScaler'.
    clip : bool, default=False
        Set to True to clip transformed values to the provided feature range.
        Only applicable when kind is 'MinMaxScaler'.
    norm : {'l1', 'l2', 'max'}, default='l2'
        The norm to use to normalize each non-zero sample or feature.
        Only applicable when kind is 'Normalizer'.
        
    verbose : int, default=0
        If > 0, print messages about the processing.
        
    **kwargs : additional keyword arguments
        Additional fitting parameters to pass to the scaler.
        
    Returns
    -------
    X_scaled : {ndarray, sparse matrix, dataframe} of shape (n_samples, n_features)
        The scaled data. The scaled data with numerical features scaled according
        to the specified kind, and categorical features returned unchanged. 
        The return type matches the input type.

    Examples
    --------
    >>> import numpy as np 
    >>> import pandas as pd 
    >>> from gofast.tools.mlutils import soft_scaler
    >>> X = np.array([[1, -1, 2], [2, 0, 0], [0, 1, -1]])
    >>> X_scaled = soft_scaler(X, kind='StandardScaler')
    >>> print(X_scaled)
    [[ 0.  -1.22474487  1.33630621]
     [ 1.22474487  0.  -0.26726124]
     [-1.22474487  1.22474487 -1.06904497]]

    >>> df = pd.DataFrame(X, columns=['a', 'b', 'c'])
    >>> df_scaled = soft_scaler(df, kind='RobustScaler', with_centering=True,
                                with_scaling=True)
    >>> print(df_scaled)
              a    b    c
        0 -0.5 -1.0  1.0
        1  0.5  0.0  0.0
        2 -0.5  1.0 -1.0
    """
    X= to_numeric_dtypes(X)
    input_is_dataframe = isinstance(X, pd.DataFrame)
    cat_features = X.select_dtypes(
        exclude=['number']).columns if input_is_dataframe else []

    if verbose > 0 and len(cat_features) > 0:
        print("Note: Categorical data detected and excluded from scaling.")

    kind= kind if isinstance(kind, str) else kind.__name__
    scaler = _determine_scaler(
        kind, copy=copy, with_mean=with_mean, with_std=with_std, norm=norm, 
        feature_range=feature_range, clip=clip, **kwargs)

    if input_is_dataframe:
        num_features = X.select_dtypes(include=['number']).columns
        X_scaled_numeric = _scale_numeric_features(X, scaler, num_features)
        X_scaled = _concat_scaled_numeric_with_categorical(
            X_scaled_numeric, X, cat_features)
    else:
        X_scaled = scaler.fit_transform(X)
    
    return X_scaled

def _determine_scaler(kind, **kwargs):
    """
    Determines the scaler based on the kind parameter.
    """
    scaler_classes = {
        'StandardScaler': StandardScaler,
        'MinMaxScaler': MinMaxScaler,
        'Normalizer': Normalizer,
        'RobustScaler': RobustScaler
    }
    scaler_class = scaler_classes.get(kind, None)
    if scaler_class is None:
        raise ValueError(f"Unsupported scaler kind: {kind}. Supported scalers"
                         f" are: {', '.join(scaler_classes.keys())}.")
    kwargs= get_valid_kwargs(scaler_class, **kwargs)
    return scaler_class(**kwargs)

def _scale_numeric_features(X, scaler, num_features):
    """
    Scales numerical features of the DataFrame X using the provided scaler.
    """
    return scaler.fit_transform(X[num_features])

def _concat_scaled_numeric_with_categorical(X_scaled_numeric, X, cat_features):
    """
    Concatenates scaled numerical features with original categorical features.
    """
    X_scaled = pd.concat([pd.DataFrame(X_scaled_numeric, index=X.index, 
                        columns=X.select_dtypes(include=['number']).columns),
                          X[cat_features]], axis=1)
    return X_scaled[X.columns]  # Maintain original column order


        
        
        
        
        
        
        

