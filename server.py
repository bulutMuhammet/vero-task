from flask import Flask, request, jsonify
import requests
import pandas as pd
from io import StringIO

app = Flask(__name__)

LOGIN_URL = "https://api.baubuddy.de/index.php/login"
VEHICLE_URL = "https://api.baubuddy.de/dev/index.php/v1/vehicles/select/active"
LABEL_URL = "https://api.baubuddy.de/dev/index.php/v1/labels/"

AUTH = {
    "Authorization": "Basic QVBJX0V4cGxvcmVyOjEyMzQ1NmlzQUxhbWVQYXNz",
    "Content-Type": "application/json"
}
LOGIN_PAYLOAD = {
    "username": "365",
    "password": "1"
}


def get_access_token():
    response = requests.post(LOGIN_URL, json=LOGIN_PAYLOAD, headers=AUTH)
    response_data = response.json()
    return response_data["oauth"]["access_token"]


def fetch_data(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(VEHICLE_URL, headers=headers)
    return response.json()


def fetch_labels(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(LABEL_URL, headers=headers)
    return response.json()


def fetch_label_color(label_ids, labels):
    color_map = {}
    for label in labels:
        color_map[label['id']] = label.get('colorCode', '#FFFFFF')

    return [color_map.get(int(label_id), '#FFFFFF') for label_id in label_ids if label_id.isdigit()]


@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Invalid file type"}), 400

    csv_data = StringIO(file.read().decode("utf-8"))
    df = pd.read_csv(csv_data, delimiter=';')

    access_token = get_access_token()
    api_data = fetch_data(access_token)
    labels = fetch_labels(access_token)

    api_df = pd.json_normalize(api_data)
    api_df = api_df[api_df['hu'].notna()]

    combined_df = pd.merge(df, api_df, how='inner', left_on='kurzname', right_on='kurzname')

    result = combined_df.to_dict(orient='records')
    for record in result:
        if record.get('labelIds'):
            record['labelColors'] = fetch_label_color(record['labelIds'].split(','), labels)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
