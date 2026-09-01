"""
TradeFlow Load Testing Framework (Locust)

This module defines user behaviors to load test the TradeFlow API.
It simulates concurrent traders interacting with the system: logging in,
viewing market data, and placing orders.

To run:
1. Ensure the backend server is running on localhost:8001
2. Run command: locust -f load_tests/locustfile.py
3. Open http://localhost:8089 in your browser to configure and start the test
"""

import time
import random
from locust import HttpUser, task, between, events

class TradeFlowUser(HttpUser):
    # Wait between 1 and 3 seconds between tasks
    wait_time = between(1.0, 3.0)
    
    # The default host if not specified in UI
    host = "http://localhost:8001"

    def on_start(self):
        """
        Setup run once per user instance. 
        Registers a new unique user and logs in to get a JWT token.
        """
        self.username = f"locust_{int(time.time())}_{random.randint(1000, 99999)}"
        self.password = "LoadTest123!"
        
        # 1. Register
        with self.client.post(
            "/api/v1/auth/register",
            json={"username": self.username, "password": self.password},
            catch_response=True,
            name="Auth: Register"
        ) as response:
            if response.status_code not in (200, 400):
                response.failure(f"Failed to register: {response.text}")

        # 2. Login to get token
        with self.client.post(
            "/api/v1/auth/token",
            data={"username": self.username, "password": self.password},
            catch_response=True,
            name="Auth: Login"
        ) as response:
            if response.status_code == 200:
                token = response.json()["access_token"]
                # Apply token to all subsequent requests for this user
                self.client.headers.update({"Authorization": f"Bearer {token}"})
            else:
                response.failure("Failed to login.")

    @task(3)
    def view_market_data(self):
        """Weight 3: Simulates a user looking at bond lists and order books."""
        # Get all bonds
        self.client.get("/api/v1/bonds/", name="Market: Get All Bonds")
        
        # Randomly inspect an order book (Assuming seed bond IDs 1 to 7)
        bond_id = random.randint(1, 7)
        self.client.get(f"/api/v1/bonds/{bond_id}/order-book", name="Market: Get Order Book")

    @task(1)
    def place_order(self):
        """Weight 1: Simulates placing a trade order."""
        bond_id = random.randint(1, 7)
        side = random.choice(["BUY", "SELL"])
        
        # Randomize price around par (100.0)
        price = round(random.uniform(95.0, 105.0), 3)
        qty = random.choice([100, 500, 1000, 2000])

        self.client.post(
            "/api/v1/orders/",
            json={
                "bond_id": bond_id,
                "side": side,
                "type": "LIMIT",
                "price": price,
                "quantity": qty
            },
            name="Trading: Place Limit Order"
        )

    @task(2)
    def check_portfolio(self):
        """Weight 2: Simulates checking open orders, trades blotter, and analytics."""
        self.client.get("/api/v1/orders/open", name="Portfolio: Open Orders")
        self.client.get("/api/v1/trades/", name="Portfolio: Trade Blotter")
        self.client.get("/api/v1/analytics/", name="Portfolio: Analytics")
