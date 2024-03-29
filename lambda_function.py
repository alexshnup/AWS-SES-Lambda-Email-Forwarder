import boto3
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from email import encoders

s3 = boto3.client('s3')
ses = boto3.client('ses')

def lambda_handler(event, context):
    print("received event=", event)
    # Retrieve email details from the SES event
    for record in event['Records']:
        bucket_name = "your-backet-email-ses"
        object_key = record['ses']['mail']['messageId']
        
        print("bucket_name=", bucket_name)
        print("object_key=", object_key)
        
        # Fetch the email from S3
        email_object = s3.get_object(Bucket=bucket_name, Key=object_key)
        email_content = email_object['Body'].read()
        
        # Parse the email content
        msg = email.message_from_bytes(email_content)
        
        # Prepare the message to send
        forward_msg = MIMEMultipart()
        forward_from = record['ses']['mail']['destination'][0]  # The email you're forwarding from
        forward_to = 'alexshnup@gmail.com'       # The destination email
        forward_msg['From'] = forward_from
        forward_msg['To'] = forward_to
        forward_source = record['ses']['mail']['source'] # The original sender
        forward_msg['Subject'] = "Fwd: "+ forward_source + " " + msg['Subject']
        
        no_need_text_plain = False
        # Check if the message is multipart
        if msg.is_multipart():
            
            for part in msg.walk():
                if part.get_content_type() in ['text/html']:
                    no_need_text_plain = True
            for part in msg.walk():
                print("Processing part, ContentType=", part.get_content_type())
                if part.get_content_type() in ['text/html']:
                    part_payload = part.get_payload(decode=True)  # Decode binary string
                    charset = part.get_content_charset() or 'utf-8'  # Default charset to utf-8 if not specified
                    # Correctly create the MIMEText part
                    mime_part = MIMEText(part_payload.decode(charset), part.get_content_subtype(), charset)
                    forward_msg.attach(mime_part)
                # Skip container multipart types
                if part.get_content_maintype() == 'multipart':
                    continue
                elif not no_need_text_plain and part.get_content_maintype() == 'text':
                    # Handle text/plain and text/html
                    forward_msg.attach(MIMEText(part.get_payload(decode=True), part.get_content_subtype(), part.get_content_charset()))
                elif part.get_content_maintype() == 'image':
                    # Handle image attachments
                    img = MIMEImage(part.get_payload(decode=True), part.get_content_subtype())
                    img.add_header('Content-Disposition', 'attachment', filename=part.get_filename())
                    forward_msg.attach(img)
                elif part.get_content_maintype() == 'application':
                    # Handle generic application/octet-stream types and others
                    app = MIMEApplication(part.get_payload(decode=True), part.get_content_subtype())
                    app.add_header('Content-Disposition', 'attachment', filename=part.get_filename())
                    encoders.encode_base64(app)
                    forward_msg.attach(app)
        else:
            print("Procession as a not multipart")
            # For non-multipart messages, decode and attach as plain text
            text_payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            mime_part = MIMEText(text_payload.decode(charset), 'plain', charset)
            forward_msg.attach(mime_part)
        
        # Send the email through SES
        try:
            response = ses.send_raw_email(
                Source=forward_from,
                Destinations=[forward_to],
                RawMessage={'Data': forward_msg.as_string()}
            )
            print(response)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
