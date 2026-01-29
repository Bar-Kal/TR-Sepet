import os
import scipy
import numpy as np
import onnxruntime
from loguru import logger
from transformers import AutoTokenizer

class ProductClassifier:
    """
    A utility class providing common functionalities for scraper,
    such as product classification using a DistilBERT model.
    """

    def __init__(self):
        """
        Initializes the ProductClassifier by loading the DistilBERT model.
        """

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        model_folder_path = os.path.join('sepet_app', "models", "trained_model_distilbert")

        if os.path.exists(model_folder_path):
            try:
                # The training script used '0' for non-food and '1' for food.
                self.id2label = {0: False, 1: True}
                self.session = onnxruntime.InferenceSession(model_folder_path + "\\" + "model.onnx")
                self.transformer_tokenizer = AutoTokenizer.from_pretrained(model_folder_path)
                logger.info("Model and tokenizer loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load DistilBERT model: {e}")
        else:
            logger.warning(f"DistilBERT model not found at {model_folder_path}. Prediction will default to True.")

    def predict(self, text: str):
        """
        Predicts if an article is a food or non-food product.

        Args:
            text (str): The text to classify.

        Returns:
            dict: {label, confidence}.
        """
        if self.session and self.transformer_tokenizer:
            try:
                # Tokenize the input text
                inputs = self.transformer_tokenizer(text, return_tensors="np", truncation=True, padding=True)
                # Prepare the inputs for ONNX Runtime
                # The input names must match the names the model was exported with.
                # For Hugging Face models, these are typically 'input_ids' and 'attention_mask'.
                ort_inputs = {
                    "input_ids": inputs["input_ids"],
                    "attention_mask": inputs["attention_mask"],
                }

                # Run inference
                ort_outs = self.session.run(None, ort_inputs)

                # The output is typically a list of numpy arrays. For sequence classification,
                # it's usually one array of shape (batch_size, num_labels).
                logits = ort_outs[0]

                # Apply softmax to get probabilities
                probabilities = scipy.special.softmax(logits, axis=1)[0]

                # Get the corresponding label and confidence score
                predicted_class_id = np.argmax(probabilities)
                label = self.id2label[predicted_class_id]
                score = probabilities[predicted_class_id]

                return {"label": label, "confidence": float(score)}
            except Exception as e:
                logger.warning(f"DistilBERT prediction failed: {e}")

        # Default to True if model fails or is missing (safest for a food scraper)
        return {"label": 1, "confidence": float(0.0)}
