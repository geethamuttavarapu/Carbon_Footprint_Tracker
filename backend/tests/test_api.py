"""API smoke tests. Run from backend with: python -m unittest discover -s tests."""
import datetime
import os
import tempfile
import unittest

import app as api


class CarbonApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db = api.DB
        api.DB = os.path.join(self.tmp.name, 'test.db')
        api.init_db()
        con = api.db()
        cur = con.execute(
            'INSERT INTO users(name,email,password,email_verified,created_at) VALUES(?,?,?,?,?)',
            ('Test User', 'test@example.com', api.generate_password_hash('TestPassword123'), 1,
             datetime.datetime.utcnow().isoformat()),
        )
        self.user_id = cur.lastrowid
        con.execute('INSERT INTO profiles(user_id,answers) VALUES(?,?)', (self.user_id, '{}'))
        self.token = 'test-token'
        con.execute('INSERT INTO sessions(token,user_id,created_at) VALUES(?,?,?)',
                    (self.token, self.user_id, datetime.datetime.utcnow().isoformat()))
        con.commit()
        con.close()
        self.client = api.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + self.token}

    def tearDown(self):
        api.DB = self.original_db
        self.tmp.cleanup()

    def profile(self):
        return {
            'city': 'Hyderabad', 'home_type': 'Apartment', 'household_size': 2,
            'car_occupants': 1, 'transport_mode': 'Metro', 'cooking_source': 'LPG',
            'diet_type': 'Vegetarian', 'renewable_energy': 'No',
        }

    def daily(self, date=None, **overrides):
        inputs = {
            'travel_mode': 'Metro', 'travel_km': 10, 'meals': 'Vegetarian',
            'electricity_kwh': 4, 'shopping': 'No', 'waste': 'Mostly recycled',
        }
        inputs.update(overrides)
        body = {'inputs': inputs}
        if date:
            body['date'] = date
        return self.client.post('/api/daily', json=body, headers=self.headers)

    def test_profile_and_daily_save_edit(self):
        self.assertEqual(self.client.put('/api/profile', json=self.profile(), headers=self.headers).status_code, 200)
        first = self.daily()
        self.assertEqual(first.status_code, 200)
        self.assertAlmostEqual(first.get_json()['footprint']['categories']['electricity'], 1.454)
        edited = self.daily(travel_km=5)
        self.assertEqual(edited.status_code, 200)
        history = self.client.get('/api/history', headers=self.headers).get_json()['history']
        self.assertEqual(len(history), 1)

    def test_invalid_numeric_input_rejected(self):
        self.assertEqual(self.client.put('/api/profile', json=self.profile(), headers=self.headers).status_code, 200)
        response = self.daily(travel_km='NaN')
        self.assertEqual(response.status_code, 400)

    def test_challenge_join_and_progress(self):
        self.assertEqual(self.client.put('/api/profile', json=self.profile(), headers=self.headers).status_code, 200)
        self.assertEqual(self.client.post('/api/challenges/green-commute/join', headers=self.headers).status_code, 200)
        start = api.local_today() - datetime.timedelta(days=4)
        con = api.db()
        con.execute('UPDATE challenge_participation SET joined_at=? WHERE user_id=? AND challenge_id=?',
                    (start.isoformat() + 'T00:00:00', self.user_id, 'green-commute'))
        con.commit()
        con.close()
        for i in range(5):
            day = (start + datetime.timedelta(days=i)).isoformat()
            response = self.daily(date=day, travel_mode='Bus')
            self.assertEqual(response.status_code, 200)
        challenges = self.client.get('/api/challenges', headers=self.headers).get_json()['challenges']
        green = next(x for x in challenges if x['id'] == 'green-commute')
        self.assertIsNotNone(green['completed_at'])

    def test_account_deletion_revokes_access(self):
        response = self.client.delete('/api/account', json={'confirm': 'DELETE'}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/api/me', headers=self.headers).status_code, 401)


if __name__ == '__main__':
    unittest.main()
