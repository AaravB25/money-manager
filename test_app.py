import unittest
import json
from app import app
from db import init_db
from seed_user_data import seed_user_exact_data
from calculator import calculate_pay_split

class TestMoneyManager(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        seed_user_exact_data()

    def test_pay_split_calculator(self):
        split = calculate_pay_split(950.0, 10.0, 40.0, 50.0)
        self.assertEqual(split['pay_amount'], 950.0)
        self.assertEqual(split['spending_amount'], 95.0)
        self.assertEqual(split['savings_amount'], 380.0)
        self.assertEqual(split['stock_allocation'], 475.0)

    def test_dashboard_balances(self):
        res = self.client.get('/api/dashboard')
        data = res.get_json()
        self.assertEqual(data['spending_balance'], 108.02)
        self.assertEqual(data['liquid_savings'], 306.34)
        self.assertEqual(data['holdings_count'], 10)

    def test_income_endpoint(self):
        res = self.client.post('/api/income', json={
            'description': 'Fortnightly Paycheck',
            'amount': 950.0,
            'spending_pct': 10.0,
            'savings_pct': 40.0,
            'stock_pct': 50.0
        })
        data = res.get_json()
        self.assertTrue(data['success'])

    def test_spending_sync(self):
        res = self.client.post('/api/expenses/sync', json={
            'new_balance': 108.02,
            'description': 'Spending Balance Sync'
        })
        data = res.get_json()
        self.assertTrue(data['success'])

    def test_inter_account_transfer(self):
        res = self.client.post('/api/transfer', json={
            'from_account': 'savings',
            'to_account': 'stock_budget',
            'amount': 50.0,
            'description': 'Stake transfer'
        })
        data = res.get_json()
        self.assertTrue(data['success'])

    def test_projection_simulation(self):
        res = self.client.post('/api/simulate', json={
            'type': 'projection',
            'pay_amount': 950.0,
            'pay_frequency': 'fortnightly',
            'stock_annual_return': 8.0,
            'savings_annual_return': 4.0,
            'years': 10
        })
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertIn('final_net_worth', data['simulation'])

if __name__ == '__main__':
    unittest.main()
