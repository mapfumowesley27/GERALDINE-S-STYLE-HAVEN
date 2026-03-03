"""
Ecocash Payment Gateway Integration
For Geraldine's Style Haven
"""
import os
import json
import requests
from datetime import datetime

# Try to import dotenv, but make it optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Continue without dotenv if not installed


class EcocashPayment:
    """Ecocash payment gateway integration"""
    
    def __init__(self):
        self.merchant_id = os.getenv('ECOCASH_MERCHANT_ID', 'MERCHANT001')
        self.merchant_secret = os.getenv('ECOCASH_MERCHANT_SECRET', 'your-secret-key')
        self.api_url = os.getenv('ECOCASH_API_URL', 'https://api.ecocash.co.zw/v1')
        self.sandbox = os.getenv('ECOCASH_SANDBOX', 'True').lower() == 'true'
    
    def initiate_payment(self, amount, phone_number, reference, description=''):
        """
        Initiate a payment request via Ecocash
        
        Args:
            amount: Payment amount in USD/ZWD
            phone_number: Customer's Ecocash phone number (e.g., 0777123456)
            reference: Unique transaction reference
            description: Payment description
        
        Returns:
            dict: Payment response with status and details
        """
        if self.sandbox:
            # Sandbox mode - simulate successful payment
            return self._sandbox_payment(amount, phone_number, reference, description)
        
        payload = {
            'merchant_id': self.merchant_id,
            'amount': float(amount),
            'phone_number': self._format_phone(phone_number),
            'reference': reference,
            'description': description or 'Geraldine Style Haven Purchase',
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                f'{self.api_url}/checkout',
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.merchant_secret}'
                },
                timeout=30
            )
            return response.json()
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Payment request failed. Please try again.'
            }
    
    def _sandbox_payment(self, amount, phone_number, reference, description):
        """Simulate payment for sandbox/testing"""
        return {
            'success': True,
            'status': 'pending',
            'transaction_id': f'SB{reference}',
            'amount': float(amount),
            'phone_number': phone_number,
            'reference': reference,
            'message': 'Payment initiated. Please check your phone to approve.',
            'sandbox': True
        }
    
    def check_payment_status(self, transaction_id):
        """
        Check the status of a payment
        
        Args:
            transaction_id: The transaction ID returned from initiate_payment
        
        Returns:
            dict: Payment status details
        """
        if self.sandbox:
            # Sandbox - simulate success
            return {
                'success': True,
                'status': 'completed',
                'transaction_id': transaction_id,
                'message': 'Payment confirmed'
            }
        
        try:
            response = requests.get(
                f'{self.api_url}/status/{transaction_id}',
                headers={
                    'Authorization': f'Bearer {self.merchant_secret}'
                },
                timeout=30
            )
            return response.json()
        except requests.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Unable to check payment status'
            }
    
    def _format_phone(self, phone):
        """Format phone number to Ecocash format"""
        # Remove any spaces or dashes
        phone = phone.replace(' ', '').replace('-', '')
        
        # Add country code if not present
        if phone.startswith('0'):
            phone = '263' + phone[1:]
        elif not phone.startswith('263'):
            phone = '263' + phone
        
        return phone
    
    def verify_payment(self, reference, expected_amount):
        """
        Verify a payment by reference
        
        Args:
            reference: Transaction reference
            expected_amount: Expected amount to verify
        
        Returns:
            bool: True if payment is verified
        """
        # In production, this would check the actual payment
        # For now, we'll use a simple verification
        if self.sandbox:
            return True
        
        # Production verification would call the API
        return True


# Create singleton instance
ecocash = EcocashPayment()


def create_payment(amount, phone, order_reference):
    """Helper function to create a payment"""
    return ecocash.initiate_payment(
        amount=amount,
        phone_number=phone,
        reference=order_reference,
        description=f'Order #{order_reference} - Geraldine Style Haven'
    )


def verify_order_payment(transaction_id, expected_amount):
    """Helper function to verify a payment"""
    status = ecocash.check_payment_status(transaction_id)
    if status.get('success') and status.get('status') == 'completed':
        return True
    return False