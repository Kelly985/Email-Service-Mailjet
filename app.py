from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import base64

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from Netlify

# Load environment variables
load_dotenv()
# Mailjet API Configuration
MAILJET_API_KEY = os.getenv("MAILJET_API_KEY")
MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY")
SALES_EMAIL = os.getenv("SALES_EMAIL")
FROM_EMAIL = os.getenv("FROM_EMAIL")

def send_email(to_email, subject, body):
    """Helper function to send email via Mailjet HTTP API"""
    try:
        # Mailjet API endpoint
        url = "https://api.mailjet.com/v3.1/send"
        
        # Create authentication header
        auth_string = f"{MAILJET_API_KEY}:{MAILJET_SECRET_KEY}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Basic {auth_b64}'
        }
        
        # Email payload
        payload = {
            "Messages": [
                {
                    "From": {
                        "Email": FROM_EMAIL,
                        "Name": "Healthline Naturals"
                    },
                    "To": [
                        {
                            "Email": to_email
                        }
                    ],
                    "Subject": subject,
                    "HTMLPart": body
                }
            ]
        }
        
        # Send email via HTTP API
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            print(f"Email sent successfully to {to_email}")
            return True
        else:
            print(f"Error sending email to {to_email}: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending email to {to_email}: {str(e)}")
        return False

@app.route('/send-order-emails', methods=['POST'])
def send_order_emails():
    """Endpoint to send order confirmation emails"""
    try:
        data = request.get_json()
        required_fields = [
            'order_id', 'customer_email', 'customer_name', 'customer_phone',
            'shipping_option', 'payment_method',
            'order_details', 'subtotal', 'delivery_fee', 'tax', 'order_total'
        ]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Extract data
        order_id = data['order_id']
        customer_email = data['customer_email']
        customer_name = data['customer_name']
        customer_phone = data['customer_phone']
        shipping_option = data['shipping_option']
        shipping_address = data.get('shipping_address', 'Store Pickup')  # Default to 'Store Pickup' if missing
        payment_method = data['payment_method']
        order_details = data['order_details']
        subtotal = data['subtotal']
        delivery_fee = data['delivery_fee']
        tax = data['tax']
        order_total = data['order_total']

        # Validate order_details is a list
        if not isinstance(order_details, list):
            return jsonify({"error": "order_details must be a list"}), 400

        # Format order items for email
        items_formatted = "\n".join([
            f"{item['name']} x {item['quantity']} @ Ksh {item['price']:.2f} = Ksh {item['total']:.2f}"
            for item in order_details
        ])

        # Format shipping info based on shipping_option
        shipping_info = f"Shipping: {shipping_option.title()}"
        if shipping_option == 'delivery' and shipping_address != 'Store Pickup':
            shipping_info += f" ({shipping_address})"
        else:
            shipping_info += " (Store Pickup)"

        # Customer email
        customer_subject = f"Order Confirmation - Order #{order_id}"
        customer_body = f"""
Dear {customer_name},<br><br>

Thank you for your order with Healthline Naturals! Below are your order details:<br><br>

<strong>Order ID:</strong> {order_id}<br>
<strong>Customer Name:</strong> {customer_name}<br>
<strong>Email:</strong> {customer_email}<br>
<strong>Phone:</strong> {customer_phone}<br>
<strong>{shipping_info}</strong><br>
<strong>Payment Method:</strong> {payment_method}<br><br>

<strong>Order Items:</strong><br>
{items_formatted.replace(chr(10), '<br>')}<br><br>

<strong>Summary:</strong><br>
- Subtotal: Ksh {subtotal:.2f}<br>
- Delivery Fee: Ksh {delivery_fee:.2f}<br>
- Tax (16%): Ksh {tax:.2f}<br>
- Total: Ksh {order_total:.2f}<br><br>

We'll process your order soon. For any queries, contact us at {FROM_EMAIL}.<br><br>

Best regards,<br>
Healthline Naturals
"""
        customer_success = send_email(customer_email, customer_subject, customer_body)

        # Sales team email
        sales_subject = f"New Order Notification - Order #{order_id}"
        sales_body = f"""
<strong>New order received!</strong><br><br>

<strong>Order ID:</strong> {order_id}<br>
<strong>Customer Name:</strong> {customer_name}<br>
<strong>Email:</strong> {customer_email}<br>
<strong>Phone:</strong> {customer_phone}<br>
<strong>{shipping_info}</strong><br>
<strong>Payment Method:</strong> {payment_method}<br><br>

<strong>Order Items:</strong><br>
{items_formatted.replace(chr(10), '<br>')}<br><br>

<strong>Summary:</strong><br>
- Subtotal: Ksh {subtotal:.2f}<br>
- Delivery Fee: Ksh {delivery_fee:.2f}<br>
- Tax (16%): Ksh {tax:.2f}<br>
- Total: Ksh {order_total:.2f}<br><br>

Please process the order promptly.<br><br>

Healthline Naturals
"""
        sales_success = send_email(SALES_EMAIL, sales_subject, sales_body)

        if customer_success and sales_success:
            return jsonify({"message": "Emails sent successfully"}), 200
        else:
            return jsonify({"error": "Failed to send one or both emails"}), 500

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))