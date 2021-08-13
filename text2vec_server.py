from flask import Flask, request, Response, jsonify
from sentence_transformers import SentenceTransformer
import tensorflow_hub as hub
import tensorflow_text
import tensorflow as tf


hub_embed = hub.load("https://tfhub.dev/google/universal-sentence-encoder-multilingual-large/3")
bert_embed = SentenceTransformer('dbmdz/bert-base-turkish-cased', device="cpu")
app = Flask(__name__)

@app.route("/", methods=["POST"])
def t2v():
    vec_type = request.form.get('vec_type')
    text = request.form.get('text')
    
    if text == "":
        return "Empty string.", 406

    if vec_type == "bert":
        resp = bert_embed.encode(text).tolist()
    elif vec_type == "google_use":
        resp = hub_embed(text).numpy().tolist()[0]
    else:
        return "Wrong vector type.", 406

    return jsonify(resp)

if __name__ == "__main__":
    app.run()
