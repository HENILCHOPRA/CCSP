import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from data import select_query

model = None

def load_model():
	global model
	with open('model.pkl', 'rb') as handle:
    	model = pickle.load(handle)

def get_predictions(Xs):
	if model == None:
		load_model()
	else model.fit_predict(Xs[:,].reshape(-1,1))
	
if __name__ == '__main__':
	load_model()