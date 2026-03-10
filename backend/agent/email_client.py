"""
Email client: IMAP connection, fetch, parse.
Supports IMAP IDLE (push) with fallback to polling.
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from email.message import Message
from datetime import datetime, timezone
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


def decode_mime_header(header_value: str) -> str:
    if not header_value:
        return ""
    parts = decode_header(header_value)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded.append(data)
    return ' '.join(decoded)


def extract_body(msg: Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/plain':
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
                    break
            elif ct == 'text/html' and not body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    body = payload.decode(charset, errors='replace')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
    return body


def parse_email_date(msg: Message) -> Optional[str]:
    date_str = msg.get('Date')
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return date_str


class EmailMessage:
    def __init__(self, message_id: str, subject: str, body: str,
                 from_addr: str, date: Optional[str], uid: str):
        self.message_id = message_id
        self.subject = subject
        self.body = body
        self.from_addr = from_addr
        self.date = date
        self.uid = uid

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "subject": self.subject,
            "body": self.body,
            "from_addr": self.from_addr,
            "date": self.date,
            "uid": self.uid
        }


class IMAPClient:
    def __init__(self, host: str, port: int, user: str, password: str,
                 use_ssl: bool = True, folder: str = "INBOX"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.folder = folder
        self._conn: Optional[imaplib.IMAP4_SSL] = None

    def connect(self):
        try:
            if self.use_ssl:
                self._conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self._conn = imaplib.IMAP4(self.host, self.port)
            self._conn.login(self.user, self.password)
            logger.info(f"IMAP connected to {self.host} as {self.user}")
            return True
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            self._conn = None
            return False

    def disconnect(self):
        if self._conn:
            try:
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def fetch_unseen(self, since_uid: Optional[str] = None) -> list[EmailMessage]:
        if not self._conn:
            if not self.connect():
                return []
        messages = []
        try:
            self._conn.select(self.folder, readonly=False)
            if since_uid:
                status, data = self._conn.uid('search', None, f'UID {since_uid}:*')
            else:
                status, data = self._conn.search(None, 'UNSEEN')
            if status != 'OK' or not data[0]:
                return []
            uids = data[0].split()
            for uid_bytes in uids:
                uid = uid_bytes.decode()
                if since_uid and uid == since_uid:
                    continue
                try:
                    if since_uid:
                        status, msg_data = self._conn.uid('fetch', uid, '(RFC822)')
                    else:
                        status, msg_data = self._conn.fetch(uid, '(RFC822)')
                    if status != 'OK' or not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    message_id = msg.get('Message-ID', f'no-id-{uid}')
                    subject = decode_mime_header(msg.get('Subject', ''))
                    body = extract_body(msg)
                    from_addr = decode_mime_header(msg.get('From', ''))
                    date = parse_email_date(msg)
                    messages.append(EmailMessage(
                        message_id=message_id,
                        subject=subject, body=body,
                        from_addr=from_addr, date=date, uid=uid
                    ))
                except Exception as e:
                    logger.error(f"Error parsing email UID {uid}: {e}")
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            self._conn = None
        return messages

    def list_folders(self) -> list[str]:
        if not self._conn:
            if not self.connect():
                return []
        try:
            status, folders = self._conn.list()
            if status == 'OK':
                result = []
                for f in folders:
                    decoded = f.decode() if isinstance(f, bytes) else f
                    parts = decoded.split('"')
                    if len(parts) >= 3:
                        result.append(parts[-2])
                    else:
                        result.append(decoded.split()[-1])
                return result
        except Exception as e:
            logger.error(f"Error listing folders: {e}")
        return []

    def test_connection(self) -> dict:
        try:
            connected = self.connect()
            if connected:
                folders = self.list_folders()
                self.disconnect()
                return {"success": True, "folders": folders}
            return {"success": False, "error": "Login failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
