from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

DAYS = 7    # Số ngày cần kiểm tra mail gần nhất
MAX_RS_MAIL = 20    # Số mail tối đa đọc được


############################################### Cấu hình OAuth2 #####################################################

# Chỉ cần đọc mail nên cấu hình là readonly
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Đường dẫn đến file chứa thông tin OAuth2. Cái này cần xác thực trên Google Cloud Console sau đó tải file json về rồi cho vào container docker
CREDENTIALS_PATH = '/opt/airflow/creds/credentials2.json'

# Đường dẫn để lưu file token sau khi xác thực thành công. Tiến hành xác thực trước bằng file gmail_auth.py. Sau khi xác thực xong thì tải file token đó về rồi cho vào container
TOKEN_PATH = '/opt/airflow/creds/token.json'



############################################## Hàm xác thực mail #######################################################
def authenticate_gmail():
    creds = None   # Ban đầu khởi tạo là None trước khi gán giá trị từ file token

    # Kiểm tra file token có tồn tại không
    if os.path.exists(TOKEN_PATH):
        # Có file token, vậy là trước đó đã log in gmail thành công
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)   # Sử dụng lại thông tin đã đăng nhập thành công đó
        if (creds) and (creds.expired) and (creds.refresh_token):
            creds.refresh(Request())    # Làm mới token để tiếp tục truy cập mà không cần đăng nhập lại

    # Nếu không có token hoặc token hết hạn, cần xác thực lại
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Nếu không có token thì yêu cầu người dùng đăng nhập
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)   # Mở cửa sổ trình duyệt cho xác thực
        # Lưu token vào file
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds



######################################### Hàm để kiểm tra mail ####################################################
def check_gmail():
    # Thiết lập để ghi lại log
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Lấy token truy cập
    creds = authenticate_gmail()

    try:
        # Khởi tạo Gmail API version 1
        service = build('gmail', 'v1', credentials=creds)

        # Lấy địa chỉ email hiện đang đăng nhập
        profile = service.users().getProfile(userId='me').execute()
        email_address = profile.get('emailAddress')
        logger.info(f"Đang đăng nhập Gmail: {email_address}")

        # Tính thời gian n ngày trước
        x_days_ago = datetime.utcnow() - timedelta(days=DAYS)  # Muốn đọc mail của mấy ngày trước thì chỉnh ở macro
        after_unix = int(x_days_ago.timestamp())
        query = f"after:{after_unix} subject:Important"  # Lọc các email có chủ đề chứa từ "important"

        # Truy vấn Gmail. Chỉ lấy tối đa MAX_RS_MAIL trả về
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query, maxResults=MAX_RS_MAIL).execute()
        messages = results.get('messages', [])

        logger.info(f"Tìm thấy {len(messages)} email trong {DAYS} ngày gần nhất.")
        for msg in messages:
            detail = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = detail.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Không có tiêu đề)')
            snippet = detail.get('snippet', '')
            logger.info(f"---\nTiêu đề: {subject}\nNội dung: {snippet}\n")
    except Exception as e:
        logger.error(f"Lỗi khi truy cập Gmail API: {e}")

# Khởi tạo DAG
with DAG(
    'check_gmail_dag',
    start_date=datetime(2025, 5, 5),
    schedule_interval='@hourly',  # Tự động đọc mail mỗi giờ 1 lần
    catchup=False,  # Không chạy lại những lần bị miss
    tags=["gmail"]
) as dag:
    task = PythonOperator(
        task_id='check_gmail',
        python_callable=check_gmail
    )










    
