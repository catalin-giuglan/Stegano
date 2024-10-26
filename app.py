from flask import Flask, request, render_template, url_for, flash, redirect
from stegano import lsb

import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('./index.html')

@app.route('/image/encode',methods = ["GET","POST"])
def img_encode():
    if request.method == "POST":
        file = request.files["pic"]
        hided_message = request.form["msg"]
        secret = lsb.hide(file,hided_message)
        secret.save("./static/img/enc_image.png")
        return render_template("./success.html",message="Operation was successful")
    return render_template("./img_enc.html")

@app.route('/image/last/encoded')
def img_last_encode():
    return render_template("./last_encoded.html")

@app.route('/image/decode', methods = ["GET","POST"])
def img_decode():
    if request.method == "POST":
        file = request.files["pic"]
        msg = lsb.reveal(file)
        return render_template("./success.html",message = msg)
    return render_template("./img_dec.html")

@app.route('/image/last/decoded')
def img_last_decode():
        msg = lsb.reveal("./static/img/enc_image.png")
        return render_template("./last_decoded.html", message = msg)