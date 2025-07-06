import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

import boto3


def validate_email(email: str) -> bool:
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    return bool(email_pattern.match(email))


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    content_type: str


@dataclass
class EmailData:
    subject: str
    body: str
    to: List[str] = field(default_factory=list)
    cc: List[str] = field(default_factory=list)
    bcc: List[str] = field(default_factory=list)
    attachments: List[EmailAttachment] = field(default_factory=list)

    @staticmethod
    def is_valid_email(email):
        return validate_email(email)

    def get_body_as_MIME(self) -> MIMEText:
        return MIMEText(self.body, "plain", "utf-8")

    def __post_init__(self):
        if len(self.to) == 0:
            raise ValueError("You must specify at least to Email!")

        for email_list in [self.to, self.cc, self.bcc]:
            for email in email_list:
                if not self.is_valid_email(email):
                    raise ValueError(f"{email} is not a valid email address!")


@dataclass
class EmailHTMLData(EmailData):
    def get_body_as_MIME(self) -> MIMEText:
        return MIMEText(self.body, "html", "utf-8")


class EmailExecuter(ABC):
    @abstractmethod
    def send(email_data: EmailData):
        raise NotImplementedError("send method not implemented")


class AWSEmailExecuter(EmailExecuter):
    def __init__(
        self,
        sender_email: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        aws_region: str = "ap-southeast-2",
    ):
        self.client = boto3.client(
            "ses",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.sender_email = sender_email
        self.region_name = aws_region

    def send(self, email_data: EmailData):
        msg = MIMEMultipart()
        msg["From"] = self.sender_email
        msg["To"] = ", ".join(email_data.to)
        if email_data.cc:
            msg["Cc"] = ", ".join(email_data.cc)
        if email_data.bcc:
            msg["Bcc"] = ", ".join(email_data.bcc)
        msg["Subject"] = email_data.subject

        msg.attach(email_data.get_body_as_MIME())

        if email_data.attachments:
            for att in email_data.attachments:
                mime_base = MIMEBase("application", "octet-stream")
                mime_base.set_payload(att.content)
                encoders.encode_base64(mime_base)
                mime_base.add_header(
                    "Content-Disposition", f"attachment; filename={att.filename}"
                )
                msg.attach(mime_base)

        raw_message = msg.as_string()

        response = self.client.send_raw_email(
            Source=self.sender_email,
            Destinations=email_data.to + email_data.cc + email_data.bcc,
            RawMessage={"Data": raw_message},
        )
        return response


class EmailService:
    def __init__(self, email_executer: EmailExecuter):
        self.email_executer = email_executer

    def send(self, email_data: EmailData):
        self.email_executer.send(email_data)


if __name__ == "__main__":
    # email_data = EmailData(
    #     **{
    #         "subject": "Test Subject",
    #         "body": "This is a test email",
    #         "to": ["example@gmail.com"],
    #         "attachments": [EmailAttachment("test.txt", b"Hello World!", "text/plain")],
    #     }
    # )

    # email_service = EmailService(AWSEmailExecuter())
    # email_service.send(email_data)

    email_data = EmailHTMLData(
        **{
            "subject": "Test Subject",
            "body": "<h1>This is a test email</h1>",
            "to": ["goricoaico@gmail.com", "goricoaico@gmail.com"],
            "attachments": [EmailAttachment("test.txt", b"Hello World!", "text/plain")],
        }
    )

    email_service = EmailService(
        AWSEmailExecuter(
            "<sender_email>", "<aws_access_key_id>", "<aws_secret_access_key>"
        )
    )
    email_service.send(email_data)
