# -*- coding: utf-8 -*-

from .plot import ( 
    pobj,
    biPlot, 
    EvalPlot, 
    plotLearningInspection, 
    plotLearningInspections, 
    plotSilhouette,
    plotDendrogram, 
    plotDendroheat, 
    plotProjection, 
    plotModel, 
    plot_reg_scoring, 
    plot_matshow, 
    plot_model_scores, 
    plot2d,
    )
from .plotutils import ( 
    plot_mlxtend_heatmap , 
    plot_mlxtend_matrix, 
    plot_cost_vs_epochs, 
    plot_elbow, 
    plot_clusters, 
    plot_pca_components, 
    plot_naive_dendrogram, 
    plot_learning_curves, 
    plot_confusion_matrices, 
    plot_yb_confusion_matrix, 
    plot_sbs_feature_selection, 
    plot_regularization_path, 
    plot_rf_feature_importances, 
    plot_silhouette, 
    plot_voronoi, 
    plot_roc_curves, 
    plot_l_curve, 
    )
__all__= [
    "pobj",
    "biPlot", 
    "EvalPlot", 
    "QuickPlot" , 
    "ExPlot",
    "plotLearningInspection", 
    "plotLearningInspections", 
    "plotSilhouette", 
    "plotDendrogram", 
    "plotDendroheat", 
    "viewtemplate", 
    "plotProjection", 
    "plotModel", 
    "plot_reg_scoring", 
    "plot_matshow", 
    "plot_model_scores", 
    "plot2d", 
    'plot_mlxtend_heatmap' , 
    'plot_mlxtend_matrix', 
    'plot_cost_vs_epochs', 
    'plot_elbow', 
    'plot_clusters', 
    'plot_pca_components', 
    'plot_naive_dendrogram', 
    'plot_learning_curves', 
    'plot_confusion_matrices', 
    'plot_yb_confusion_matrix', 
    'plot_sbs_feature_selection', 
    'plot_regularization_path', 
    'plot_rf_feature_importances', 
    'plot_silhouette', 
    'plot_voronoi', 
    'plot_roc_curves', 
    'plot_l_curve', 

    ]