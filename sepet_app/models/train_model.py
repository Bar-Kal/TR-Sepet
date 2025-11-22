import numpy as np
from gensim.models import FastText
from sklearn.svm import SVC
from sklearn.metrics import classification_report
from sklearn.model_selection import GridSearchCV
from loguru import logger
import re
import argparse

def preprocess(text):
    text = text.lower()
    return text.split()

def get_document_vector(doc_tokens, model):
    valid_tokens = [word for word in doc_tokens if word in model.wv]
    if not valid_tokens:
        return np.zeros(model.vector_size)
    vectors = [model.wv[word] for word in valid_tokens]
    return np.mean(vectors, axis=0)

def train_model(run_hyperparameter: int = 0):
    """
    Trains a fastText model on the training data.
    """
    logger.info("Starting model training...")
    try:
        # Load the training data
        with open("./train/fasttext_training_data.txt", "r", encoding="utf-8") as f:
            train_data = f.readlines()

        # Load the testing data
        with open("./test/fasttext_test_data.txt", "r", encoding="utf-8") as f:
            test_data = f.readlines()

        # Prepare data for Gensim and Scikit-learn
        train_texts = [preprocess(line.strip().split(" ", 1)[1]) for line in train_data]
        train_labels = [line.split(" ")[0] for line in train_data]
        test_texts = [preprocess(line.strip().split(" ", 1)[1]) for line in test_data]
        test_labels = [line.split(" ")[0] for line in test_data]

        # Train Unsupervised FastText Model with Gensim
        logger.info("Training FastText model...")
        ft_model = FastText(
            sentences=train_texts,
            vector_size=100,
            window=5,
            min_count=1,
            workers=4,
            sg=1  # Use skip-gram algorithm to train
        )
        logger.info("FastText model training complete.")

        # Create Document Vectors
        X_train = np.array([get_document_vector(text, ft_model) for text in train_texts])
        X_test = np.array([get_document_vector(text, ft_model) for text in test_texts])

        logger.info(f"X_train shape: {X_train.shape}")
        logger.info(f"X_test shape: {X_test.shape}")


        if run_hyperparameter == 1:
            # Hyperparameter search for SVC
            logger.info("\nStarting hyperparameter search for SVC...")
            param_grid = {
                'C': [1, 10, 100],
                'gamma': ['scale', 'auto', 1, 10],
                'kernel': ['linear', 'rbf']
            }
            grid_search = GridSearchCV(SVC(probability=True), param_grid, refit=True, verbose=2)
            grid_search.fit(X_train, train_labels)
            logger.info(f"Best hyperparameters found: {grid_search.best_params_}")

            # Train a Supervised Classifier with Scikit-learn
            logger.info("\nTraining classification model with best hyperparameters...")
            classifier = grid_search.best_estimator_
            classifier.fit(X_train, train_labels)
            logger.info("Classifier training complete.")

        else:
            classifier = SVC(probability=True, C=10, gamma=1, kernel='rbf') # Best parameters from last run
            classifier.fit(X_train, train_labels)
            logger.info("Classifier training without hyperparameter tuning completed.")

        # Evaluate the Classifier
        y_pred = classifier.predict(X_test)
        logger.info("\nClassification report:")
        logger.info(classification_report(test_labels, y_pred))

        # Save the models
        ft_model.save("./trained_model/fasttext_model.bin")
        import pickle
        with open("./trained_model/classifier_model.pkl", "wb") as f:
            pickle.dump(classifier, f)
        logger.info("Models saved.")

    except Exception as e:
        logger.error(f"An error occurred during model training: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to train a model for classifying products."
    )
    parser.add_argument("--hyper", required=False, type=int, default=1)
    args = parser.parse_args()
    param1 = args.hyper

    train_model(run_hyperparameter=param1)

