# Stegano

Stegano is a web application for encoding and decoding messages within images using steganography techniques. The project is implemented using Flask for the backend and HTML for the frontend, with some Python libraries for the steganography operations.

## Features

- **Encode Messages:** Users can encode secret messages into images.
- **Decode Messages:** Users can decode messages from images.
- **Last Encoded/Decoded Images:** View the last encoded or decoded image directly.

## Implementation

The application is built with the following technologies:
- **Flask:** A lightweight WSGI web application framework in Python.
- **Stegano Library:** Used for hiding and revealing messages within images.
- **HTML/CSS:** For the frontend interface.

## Encoding a Message

1. Upload an image and enter the message to hide.
2. Click "Send" to encode the message into the image.
3. The encoded image will be saved and displayed.

## Decoding a Message

1. Upload an image with an encoded message.
2. Click "Send" to reveal the hidden message.
3. The decoded message will be displayed.
