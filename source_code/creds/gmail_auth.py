from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
import pickle

# Quyền truy cập
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Cấu hình OAuth flow
flow = InstalledAppFlow.from_client_secrets_file(
    'credentials2.json', SCOPES)

# Chạy flow và lấy token
creds = flow.run_local_server(port=0)

# Lưu token vào file 
with open('token.json', 'w') as token:
    token.write(creds.to_json())

# Sử dụng token kết nối với Google API
service = build('gmail', 'v1', credentials=creds)
results = service.users().labels().list(userId='me').execute()
labels = results.get('labels', [])
print('Labels:')
for label in labels:
    print(label['name'])
